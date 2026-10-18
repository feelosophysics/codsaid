"""꼭짓점 정렬과 종횡비 계산. 좌표 처리는 외부 기하 라이브러리 없이 NumPy 연산으로만 구현한다.

좌표계는 OpenCV 이미지 좌표다. x는 오른쪽, y는 아래쪽으로 커진다.
네 점은 항상 (좌상, 우상, 우하, 좌하) = (TL, TR, BR, BL) 순서로 다룬다.

점 배열의 shape:
    (4, 2)     네 점, 각 행이 (x, y). pts[:, 0]은 모든 x, pts[:, 1]은 모든 y
    (4, 1, 2)  OpenCV 윤곽선 함수가 주는 모양. 가운데 길이 1인 축이 하나 더 있다
이미지 배열은 image[y, x]로 읽지만 점은 (x, y)로 적는다. 순서가 반대라는 점에 주의한다.

미션 요구사항 "좌표 정렬 직접 구현"이 order_points다. 정렬 과정의 숫자 추적은
study/code-walkthrough.md 3장, 종횡비 수식 유도는 study/a3-1.html 8절에 있다.
"""
import numpy as np


def as_points(points):
    """(4,1,2)·(4,2)·리스트 입력을 float64 (4,2) 배열로 바꾼다.

    Args:
        points: 네 점. NumPy 배열, 리스트 [[x, y], ...] 모두 된다.

    Returns:
        numpy.ndarray: (4, 2) float64 배열. 입력이 이미 float64 배열이면 같은 메모리를 볼 수 있으므로
        돌려받은 배열을 제자리에서 고치지 않는다.

    Raises:
        ValueError: 점이 4개가 아닌 경우.
    """
    # asarray는 리스트를 배열로 바꾸고, 이미 원하는 자료형의 배열이면 복사하지 않는다.
    # reshape(-1, 2)의 -1은 "나머지 원소 수에 맞춰 자동으로"라는 뜻이다. (4, 1, 2)의 8개 원소 → (4, 2).
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if pts.shape != (4, 2):
        # raise는 함수를 즉시 멈추고 오류를 알린다. 꼭짓점 3개로 계산을 계속하면 엉뚱한 결과가 나오기 때문이다.
        raise ValueError(f"꼭짓점은 4개여야 한다: shape={pts.shape}")
    return pts


def order_points_sum_diff(points):
    """널리 쓰이는 합·차 규칙. 비교용으로만 둔다.

    TL은 x+y가 가장 작고 BR은 가장 크다. TR은 y-x가 가장 작고 BL은 가장 크다.
    문서가 45° 가까이 돌아가면 두 점의 x+y가 같아져 같은 점이 두 번 뽑힐 수 있다.

    설명용 예: 45° 돌린 정사각형 (200,100), (300,200), (200,300), (100,200)은
    x+y = [300, 500, 500, 300], y−x = [−100, −100, 100, 100]으로 동점이 생긴다.
    결과의 TL과 TR이 둘 다 (200, 100)이 된다(tests의 test_sum_diff_rule_breaks_at_45_degrees).

    Args:
        points: 순서가 섞인 네 점.

    Returns:
        numpy.ndarray: (4, 2) 배열. 같은 점이 두 번 들어갈 수 있다.
    """
    pts = as_points(points)
    # axis=1은 "각 행 안에서(가로로)" 계산한다. (4, 2) → (4,). 행마다 x + y.
    s = pts.sum(axis=1)
    d = pts[:, 1] - pts[:, 0]  # (4,) 행마다 y − x
    # argmin은 가장 작은 값의 "위치(번호)"를 준다. pts[번호]로 그 점을 꺼낸다. 동점이면 앞의 번호를 준다.
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def order_points(points):
    """네 점을 TL, TR, BR, BL 순서로 정렬한다.

    1. 무게중심 기준 각도 atan2(dy, dx)로 정렬한다. y축이 아래로 향하므로 각도 오름차순은
       화면에서 시계 방향이다. 볼록 사각형이면 이웃한 점끼리 이어진다.
    2. 시계 방향으로 이어진 네 변 중 방향이 오른쪽(+x)에 가장 가까운 변을 윗변으로 본다.
       그 변의 시작점이 TL이다. 문서가 ±45° 안에서 돌아가 있으면 실제 윗변이 뽑힌다.

    이 정렬이 틀리면 warp_document의 목적지 네 점과 짝이 어긋나 결과가 90°·180° 돌아가거나 뒤집힌다.

    Args:
        points: 볼록 사각형의 네 점. 순서는 상관없다.

    Returns:
        numpy.ndarray: TL, TR, BR, BL 순서의 (4, 2) float64 새 배열.

    Raises:
        ValueError: 점이 4개가 아닌 경우(as_points).
    """
    pts = as_points(points)
    # axis=0은 "행들을 따라(세로로)" 계산한다. (4, 2) → (2,). 네 점의 평균 (x, y) = 무게중심.
    center = pts.mean(axis=0)
    # arctan2(dy, dx)는 중심에서 각 점을 향한 각도(라디안, −π~π). 인자 순서가 (y, x)다. 결과 (4,).
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    # argsort는 "작은 값부터 정렬했을 때의 원래 위치 목록"을 준다. pts[목록]은 그 순서로 행을 다시 뽑은 새 배열.
    # kind="stable"은 같은 각도가 있을 때 원래 순서를 지켜 결과가 항상 같게 한다.
    cw = pts[np.argsort(angles, kind="stable")]
    # np.roll(cw, -1, axis=0)은 행을 한 칸씩 위로 민다: [p0, p1, p2, p3] → [p1, p2, p3, p0].
    # 그래서 빼면 각 점에서 다음 점으로 가는 변 벡터 (4, 2)가 된다. 마지막 변은 p3 → p0.
    edges = np.roll(cw, -1, axis=0) - cw
    lengths = np.linalg.norm(edges, axis=1)  # (4,) 변마다 √(dx² + dy²)
    # lengths == 0은 True/False 배열(마스크). 그 위치에만 1.0을 넣는다(제자리 수정). 0으로 나누기를 막는다.
    lengths[lengths == 0] = 1.0
    alignment = edges[:, 0] / lengths  # cos(변 방향, +x)
    # round(…, 12)로 1e-15 수준의 계산 오차를 지워, 45°처럼 두 변이 같을 때 항상 앞선 변이 뽑히게 한다.
    start = int(np.argmax(np.round(alignment, 12)))  # 정확히 45°면 앞선 변을 고른다
    # 윗변의 시작점(start번)이 맨 앞에 오도록 행을 민다. 시계 방향 순서는 유지되므로 TL, TR, BR, BL이 된다.
    return np.roll(cw, -start, axis=0)


def polygon_area(points):
    """신발끈 공식으로 다각형 면적을 구한다 (부호 없음).

    면적 = ½ |Σ (xᵢ·yᵢ₊₁ − yᵢ·xᵢ₊₁)|. 설명용 예: 4×3 직사각형 (0,0), (4,0), (4,3), (0,3) → 12.
    점이 둘레를 따라 순서대로 있어야 맞다. 순서가 섞이면 엉뚱한 값이 나온다.

    Args:
        points: (N, 2) 또는 (N, 1, 2) 꼭짓점. 둘레 순서대로.

    Returns:
        numpy.float64: 면적(0 이상).
    """
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    x, y = pts[:, 0], pts[:, 1]  # 열 두 개를 각각 (N,) 벡터로
    # np.roll(y, -1)은 [y1, y2, ..., y0]. np.dot은 같은 위치끼리 곱해 모두 더한다(내적).
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def is_convex(points):
    """연속한 두 변의 외적 부호가 모두 같으면 볼록 다각형이다.

    2차원 외적 a×b = aₓ·b_y − a_y·bₓ의 부호는 "a에서 b로 꺾는 방향"이다. 볼록이면 모든 모서리에서 같은 쪽으로 꺾는다.
    설명용 예: 직사각형 (0,0), (4,0), (4,3), (0,3) → [12, 12, 12, 12] 볼록.
    한 점을 안쪽 (1,1)로 옮긴 (0,0), (4,0), (1,1), (0,3) → [4, −5, 3, 12] 오목.

    Args:
        points: (N, 2) 또는 (N, 1, 2) 꼭짓점. 둘레 순서대로.

    Returns:
        bool: 모든 외적이 양수이거나 모두 음수면 True. 0이 하나라도 있으면(세 점이 일직선) False.
    """
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    a = np.roll(pts, -1, axis=0) - pts  # (N, 2) 각 점에서 다음 점으로 가는 변
    b = np.roll(pts, -2, axis=0) - np.roll(pts, -1, axis=0)  # (N, 2) 그다음 변
    cross = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]  # (N,) 모서리마다 외적
    # np.all(조건)은 모든 원소가 참인지. bool()로 NumPy 참/거짓을 파이썬 True/False로 바꾼다.
    return bool(np.all(cross > 0) or np.all(cross < 0))


def side_lengths(quad):
    """정렬된 사각형의 윗변·아랫변·왼변·오른변 길이.

    Args:
        quad: TL, TR, BR, BL 순서의 네 점.

    Returns:
        dict: {"top", "bottom", "left", "right"} → 길이(픽셀). E01은 top 641.9, bottom 568.0이다.
    """
    # (4, 2) 배열을 네 변수에 나눠 담는다. 첫 축(행)을 기준으로 나뉘므로 tl은 (2,) 벡터 [x, y]다.
    tl, tr, br, bl = as_points(quad)
    # tr - tl은 (2,) 벡터. norm은 그 길이 √(dx² + dy²). float()로 파이썬 실수로 바꿔 JSON에 저장할 수 있게 한다.
    return {"top": float(np.linalg.norm(tr - tl)), "bottom": float(np.linalg.norm(br - bl)),
            "left": float(np.linalg.norm(bl - tl)), "right": float(np.linalg.norm(br - tr))}


def output_size_by_distance(quad):
    """원본 좌표 간 거리로 결과 이미지 크기를 정한다 (보너스 2 기본형).

    마주 보는 두 변 중 긴 쪽을 쓴다. 원근 때문에 먼 변은 짧게 찍히므로, 긴 변이 실제 길이에 더 가깝다.

    한계: 강하게 기울이면 가로·세로가 서로 다른 비율로 줄어든다. T01(A4, 실제 0.707)은
    이 방법으로 1.358이 되어 가로로 길쭉한 결과가 나온다. 이 문제를 estimate_aspect_ratio가 푼다.

    Args:
        quad: TL, TR, BR, BL 순서의 네 점.

    Returns:
        tuple: (width, height) 정수 픽셀 수. 최소 1.
    """
    s = side_lengths(quad)
    return max(1, int(round(max(s["top"], s["bottom"])))), max(1, int(round(max(s["left"], s["right"]))))


def estimate_aspect_ratio(quad, image_shape):
    """원근으로 찍힌 직사각형의 실제 가로/세로 비율을 추정한다 (보너스 2 확장).

    Zhang & He(2007)의 화이트보드 스캔 방법이다. 카메라 주점이 이미지 중심이고 픽셀이 정사각형이라고
    가정한다. 네 점으로 초점거리 f를 먼저 구하고, 그 카메라로 두 변의 3차원 방향 길이를 비교한다.
    정면 촬영처럼 f를 구할 수 없으면 거리 방법으로 돌아간다.

    실행 결과: T01 0.743, T02 0.700, T05 0.772 (실제 0.707, 0.707, 0.774). 거리 방법은 1.358, 1.336, 1.876이다.
    수식 유도는 study/a3-1.html 8절에 있고, 이 함수는 그 식을 그대로 옮겼다.

    Args:
        quad: TL, TR, BR, BL 순서의 원본 좌표 (4, 2).
        image_shape: 원본 이미지의 shape. 주점(이미지 중심)을 정하는 데 쓴다.

    Returns:
        tuple: (aspect, focal 또는 None, method 문자열). method는 "zhang" 또는 "distance".
    """
    tl, tr, br, bl = as_points(quad)
    h, w = image_shape[:2]
    u0, v0 = w / 2.0, h / 2.0
    # 주점을 원점으로 옮긴 동차 좌표. m1=TL, m2=TR, m3=BL, m4=BR (논문의 번호)
    # (식 for p in 목록)은 제너레이터: 값을 하나씩 만들어 네 변수에 나눠 담는다. 각 m은 (3,) 벡터 [x−u0, y−v0, 1].
    m1, m2, m3, m4 = (np.array([p[0] - u0, p[1] - v0, 1.0]) for p in (tl, tr, bl, br))
    # np.cross는 3차원 외적 (3,), np.dot은 내적(숫자 하나). k2, k3는 숫자 하나씩이다.
    k2 = np.dot(np.cross(m1, m4), m3) / np.dot(np.cross(m2, m4), m3)
    k3 = np.dot(np.cross(m1, m4), m2) / np.dot(np.cross(m3, m4), m2)
    n2 = k2 * m2 - m1  # 3차원 가로 방향에 비례
    n3 = k3 * m3 - m1  # 3차원 세로 방향에 비례

    width, height = output_size_by_distance(quad)
    fallback = (width / height, None, "distance")  # 아래에서 계산이 불안정하면 이 값을 돌려준다
    denom = n2[2] * n3[2]
    if abs(denom) < 1e-9:
        return fallback  # 소실점이 무한대: 두 변이 영상면과 평행
    f2 = -(n2[0] * n3[0] + n2[1] * n3[1]) / denom
    # isfinite는 inf·nan이 아닌지. f²가 음수면 실제 카메라로 설명할 수 없는 점 배치라 믿지 않는다.
    if not np.isfinite(f2) or f2 <= 0:
        return fallback
    f = np.sqrt(f2)
    # 초점거리가 너무 작거나 크면 수치적으로 불안정하다(거의 정면 촬영). 이미지 크기 기준으로 거른다.
    # "a < f < b"처럼 비교를 이어 쓰면 "a < f and f < b"와 같다.
    if not (0.2 * max(w, h) < f < 20 * max(w, h)):
        return fallback
    a_inv = np.diag([1 / f, 1 / f, 1.0])  # 주점을 원점으로 옮겼으므로 A^-1 = diag(1/f, 1/f, 1)
    r2 = a_inv @ n2  # @는 행렬 곱. (3, 3) @ (3,) → (3,)
    r3 = a_inv @ n3
    aspect = float(np.sqrt(np.dot(r2, r2) / np.dot(r3, r3)))  # 두 3차원 방향의 길이 비
    return aspect, float(f), "zhang"


def output_size_by_aspect(quad, image_shape):
    """추정한 실제 종횡비로 결과 크기를 정한다. 면적은 거리 방법과 비슷하게 유지한다.

    E01 실행 결과: 거리 방법 642 × 857(면적 550,194), 종횡비 0.7058 → 623 × 883.
    높이 = √(면적 / 종횡비), 너비 = 높이 × 종횡비로 정하면 너비/높이가 종횡비가 되고 면적은 거의 같다.

    Args:
        quad: TL, TR, BR, BL 순서의 원본 좌표.
        image_shape: 원본 이미지의 shape.

    Returns:
        tuple: (width, height) 정수 픽셀 수.
    """
    width, height = output_size_by_distance(quad)
    aspect, _, _ = estimate_aspect_ratio(quad, image_shape)  # 필요 없는 두 값은 _로 버린다
    area = width * height
    new_h = max(1, int(round(np.sqrt(area / aspect))))
    new_w = max(1, int(round(new_h * aspect)))
    return new_w, new_h


def corner_error(detected, truth):
    """두 사각형의 꼭짓점 오차. 회전 순서(시작점) 차이는 허용하고 가장 잘 맞는 대응을 쓴다.

    반환: (최대 꼭짓점 거리, 평균 거리, 시작점 이동 수). 이동 수가 0이 아니면 결과가 90° 단위로 돌아간 것이다.

    E01 실행 결과: 최대 1.98px, 평균 1.29px, 이동 0. 평가(evaluate.judge)는 최대 오차를 대각선 길이로 나눠 쓴다.

    Args:
        detected: 검출한 네 점. 순서는 상관없다(안에서 order_points로 정렬한다).
        truth: 정답 네 점. TL, TR, BR, BL 순서.

    Returns:
        tuple: (max_err, mean_err, shift). shift는 0~3.
    """
    d = order_points(detected)
    t = as_points(truth)
    best = None
    # range(4)는 0, 1, 2, 3. 시작점을 한 칸씩 돌려 가며 네 가지 대응을 모두 비교한다.
    for shift in range(4):
        # (4, 2) − (4, 2) → (4, 2) 차이 벡터, norm(axis=1) → (4,) 꼭짓점별 거리
        dist = np.linalg.norm(np.roll(d, -shift, axis=0) - t, axis=1)
        cand = (float(dist.max()), float(dist.mean()), shift)
        if best is None or cand[0] < best[0]:  # 최대 오차가 더 작은 대응을 남긴다
            best = cand
    return best
