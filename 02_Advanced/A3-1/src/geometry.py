"""꼭짓점 정렬과 종횡비 계산. 좌표 처리는 외부 기하 라이브러리 없이 NumPy 연산으로만 구현한다.

좌표계는 OpenCV 이미지 좌표다. x는 오른쪽, y는 아래쪽으로 커진다.
네 점은 항상 (좌상, 우상, 우하, 좌하) = (TL, TR, BR, BL) 순서로 다룬다.
"""
import numpy as np


def as_points(points):
    """(4,1,2)·(4,2)·리스트 입력을 float64 (4,2) 배열로 바꾼다."""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if pts.shape != (4, 2):
        raise ValueError(f"꼭짓점은 4개여야 한다: shape={pts.shape}")
    return pts


def order_points_sum_diff(points):
    """널리 쓰이는 합·차 규칙. 비교용으로만 둔다.

    TL은 x+y가 가장 작고 BR은 가장 크다. TR은 y-x가 가장 작고 BL은 가장 크다.
    문서가 45° 가까이 돌아가면 두 점의 x+y가 같아져 같은 점이 두 번 뽑힐 수 있다.
    """
    pts = as_points(points)
    s = pts.sum(axis=1)
    d = pts[:, 1] - pts[:, 0]
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def order_points(points):
    """네 점을 TL, TR, BR, BL 순서로 정렬한다.

    1. 무게중심 기준 각도 atan2(dy, dx)로 정렬한다. y축이 아래로 향하므로 각도 오름차순은
       화면에서 시계 방향이다. 볼록 사각형이면 이웃한 점끼리 이어진다.
    2. 시계 방향으로 이어진 네 변 중 방향이 오른쪽(+x)에 가장 가까운 변을 윗변으로 본다.
       그 변의 시작점이 TL이다. 문서가 ±45° 안에서 돌아가 있으면 실제 윗변이 뽑힌다.
    """
    pts = as_points(points)
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    cw = pts[np.argsort(angles, kind="stable")]
    edges = np.roll(cw, -1, axis=0) - cw
    lengths = np.linalg.norm(edges, axis=1)
    lengths[lengths == 0] = 1.0
    alignment = edges[:, 0] / lengths  # cos(변 방향, +x)
    start = int(np.argmax(np.round(alignment, 12)))  # 정확히 45°면 앞선 변을 고른다
    return np.roll(cw, -start, axis=0)


def polygon_area(points):
    """신발끈 공식으로 다각형 면적을 구한다 (부호 없음)."""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def is_convex(points):
    """연속한 두 변의 외적 부호가 모두 같으면 볼록 다각형이다."""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    a = np.roll(pts, -1, axis=0) - pts
    b = np.roll(pts, -2, axis=0) - np.roll(pts, -1, axis=0)
    cross = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return bool(np.all(cross > 0) or np.all(cross < 0))


def side_lengths(quad):
    """정렬된 사각형의 윗변·아랫변·왼변·오른변 길이."""
    tl, tr, br, bl = as_points(quad)
    return {"top": float(np.linalg.norm(tr - tl)), "bottom": float(np.linalg.norm(br - bl)),
            "left": float(np.linalg.norm(bl - tl)), "right": float(np.linalg.norm(br - tr))}


def output_size_by_distance(quad):
    """원본 좌표 간 거리로 결과 이미지 크기를 정한다 (보너스 2 기본형).

    마주 보는 두 변 중 긴 쪽을 쓴다. 원근 때문에 먼 변은 짧게 찍히므로, 긴 변이 실제 길이에 더 가깝다.
    """
    s = side_lengths(quad)
    return max(1, int(round(max(s["top"], s["bottom"])))), max(1, int(round(max(s["left"], s["right"]))))


def estimate_aspect_ratio(quad, image_shape):
    """원근으로 찍힌 직사각형의 실제 가로/세로 비율을 추정한다 (보너스 2 확장).

    Zhang & He(2007)의 화이트보드 스캔 방법이다. 카메라 주점이 이미지 중심이고 픽셀이 정사각형이라고
    가정한다. 네 점으로 초점거리 f를 먼저 구하고, 그 카메라로 두 변의 3차원 방향 길이를 비교한다.
    정면 촬영처럼 f를 구할 수 없으면 거리 방법으로 돌아간다.

    반환: (aspect, focal 또는 None, method 문자열)
    """
    tl, tr, br, bl = as_points(quad)
    h, w = image_shape[:2]
    u0, v0 = w / 2.0, h / 2.0
    # 주점을 원점으로 옮긴 동차 좌표. m1=TL, m2=TR, m3=BL, m4=BR (논문의 번호)
    m1, m2, m3, m4 = (np.array([p[0] - u0, p[1] - v0, 1.0]) for p in (tl, tr, bl, br))
    k2 = np.dot(np.cross(m1, m4), m3) / np.dot(np.cross(m2, m4), m3)
    k3 = np.dot(np.cross(m1, m4), m2) / np.dot(np.cross(m3, m4), m2)
    n2 = k2 * m2 - m1  # 3차원 가로 방향에 비례
    n3 = k3 * m3 - m1  # 3차원 세로 방향에 비례

    width, height = output_size_by_distance(quad)
    fallback = (width / height, None, "distance")
    denom = n2[2] * n3[2]
    if abs(denom) < 1e-9:
        return fallback  # 소실점이 무한대: 두 변이 영상면과 평행
    f2 = -(n2[0] * n3[0] + n2[1] * n3[1]) / denom
    if not np.isfinite(f2) or f2 <= 0:
        return fallback
    f = np.sqrt(f2)
    # 초점거리가 너무 작거나 크면 수치적으로 불안정하다(거의 정면 촬영). 이미지 크기 기준으로 거른다.
    if not (0.2 * max(w, h) < f < 20 * max(w, h)):
        return fallback
    a_inv = np.diag([1 / f, 1 / f, 1.0])  # 주점을 원점으로 옮겼으므로 A^-1 = diag(1/f, 1/f, 1)
    r2 = a_inv @ n2
    r3 = a_inv @ n3
    aspect = float(np.sqrt(np.dot(r2, r2) / np.dot(r3, r3)))
    return aspect, float(f), "zhang"


def output_size_by_aspect(quad, image_shape):
    """추정한 실제 종횡비로 결과 크기를 정한다. 면적은 거리 방법과 비슷하게 유지한다."""
    width, height = output_size_by_distance(quad)
    aspect, _, _ = estimate_aspect_ratio(quad, image_shape)
    area = width * height
    new_h = max(1, int(round(np.sqrt(area / aspect))))
    new_w = max(1, int(round(new_h * aspect)))
    return new_w, new_h


def corner_error(detected, truth):
    """두 사각형의 꼭짓점 오차. 회전 순서(시작점) 차이는 허용하고 가장 잘 맞는 대응을 쓴다.

    반환: (최대 꼭짓점 거리, 평균 거리, 시작점 이동 수). 이동 수가 0이 아니면 결과가 90° 단위로 돌아간 것이다.
    """
    d = order_points(detected)
    t = as_points(truth)
    best = None
    for shift in range(4):
        dist = np.linalg.norm(np.roll(d, -shift, axis=0) - t, axis=1)
        cand = (float(dist.max()), float(dist.mean()), shift)
        if best is None or cand[0] < best[0]:
            best = cand
    return best
