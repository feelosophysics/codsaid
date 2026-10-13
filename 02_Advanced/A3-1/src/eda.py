"""이미지 탐색적 분석(EDA): 밝기 히스토그램과 문서 경계의 대비를 측정한다.

정답 꼭짓점이 있으면 문서 안·밖 픽셀을 나눠 "배경 대비 문서가 얼마나 밝은가"와
"문서 경계를 가로지르는 밝기 차(엣지 세기)"를 직접 잴 수 있다.
"""
import cv2
import numpy as np

from . import geometry


def to_gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def histogram(gray):
    """256단계 밝기 히스토그램 (픽셀 비율)."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    return hist / hist.sum()


def document_mask(shape, corners):
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.asarray(corners, np.float64).round().astype(np.int32)], 1)
    return mask.astype(bool)


def boundary_samples(corners, step=4.0, offset=6.0):
    """정답 사각형 네 변을 따라 안쪽·바깥쪽으로 offset만큼 떨어진 점 쌍을 만든다.

    반환: (경계 위 점, 안쪽 점, 바깥쪽 점) — 각각 (N,2)
    """
    q = geometry.order_points(corners)
    center = q.mean(axis=0)
    on, inner, outer = [], [], []
    for a, b in zip(q, np.roll(q, -1, axis=0)):
        length = np.linalg.norm(b - a)
        n = max(2, int(length / step))
        t = np.linspace(0.08, 0.92, n)[:, None]  # 모서리 근처는 두 변이 섞이므로 뺀다
        pts = a + (b - a) * t
        normal = np.array([-(b - a)[1], (b - a)[0]]) / length
        if np.dot(center - (a + b) / 2, normal) < 0:
            normal = -normal  # 안쪽을 향하게
        on.append(pts)
        inner.append(pts + normal * offset)
        outer.append(pts - normal * offset)
    return np.vstack(on), np.vstack(inner), np.vstack(outer)


def sample(gray, pts):
    h, w = gray.shape
    x = np.clip(pts[:, 0].round().astype(int), 0, w - 1)
    y = np.clip(pts[:, 1].round().astype(int), 0, h - 1)
    return gray[y, x].astype(np.float64)


def gradient_magnitude(gray, blur=5):
    """블러 후 Sobel 기울기 크기 (OpenCV Canny와 같은 L1 노름: |gx| + |gy|)."""
    g = cv2.GaussianBlur(gray, (blur, blur), 0) if blur > 1 else gray
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3)
    return np.abs(gx) + np.abs(gy)


def edge_recall(edges, on_points, radius=2):
    """경계 위 점 중 반경 radius 안에 Canny 엣지 픽셀이 있는 비율."""
    k = 2 * radius + 1
    near = cv2.dilate(edges, np.ones((k, k), np.uint8))
    return float((sample(near, on_points) > 0).mean())


def image_stats(image, corners=None, canny=(50, 150), blur=5):
    """이미지 한 장의 밝기 통계. corners가 있으면 문서 안·밖과 경계 통계도 낸다."""
    gray = to_gray(image)
    vals = gray.ravel()
    p5, p50, p95 = np.percentile(vals, [5, 50, 95])
    stats = {
        "mean": float(vals.mean()), "std": float(vals.std()), "p5": float(p5), "median": float(p50), "p95": float(p95),
        "dynamic_range": float(p95 - p5), "dark_fraction": float((vals < 64).mean()),
        "saturated_fraction": float((vals >= 250).mean()),
    }
    if corners is not None:
        mask = document_mask(gray.shape, corners)
        doc, bg = gray[mask], gray[~mask]
        on, inner, outer = boundary_samples(corners)
        step = sample(gray, inner) - sample(gray, outer)
        grad = gradient_magnitude(gray, blur)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (blur, blur), 0), *canny)
        stats.update({
            "doc_mean": float(doc.mean()), "bg_mean": float(bg.mean()),
            "doc_bg_contrast": float(doc.mean() - bg.mean()),
            "boundary_step_median": float(np.median(np.abs(step))),
            "boundary_step_p10": float(np.percentile(np.abs(step), 10)),
            "boundary_gradient_median": float(np.median(sample(grad, on))),
            "boundary_edge_recall": edge_recall(edges, on),
            "edge_density": float((edges > 0).mean()),
            "bg_edge_density": float((edges[~mask] > 0).mean()),
        })
    return stats


def darkening_experiment(image, corners, factors=(1.0, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1), noise_sigma=3.0,
                         canny=(50, 150), blur=5, seed=0):
    """밝기를 factor배로 줄이고 같은 크기의 센서 잡음을 더해, 고정 Canny 임계값의 엣지 검출률을 잰다.

    어두워지면 히스토그램이 왼쪽으로 몰리며 폭이 factor배로 좁아진다. 경계의 밝기 차도 factor배가 되지만
    잡음은 그대로라 신호 대 잡음비가 떨어진다. Canny 임계값은 절대값이라 어느 순간 경계 기울기가 임계값 아래로 내려간다.
    """
    rng = np.random.default_rng(seed)
    gray = to_gray(image).astype(np.float64)
    on, _, _ = boundary_samples(corners)
    rows = []
    for f in factors:
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
