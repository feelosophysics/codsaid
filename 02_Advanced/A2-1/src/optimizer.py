"""최적화: VanillaGD, Momentum, Adam(보너스), Newton Method(보너스)와 수렴 경로 시각화.

모든 옵티마이저는 같은 인터페이스를 가진다.
    new_params = optimizer.step(params, grad)
상태(속도·모멘트)는 객체 안에 보관하고, 새 실험 전에는 reset()으로 비운다.
"""
import numpy as np
import matplotlib.pyplot as plt

from .calculus import numerical_hessian


# ---------------------------------------------------------------------------
# 테스트 함수. 입력 p의 첫 축이 (x, y)이므로 점 하나와 meshgrid 모두 받는다.
# ---------------------------------------------------------------------------

def quadratic(p):
    """f(x, y) = x² + y². 모든 방향의 곡률이 같은 둥근 그릇."""
    return p[0] ** 2 + p[1] ** 2


def quadratic_grad(p):
    """∇f = (2x, 2y)."""
    return np.array([2 * p[0], 2 * p[1]], dtype=float)


def elliptic(p):
    """f(x, y) = x² + 10y². y 방향 곡률이 10배인 좁은 골짜기."""
    return p[0] ** 2 + 10 * p[1] ** 2


def elliptic_grad(p):
    """∇f = (2x, 20y)."""
    return np.array([2 * p[0], 20 * p[1]], dtype=float)


def rosenbrock(p):
    """f(x, y) = (1 − x)² + 100(y − x²)². 최솟값 (1, 1), 휘어진 좁은 골짜기."""
    return (1 - p[0]) ** 2 + 100 * (p[1] - p[0] ** 2) ** 2


def rosenbrock_grad(p):
    """∇f = (−2(1 − x) − 400x(y − x²), 200(y − x²))."""
    x, y = p
    return np.array([-2 * (1 - x) - 400 * x * (y - x ** 2), 200 * (y - x ** 2)], dtype=float)


def saddle(p):
    """f(x, y) = x² − y². 원점은 최솟값이 아니라 안장점이다."""
    return p[0] ** 2 - p[1] ** 2


def saddle_grad(p):
    """∇f = (2x, −2y)."""
    return np.array([2 * p[0], -2 * p[1]], dtype=float)


# ---------------------------------------------------------------------------
# 옵티마이저
# ---------------------------------------------------------------------------

class Optimizer:
    """옵티마이저 기본 클래스."""

    def __init__(self, lr):
        """학습률 lr을 저장하고 상태를 초기화한다."""
        self.lr = lr
        self.reset()

    def reset(self):
        """반복 간 상태를 비운다."""
        self.t = 0

    def step(self, params, grad):
        """파라미터를 한 번 갱신한 새 배열을 반환한다."""
        raise NotImplementedError


class VanillaGD(Optimizer):
    """경사하강법:  θ_{t+1} = θ_t − η ∇f(θ_t).

    f = x² + y²에서는 θ_{t+1} = (1 − 2η) θ_t 이다.
    |1 − 2η| < 1, 즉 0 < η < 1일 때만 수렴한다 (일반적으로 η < 2 / 최대 곡률).
    """

    def step(self, params, grad):
        """기울기 반대 방향으로 lr만큼 이동한다."""
        self.t += 1
        return np.asarray(params, dtype=float) - self.lr * np.asarray(grad, dtype=float)


class Momentum(Optimizer):
    """Momentum(heavy ball):  v_{t+1} = β v_t + ∇f(θ_t),  θ_{t+1} = θ_t − η v_{t+1}.

    v는 과거 기울기의 지수 가중 합이다. 방향이 일정한 성분은 쌓여 빨라지고,
    부호가 번갈아 바뀌는(지그재그) 성분은 서로 상쇄된다.
    """

    def __init__(self, lr, beta=0.9):
        """학습률과 관성 계수 beta를 저장한다."""
        self.beta = beta
        super().__init__(lr)

    def reset(self):
        """속도 v를 비운다."""
        super().reset()
        self.v = None

    def step(self, params, grad):
        """속도를 누적한 뒤 그 방향으로 이동한다."""
        self.t += 1
        g = np.asarray(grad, dtype=float)
        self.v = g if self.v is None else self.beta * self.v + g
        return np.asarray(params, dtype=float) - self.lr * self.v


class Adam(Optimizer):
    """Adam = Momentum(1차 모멘트) + RMSProp(2차 모멘트) + 편향 보정.

        m_t = β1 m_{t−1} + (1 − β1) g            기울기의 이동 평균
        v_t = β2 v_{t−1} + (1 − β2) g²           기울기 제곱의 이동 평균
        m̂ = m_t / (1 − β1^t),  v̂ = v_t / (1 − β2^t)
        θ_t = θ_{t−1} − η m̂ / (√v̂ + ε)

    좌표마다 기울기 크기로 나누므로 곡률이 다른 방향에서도 이동 폭이 비슷해진다.
    """

    def __init__(self, lr, beta1=0.9, beta2=0.999, eps=1e-8):
        """학습률과 두 이동 평균 계수, 분모 안정화 상수를 저장한다."""
        self.beta1, self.beta2, self.eps = beta1, beta2, eps
        super().__init__(lr)

    def reset(self):
        """1차·2차 모멘트를 비운다."""
        super().reset()
        self.m = None
        self.v = None

    def step(self, params, grad):
        """편향 보정한 모멘트로 좌표별 적응 학습률 갱신을 한다."""
        self.t += 1
        g = np.asarray(grad, dtype=float)
        if self.m is None:
            self.m = np.zeros_like(g)
            self.v = np.zeros_like(g)
        self.m = self.beta1 * self.m + (1 - self.beta1) * g
        self.v = self.beta2 * self.v + (1 - self.beta2) * g ** 2
        m_hat = self.m / (1 - self.beta1 ** self.t)
        v_hat = self.v / (1 - self.beta2 ** self.t)
        return np.asarray(params, dtype=float) - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


class NewtonMethod(Optimizer):
    """Newton Method:  θ_{t+1} = θ_t − η H(θ_t)^{-1} ∇f(θ_t).

    2차 테일러 근사 f(θ+d) ≈ f + gᵀd + ½ dᵀHd 를 최소로 만드는 d = −H⁻¹g로 이동한다.
    이차 함수에서는 η=1로 한 번에 최적점에 도달한다. 대신 H(n×n) 계산·풀이 비용이
    크고, H가 양의 정부호가 아니면 안장점이나 최댓값 쪽으로도 이동한다.
    """

    def __init__(self, f=None, hess_fn=None, lr=1.0):
        """Hessian 함수를 받거나, 없으면 f의 수치 Hessian을 사용한다."""
        if hess_fn is None and f is None:
            raise ValueError("f 또는 hess_fn이 필요하다")
        self.f = f
        self.hess_fn = hess_fn
        super().__init__(lr)

    def hessian(self, params):
        """현재 위치의 Hessian 행렬."""
        if self.hess_fn is not None:
            return np.asarray(self.hess_fn(params), dtype=float)
        return numerical_hessian(self.f, params)

    def step(self, params, grad):
        """H d = g를 풀어 Newton 방향 d로 이동한다 (역행렬을 직접 만들지 않는다)."""
        self.t += 1
        direction = np.linalg.solve(self.hessian(params), np.asarray(grad, dtype=float))
        return np.asarray(params, dtype=float) - self.lr * direction


def optimize(optimizer, grad_fn, x0, n_iters=100, stop_tol=None):
    """옵티마이저를 n_iters번 반복하고 모든 위치를 기록한다.

    Args:
        stop_tol: 지정하면 ‖∇f‖ < stop_tol일 때 일찍 멈춘다.

    Returns:
        np.ndarray: shape (반복 수 + 1, 2) 경로. 0행이 시작점이다.
    """
    optimizer.reset()
    x = np.asarray(x0, dtype=float)
    path = [x.copy()]
    for _ in range(n_iters):
        g = grad_fn(x)
        if stop_tol is not None and np.linalg.norm(g) < stop_tol:
            break
        x = optimizer.step(x, g)
        path.append(x.copy())
        if not np.all(np.isfinite(x)):
            break
    return np.array(path)


def iterations_to_reach(path, target, tol):
    """경로가 처음으로 ‖θ − target‖ < tol이 되는 반복 번호. 도달하지 못하면 None."""
    dist = np.linalg.norm(np.asarray(path) - np.asarray(target), axis=1)
    hits = np.nonzero(dist < tol)[0]
    return int(hits[0]) if hits.size else None


# ---------------------------------------------------------------------------
# 시각화
# ---------------------------------------------------------------------------

STYLES = {
    "VanillaGD": dict(color="tab:blue", ls="--", marker="o"),
    "Momentum": dict(color="tab:red", ls="--", marker="s"),
    "Adam": dict(color="tab:green", ls="--", marker="^"),
    "Newton": dict(color="tab:purple", ls="--", marker="D"),
}


def plot_contour(f, ax, xlim=(-6, 6), ylim=(-6, 6), levels=20, log_levels=False):
    """함수 f의 등고선을 그린다."""
    X, Y = np.meshgrid(np.linspace(*xlim, 300), np.linspace(*ylim, 300))
    Z = f(np.stack([X, Y]))
    if log_levels:
        levels = np.logspace(-1, np.log10(Z.max()), levels)
    ax.contour(X, Y, Z, levels=levels, cmap="viridis", linewidths=0.8, alpha=0.8)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")


def plot_convergence_paths(f, paths, ax=None, title="", xlim=(-6, 6), ylim=(-6, 6),
                           target=(0, 0), log_levels=False, target_label="minimum", markevery=None):
    """등고선 위에 옵티마이저별 수렴 경로를 점선으로 겹쳐 그린다.

    Args:
        paths: {이름: shape (T, 2) 경로}.
        markevery: {이름: 간격}. 반복이 많은 경로는 일부 점에만 표시한다.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    plot_contour(f, ax, xlim, ylim, log_levels=log_levels)
    for name, path in paths.items():
        style = dict(STYLES.get(name, dict(ls="--", marker=".")))
        every = (markevery or {}).get(name)
        ax.plot(path[:, 0], path[:, 1], label=f"{name} ({len(path) - 1} steps)",
                markersize=3, lw=1.3, markevery=every, **style)
        ax.plot(*path[0], "ko", markersize=5)
    ax.plot(*target, "k*", markersize=12, label=target_label)
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper left")
    return ax


def plot_distance_curves(paths, ax=None, target=(0, 0), title=""):
    """반복마다 최적점까지 거리 ‖θ_t − θ*‖를 로그 축으로 그린다."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for name, path in paths.items():
        dist = np.linalg.norm(path - np.asarray(target), axis=1)
        color = STYLES.get(name, {}).get("color")
        ax.semilogy(np.arange(len(dist)), np.maximum(dist, 1e-16), label=name, color=color)
    ax.set_xlabel("iteration")
    ax.set_ylabel("distance to minimum (log)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return ax
