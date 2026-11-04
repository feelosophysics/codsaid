"""보고서용 실험. run_all.py가 순서대로 부르고, 결과는 JSON으로 바꿀 수 있는 dict다."""
import time
from collections import OrderedDict

import cv2
import numpy as np

from . import cache as K
from . import evaluate as E
from . import synthetic as S
from .features import TargetMatcher, make_view, score_view
from .hungarian import brute_force, gated_assignment, greedy, hungarian
from .image_io import imread
from .motion import MotionDetector, MotionParams, clean_mask, find_detections, foreground_mask, make_subtractor
from .pipeline import VideoAnalyzer
from .tracker import Tracker
from .zone import IntrusionZone

TRACK_SCENARIOS = ("single", "crossing", "crossing_same", "pause", "lighting")
TABLE_ROWS = (("single", "단일 객체 이동"), ("crossing", "두 객체 겹침"), ("pause", "객체 일시 정지"),
              ("lighting", "조명 변화"))

VARIANTS = OrderedDict([
    ("baseline", ("기본: 탐욕 + 중심점 거리", {})),
    ("hungarian", ("Hungarian 할당 (보너스 1)", {"matcher": "hungarian"})),
    ("iou", ("IoU 매칭 (보너스 3)", {"cost": "iou"})),
    ("kalman", ("칼만 예측 (보너스 4)", {"kalman": True})),
    ("kalman_hungarian", ("칼만 + Hungarian", {"kalman": True, "matcher": "hungarian"})),
    ("appearance", ("색 히스토그램 섞기", {"appearance_weight": 0.5})),
    ("kalman_appearance", ("칼만 + 색 히스토그램", {"kalman": True, "appearance_weight": 0.5})),
    ("all_rules", ("칼만 + Hungarian + 색 + 긴 기억", {"kalman": True, "matcher": "hungarian",
                                                   "appearance_weight": 0.5, "max_missed": 60})),
])


def summary(r):
    """evaluate_tracking 결과에서 이벤트 목록을 뺀 요약."""
    return {k: v for k, v in r.items() if k not in ("events", "objects")}


# ---------------------------------------------------------------- 추적

def detection_cache(split, scenarios=TRACK_SCENARIOS, params=None):
    params = params or MotionParams(compute_hist=True)
    out = {}
    src = [K.ROOT / "src" / "motion.py"]
    for sc in scenarios:
        gt = S.load_gt(sc, split)
        video = S.DATA / gt["video"]
        out[sc] = (gt, K.cached(f"det-{sc}-{split}", (repr(params), K.file_hash(video)), src,
                                lambda v=video: E.detect_video(v, params)))
    return out


def run_tracker(cache, sc, **kw):
    gt, dets = cache[sc]
    return E.evaluate_tracking(gt, E.track_detections(dets, Tracker(**kw)))


def tracking_table(cache, **kw):
    """미션 표 1: 상황별 테스트 횟수, ID Switch, 추적 실패 + 기록 템플릿 행."""
    rows, logs, full = [], [], {}
    for sc, name in TABLE_ROWS:
        r = run_tracker(cache, sc, **kw)
        full[sc] = r
        rows.append({"scenario": sc, "name": name, "video": r["video"], "tests": r["tests"],
                     "switch_events": r["switch_events"], "switches": r["switches"],
                     "fail_events": r["fail_events"], "fails": r["fails"],
                     "occluded": sum(e["occluded"] for e in r["events"] if not e["extra"]),
                     "merged": sum(e.get("merged", 0) for e in r["events"] if not e["extra"]),
                     "false_ids": r["false_ids"], "retention": r["retention"], "coverage": r["coverage"]})
        logs.extend(E.log_rows(r))
    return rows, logs, full


def variant_experiment(cache, scenarios=TRACK_SCENARIOS):
    """규칙 추가 실험: 추적기 변형 × 시나리오. 교차 시나리오는 이벤트별 ID Switch도 남긴다."""
    out = OrderedDict()
    for key, (label, kw) in VARIANTS.items():
        row = {"label": label, "kwargs": kw, "scenarios": {}}
        for sc in scenarios:
            r = run_tracker(cache, sc, **kw)
            row["scenarios"][sc] = summary(r)
            if sc.startswith("crossing"):
                row["scenarios"][sc]["by_event"] = [{"kind": e["kind"], "label": e["label"], "switches": e["switches"]}
                                                    for e in r["events"]]
        out[key] = row
    return out


def param_sweep(cache, name, values, scenarios=("crossing", "crossing_same", "single", "pause", "lighting"), **base):
    rows = []
    for v in values:
        kw = dict(base, **{name: v})
        rec = {"value": v}
        for sc in scenarios:
            rec[sc] = summary(run_tracker(cache, sc, **kw))
        rows.append(rec)
    return rows


def assignment_disagreement(cache, scenarios=("crossing", "crossing_same", "single")):
    """같은 추적 상태에서 탐욕과 Hungarian의 할당이 달라지는 프레임 수."""
    out = {}
    for sc in scenarios:
        gt, dets = cache[sc]
        tr = Tracker()
        n_multi = n_diff = 0
        excess = []
        for d in dets:
            tr._predict()
            tracks = list(tr.tracks.values())
            if len(tracks) >= 2 and len(d) >= 2:
                cost, gate = tr.cost_matrix(tracks, d)
                pg, _, _ = gated_assignment(cost, gate, "greedy")
                ph, _, _ = gated_assignment(cost, gate, "hungarian")
                n_multi += 1
                if sorted(pg) != sorted(ph):
                    n_diff += 1
                    cg = sum(cost[i, j] for i, j in pg) + (1.0 * (min(cost.shape) - len(pg)))
                    ch = sum(cost[i, j] for i, j in ph) + (1.0 * (min(cost.shape) - len(ph)))
                    excess.append(float(cg - ch))
            tr.update(d)
        out[sc] = {"frames_multi": n_multi, "frames_diff": n_diff, "mean_excess": float(np.mean(excess)) if excess else 0.0}
    return out


def hungarian_random(seed=0, trials=400):
    """무작위 비용 행렬에서 탐욕의 손해와 실행 시간."""
    rng = np.random.default_rng(seed)
    by_n = []
    for n in (2, 3, 4, 5, 6, 7):
        worse, ratio = 0, []
        for _ in range(trials):
            c = rng.uniform(0, 1, (n, n))
            rg, cg = greedy(c)
            rh, ch = hungarian(c)
            opt = c[rh, ch].sum()
            g = c[rg, cg].sum()
            if n <= 6:
                assert abs(opt - brute_force(c)) < 1e-9
            if g > opt + 1e-12:
                worse += 1
                ratio.append(g / opt - 1)
        by_n.append({"n": n, "greedy_suboptimal": worse / trials,
                     "mean_excess_pct": 100 * float(np.mean(ratio)) if ratio else 0.0})
    timing = []
    for n in (5, 20, 50, 100, 200):
        c = rng.uniform(0, 1, (n, n))
        t = time.perf_counter()
        reps = 20 if n <= 50 else 3
        for _ in range(reps):
            hungarian(c)
        th = (time.perf_counter() - t) / reps
        t = time.perf_counter()
        for _ in range(reps):
            greedy(c)
        tg = (time.perf_counter() - t) / reps
        timing.append({"n": n, "hungarian_ms": th * 1e3, "greedy_ms": tg * 1e3})
    example = np.array([[1.0, 2.0], [2.0, 100.0]])
    rg, cg = greedy(example)
    rh, ch = hungarian(example)
    return {"by_n": by_n, "timing": timing, "example": {"cost": example.tolist(), "greedy": float(example[rg, cg].sum()),
                                                        "hungarian": float(example[rh, ch].sum())}}


# ---------------------------------------------------------------- 배경 모델

# 캐시 키에 넣는 실험 코드 버전. 아래 배경·특징점 실험 함수의 계산을 바꾸면 올린다.
BG_VERSION = 1
FEATURE_VERSION = 2


def bg_configs():
    cfgs = OrderedDict()
    for lr in (0.0005, 0.002, 0.01, 0.05):
        cfgs[f"mog2_{lr:g}"] = MotionParams(method="mog2", learning_rate=lr)
    cfgs["mog2_0.002_noshadow"] = MotionParams(method="mog2", learning_rate=0.002, detect_shadows=False)
    for lr in (0.002, 0.01, 0.05):
        cfgs[f"ravg_{lr:g}"] = MotionParams(method="running_avg", learning_rate=lr)
    cfgs["framediff"] = MotionParams(method="frame_diff")
    return cfgs


def background_experiment(split="test", scenarios=("pause", "lighting", "single"), configs=None, sample_frames=None):
    """한 번 영상을 읽으며 모든 배경 설정을 함께 돌린다. 프레임별 전경 마스크 TP/FP/FN과 검출 결과를 모은다."""
    configs = configs or bg_configs()
    sample_frames = sample_frames or {}
    src = [K.ROOT / "src" / n for n in ("motion.py", "synthetic.py", "evaluate.py")]
    out = {}
    for sc in scenarios:
        key = (BG_VERSION, [(k, repr(p)) for k, p in configs.items()], sorted(sample_frames.get(sc, ())),
               K.file_hash(S.DATA / f"{sc}_{split}.mp4"))
        out[sc] = K.cached(f"bg-{sc}-{split}", key, src,
                           lambda sc=sc: _background_one(sc, split, configs, sample_frames))
    return out


def _background_one(sc, split, configs, sample_frames):
    """영상 하나에 대해 모든 배경 설정을 함께 돌린다."""
    gt = S.load_gt(sc, split)
    rend = S.Renderer(S.build(sc, split))
    subs = {k: make_subtractor(p) for k, p in configs.items()}
    stats = {k: np.zeros((gt["frames"], 3), np.int64) for k in configs}
    dets = {k: [] for k in configs}
    # 정지 후 다시 걸을 때 '유령'(배경에 남은 자국)을 잴 영역: 멈춘 자리의 정답 박스
    regions = {}
    if sc == "pause":
        for e in gt["events"]:
            if "resume" in e:
                o = next(o for o in gt["gt"][e["resume"] - 1] if o["id"] == "A")
                regions[e["index"]] = (e["resume"], o["bbox"])
    ghost = {k: {i: [] for i in regions} for k in configs}
    samples = {}
    for i, frame in enumerate(E.read_frames(S.DATA / gt["video"])):
        truth = rend.frame(i, with_noise=False)[2]
        for k, p in configs.items():
            mask, raw = foreground_mask(subs[k], frame, p)
            cleaned = clean_mask(mask, p)
            m = E.mask_scores(cleaned, truth)
            stats[k][i] = (m["tp"], m["fp"], m["fn"])
            dets[k].append(find_detections(cleaned, p))
            for idx, (resume, (x, y, w, h)) in regions.items():
                if resume <= i < resume + 120:
                    region = (cleaned[y:y + h, x:x + w] > 0) & ~truth[y:y + h, x:x + w]
                    ghost[k][idx].append(int(region.sum()))
            if i in sample_frames.get(sc, ()):
                samples.setdefault(i, {"frame": cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA),
                                       "truth": cv2.resize(truth.astype(np.uint8) * 255, (320, 180),
                                                           interpolation=cv2.INTER_NEAREST)})
                samples[i][k] = cv2.resize(cleaned, (320, 180), interpolation=cv2.INTER_NEAREST)
                if k == "mog2_0.002":
                    samples[i]["raw"] = cv2.resize(raw, (320, 180), interpolation=cv2.INTER_NEAREST)
    return {"gt": gt, "stats": stats, "dets": dets, "ghost": ghost, "samples": samples}


def first_recovery(fp_ratio, start, limit, thr=0.005, hold=5):
    """start 이후 FP 비율이 thr 아래로 hold프레임 연속 유지되기 시작하는 시점까지의 프레임 수."""
    for i in range(start, min(len(fp_ratio) - hold, start + limit)):
        if np.all(fp_ratio[i:i + hold] < thr):
            return i - start
    return None


def background_summary(bg, configs):
    """학습률 트레이드오프 요약: 흡수 시간·유령·조명 회복 시간·F1·추적 결과."""
    res = OrderedDict()
    for k, p in configs.items():
        row = {"method": p.method, "learning_rate": p.learning_rate, "shadows": p.detect_shadows}
        if "pause" in bg:
            d = bg["pause"]
            st = d["stats"][k]
            stops = []
            for e in d["gt"]["events"]:
                if "resume" not in e:
                    continue
                tp, fn = st[e["start"]:e["resume"], 0], st[e["start"]:e["resume"], 2]
                recall = tp / np.maximum(tp + fn, 1)
                below = np.nonzero(recall < 0.5)[0]
                g = np.array(d["ghost"][k][e["index"]])
                stops.append({"stop_frames": e["resume"] - e["start"],
                              "absorbed_after": int(below[0]) if len(below) else None,
                              "ghost_frames": int((g > 150).sum())})
            row["pause"] = stops
            row["pause_tracking"] = summary(E.evaluate_tracking(d["gt"], E.track_detections(d["dets"][k], Tracker())))
        if "lighting" in bg:
            d = bg["lighting"]
            st = d["stats"][k]
            fp_ratio = st[:, 1] / float(S.W * S.H)
            evs = []
            for e in d["gt"]["events"]:
                s = e["start"]
                evs.append({"kind": e["kind"], "peak_fp": float(fp_ratio[s:s + 75].max()),
                            "recovery": first_recovery(fp_ratio, s, 75)})
            row["lighting"] = evs
            row["lighting_tracking"] = summary(E.evaluate_tracking(d["gt"], E.track_detections(d["dets"][k], Tracker())))
            row["lighting_fp_series"] = [round(float(v), 5) for v in fp_ratio]
        if "single" in bg:
            st = bg["single"]["stats"][k]
            has = (st[:, 0] + st[:, 2]) > 0
            tp, fp, fn = st[has].sum(axis=0)
            prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
            row["single"] = {"precision": float(prec), "recall": float(rec), "f1": float(2 * prec * rec / max(prec + rec, 1e-9))}
        if "pause" in bg:
            st = bg["pause"]["stats"][k]
            row["pause_recall_series"] = [round(float(v), 4) for v in st[:, 0] / np.maximum(st[:, 0] + st[:, 2], 1)]
        res[k] = row
    return res


# ---------------------------------------------------------------- 특징점

FEATURE_CONDITIONS = [
    ("정면", {}), ("30도 회전 (평면 안)", {"roll": 30}), ("60도 회전 (평면 안)", {"roll": 60}),
    ("30도 기울임 (3D)", {"yaw": 30}), ("60도 기울임 (3D)", {"yaw": 60}),
    ("30% 가림", {"occlusion": 0.3}), ("50% 가림", {"occlusion": 0.5}),
]
SWEEPS = OrderedDict([
    ("roll", list(range(0, 181, 15))), ("yaw", list(range(0, 81, 10))),
    ("occlusion", [round(v, 1) for v in np.arange(0, 0.91, 0.1)]),
    ("scale", [0.15, 0.2, 0.25, 0.3, 0.4, 0.55, 0.75, 1.0]),
    ("brightness", [0.15, 0.25, 0.4, 0.6, 1.0, 1.4, 1.8]), ("blur", [0, 1, 2, 3, 4]),
])


def feature_background(k):
    """시험 장면 배경: 실내 배경 + 다른 표지 하나 (특징점이 많은 방해물)."""
    rng = np.random.default_rng([k, 31])
    bg = S.make_background(rng)
    other = S.make_cover(int(rng.integers(100, 999)), title="NOTE")
    cx = rng.choice([90, 560])
    colr, a = S.warp_layer(other, S.card_corners(cx, rng.uniform(80, 260), 0.3, rng.uniform(-20, 20), 0))
    return bg * (1 - a[..., None]) + colr


def _views(texture, cond, trials, seed=0):
    for k in range(trials):
        rng = np.random.default_rng([seed, k])
        params = dict(cond)
        scale = params.pop("scale", 0.55)
        yield make_view(texture, feature_background(k), rng.uniform(250, 390), rng.uniform(130, 230), scale=scale,
                        occ_side=int(rng.integers(4)), rng=rng, **params)


FEATURE_SOURCES = [K.ROOT / "src" / n for n in ("features.py", "synthetic.py")]


def _feature_cached(name, texture, args, compute):
    key = (FEATURE_VERSION, args, K.hashlib.sha256(np.ascontiguousarray(texture).tobytes()).hexdigest())
    return K.cached(name, key, FEATURE_SOURCES, compute)


def feature_conditions(texture, methods=("orb", "sift"), trials=10):
    return _feature_cached("feat-table", texture, (methods, trials), lambda: _feature_conditions(texture, methods, trials))


def feature_sweeps(texture, methods=("orb", "sift"), trials=6):
    return _feature_cached("feat-sweep", texture, (methods, trials), lambda: _feature_sweeps(texture, methods, trials))


def generalization(texture, methods=("orb", "sift"), trials=10):
    return _feature_cached("feat-gen", texture, (methods, trials), lambda: _generalization(texture, methods, trials))


def _feature_conditions(texture, methods, trials):
    out = OrderedDict()
    for m in methods:
        matcher = TargetMatcher(texture, m)
        rows = []
        for name, cond in FEATURE_CONDITIONS:
            rs = [score_view(matcher, img, H, c) for img, c, H in _views(texture, cond, trials)]
            rows.append({"condition": name, "n_ref": matcher.n_ref,
                         **{k: float(np.mean([r[k] for r in rs])) for k in
                            ("n_scene_target", "n_good", "n_correct", "n_inliers", "match_rate", "precision")},
                         "found_rate": float(np.mean([r["localized"] for r in rs]))})
        out[m] = rows
    return out


def _feature_sweeps(texture, methods, trials):
    out = {}
    for m in methods:
        matcher = TargetMatcher(texture, m)
        out[m] = {}
        for name, values in SWEEPS.items():
            pts = []
            for v in values:
                rs = [score_view(matcher, img, H, c) for img, c, H in _views(texture, {name: v}, trials, seed=1)]
                pts.append({"value": v, "match_rate": float(np.mean([r["match_rate"] for r in rs])),
                            "n_correct": float(np.mean([r["n_correct"] for r in rs])),
                            "found_rate": float(np.mean([r["localized"] for r in rs]))})
            out[m][name] = pts
    return out


def _generalization(texture, methods, trials):
    """학습하지 않은 특징의 일반화: 같은 시리즈 다른 권, 무관한 표지, 색 반전, 선 그림."""
    same = imread(S.TARGET_DIR / "same_series.png")
    other = imread(S.TARGET_DIR / "other.png")
    gray = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 60, 160)
    sketch = cv2.cvtColor(255 - cv2.dilate(edges, np.ones((2, 2), np.uint8)), cv2.COLOR_GRAY2BGR)
    cases = OrderedDict([("등록 물체 그대로", texture), ("같은 시리즈 다른 권", same), ("무관한 표지", other),
                         ("색 반전 (음화)", 255 - texture), ("윤곽선 그림", sketch)])
    out = OrderedDict()
    for m in methods:
        matcher = TargetMatcher(texture, m)
        rows = []
        for name, tex in cases.items():
            rs = [matcher.match(img) for img, _, _ in _views(tex, {}, trials, seed=2)]
            rows.append({"case": name, "found_rate": float(np.mean([r.found for r in rs])),
                         "n_good": float(np.mean([r.n_good for r in rs])),
                         "n_inliers": float(np.mean([r.n_inliers for r in rs]))})
        out[m] = rows
    return out


def target_video(split="test", methods=("orb", "sift")):
    """등록 물체 영상: 구간(조건)별 검출률과 물체가 없을 때의 오검출."""
    key = (FEATURE_VERSION, split, methods, K.file_hash(S.DATA / f"target_{split}.mp4"),
           K.file_hash(S.TARGET_DIR / "target.png"))
    out = dict(K.cached(f"feat-video-{split}", key, FEATURE_SOURCES, lambda: _target_video(split, methods)))
    out["ms_per_frame"] = _time_matchers(split, methods)   # 시간은 그때그때 잰다 (캐시하지 않음)
    return out


def _time_matchers(split, methods, n_frames=60, repeats=3):
    """물체가 보이는 구간 n_frames프레임의 매칭 시간. 예열 후 repeats번 재서 가장 빠른 값 (ms/프레임)."""
    texture = imread(S.TARGET_DIR / "target.png")
    frames = [f for i, f in enumerate(E.read_frames(S.DATA / f"target_{split}.mp4")) if 110 <= i < 110 + n_frames]
    out = {}
    for m in methods:
        mt = TargetMatcher(texture, m)
        mt.match(frames[0])
        best = float("inf")
        for _ in range(repeats):
            t = time.perf_counter()
            for f in frames:
                mt.match(f)
            best = min(best, (time.perf_counter() - t) / len(frames))
        out[m] = 1e3 * best
    return out


def _target_video(split, methods):
    gt = S.load_gt("target", split)
    texture = imread(S.TARGET_DIR / "target.png")
    matchers = {m: TargetMatcher(texture, m) for m in methods}
    per = {m: [] for m in methods}
    times = {m: 0.0 for m in methods}
    for i, frame in enumerate(E.read_frames(S.DATA / gt["video"])):
        t = next((o for o in gt["gt"][i] if o["id"] == "T"), None)
        for m, mt in matchers.items():
            t0 = time.perf_counter()
            r = mt.match(frame)
            times[m] += time.perf_counter() - t0
            err = None
            if r.found and t is not None and t.get("corners"):
                err = float(np.linalg.norm(r.corners - np.array(t["corners"]), axis=1).mean())
            per[m].append({"found": bool(r.found), "inliers": r.n_inliers, "err": err,
                           "present": t is not None and t.get("vis", 0) > 0.3, "vis": t["vis"] if t else 0.0})
    segs = []
    for e in gt["events"]:
        row = {"kind": e["kind"], "start": e["start"], "end": e["end"]}
        for m in methods:
            fr = per[m][e["start"]:e["end"] + 1]
            if e["kind"] == "absent":
                row[m] = {"false_positive": sum(f["found"] for f in fr) / len(fr)}
            else:
                pres = [f for f in fr if f["present"]]
                ok = [f for f in pres if f["found"] and f["err"] is not None and f["err"] < 10]
                errs = [f["err"] for f in pres if f["err"] is not None]
                row[m] = {"detect_rate": len(ok) / max(len(pres), 1), "frames": len(pres),
                          "found_rate": sum(f["found"] for f in pres) / max(len(pres), 1),
                          "median_err": float(np.median(errs)) if errs else None}
        segs.append(row)
    n = gt["frames"]
    return {"segments": segs, "inliers": {m: [f["inliers"] for f in per[m]] for m in methods},
            "found": {m: [int(f["found"]) for f in per[m]] for m in methods},
            "ms_per_frame": {m: 1e3 * times[m] / n for m in methods},
            "poses": [_pose(g) for g in gt["gt"]]}


def _pose(objs):
    o = next((o for o in objs if o["id"] == "T"), None)
    return [o.get("roll", 0), o.get("yaw", 0), o.get("vis", 0)] if o else None


# ---------------------------------------------------------------- 침입 구역

def zone_experiment(cache, rect=(470, 200, 120, 130), sc="single"):
    gt, dets = cache[sc]
    zone = IntrusionZone(rect, echo=False)
    tr = Tracker()
    for i, d in enumerate(dets):
        tr.update(d)
        zone.update(tr.visible_tracks(), i, alive_ids=set(tr.tracks))
    truth = E.zone_ground_truth(gt, rect)
    enters = [e["frame"] for e in zone.events if e["event"] == "enter"]
    matched = [s for s, _ in truth if any(abs(f - s) <= 10 for f in enters)]
    return {"rect": list(rect), "truth": truth, "events": zone.events, "true_enters": len(truth),
            "detected_enters": len(matched), "alarms": len(enters), "false_alarms": len(enters) - len(matched)}


# ---------------------------------------------------------------- 속도

def speed_benchmark(split="test", n_frames=150, repeats=3):
    """전체 파이프라인의 처리 속도 (화면 표시 제외). 예열 후 repeats번 재서 가장 빠른 값을 쓴다.

    같은 노트북에서도 전원·발열 상태에 따라 2~3배 달라지므로, 측정마다의 최댓값(가장 느린 값)도 함께 남긴다.
    """
    path = S.DATA / f"crossing_{split}.mp4"
    texture = imread(S.TARGET_DIR / "target.png")
    cases = OrderedDict([("배경 차분 + 추적", None), ("+ ORB 매 프레임", ("orb", 1)), ("+ ORB 2프레임마다", ("orb", 2)),
                         ("+ SIFT 매 프레임", ("sift", 1))])
    frames = []
    for i, f in enumerate(E.read_frames(path)):
        if i >= n_frames:
            break
        frames.append(f)
    out = []
    for name, tgt in cases.items():
        times = []
        for r in range(repeats + 1):            # 첫 번은 예열
            an = VideoAnalyzer(MotionParams(), Tracker(), TargetMatcher(texture, tgt[0]) if tgt else None,
                               target_every=tgt[1] if tgt else 1)
            t = time.perf_counter()
            for f in frames:
                res = an.process(f)
                an.draw(f, res, 30.0)
            if r:
                times.append((time.perf_counter() - t) / len(frames))
        best = min(times)
        out.append({"case": name, "fps": 1.0 / best, "ms": 1e3 * best, "ms_worst": 1e3 * max(times)})
    return out
