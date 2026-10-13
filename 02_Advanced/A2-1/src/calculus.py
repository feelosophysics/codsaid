"""미적분: 중심차분 수치 미분, Gradient·Hessian, Gradient 시각화.

중심차분  f'(x) ≈ [f(x+h) − f(x−h)] / 2h  의 절단 오차는 O(h²)이다.
전진차분 [f(x+h) − f(x)] / h 의 O(h)보다 같은 h에서 훨씬 정확하다.
"""
import numpy as np
import matplotlib.pyplot as plt


def numerical_derivative(f, x, h=1e-5):
    """1변수 함수의 중심차분 미분값.

    f'(x) ≈ [f(x + h) − f(x − h)] / (2h)

    Args:
        f: 스칼라 → 스칼라 함수.
        x: 미분할 위치.
        h: 간격. 너무 크면 절단 오차, 너무 작으면 부동소수점 반올림 오차가 커진다.
    """
    return (f(x + h) - f(x - h)) / (2 * h)


def numerical_gradient(f, point, h=1e-5):
    """다변수 스칼라 함수의 Gradient를 좌표별 중심차분으로 구한다.

    ∂f/∂x_i ≈ [f(x + h·e_i) − f(x − h·e_i)] / (2h)

    Args:
        f: 배열 → 스칼라 함수. 입력 shape은 point와 같다.
        point: 미분할 위치. 어떤 shape이든 된다 (예: 가중치 행렬).

    Returns:
        np.ndarray: point와 같은 shape의 Gradient.
    """
    x = np.array(point, dtype=float)
    grad = np.zeros_like(x)
    for idx in np.ndindex(x.shape):
        original = x[idx]
        x[idx] = original + h
        f_plus = f(x)
        x[idx] = original - h
        f_minus = f(x)
        x[idx] = original
        grad[idx] = (f_plus - f_minus) / (2 * h)
    return grad


def numerical_hessian(f, point, h=1e-4):
    """Gradient를 한 번 더 중심차분해 Hessian 행렬을 구한다.

    H_ij = ∂²f / ∂x_i ∂x_j ≈ [∇f(x + h·e_j) − ∇f(x − h·e_j)]_i / (2h)

    Returns:
        np.ndarray: shape (n, n) 대칭화한 Hessian.
    """
    x = np.array(point, dtype=float).ravel()
    n = x.size
    H = np.zeros((n, n))
    for j in range(n):
        step = np.zeros(n)
        step[j] = h
        H[:, j] = (numerical_gradient(f, x + step, h) - numerical_gradient(f, x - step, h)) / (2 * h)
    return 0.5 * (H + H.T)


def derivative_error_curve(f, df, x, hs=None):
    """여러 h에서 전진차분·중심차분의 절대 오차를 계산한다.

    h를 줄이면 처음에는 절단 오차가 줄지만, 너무 작으면 f(x+h)와 f(x−h)가
    거의 같아져 뺄셈에서 유효숫자를 잃는다(반올림 오차 ∝ ε/h).

    Returns:
        dict: hs, forward 오차 배열, central 오차 배열.
    """
    if hs is None:
        hs = np.logspace(-12, 0, 49)
    exact = df(x)
    forward = np.array([abs((f(x + h) - f(x)) / h - exact) for h in hs])
    central = np.array([abs(numerical_derivative(f, x, h) - exact) for h in hs])
    return {"hs": np.asarray(hs), "forward": forward, "central": central}


def level_set_points(f, level, n_points=24, r_max=10.0, iters=80, angles=None):
    """원점을 감싸는 등고선 f(x, y) = level 위의 점을 이분법으로 찾는다.

    각 방향 φ에 대해 g(r) = f(r cos φ, r sin φ) − level의 근을 찾는다.
    원점이 최솟값이고 반지름 방향으로 f가 증가하는 함수에서 쓸 수 있다.

    Args:
        angles: 직접 지정할 방향 각도 배열. 없으면 n_points개를 균등하게 만든다.

    Returns:
        np.ndarray: shape (2, 각도 수), 각도 순서로 정렬된 등고선 위의 점.
    """
    if angles is None:
        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    pts = []
    for phi in angles:
        direction = np.array([np.cos(phi), np.sin(phi)])
        lo, hi = 0.0, r_max
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            if f(mid * direction) < level:
                lo = mid
            else:
                hi = mid
        pts.append(0.5 * (lo + hi) * direction)
    return np.array(pts).T


def gradient_contour_orthogonality(f, level, n_points=24, h=1e-5, delta=1e-4):
    """등고선 접선과 Gradient가 수직인지 수치로 확인한다.

    접선은 각도 φ ± delta 방향의 등고선 위 두 점의 차이로, Gradient는
    numerical_gradient로 따로 구한다. 두 벡터의 코사인 |cos θ|가 0에 가까우면 수직이다.

    Returns:
        dict: points(2, n), gradients(2, n), tangents(2, n), cosines(n,), max_abs_cos.
    """
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    pts = level_set_points(f, level, angles=angles)
    tangents = (level_set_points(f, level, angles=angles + delta)
                - level_set_points(f, level, angles=angles - delta))
    grads = np.column_stack([numerical_gradient(f, pts[:, i], h) for i in range(pts.shape[1])])
    cos = np.sum(grads * tangents, axis=0) / (
        np.linalg.norm(grads, axis=0) * np.linalg.norm(tangents, axis=0))
    return {"points": pts, "gradients": grads, "tangents": tangents,
            "cosines": cos, "max_abs_cos": float(np.max(np.abs(cos)))}


def plot_gradient_field(f, levels=(1, 4, 9), lim=3.5, ax=None, arrow_points=16):
    """등고선 위에 Gradient 화살표를 그린다.

    ∇f는 f가 가장 빨리 증가하는 방향이며, 등고선(값이 같은 곡선)과 수직이다.
    화살표는 등고선 위의 점에서 시작하므로 수직 관계를 바로 볼 수 있다.
    ax.set_aspect('equal')이 없으면 축 비율 때문에 수직이 비스듬해 보인다.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    xs = np.linspace(-lim, lim, 200)
    X, Y = np.meshgrid(xs, xs)
    Z = f(np.stack([X, Y]))
    cs = ax.contour(X, Y, Z, levels=list(levels) + [16], cmap="viridis")
    ax.clabel(cs, fontsize=8)
    checks = []
    for level in levels:
        res = gradient_contour_orthogonality(f, level, arrow_points)
        checks.append(res)
        p, g = res["points"], res["gradients"]
        scale = 0.12
        ax.quiver(p[0], p[1], g[0] * scale, g[1] * scale, angles="xy",
                  scale_units="xy", scale=1, color="tab:red", width=0.004)
        t = res["tangents"] / np.linalg.norm(res["tangents"], axis=0) * 0.35
        ax.plot([p[0] - t[0], p[0] + t[0]], [p[1] - t[1], p[1] + t[1]],
                color="black", lw=1.2, alpha=0.8)
    worst = max(c["max_abs_cos"] for c in checks)
    ax.set_title(f"Gradient (red) is perpendicular to contour tangent (black)\nmax |cos| = {worst:.1e}")
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return checks
