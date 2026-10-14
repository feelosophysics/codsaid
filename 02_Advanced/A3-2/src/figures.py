"""보고서 그림. 운영체제마다 한글 글꼴이 달라 그림 안의 글자는 영어로 쓰고, 설명은 보고서에 한글로 단다."""
import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .pipeline import id_color  # noqa: E402

SCEN_EN = {"single": "single object", "crossing": "two objects crossing", "crossing_same": "crossing, same clothes",
           "pause": "stop / reappear", "lighting": "lighting change", "target": "registered object"}
KIND_EN = {"pass": "pass", "bounce": "bounce", "speed": "speed diff", "one_stops": "one stops", "offset": "offset",
           "diagonal": "diagonal X", "stop_pass": "stop+pass", "stop_bounce": "stop+bounce", "group": "walk together",
           "turn": "turn"}
VAR_EN = {"baseline": "greedy + centroid", "hungarian": "Hungarian", "iou": "IoU cost", "kalman": "Kalman",
          "kalman_hungarian": "Kalman + Hungarian", "appearance": "color histogram", "kalman_appearance":
          "Kalman + color", "all_rules": "all rules + long memory"}
C = {"orb": "#2563c9", "sift": "#c8402f", "A": "#2563c9", "B": "#c8402f"}
LR_COLORS = ["#7b3fb5", "#2563c9", "#23824a", "#d07a12"]


def rgb(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image


def save(fig, path):
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def hex_bgr(tid):
    b, g, r = id_color(tid)
    return (r / 255, g / 255, b / 255)


def draw_tracks(frame, tracks, trails=None, gt=None):
    """추적 결과를 영상에 그린다 (그림용, pipeline.draw와 같은 모양)."""
    out = frame.copy()
    if gt:
        for o in gt:
            if o.get("bbox"):
                x, y, w, h = o["bbox"]
                cv2.rectangle(out, (x, y), (x + w, y + h), (255, 255, 0), 1)
                cv2.putText(out, o["id"], (x + w + 2, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, cv2.LINE_AA)
    for tid, pts in (trails or {}).items():
        if len(pts) > 1:
            cv2.polylines(out, [np.int32(pts)], False, (40, 40, 230), 2, cv2.LINE_AA)
    for tid, (x, y, w, h), c in tracks:
        cv2.rectangle(out, (x, y), (x + w, y + h), (60, 200, 60), 2)
        cv2.rectangle(out, (x, y - 14), (x + 40, y), id_color(tid), -1)
        cv2.putText(out, f"ID:{tid}", (x + 2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def scenarios_overview(frames, path):
    """frames: [(이름, 프레임, 정답)]"""
    fig, axes = plt.subplots(2, 3, figsize=(15, 6))
    for ax, (name, frame, gt) in zip(axes.flat, frames):
        ax.imshow(rgb(draw_tracks(frame, [], gt=gt)))
        ax.set_title(SCEN_EN.get(name, name), fontsize=11)
        ax.axis("off")
    fig.suptitle("Synthetic test videos (640x360, 30 fps) with ground-truth boxes (cyan)", fontsize=12)
    fig.tight_layout()
    return save(fig, path)


def pipeline_stages(frame, raw, cleaned, annotated, path):
    fig, axes = plt.subplots(1, 4, figsize=(18, 3.4))
    titles = ["1 input frame", "2 MOG2 raw (white=fg, gray=shadow)", "3 shadow removed + open/close", "4 boxes, IDs, trails"]
    for ax, img, t in zip(axes, [frame, raw, cleaned, annotated], titles):
        ax.imshow(rgb(img), cmap="gray", vmin=0, vmax=255)
        ax.set_title(t, fontsize=10)
        ax.axis("off")
    fig.tight_layout()
    return save(fig, path)


def id_timeline(gt, variants, path):
    """variants: [(이름, seq dict)]. 정답 객체마다 프레임별 추적 ID를 색 띠로 그린다."""
    objs = list(variants[0][1].keys())
    n = gt["frames"]
    fig, ax = plt.subplots(figsize=(15, 0.9 + 0.55 * len(variants) * len(objs)))
    y = 0
    yt, yl = [], []
    for name, seq in variants:
        for o in objs:
            s = seq[o]
            i = 0
            while i < n:
                tid = s[i]
                j = i
                while j < n and s[j] == tid:
                    j += 1
                if tid is not None:
                    color = (0.75, 0.75, 0.75) if tid == -1 else hex_bgr(tid)
                    ax.barh(y, j - i, left=i, height=0.8, color=color, edgecolor="none")
                    if tid != -1 and j - i > 18:
                        ax.text((i + j) / 2, y, str(tid), ha="center", va="center", fontsize=7)
                i = j
            yt.append(y)
            yl.append(f"{name}: {o}")
            y += 1
        y += 0.6
    for e in gt["events"]:
        ax.axvspan(e["start"], e["end"], color="#000000", alpha=0.04 if e["index"] % 2 else 0.0)
        ax.text((e["start"] + e["end"]) / 2, y - 0.1, KIND_EN.get(e["kind"], e["kind"]), ha="center", va="top",
                fontsize=7)
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=8)
    ax.set_ylim(y + 0.3, -0.7)
    ax.set_xlim(0, n)
    ax.set_xlabel("frame (gray = merged blob, blank = no match)")
    ax.set_title(f"Track ID attached to each person over time ({gt['video']})", fontsize=11)
    return save(fig, path)


def crossing_frames(panels, path):
    """panels: [(행 이름, [(제목, 그림)...])]"""
    rows = len(panels)
    cols = max(len(p[1]) for p in panels)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.3, rows * 2.2))
    axes = np.atleast_2d(axes)
    for r, (rowname, items) in enumerate(panels):
        for c in range(cols):
            ax = axes[r, c]
            ax.axis("off")
            if c < len(items):
                t, img = items[c]
                ax.imshow(rgb(img))
                ax.set_title(t, fontsize=8)
        axes[r, 0].text(-0.04, 0.5, rowname, transform=axes[r, 0].transAxes, ha="right", va="center", fontsize=9,
                        rotation=90)
    fig.tight_layout()
    return save(fig, path)


def xt_plot(gt, cases, path):
    """cases: [(제목, 이벤트, {변형: outputs})]. 가로 위치-시간 그래프. 선=정답, 점=추적(ID 색)."""
    fig, axes = plt.subplots(len(cases), len(cases[0][2]), figsize=(13, 3.6 * len(cases)), squeeze=False)
    for r, (title, ev, outs) in enumerate(cases):
        s, e = ev["start"], ev["end"]
        for c, (vname, outputs) in enumerate(outs.items()):
            ax = axes[r, c]
            for oid in ("A", "B"):
                xs = [(i, o["bbox"][0] + o["bbox"][2] / 2) for i in range(s, e + 1) for o in gt["gt"][i]
                      if o["id"] == oid and o.get("bbox")]
                if xs:
                    ax.plot(*zip(*xs), "-", color=C[oid], lw=6, alpha=0.25, label=f"GT {oid}")
            for i in range(s, e + 1):
                for tid, (x, y, w, h), cen in outputs[i]:
                    ax.plot(i, cen[0], "o", ms=3, color=hex_bgr(tid))
            ax.set_title(f"{title} — {VAR_EN.get(vname, vname)}", fontsize=10)
            ax.set_xlabel("frame")
            ax.set_ylabel("x (px)")
            if r == 0 and c == 0:
                ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    return save(fig, path)


def rules_heatmap(variants, path, scenarios=("crossing", "crossing_same")):
    keys = list(variants.keys())
    fig, axes = plt.subplots(1, len(scenarios), figsize=(16, 4.6))
    for ax, sc in zip(np.atleast_1d(axes), scenarios):
        ev = variants[keys[0]]["scenarios"][sc]["by_event"]
        m = np.array([[x["switches"] for x in variants[k]["scenarios"][sc]["by_event"]] for k in keys])
        ax.imshow(m, cmap="Reds", vmin=0, vmax=2, aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, int(m[i, j]), ha="center", va="center", fontsize=9, color="white" if m[i, j] >= 2 else "black")
        ax.set_xticks(range(len(ev)))
        ax.set_xticklabels([KIND_EN.get(x["kind"], x["kind"]) for x in ev], rotation=40, ha="right", fontsize=8)
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels([f"{VAR_EN[k]} ({m[i].sum()})" for i, k in enumerate(keys)], fontsize=8)
        ax.set_title(f"ID switches per event — {SCEN_EN[sc]}", fontsize=10)
    fig.tight_layout()
    return save(fig, path)


def param_sweeps(sweeps, path):
    """sweeps: {(파라미터, 분할): rows}"""
    params = sorted({p for p, _ in sweeps})
    fig, axes = plt.subplots(1, len(params), figsize=(6.5 * len(params), 3.8))
    for ax, p in zip(np.atleast_1d(axes), params):
        for split, ls in (("dev", "--"), ("test", "-")):
            rows = sweeps.get((p, split))
            if not rows:
                continue
            x = [r["value"] for r in rows]
            sw = [r["crossing"]["switches"] + r["crossing_same"]["switches"] for r in rows]
            fl = [sum(r[s]["fails"] for s in ("single", "pause", "lighting", "crossing")) for r in rows]
            fi = [sum(r[s]["false_ids"] for s in ("single", "pause", "lighting", "crossing")) for r in rows]
            ax.plot(x, sw, ls, marker="o", color="#c8402f", label=f"ID switches, crossing x2 ({split})")
            ax.plot(x, fl, ls, marker="s", color="#2563c9", label=f"track failures, all ({split})")
            ax.plot(x, fi, ls, marker="^", color="#888888", label=f"false IDs ({split})")
        ax.set_xlabel(p)
        ax.set_ylabel("count")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    return save(fig, path)


def learning_rate(bg_summary, pause_gt, light_gt, path):
    keys = [k for k in bg_summary if k.startswith("mog2_") and "noshadow" not in k]
    fig = plt.figure(figsize=(16, 8.5))
    gs = fig.add_gridspec(2, 3)
    ax1 = fig.add_subplot(gs[0, :2])
    for k, c in zip(keys, LR_COLORS):
        ax1.plot(bg_summary[k]["pause_recall_series"], color=c, lw=1, label=f"lr={bg_summary[k]['learning_rate']:g}")
    for e in pause_gt["events"]:
        if "resume" in e:
            ax1.axvspan(e["start"], e["resume"], color="#e4a74a", alpha=0.25)
    ax1.set_title("Stop video: recall of the person's pixels (orange = person standing still)", fontsize=10)
    ax1.set_ylabel("foreground recall")
    ax1.set_xlabel("frame")
    ax1.legend(fontsize=8, ncol=4)
    ax2 = fig.add_subplot(gs[1, :2])
    for k, c in zip(keys, LR_COLORS):
        ax2.plot(100 * np.array(bg_summary[k]["lighting_fp_series"]), color=c, lw=1, label=f"lr={bg_summary[k]['learning_rate']:g}")
    for e in light_gt["events"]:
        ax2.axvline(e["start"], color="k", lw=0.8, ls=":")
        ax2.text(e["start"] + 3, 92, e["kind"], fontsize=8)
    ax2.set_ylim(0, 100)
    ax2.set_title("Lighting video: false-foreground area (% of frame)", fontsize=10)
    ax2.set_ylabel("false fg %")
    ax2.set_xlabel("frame")
    ax3 = fig.add_subplot(gs[:, 2])
    for k, c in zip(keys, LR_COLORS):
        r = bg_summary[k]
        absorb = [s["absorbed_after"] for s in r["pause"]]
        stop_long = next((s for s in r["pause"] if s["stop_frames"] >= 150), r["pause"][-1])
        a = stop_long["absorbed_after"] if stop_long["absorbed_after"] is not None else stop_long["stop_frames"]
        rec = [ev["recovery"] if ev["recovery"] is not None else 75 for ev in r["lighting"] if ev["kind"] in ("on", "off")]
        capped = stop_long["absorbed_after"] is None or any(ev["recovery"] is None for ev in r["lighting"]
                                                             if ev["kind"] in ("on", "off"))
        ax3.scatter(np.mean(rec), a, s=120, color=c, zorder=3, facecolors="none" if capped else c, linewidths=2)
        ax3.annotate(f"lr={r['learning_rate']:g}", (np.mean(rec), a), textcoords="offset points", xytext=(8, 4), fontsize=9)
        del absorb
    ax3.set_xlabel("frames to recover after light on/off, mean (lower = better)")
    ax3.set_ylabel("frames until a person standing 5 s vanishes (higher = better)")
    ax3.text(0.02, 0.02, "hollow = capped (not recovered in 75 f / never vanished)", transform=ax3.transAxes, fontsize=8)
    ax3.set_title("The trade-off: slow vs fast background update", fontsize=10)
    ax3.grid(alpha=0.3)
    fig.tight_layout()
    return save(fig, path)


def bg_masks(samples, columns, path):
    """samples: [(행 제목, dict)] dict에는 frame, truth, 설정별 마스크가 있다."""
    rows = len(samples)
    cols = 2 + len(columns)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 1.55))
    axes = np.atleast_2d(axes)
    for r, (title, d) in enumerate(samples):
        ims = [("frame", d["frame"]), ("ground truth", d["truth"])] + [(lab, d[k]) for k, lab in columns]
        for c, (t, img) in enumerate(ims):
            ax = axes[r, c]
            ax.imshow(rgb(img), cmap="gray", vmin=0, vmax=255)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(t, fontsize=8)
        axes[r, 0].set_ylabel(title, fontsize=8)
    fig.tight_layout()
    return save(fig, path)


def feature_curves(sweeps, path):
    names = [("roll", "in-plane rotation (deg)"), ("yaw", "3D tilt / viewpoint (deg)"), ("occlusion", "occluded fraction"),
             ("scale", "scale (1.0 = 320 px wide)"), ("brightness", "brightness factor"), ("blur", "Gaussian blur sigma")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for ax, (k, lab) in zip(axes.flat, names):
        for m in sweeps:
            pts = sweeps[m][k]
            x = [p["value"] for p in pts]
            ax.plot(x, [p["match_rate"] for p in pts], "-o", color=C[m], ms=4, label=f"{m.upper()} match rate")
            ax.plot(x, [p["found_rate"] for p in pts], "--", color=C[m], alpha=0.6, label=f"{m.upper()} found")
        ax.set_xlabel(lab)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Feature matching: correct matches / reference keypoints (solid), target localized (dashed)", fontsize=11)
    fig.tight_layout()
    return save(fig, path)


def feature_examples(items, path):
    """items: [(제목, drawMatches 그림)]"""
    fig, axes = plt.subplots(len(items), 1, figsize=(12, 3.3 * len(items)))
    for ax, (t, img) in zip(np.atleast_1d(axes), items):
        ax.imshow(rgb(img))
        ax.set_title(t, fontsize=10)
        ax.axis("off")
    fig.tight_layout()
    return save(fig, path)


def generalization(gen, thumbs, path):
    fig = plt.figure(figsize=(14, 4.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1])
    sub = gs[0].subgridspec(1, len(thumbs))
    for i, (name, img) in enumerate(thumbs):
        ax = fig.add_subplot(sub[0, i])
        ax.imshow(rgb(img))
        ax.set_title(name, fontsize=8)
        ax.axis("off")
    ax = fig.add_subplot(gs[1])
    cases = [r["case"] for r in gen["orb"]]
    x = np.arange(len(cases))
    for k, m in enumerate(gen):
        ax.bar(x + (k - 0.5) * 0.38, [r["found_rate"] for r in gen[m]], 0.36, color=C[m], label=m.upper())
        for xi, r in zip(x, gen[m]):
            ax.text(xi + (k - 0.5) * 0.38, r["found_rate"] + 0.02, f"{r['n_inliers']:.0f}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([f"case {i + 1}" for i in x], fontsize=8)
    ax.set_ylabel("'TARGET DETECTED' rate (numbers = mean inliers)")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return save(fig, path)


def target_timeline(tv, gt, path):
    fig, ax = plt.subplots(figsize=(15, 3.8))
    for m in tv["inliers"]:
        ax.plot(tv["inliers"][m], color=C[m], lw=1.2, label=f"{m.upper()} inliers")
        f = np.array(tv["found"][m])
        ax.scatter(np.nonzero(f)[0], np.full(f.sum(), -6 if m == "orb" else -12), s=4, color=C[m])
    for e in gt["events"]:
        ax.axvspan(e["start"], e["end"], color="#000000", alpha=0.05 if e["index"] % 2 else 0.0)
        ax.text((e["start"] + e["end"]) / 2, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] > 0 else 50, e["kind"],
                ha="center", fontsize=8)
    ax.axhline(12, color="k", ls=":", lw=0.8)
    ax.set_xlabel("frame (dots below 0 = TARGET DETECTED)")
    ax.set_ylabel("RANSAC inliers")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Registered object in video: inliers per frame (threshold 12)", fontsize=11)
    return save(fig, path)


def hungarian_fig(h, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
    n = [r["n"] for r in h["by_n"]]
    axes[0].bar(n, [100 * r["greedy_suboptimal"] for r in h["by_n"]], color="#c8402f")
    for x, r in zip(n, h["by_n"]):
        axes[0].text(x, 100 * r["greedy_suboptimal"] + 1, f"+{r['mean_excess_pct']:.0f}%", ha="center", fontsize=8)
    axes[0].set_xlabel("matrix size n x n (uniform random costs)")
    axes[0].set_ylabel("% of matrices where greedy is not optimal")
    axes[0].set_title("Greedy vs optimal (labels = mean extra cost when worse)", fontsize=10)
    t = h["timing"]
    axes[1].loglog([r["n"] for r in t], [r["hungarian_ms"] for r in t], "-o", label="Hungarian (NumPy)")
    axes[1].loglog([r["n"] for r in t], [r["greedy_ms"] for r in t], "-s", label="greedy")
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("ms per assignment")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    return save(fig, path)


def zone_fig(frame, zone, n_frames, path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 3.6), gridspec_kw={"width_ratios": [1, 1.6]})
    axes[0].imshow(rgb(frame))
    axes[0].set_title("Intrusion zone (bonus 2)", fontsize=10)
    axes[0].axis("off")
    ax = axes[1]
    for s, e in zone["truth"]:
        ax.barh(1, e - s + 1, left=s, color="#23824a", height=0.5)
    for ev in zone["events"]:
        ax.plot(ev["frame"], 0, "v" if ev["event"] == "enter" else "^", color="#c8402f" if ev["event"] == "enter" else "#2563c9",
                ms=8)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["logged events\n(v enter, ^ exit)", "ground truth\ncenter inside"])
    ax.set_xlim(0, n_frames)
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel("frame")
    fig.tight_layout()
    return save(fig, path)
