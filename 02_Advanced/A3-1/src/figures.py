"""보고서 그림. 운영체제마다 한글 글꼴이 달라 그림 안의 글자는 영어로 쓰고, 설명은 보고서에 한글로 단다.

matplotlib 기본 문법 (이 파일 전체에서 반복된다):
    fig, axes = plt.subplots(행, 열, figsize=(가로인치, 세로인치))   fig는 그림 전체, axes는 칸들의 2차원 배열
    axes.flat                 2차원 칸 배열을 한 줄로 펴서 for로 순서대로 돌게 한다
    ax.imshow(이미지)          배열을 그림으로. 컬러는 RGB 순서여야 하므로 OpenCV의 BGR을 rgb()로 바꾼다
    ax.plot(x들, y들)          선 그래프. ax.scatter는 점, ax.bar는 막대
    save(fig, path)           파일로 저장하고 메모리를 비운다
각 함수는 계산을 새로 하지 않고, run_all이 넘긴 결과를 그리기만 한다.
"""
import cv2
import matplotlib

# Agg는 화면 창 없이 이미지 파일만 만드는 방식이다. 서버·명령줄에서도 그림을 저장할 수 있다.
# pyplot을 import하기 전에 정해야 해서 아래 import에 noqa: E402(위치 경고 무시)를 붙였다.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

COND_EN = {"easy": "easy (plain, frontal)", "shadow": "shadow / lighting", "tilt": "tilt >= 45 deg",
           "complex": "complex background", "unknown": "unlabeled"}
COND_COLOR = {"easy": "#2a9d4b", "shadow": "#6a4fb3", "tilt": "#d07a12", "complex": "#c8402f", "unknown": "#666666"}
STATUS_COLOR = {"success": "#2a9d4b", "partial": "#e0a100", "fail": "#c8402f", "unknown": "#888888"}
STATUS_EN = {"success": "SUCCESS", "partial": "PARTIAL", "fail": "FAIL", "unknown": "NO GT"}


def rgb(image):
    """OpenCV의 BGR 이미지를 matplotlib용 RGB로 바꾼다. 회색은 그대로 둔다.

    Args:
        image: (H, W, 3) BGR 또는 (H, W) 회색.

    Returns:
        numpy.ndarray: (H, W, 3) RGB 새 배열 또는 입력 회색 이미지.
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image


def save(fig, path):
    """그림을 저장하고 닫는다.

    plt.close를 하지 않으면 그림이 메모리에 계속 쌓여 그림 수십 장을 만들 때 느려진다.

    Args:
        fig: matplotlib Figure.
        path: 저장할 PNG 경로.

    Returns:
        pathlib.Path 또는 str: 받은 path 그대로.
    """
    fig.savefig(path, dpi=110, bbox_inches="tight")  # bbox_inches="tight"는 바깥 빈 여백을 잘라 낸다
    plt.close(fig)
    return path


def dataset_overview(dataset, path):
    """촬영 조건별 20장과 정답 꼭짓점.

    Args:
        dataset: (label, image) 목록.
        path: 저장 경로(01_dataset.png).

    Returns:
        저장한 경로.
    """
    n = len(dataset)
    cols = 5
    rows = int(np.ceil(n / cols))  # ceil은 올림. 20장 / 5열 = 4줄
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 3.4))
    for ax, (lab, img) in zip(axes.flat, dataset):
        ax.imshow(rgb(img))
        if lab.get("corners"):
            # 리스트 + [첫 점]으로 첫 점을 끝에 한 번 더 붙여, 선이 닫힌 사각형이 되게 한다. (5, 2) 배열.
            q = np.array(lab["corners"] + [lab["corners"][0]])
            ax.plot(q[:, 0], q[:, 1], "-", color="cyan", lw=1.2)
            # *리스트는 [x, y]를 두 인자로 풀어 넘긴다: plot(x, y, "o").
            ax.plot(*lab["corners"][0], "o", color="lime", ms=4)
        # .get("angle", {})는 키가 없으면 빈 dict를 주어 이어지는 .get이 오류 없이 None을 돌려주게 한다.
        tilt = lab.get("angle", {}).get("tilt_deg")
        ax.set_title(f"{lab['id']}  {COND_EN.get(lab['condition'], '')}" + (f"\ntilt {tilt:.0f} deg" if tilt else ""),
                     fontsize=8, color=COND_COLOR.get(lab["condition"], "k"))
        ax.axis("off")
    for ax in list(axes.flat)[n:]:  # 이미지보다 칸이 많으면 남는 칸의 축을 숨긴다
        ax.axis("off")
    fig.suptitle("Synthetic test set: ground-truth corners (cyan), TL corner (green)", fontsize=11)
    return save(fig, path)


def histogram_grid(dataset, stats, path):
    """이미지별 밝기 히스토그램. 회색 막대는 정답 문서 영역, 선은 전체.

    채운 면은 전체 이미지, 실선은 문서 픽셀, 점선은 배경 픽셀이다. 문서·배경을 같은 분모(전체 픽셀 수)로
    나눴으므로 실선 + 점선 = 채운 면이다.

    Args:
        dataset: (label, image) 목록.
        stats: run_eda가 만든 {id: 통계 dict}.
        path: 저장 경로(02_histograms.png).

    Returns:
        저장한 경로.
    """
    from .eda import document_mask, histogram, to_gray  # 함수 안의 import는 이 함수를 부를 때만 불러온다
    n = len(dataset)
    cols = 5
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.8, rows * 1.9), sharex=True)
    x = np.arange(256)
    for ax, (lab, img) in zip(axes.flat, dataset):
        gray = to_gray(img)
        color = COND_COLOR.get(lab["condition"], "k")
        ax.fill_between(x, histogram(gray), color=color, alpha=0.35, lw=0)
        if lab.get("corners"):
            m = document_mask(gray.shape, lab["corners"])
            hd = np.bincount(gray[m], minlength=256) / gray.size  # 문서 픽셀만 센 (256,)
            hb = np.bincount(gray[~m], minlength=256) / gray.size  # 배경 픽셀만 센 (256,)
            ax.plot(x, hd, color="#333333", lw=0.8, label="document")
            ax.plot(x, hb, color=color, lw=0.8, ls="--", label="background")
        s = stats[lab["id"]]
        ax.set_title(f"{lab['id']}  mean {s['mean']:.0f}  std {s['std']:.0f}", fontsize=8, color=color)
        ax.set_yticks([])
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=6, loc="upper left")
    for ax in axes[-1]:  # axes[-1]은 마지막 줄의 칸들
        ax.set_xlabel("gray level", fontsize=8)
    fig.suptitle("Brightness histograms (filled: whole image, solid: document pixels, dashed: background pixels)",
                 fontsize=10)
    fig.tight_layout()
    return save(fig, path)


def histogram_by_condition(dataset, stats, rows, path):
    """조건별 평균 히스토그램과, 문서-배경 대비 vs 경계 밝기 차 산점도.

    가운데 그림(전역 평균·표준편차)에서는 성공·실패가 섞이고, 오른쪽 그림(경계 밝기 차)에서는 갈린다.
    "전체 밝기보다 경계 대비가 검출을 결정한다"를 보이는 그림이다.

    Args:
        dataset: (label, image) 목록.
        stats: {id: 통계 dict}.
        rows: 기본 파라미터 평가 행 목록(점 모양을 판정별로 바꾸는 데 쓴다).
        path: 저장 경로(03_histogram_by_condition.png).

    Returns:
        저장한 경로.
    """
    from .eda import histogram, to_gray
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    x = np.arange(256)
    groups = {}
    for lab, img in dataset:
        # setdefault(키, [])는 키가 없으면 빈 리스트를 넣고 그 리스트를 돌려준다. 바로 append할 수 있다.
        groups.setdefault(lab["condition"], []).append(histogram(to_gray(img)))
    for cond, hs in groups.items():
        # mean(axis=0): (5, 256) → (256,) 조건별 평균. convolve(…, ones(5)/5)는 5칸 이동 평균으로 선을 부드럽게 한다.
        axes[0].plot(x, np.convolve(np.mean(hs, axis=0), np.ones(5) / 5, mode="same"), color=COND_COLOR[cond],
                     lw=1.8, label=f"{COND_EN[cond]} (n={len(hs)})")
    axes[0].set_xlabel("gray level")
    axes[0].set_ylabel("pixel fraction")
    axes[0].set_title("Mean histogram by condition")
    axes[0].legend(fontsize=8)

    status = {r["id"]: r["status"] for r in rows}
    for lab, _ in dataset:
        s = stats[lab["id"]]
        st = status[lab["id"]]
        marker = {"success": "o", "partial": "s", "fail": "X"}.get(st, "o")
        # 튜플 세 개짜리 묶음을 두 번 돈다: (가운데 칸, x키, y키), (오른쪽 칸, x키, y키).
        for ax, key_x, key_y in ((axes[1], "mean", "std"), (axes[2], "doc_bg_contrast", "boundary_step_p10")):
            ax.scatter(s[key_x], s[key_y], s=70, marker=marker, color=COND_COLOR[lab["condition"]],
                       edgecolor="k", lw=0.5)
            ax.annotate(lab["id"], (s[key_x], s[key_y]), fontsize=7, xytext=(4, 3), textcoords="offset points")
    axes[1].set_xlabel("mean brightness")
    axes[1].set_ylabel("std (global contrast)")
    axes[1].set_title("Global statistics (o success, s partial, X fail)")
    axes[2].set_xlabel("document mean - background mean")
    axes[2].set_ylabel("10th pct |step| across document border")
    axes[2].set_title("Border contrast decides detection")
    axes[2].axhline(0, color="#999", lw=0.6)
    for ax in axes[1:]:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return save(fig, path)


def darkening_figure(rows_dark, s04_stats, path, canny=(50, 150)):
    """같은 문서를 점점 어둡게 했을 때 히스토그램·경계 기울기·엣지 검출률.

    오른쪽 칸의 S04 별표는 x = 0.30에 고정해 찍는다. S04의 실제 조명 배율(노출 30%)에 맞춘 위치이며 계산값이 아니다.

    Args:
        rows_dark: eda.darkening_experiment의 행 목록.
        s04_stats: S04의 통계 dict. None이면 별표를 찍지 않는다.
        path: 저장 경로(04_darkening.png).
        canny: 가운데 칸에 수평선으로 그릴 (low, high).

    Returns:
        저장한 경로.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    cmap = plt.get_cmap("viridis")  # 0~1 값을 색으로 바꾸는 색상표
    x = np.arange(256)
    for i, r in enumerate(rows_dark):
        axes[0].plot(x, np.convolve(r["hist"], np.ones(3) / 3, mode="same"), color=cmap(i / len(rows_dark)),
                     label=f"x{r['factor']:.2f}")
    axes[0].set_xlim(0, 255)
    axes[0].set_title("E01 darkened: histogram squeezes left")
    axes[0].set_xlabel("gray level")
    axes[0].legend(fontsize=7, ncol=2)
    f = [r["factor"] for r in rows_dark]
    g = [r["boundary_gradient_median"] for r in rows_dark]
    axes[1].plot(f, g, "o-", color="#2563c9", label="median border gradient |gx|+|gy|")
    axes[1].axhline(canny[1], color="#c8402f", ls="--", label=f"Canny high = {canny[1]}")
    axes[1].axhline(canny[0], color="#e0a100", ls="--", label=f"Canny low = {canny[0]}")
    axes[1].set_xlabel("brightness factor")
    axes[1].set_title("Border gradient scales with brightness")
    axes[1].legend(fontsize=8)
    axes[1].invert_xaxis()  # 왼쪽 = 밝음, 오른쪽 = 어두움 순서로 읽게 x축을 뒤집는다
    axes[2].plot(f, [r["boundary_edge_recall"] for r in rows_dark], "o-", color="#2a9d4b", label="border edge recall")
    axes[2].plot(f, [r["bg_edge_density"] * 10 for r in rows_dark], "s--", color="#888", label="background edge density x10")
    if s04_stats:
        axes[2].scatter([0.30], [s04_stats["boundary_edge_recall"]], marker="*", s=200, color="#6a4fb3",
                        label="S04 (real low-light case)", zorder=5)
    axes[2].set_xlabel("brightness factor")
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].invert_xaxis()
    axes[2].set_title("Fixed thresholds lose the document border")
    axes[2].legend(fontsize=8)
    for ax in axes[1:]:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return save(fig, path)


def pipeline_figure(result, label, row, path):
    """한 이미지의 5단계: 원본 → 전처리 → 엣지 → 윤곽선 → 결과.

    Args:
        result: 그 이미지의 ScanResult.
        label: 라벨 dict.
        row: 평가 행.
        path: 저장 경로(05_pipeline_ID.png).

    Returns:
        저장한 경로.
    """
    from .scanner import stage_images
    stages = stage_images(result)
    fig, axes = plt.subplots(1, 5, figsize=(17, 4.6), gridspec_kw={"width_ratios": [1, 1, 1, 1, 0.9]})
    for ax, (name, img) in zip(axes, stages.items()):
        ax.imshow(rgb(img), cmap="gray")
        ax.set_title(name, fontsize=10)
        ax.axis("off")
    p = result.params
    msg = f"{label['id']}: blur {p.blur}, Canny ({p.canny_low}, {p.canny_high}) -> {STATUS_EN[row['status']]}"
    if "error_ratio" in row:
        msg += f", max corner error {row['error_ratio'] * 100:.2f}% of diagonal"
    fig.suptitle(msg, fontsize=11, color=STATUS_COLOR[row["status"]])
    fig.tight_layout()
    return save(fig, path)


def detection_grid(dataset, results, rows, path):
    """20장 전체: 정답(청록)과 검출(빨강) 비교, 판정.

    Args:
        dataset: (label, image) 목록.
        results: ScanResult 목록(dataset과 같은 순서).
        rows: 평가 행 목록.
        path: 저장 경로(06_detection.png).

    Returns:
        저장한 경로.
    """
    n = len(dataset)
    cols = 5
    rws = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rws, cols, figsize=(cols * 2.6, rws * 3.4))
    for ax, (lab, img), res, row in zip(axes.flat, dataset, results, rows):
        ax.imshow(rgb(img))
        if lab.get("corners"):
            q = np.array(lab["corners"] + [lab["corners"][0]])
            ax.plot(q[:, 0], q[:, 1], "-", color="cyan", lw=2.2, alpha=0.8)
        if res.found:
            # vstack으로 (4, 2) 아래에 첫 행 (1, 2)를 붙여 (5, 2). quad[:1]처럼 슬라이스로 자르면 2차원이 유지된다.
            q = np.vstack([res.quad, res.quad[:1]])
            ax.plot(q[:, 0], q[:, 1], "-", color="red", lw=1.2)
        err = f" {row['error_ratio'] * 100:.1f}%" if "error_ratio" in row else ""
        ax.set_title(f"{lab['id']} {STATUS_EN[row['status']]}{err}", fontsize=9, color=STATUS_COLOR[row["status"]])
        ax.axis("off")
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle("Default parameters: ground truth (cyan) vs detected (red); % = max corner error / diagonal",
                 fontsize=11)
    return save(fig, path)


def failure_panels(cases, path):
    """실패·부분 성공 사례: 윤곽선 후보와 엣지 맵을 나란히 보여 준다.

    cases: [(label, ScanResult, row, 설명 문자열)]

    Args:
        cases: 위 형식의 목록. 실행 결과 8건.
        path: 저장 경로(07_failures.png).

    Returns:
        저장한 경로.
    """
    from .scanner import draw_contours
    n = len(cases)
    fig, axes = plt.subplots(n, 3, figsize=(13, 4.0 * n))
    axes = np.atleast_2d(axes)  # 사례가 1건이면 axes가 1차원이 되므로 항상 (n, 3)으로 맞춘다
    for (lab, res, row, note), ax in zip(cases, axes):
        crop = draw_contours(res)
        if lab.get("corners"):
            # 정답은 원본 좌표라 축소 배율(scale)을 곱해 축소본 위에 그린다. (4, 2) × 숫자 → (4, 2).
            q = (np.array(lab["corners"]) * res.scale).round().astype(np.int32)
            cv2.polylines(crop, [q], True, (255, 255, 0), 1, cv2.LINE_AA)
        ax[0].imshow(rgb(res.work))
        ax[0].set_title(f"{lab['id']} original", fontsize=10)
        ax[1].imshow(res.edges, cmap="gray")
        ax[1].set_title("Canny edges", fontsize=10)
        ax[2].imshow(rgb(crop))
        ax[2].set_title(f"candidates (green), chosen (red), GT (cyan) -> {STATUS_EN[row['status']]}", fontsize=9,
                        color=STATUS_COLOR[row["status"]])
        ax[0].set_ylabel(note, fontsize=9)
        for a in ax:
            a.set_xticks([])
            a.set_yticks([])
    fig.tight_layout()
    return save(fig, path)


def sweep_figure(configs, matrix, ids, summary, path):
    """이미지 × 파라미터 조합 판정표와 조합별 성공 수.

    Args:
        configs: 조합 목록(266개).
        matrix: (20, 266) 판정 행렬.
        ids: 이미지 id 목록.
        summary: evaluate.sweep_summary의 결과.
        path: 저장 경로(08_parameter_sweep.png).

    Returns:
        저장한 경로.
    """
    # 성공 수가 많은 조합부터 보이도록 열 순서를 정한다. -배열로 내림차순, stable로 동점은 원래 순서.
    order = np.argsort(-np.array(summary["per_config_success"]), kind="stable")
    fig, axes = plt.subplots(2, 1, figsize=(15, 8.5), gridspec_kw={"height_ratios": [2.2, 1]})
    cmap = ListedColormap([STATUS_COLOR["fail"], STATUS_COLOR["partial"], STATUS_COLOR["success"]])  # 0, 1, 2 → 색
    axes[0].imshow(matrix[:, order], aspect="auto", cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
    axes[0].set_yticks(range(len(ids)))
    axes[0].set_yticklabels(ids, fontsize=8)
    axes[0].set_xlabel(f"{len(configs)} parameter sets (blur, Canny low, high), sorted by #success")
    axes[0].set_title("Every image x every parameter set (green success, yellow partial, red fail)")
    counts = np.array(summary["per_config_success"])[order]
    axes[1].bar(range(len(counts)), counts, color="#2563c9", width=1.0)
    axes[1].axhline(summary["oracle_success"], color="#2a9d4b", ls="--",
                    label=f"best set chosen per image = {summary['oracle_success']}/20")
    axes[1].axhline(summary["best"]["success"], color="#c8402f", ls=":",
                    label=f"best single set = {summary['best']['success']}/20")
    d = summary["default"]
    axes[1].axhline(d["success"], color="#888", ls="-.", label=f"default {tuple(d['config'])} = {d['success']}/20")
    axes[1].set_xlim(-0.5, len(counts) - 0.5)
    axes[1].set_ylabel("# success (of 20)")
    axes[1].legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    return save(fig, path)


def dilemma_figure(configs, matrix, ids, pairs, path):
    """두 이미지의 성공 영역(Canny low × high, 블러별 최대)이 겹치지 않는 것을 보여 준다.

    Args:
        configs: 조합 목록.
        matrix: (20, 266) 판정 행렬.
        ids: 이미지 id 목록.
        pairs: 성공 조합이 겹치지 않는 (id, id) 쌍 목록. 실행 결과 앞의 두 쌍은 (S03, T04), (S04, C02).
        path: 저장 경로(09_dilemma.png).

    Returns:
        저장한 경로.
    """
    from .evaluate import SWEEP_HIGH, SWEEP_LOW
    fig, axes = plt.subplots(1, len(pairs) * 2, figsize=(4.0 * len(pairs) * 2, 3.8))
    axes = np.atleast_1d(axes)
    cmap = ListedColormap(["#f3f3f3", STATUS_COLOR["fail"], STATUS_COLOR["partial"], STATUS_COLOR["success"]])
    k = 0
    for a, b in pairs:
        for name in (a, b):
            i = ids.index(name)
            # (7, 7) 격자. −1은 "low ≥ high라 시험하지 않은 칸". 블러 7가지 중 가장 좋은 판정을 칸마다 남긴다.
            grid = np.full((len(SWEEP_LOW), len(SWEEP_HIGH)), -1)
            best_blur = {}
            for j, (bl, lo, hi) in enumerate(configs):
                r, c = SWEEP_LOW.index(lo), SWEEP_HIGH.index(hi)
                if matrix[i, j] > grid[r, c]:
                    grid[r, c] = matrix[i, j]
                    best_blur[(r, c)] = bl  # 튜플 (r, c)를 dict의 키로 쓸 수 있다
            ax = axes[k]
            ax.imshow(grid + 1, cmap=cmap, vmin=0, vmax=3, origin="lower")  # +1로 −1~2를 색 번호 0~3에 맞춘다
            for (r, c), bl in best_blur.items():
                if grid[r, c] == 2:
                    ax.text(c, r, f"b{bl}", ha="center", va="center", fontsize=7, color="white")
            ax.set_xticks(range(len(SWEEP_HIGH)))
            ax.set_xticklabels(SWEEP_HIGH, fontsize=7)
            ax.set_yticks(range(len(SWEEP_LOW)))
            ax.set_yticklabels(SWEEP_LOW, fontsize=7)
            ax.set_xlabel("Canny high")
            ax.set_ylabel("Canny low")
            ax.set_title(f"{name}: best over blur", fontsize=10)
            k += 1
    fig.suptitle("Success regions of image pairs do not overlap (b = blur size of a successful set)", fontsize=11)
    fig.tight_layout()
    return save(fig, path)


def rule_variant_figure(variants, ids, path):
    """규칙을 더하고 뺄 때 이미지별 판정 변화.

    Args:
        variants: evaluate.rule_experiment의 결과(7개).
        ids: 이미지 id 목록.
        path: 저장 경로(10_rule_variants.png).

    Returns:
        저장한 경로.
    """
    code = {"fail": 0, "partial": 1, "success": 2, "unknown": 1}
    # 이중 리스트 컴프리헨션 → (규칙 7, 이미지 20) 배열. 바깥 for가 행, 안쪽 for가 열이다.
    mat = np.array([[code[v["status"][i]] for i in ids] for v in variants])
    fig, ax = plt.subplots(figsize=(14, 0.55 * len(variants) + 1.4))
    cmap = ListedColormap([STATUS_COLOR["fail"], STATUS_COLOR["partial"], STATUS_COLOR["success"]])
    ax.imshow(mat, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    names = {"V0 기본 규칙": "V0 baseline rules", "V1 닫힘 연산 제거": "V1 - morphological close",
             "V2 + 색 채널별 엣지": "V2 + per-channel color edges", "V3 + 자동 Canny 임계값": "V3 + auto Canny (median)",
             "V4 + CLAHE 대비 향상": "V4 + CLAHE contrast", "V5 + 근사 허용 오차 2배": "V5 + approx epsilon x2",
             "V6 V2~V5 모두": "V6 V2+V3+V4+V5"}
    ax.set_yticks(range(len(variants)))
    ax.set_yticklabels([f"{names.get(v['name'], v['name'])} ({v['success']}/20)" for v in variants], fontsize=9)
    ax.set_xticks(range(len(ids)))
    ax.set_xticklabels(ids, fontsize=8)
    base = variants[0]["status"]
    # enumerate(…, start=1)은 번호를 1부터 센다. variants[1:]이 1번 줄부터 그려지므로 줄 번호와 맞춘다.
    for r, v in enumerate(variants[1:], start=1):
        for c, i in enumerate(ids):
            if v["status"][i] != base[i]:
                ax.text(c, r, "+" if code[v["status"][i]] > code[base[i]] else "-", ha="center", va="center",
                        color="white", fontsize=12, fontweight="bold")
    ax.set_title("Adding / removing rules (+ better than V0, - worse than V0)")
    fig.tight_layout()
    return save(fig, path)


def aspect_figure(rows, path):
    """보너스 2: 결과 종횡비 오차 — 변 길이 방법 vs 소실점(Zhang) 방법.

    Args:
        rows: 평가 행 목록. aspect_error가 있고 실패가 아닌 행만 그린다.
        path: 저장 경로(11_aspect_ratio.png).

    Returns:
        저장한 경로.
    """
    sel = [r for r in rows if "aspect_error" in r and r["status"] != "fail"]
    ids = [r["id"] for r in sel]
    x = np.arange(len(sel))
    fig, ax = plt.subplots(figsize=(13, 3.8))
    # 막대 두 개를 x − 0.2, x + 0.2에 폭 0.4로 나란히 그린다.
    ax.bar(x - 0.2, [r["distance_aspect_error"] * 100 for r in sel], 0.4, color="#bbbbbb", label="side-length max")
    ax.bar(x + 0.2, [r["aspect_error"] * 100 for r in sel], 0.4, color="#2563c9", label="perspective (Zhang & He)")
    ax.set_xticks(x)
    ax.set_xticklabels(ids, fontsize=8)
    ax.set_ylabel("aspect ratio error (%)")
    ax.set_yscale("symlog", linthresh=10)  # 0~10%는 일반 눈금, 그 위는 로그 눈금. 0.3%와 142%를 한 그림에 담는다
    ax.axhline(5, color="#c8402f", ls=":", lw=1, label="5%")
    ax.legend(fontsize=8)
    ax.set_title("Bonus 2: output aspect ratio vs true paper ratio (detected images only)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return save(fig, path)


def convolution_figure(bench, sample, path):
    """보너스 1: 이중 for문·벡터화·OpenCV 실행 시간과 결과 차이.

    Args:
        bench: run_all.convolution_bonus의 결과 dict.
        sample: {"blurred": 벡터화 결과, "diff": |NumPy − OpenCV|} 두 (480, 360) 배열.
        path: 저장 경로(12_convolution.png).

    Returns:
        저장한 경로.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.0), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    names = list(bench["times"].keys())
    secs = [bench["times"][n] for n in names]
    bars = axes[0].barh(names, secs, color=["#c8402f", "#2563c9", "#2563c9", "#2563c9", "#2a9d4b"][:len(names)])
    axes[0].set_xscale("log")  # 이중 for문과 OpenCV의 시간이 수백 배 차이 나므로 로그 눈금
    axes[0].bar_label(bars, labels=[f"{s * 1000:.2f} ms" for s in secs], fontsize=8, padding=3)
    axes[0].set_xlabel("seconds (log)")
    axes[0].set_title(f"Gaussian {bench['ksize']}x{bench['ksize']} on {bench['shape'][1]}x{bench['shape'][0]} gray")
    axes[0].invert_yaxis()
    axes[1].imshow(sample["blurred"], cmap="gray")
    axes[1].set_title("NumPy vectorized result")
    axes[1].axis("off")
    im = axes[2].imshow(sample["diff"], cmap="magma")
    axes[2].set_title(f"|NumPy - OpenCV| (max {sample['diff'].max():.1e})")
    axes[2].axis("off")
    fig.colorbar(im, ax=axes[2], fraction=0.046)
    fig.tight_layout()
    return save(fig, path)


def scan_gallery(items, path):
    """성공한 이미지의 투시 변환 결과와 적응형 이진화 결과.

    Args:
        items: (id, warped, scanned) 목록. 최대 12개.
        path: 저장 경로(13_scans.png).

    Returns:
        저장한 경로.
    """
    n = len(items)
    cols = min(6, n)
    rows = int(np.ceil(n / cols)) * 2  # 한 장마다 위(warped)·아래(scanned) 두 줄
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 2.6))
    axes = np.atleast_2d(axes)
    for k, (name, warped, scanned) in enumerate(items):
        r, c = (k // cols) * 2, k % cols
        axes[r, c].imshow(rgb(warped))
        axes[r, c].set_title(f"{name} warped", fontsize=8)
        axes[r + 1, c].imshow(scanned, cmap="gray")
        axes[r + 1, c].set_title(f"{name} adaptive threshold", fontsize=8)
    for ax in axes.flat:
        ax.axis("off")
    fig.tight_layout()
    return save(fig, path)


def threshold_comparison(warped, path):
    """그림자 있는 결과에서 전역 이진화(Otsu)와 적응형 이진화 비교.

    Otsu는 이미지 전체에서 임계값 하나를 고르므로 그림자 진 쪽이 통째로 검정이 된다.

    Args:
        warped: S02의 투시 변환 결과 BGR.
        path: 저장 경로(14_threshold.png).

    Returns:
        저장한 경로.
    """
    from .scanner import enhance
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    # threshold는 (고른 임계값, 결과 이미지)를 돌려준다. 임계값은 쓰지 않아 _로 버린다.
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = enhance(warped)
    fig, axes = plt.subplots(1, 3, figsize=(12, 5.2))
    for ax, img, title in zip(axes, (gray, otsu, adaptive),
                              ("warped (gray)", "global Otsu threshold", "adaptive Gaussian threshold")):
        ax.imshow(img, cmap="gray")
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.tight_layout()
    return save(fig, path)
