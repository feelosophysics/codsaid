"""미적분: 중심차분 수치 미분, Gradient·Hessian, Gradient 시각화.

중심차분  f'(x) ≈ [f(x+h) − f(x−h)] / 2h  의 절단 오차는 O(h²)이다.
전진차분 [f(x+h) − f(x)] / h 의 O(h)보다 같은 h에서 훨씬 정확하다.

미션에서 이 파일이 맡는 문제:
    1. 미분을 공식 없이 "조금 움직여 본 변화량"으로 계산한다(수치 미분).
    2. 여러 변수 함수의 Gradient를 구하고, Gradient가 등고선과 수직임을 확인한다.
    3. 역전파로 구한 기울기가 맞는지 수치 미분으로 검증하는 도구를 제공한다(neural_net, run_all).

"함수 f"를 인자로 받는 함수가 많다. 파이썬에서는 함수도 값이라서 변수처럼 넘길 수 있고,
받은 쪽에서 f(x)처럼 호출한다. 예: numerical_derivative(lambda x: x ** 2, 3.0).
lambda x: x ** 2는 "x를 받아 x²을 돌려주는 이름 없는 함수"를 한 줄로 만든 것이다.
"""
import numpy as np
import matplotlib.pyplot as plt


def numerical_derivative(f, x, h=1e-5):
    """1변수 함수의 중심차분 미분값.

    f'(x) ≈ [f(x + h) − f(x − h)] / (2h)

    f(x) = x², x = 3, h = 0.1로 따라가면
    [f(3.1) − f(2.9)] / 0.2 = (9.61 − 8.41) / 0.2 = 6.0 이다. 해석적 미분 2x = 6과 같다.
    (x²에서는 절단 오차 항이 정확히 사라져 어떤 h에서도 6이다. sin 같은 함수에서는 h²에 비례한 오차가 남는다.)

    Args:
        f: 스칼라 → 스칼라 함수.
        x: 미분할 위치.
        h: 간격. 1e-5는 0.00001이다. 너무 크면 절단 오차, 너무 작으면 부동소수점 반올림 오차가 커진다.

    Returns:
        float: x에서의 기울기 근삿값.
    """
    return (f(x + h) - f(x - h)) / (2 * h)


def numerical_gradient(f, point, h=1e-5):
    """다변수 스칼라 함수의 Gradient를 좌표별 중심차분으로 구한다.

    ∂f/∂x_i ≈ [f(x + h·e_i) − f(x − h·e_i)] / (2h)

    좌표 하나만 ±h 움직이고 나머지는 그대로 둔 채 f를 두 번 계산한다.
    f(x, y) = x² + y², point = (1, 2)이면 결과는 (2, 4)이다.

    Args:
        f: 배열 → 스칼라 함수. 입력 shape은 point와 같다.
        point: 미분할 위치. 어떤 shape이든 된다 (예: 가중치 행렬).
        h: 좌표마다 움직일 간격.

    Returns:
        np.ndarray: point와 같은 shape의 Gradient. point 자체는 바뀌지 않는다.
    """
    # np.array(...)는 새 복사본을 만든다. 아래에서 x를 잠시 바꿔도 호출한 쪽의 point는 안전하다.
    x = np.array(point, dtype=float)
    # zeros_like(x)는 x와 같은 shape의 0 배열. 결과를 칸마다 채워 넣을 그릇이다.
    grad = np.zeros_like(x)
    # np.ndindex(shape)는 모든 칸의 위치를 차례로 준다.
    # (2, 2) 행렬이면 (0,0), (0,1), (1,0), (1,1) → 가중치 행렬 W1의 원소 4개를 하나씩 미분한다.
    for idx in np.ndindex(x.shape):
        original = x[idx]
        x[idx] = original + h      # 이 칸만 +h (제자리 수정)
        f_plus = f(x)
        x[idx] = original - h      # 이 칸만 −h
        f_minus = f(x)
        x[idx] = original          # 다음 칸으로 넘어가기 전에 원래 값으로 되돌린다
        grad[idx] = (f_plus - f_minus) / (2 * h)
    return grad


def numerical_hessian(f, point, h=1e-4):
    """Gradient를 한 번 더 중심차분해 Hessian 행렬을 구한다.

    H_ij = ∂²f / ∂x_i ∂x_j ≈ [∇f(x + h·e_j) − ∇f(x − h·e_j)]_i / (2h)

    Hessian은 "기울기가 얼마나 빨리 바뀌는가", 즉 곡률을 담는다.
    f = x² + 10y²이면 H = [[2, 0], [0, 20]]이다. Newton Method(optimizer.py)가 사용한다.

    Args:
        f: 배열 → 스칼라 함수.
        point: 미분할 위치. 1차원으로 펼쳐 다룬다.
        h: 간격. 미분을 두 번 하므로 반올림 오차를 줄이려고 1e-4로 조금 크게 잡았다.

    Returns:
        np.ndarray: shape (n, n) 대칭화한 Hessian.
    """
    # ravel()은 어떤 shape이든 1차원으로 펼친다: (2, 2) → (4,).
    x = np.array(point, dtype=float).ravel()
    n = x.size
    H = np.zeros((n, n))
    for j in range(n):
        step = np.zeros(n)
        step[j] = h     # j번 좌표만 h인 벡터 h·e_j
        # H[:, j]는 j번 열 전체. Gradient 벡터 (n,) 하나가 열 하나를 채운다.
        H[:, j] = (numerical_gradient(f, x + step, h) - numerical_gradient(f, x - step, h)) / (2 * h)
    # 이론상 H는 대칭(H_ij = H_ji)이지만 수치 오차로 조금 어긋난다. H.T(전치)와 평균 내 대칭으로 맞춘다.
    return 0.5 * (H + H.T)


def derivative_error_curve(f, df, x, hs=None):
    """여러 h에서 전진차분·중심차분의 절대 오차를 계산한다.

    h를 줄이면 처음에는 절단 오차가 줄지만, 너무 작으면 f(x+h)와 f(x−h)가
    거의 같아져 뺄셈에서 유효숫자를 잃는다(반올림 오차 ∝ ε/h).

    Args:
        f: 미분할 함수.
        df: f의 정확한 도함수(정답 비교용).
        x: 미분할 위치.
        hs: 시험할 간격들. None이면 1e-12부터 1까지 로그 간격 49개.

    Returns:
        dict: hs, forward 오차 배열, central 오차 배열. 세 배열 모두 shape (len(hs),).
    """
    if hs is None:
        # logspace(-12, 0, 49)는 10^-12부터 10^0까지 지수를 같은 간격으로 나눈 49개 값.
        hs = np.logspace(-12, 0, 49)
    exact = df(x)
    # [식 for h in hs]로 h마다 오차를 계산해 리스트로 모은 뒤 np.array로 바꾼다.
    forward = np.array([abs((f(x + h) - f(x)) / h - exact) for h in hs])
    central = np.array([abs(numerical_derivative(f, x, h) - exact) for h in hs])
    return {"hs": np.asarray(hs), "forward": forward, "central": central}


def level_set_points(f, level, n_points=24, r_max=10.0, iters=80, angles=None):
    """원점을 감싸는 등고선 f(x, y) = level 위의 점을 이분법으로 찾는다.

    각 방향 φ에 대해 g(r) = f(r cos φ, r sin φ) − level의 근을 찾는다.
    원점이 최솟값이고 반지름 방향으로 f가 증가하는 함수에서 쓸 수 있다.

    f = x² + y², level = 4라면 모든 방향에서 r = 2인 점, 즉 반지름 2인 원 위의 점이 나온다.

    Args:
        f: (2,) 배열을 받아 숫자를 돌려주는 함수.
        level: 찾을 등고선의 높이.
        n_points: angles가 없을 때 만들 방향 개수.
        r_max: 탐색할 반지름의 최댓값.
        iters: 이분법 반복 횟수. 80번이면 구간이 10 / 2^80으로 줄어 부동소수점 한계까지 좁혀진다.
        angles: 직접 지정할 방향 각도 배열. 없으면 n_points개를 균등하게 만든다.

    Returns:
        np.ndarray: shape (2, 각도 수), 각도 순서로 정렬된 등고선 위의 점.
    """
    if angles is None:
        # endpoint=False: 2π를 빼서 0과 2π가 같은 점으로 중복되지 않게 한다.
        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    pts = []
    for phi in angles:
        direction = np.array([np.cos(phi), np.sin(phi)])
        lo, hi = 0.0, r_max
        # 이분법: 답이 [lo, hi] 안에 있다고 보고, 가운데 값으로 구간을 매번 절반으로 줄인다.
        # _는 "반복 번호를 쓰지 않는다"는 관례적 변수 이름이다.
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            if f(mid * direction) < level:
                lo = mid      # 아직 등고선 안쪽 → 답은 더 바깥
            else:
                hi = mid      # 등고선 바깥 → 답은 더 안쪽
        pts.append(0.5 * (lo + hi) * direction)
    # pts는 (2,) 점들의 리스트 → np.array로 (각도 수, 2) → .T(전치)로 (2, 각도 수).
    return np.array(pts).T


def gradient_contour_orthogonality(f, level, n_points=24, h=1e-5, delta=1e-4):
    """등고선 접선과 Gradient가 수직인지 수치로 확인한다.

    접선은 각도 φ ± delta 방향의 등고선 위 두 점의 차이로, Gradient는
    numerical_gradient로 따로 구한다. 두 벡터의 코사인 |cos θ|가 0에 가까우면 수직이다.

    두 방향을 서로 다른 방법으로 구했으므로, 수직이라는 결과는 "같은 계산을 두 번 한 것"이 아니라
    독립적인 확인이다. 등고선을 따라가면 f가 변하지 않으므로 그 방향의 기울기 성분이 0이어야 한다.

    Args:
        f: 확인할 함수.
        level: 등고선 높이.
        n_points: 검사할 점의 개수.
        h: Gradient 수치 미분 간격.
        delta: 접선을 만들 때 각도를 벌리는 크기(라디안).

    Returns:
        dict: points(2, n), gradients(2, n), tangents(2, n), cosines(n,), max_abs_cos.
    """
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    pts = level_set_points(f, level, angles=angles)
    # angles + delta: 배열의 모든 원소에 같은 수를 더한다(브로드캐스팅). 결과도 (n,).
    # 바로 앞뒤 각도의 등고선 위 점 두 개를 빼면 등고선을 따라가는 방향(접선)이 된다. shape (2, n).
    tangents = (level_set_points(f, level, angles=angles + delta)
                - level_set_points(f, level, angles=angles - delta))
    # pts[:, i]는 i번 점 (2,). 점마다 Gradient (2,)를 구해 column_stack으로 열로 붙이면 (2, n).
    grads = np.column_stack([numerical_gradient(f, pts[:, i], h) for i in range(pts.shape[1])])
    # cos θ = (g · t) / (‖g‖ ‖t‖)를 n개 점에서 한 번에 계산한다.
    # grads * tangents는 같은 위치끼리 곱 (2, n). axis=0으로 더하면 0축(x, y)이 사라져 점마다 내적 (n,).
    # norm(..., axis=0)도 열마다 길이 (n,)를 준다.
    cos = np.sum(grads * tangents, axis=0) / (
        np.linalg.norm(grads, axis=0) * np.linalg.norm(tangents, axis=0))
    return {"points": pts, "gradients": grads, "tangents": tangents,
            "cosines": cos, "max_abs_cos": float(np.max(np.abs(cos)))}


def plot_gradient_field(f, levels=(1, 4, 9), lim=3.5, ax=None, arrow_points=16):
    """등고선 위에 Gradient 화살표를 그린다.

    ∇f는 f가 가장 빨리 증가하는 방향이며, 등고선(값이 같은 곡선)과 수직이다.
    화살표는 등고선 위의 점에서 시작하므로 수직 관계를 바로 볼 수 있다.
    ax.set_aspect('equal')이 없으면 축 비율 때문에 수직이 비스듬해 보인다.

    Args:
        f: 그릴 함수. (2, ...) 배열을 받아야 한다 (첫 축이 x, y).
        levels: 화살표를 그릴 등고선 높이들.
        lim: 그림 범위 [-lim, lim].
        ax: 그릴 좌표축. None이면 새로 만든다.
        arrow_points: 등고선마다 그릴 화살표 수.

    Returns:
        list[dict]: 등고선마다 gradient_contour_orthogonality의 결과.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    xs = np.linspace(-lim, lim, 200)
    # meshgrid로 200x200 격자의 x 좌표 X, y 좌표 Y를 만든다. 둘 다 (200, 200).
    X, Y = np.meshgrid(xs, xs)
    # np.stack([X, Y])는 (2, 200, 200). f는 p[0], p[1]로 x, y를 꺼내므로 격자 전체를 한 번에 계산한다.
    Z = f(np.stack([X, Y]))
    cs = ax.contour(X, Y, Z, levels=list(levels) + [16], cmap="viridis")
    ax.clabel(cs, fontsize=8)
    checks = []
    for level in levels:
        res = gradient_contour_orthogonality(f, level, arrow_points)
        checks.append(res)
        p, g = res["points"], res["gradients"]
        scale = 0.12   # 화살표가 그림 밖으로 나가지 않게 길이만 줄인다(방향은 그대로).
        # quiver(x, y, u, v)는 (x, y)에서 시작해 (u, v) 방향으로 화살표를 그린다.
        ax.quiver(p[0], p[1], g[0] * scale, g[1] * scale, angles="xy",
                  scale_units="xy", scale=1, color="tab:red", width=0.004)
        # 접선을 길이 1로 맞춘 뒤 0.35배 → 모든 점에서 같은 길이의 짧은 선분으로 그린다.
        t = res["tangents"] / np.linalg.norm(res["tangents"], axis=0) * 0.35
        ax.plot([p[0] - t[0], p[0] + t[0]], [p[1] - t[1], p[1] + t[1]],
                color="black", lw=1.2, alpha=0.8)
    # (식 for c in checks)를 max에 바로 넣으면 리스트를 만들지 않고 최댓값을 구한다.
    worst = max(c["max_abs_cos"] for c in checks)
    ax.set_title(f"Gradient (red) is perpendicular to contour tangent (black)\nmax |cos| = {worst:.1e}")
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return checks
