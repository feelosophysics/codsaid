"""이미지 탐색적 분석(EDA): 밝기 히스토그램과 문서 경계의 대비를 측정한다.

정답 꼭짓점이 있으면 문서 안·밖 픽셀을 나눠 "배경 대비 문서가 얼마나 밝은가"와
"문서 경계를 가로지르는 밝기 차(엣지 세기)"를 직접 잴 수 있다.

E01 실행 결과: 문서 평균 225.2, 배경 평균 69.8, 경계를 가로지르는 밝기 차 중앙값 171, 경계 엣지 검출률 100%.
전체 밝기 평균·표준편차만으로는 검출 성공을 설명하지 못하고, 경계의 밝기 차가 결정한다는 것이
이 파일이 보이려는 내용이다(보고서 2장, outputs/03_histogram_by_condition.png).
"""
import cv2
import numpy as np

from . import geometry


def to_gray(image):
    """BGR이면 회색으로 바꾸고, 이미 회색이면 그대로 돌려준다.

    Args:
        image: (H, W, 3) BGR 또는 (H, W) 회색.

    Returns:
        numpy.ndarray: (H, W) 회색 이미지.
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def histogram(gray):
    """256단계 밝기 히스토그램 (픽셀 비율).

    Args:
        gray: (H, W) uint8 회색 이미지.

    Returns:
        numpy.ndarray: (256,) 배열. hist[v]는 밝기가 v인 픽셀의 비율이고 합은 1이다.
    """
    # ravel은 (H, W)를 (H·W,) 한 줄로 편다. bincount는 값마다 개수를 센다: [0, 0, 3] → [2, 0, 0, 1].
    # minlength=256은 255까지 모든 칸을 만든다(밝은 픽셀이 없어도 길이 256).
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    return hist / hist.sum()  # 개수 → 비율. 이미지 크기가 달라도 비교할 수 있다


def document_mask(shape, corners):
    """정답 사각형 안쪽이 True인 마스크를 만든다.

    Args:
        shape: 이미지의 shape. 앞의 (H, W)만 쓴다.
        corners: 정답 네 꼭짓점 [[x, y], ...].

    Returns:
        numpy.ndarray: (H, W) bool 배열. gray[mask]는 문서 픽셀, gray[~mask]는 배경 픽셀만 뽑은 1차원 배열이다.
    """
    mask = np.zeros(shape[:2], np.uint8)
    # fillPoly는 다각형 안을 값 1로 칠한다(mask를 제자리에서 바꾼다). 좌표는 정수여야 해서 반올림한다.
    cv2.fillPoly(mask, [np.asarray(corners, np.float64).round().astype(np.int32)], 1)
    return mask.astype(bool)  # 0/1 → False/True. ~mask는 참·거짓을 뒤집는다


def boundary_samples(corners, step=4.0, offset=6.0):
    """정답 사각형 네 변을 따라 안쪽·바깥쪽으로 offset만큼 떨어진 점 쌍을 만든다.

    반환: (경계 위 점, 안쪽 점, 바깥쪽 점) — 각각 (N,2)

    안쪽 점의 밝기 − 바깥쪽 점의 밝기가 "경계를 가로지르는 밝기 차"다. 이것이 작으면 Canny가 경계를 놓친다.

    Args:
        corners: 정답 네 꼭짓점.
        step: 변을 따라 점을 찍는 간격(픽셀).
        offset: 경계에서 안·밖으로 떨어뜨릴 거리(픽셀).

    Returns:
        tuple: (on, inner, outer). 세 배열 모두 (N, 2)이고 같은 행끼리 짝이다.
    """
    q = geometry.order_points(corners)
    center = q.mean(axis=0)
    on, inner, outer = [], [], []
    # zip(q, np.roll(q, -1, axis=0))은 (TL, TR), (TR, BR), (BR, BL), (BL, TL) 네 변을 준다.
    for a, b in zip(q, np.roll(q, -1, axis=0)):
        length = np.linalg.norm(b - a)
        n = max(2, int(length / step))
        # linspace(0.08, 0.92, n)은 0.08부터 0.92까지 n개를 같은 간격으로. [:, None]으로 (n,) → (n, 1).
        t = np.linspace(0.08, 0.92, n)[:, None]  # 모서리 근처는 두 변이 섞이므로 뺀다
        # (2,) + (2,) × (n, 1) → (n, 2) 브로드캐스팅. 변 위의 점 n개.
        pts = a + (b - a) * t
        # 변 방향 (dx, dy)를 90° 돌린 (−dy, dx)를 길이로 나눠 길이 1인 법선 벡터를 만든다.
        normal = np.array([-(b - a)[1], (b - a)[0]]) / length
        # 변의 중점에서 중심을 향한 벡터와 법선의 내적이 음수면 법선이 바깥을 향한 것이다.
        if np.dot(center - (a + b) / 2, normal) < 0:
            normal = -normal  # 안쪽을 향하게
        on.append(pts)
        inner.append(pts + normal * offset)
        outer.append(pts - normal * offset)
    # vstack은 (n₁, 2), (n₂, 2), ... 네 배열을 세로로 이어 (N, 2) 하나로 만든다.
    return np.vstack(on), np.vstack(inner), np.vstack(outer)


def sample(gray, pts):
    """점 좌표 위치의 픽셀 값을 읽는다(가장 가까운 픽셀).

    Args:
        gray: (H, W) 이미지.
        pts: (N, 2) 점 배열, 각 행이 (x, y).

    Returns:
        numpy.ndarray: (N,) float64 픽셀 값.
    """
    h, w = gray.shape
    # 점이 이미지 밖으로 나가면 인덱스 오류가 나므로 clip으로 0 ~ w−1, 0 ~ h−1 안에 가둔다.
    x = np.clip(pts[:, 0].round().astype(int), 0, w - 1)
    y = np.clip(pts[:, 1].round().astype(int), 0, h - 1)
    # 배열 인덱스는 [행 = y, 열 = x] 순서다. 정수 배열 두 개로 인덱싱하면 같은 위치끼리 짝지은 (N,)개를 뽑는다.
    return gray[y, x].astype(np.float64)


def gradient_magnitude(gray, blur=5):
    """블러 후 Sobel 기울기 크기 (OpenCV Canny와 같은 L1 노름: |gx| + |gy|).

    Canny가 임계값과 비교하는 값과 같은 방식으로 계산해, "경계 기울기 vs Canny 임계값"을 직접 비교할 수 있게 한다.

    Args:
        gray: (H, W) uint8 회색 이미지.
        blur: 먼저 적용할 가우시안 커널 크기.

    Returns:
        numpy.ndarray: (H, W) float64 기울기 크기. E01 경계의 중앙값은 374다.
    """
    g = cv2.GaussianBlur(gray, (blur, blur), 0) if blur > 1 else gray
    # CV_64F는 결과를 실수로 받는다는 뜻이다. uint8로 받으면 음수 기울기(밝 → 어둠)가 0으로 잘린다.
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3)  # 가로 방향 밝기 변화
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3)  # 세로 방향 밝기 변화
    return np.abs(gx) + np.abs(gy)


def edge_recall(edges, on_points, radius=2):
    """경계 위 점 중 반경 radius 안에 Canny 엣지 픽셀이 있는 비율.

    Args:
        edges: Canny 결과 (H, W), 0 또는 255.
        on_points: 경계 위 점 (N, 2).
        radius: 허용 거리(픽셀). 엣지가 경계에서 1~2px 비껴 나도 찾은 것으로 본다.

    Returns:
        float: 0~1. 1이면 경계 전체를 엣지로 찾았다는 뜻이다.
    """
    k = 2 * radius + 1
    # 팽창(dilate)으로 엣지를 k×k만큼 두껍게 만든 뒤 경계 점에서 읽는다. "반경 안에 엣지가 있는가"와 같다.
    near = cv2.dilate(edges, np.ones((k, k), np.uint8))
    # (… > 0)은 True/False 배열, .mean()은 True의 비율이다(True = 1, False = 0).
    return float((sample(near, on_points) > 0).mean())


def image_stats(image, corners=None, canny=(50, 150), blur=5):
    """이미지 한 장의 밝기 통계. corners가 있으면 문서 안·밖과 경계 통계도 낸다.

    Args:
        image: 원본 BGR 이미지.
        corners: 정답 꼭짓점. None이면 전체 통계만 낸다.
        canny: (low, high) Canny 임계값. 기본 파이프라인과 같은 값.
        blur: 블러 커널 크기. 기본 파이프라인과 같은 값.

    Returns:
        dict: mean, std, p5, median, p95 등 숫자 통계. 키 목록은 아래 코드와 같다.
    """
    gray = to_gray(image)
    vals = gray.ravel()
    # percentile(값들, [5, 50, 95])는 하위 5%·50%·95% 위치의 값 세 개를 준다.
    p5, p50, p95 = np.percentile(vals, [5, 50, 95])
    stats = {
        "mean": float(vals.mean()), "std": float(vals.std()), "p5": float(p5), "median": float(p50), "p95": float(p95),
        # (vals < 64)는 True/False 배열. .mean()은 64보다 어두운 픽셀의 비율이다.
        "dynamic_range": float(p95 - p5), "dark_fraction": float((vals < 64).mean()),
        "saturated_fraction": float((vals >= 250).mean()),
    }
    if corners is not None:
        mask = document_mask(gray.shape, corners)
        doc, bg = gray[mask], gray[~mask]  # 불리언 마스크로 골라낸 1차원 배열 두 개
        on, inner, outer = boundary_samples(corners)
        step = sample(gray, inner) - sample(gray, outer)  # (N,) 경계 안 − 밖 밝기 차
        grad = gradient_magnitude(gray, blur)
        # *canny는 튜플 (50, 150)을 풀어 두 인자로 넘긴다: Canny(…, 50, 150).
        edges = cv2.Canny(cv2.GaussianBlur(gray, (blur, blur), 0), *canny)
        # update는 dict에 여러 키를 한 번에 추가한다(stats를 제자리에서 바꾼다).
        stats.update({
            "doc_mean": float(doc.mean()), "bg_mean": float(bg.mean()),
            "doc_bg_contrast": float(doc.mean() - bg.mean()),
            "boundary_step_median": float(np.median(np.abs(step))),
            # 하위 10%: 경계 중 가장 약한 부분. 한 군데만 약해도 윤곽선이 끊기므로 중앙값보다 중요하다.
            "boundary_step_p10": float(np.percentile(np.abs(step), 10)),
            "boundary_gradient_median": float(np.median(sample(grad, on))),
            "boundary_edge_recall": edge_recall(edges, on),
            "edge_density": float((edges > 0).mean()),
            "bg_edge_density": float((edges[~mask] > 0).mean()),  # 배경의 엣지 = 윤곽선 후보를 헷갈리게 하는 잡음
        })
    return stats


def darkening_experiment(image, corners, factors=(1.0, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1), noise_sigma=3.0,
                         canny=(50, 150), blur=5, seed=0):
    """밝기를 factor배로 줄이고 같은 크기의 센서 잡음을 더해, 고정 Canny 임계값의 엣지 검출률을 잰다.

    어두워지면 히스토그램이 왼쪽으로 몰리며 폭이 factor배로 좁아진다. 경계의 밝기 차도 factor배가 되지만
    잡음은 그대로라 신호 대 잡음비가 떨어진다. Canny 임계값은 절대값이라 어느 순간 경계 기울기가 임계값 아래로 내려간다.

    실행 결과(E01 경계 기울기 중앙값): ×1.0 374 → ×0.5 188 → ×0.35 132 → ×0.25 94. 밝기에 거의 비례한다.
    ×0.35에서 중앙값은 이미 high 150 아래지만, 경계 점의 약 4%가 150을 넘고 나머지가 모두 low 50 이상이라
    Canny가 그 점들에서 시작해 경계를 이어 간다(검출률 100%). ×0.25에서는 150을 넘는 점이 없어 0%가 된다.

    Args:
        image: 원본 BGR 이미지(보통 E01).
        corners: 정답 꼭짓점.
        factors: 곱할 밝기 배율들.
        noise_sigma: 더할 정규 잡음의 표준편차.
        canny: (low, high) 고정 임계값.
        blur: 블러 커널 크기.
        seed: 잡음 난수의 시작값. 같은 seed면 결과가 같다.

    Returns:
        list: factor마다 dict 한 개. hist, mean, std, boundary_gradient_median, boundary_edge_recall,
        bg_edge_density를 담고, found는 None(run_all.run_eda가 나중에 채운다).
    """
    # default_rng(seed)는 난수 생성기. 같은 seed면 실행할 때마다 같은 잡음이 나와 결과를 재현할 수 있다.
    rng = np.random.default_rng(seed)
    gray = to_gray(image).astype(np.float64)
    on, _, _ = boundary_samples(corners)
    rows = []
    for f in factors:
        # gray × f + 잡음 (H, W) → 0~255로 자르고 반올림 → uint8. 원본 gray는 바뀌지 않는다(새 배열).
        dark = np.clip(gray * f + rng.normal(0, noise_sigma, gray.shape), 0, 255).round().astype(np.uint8)
        grad = gradient_magnitude(dark, blur)
        edges = cv2.Canny(cv2.GaussianBlur(dark, (blur, blur), 0), *canny)
        mask = document_mask(dark.shape, corners)
        rows.append({
            "factor": f, "hist": histogram(dark), "mean": float(dark.mean()), "std": float(dark.std()),
            "boundary_gradient_median": float(np.median(sample(grad, on))),
            "boundary_edge_recall": edge_recall(edges, on),
            "bg_edge_density": float((edges[~mask] > 0).mean()),
            "found": None,
        })
    return rows
