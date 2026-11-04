"""최적화: VanillaGD, Momentum, Adam(보너스), Newton Method(보너스)와 수렴 경로 시각화.

모든 옵티마이저는 같은 인터페이스를 가진다.
    new_params = optimizer.step(params, grad)
상태(속도·모멘트)는 객체 안에 보관하고, 새 실험 전에는 reset()으로 비운다.

미션에서 이 파일이 맡는 문제:
    "기울기를 알면 파라미터를 어떻게 움직일 것인가"를 여러 방식으로 구현하고,
    학습률·함수 모양에 따라 수렴·진동·발산이 어떻게 갈리는지 경로로 비교한다.
    신경망 학습의 sgd_step(neural_net.py)과 같은 일을 2차원 함수 위에서 눈으로 보는 실험이다.

클래스 상속: ``class VanillaGD(Optimizer)``는 Optimizer의 기능(lr 저장, reset)을 물려받고
step만 새로 정의한다. ``super().__init__(lr)``은 부모 클래스의 초기화를 그대로 실행한다.
"""
import numpy as np
import matplotlib.pyplot as plt

# 같은 src 패키지 안의 calculus.py에서 함수를 가져온다. 앞의 점(.)은 "같은 폴더"라는 뜻이다.
from .calculus import numerical_hessian


# ---------------------------------------------------------------------------
# 테스트 함수. 입력 p의 첫 축이 (x, y)이므로 점 하나와 meshgrid 모두 받는다.
# p가 [5, 5]면 p[0]=5, p[1]=5로 숫자 하나를, p가 (2, 300, 300) 격자면 p[0], p[1]이
# 각각 (300, 300) 배열이라 격자 전체의 함수값을 한 번에 계산한다(등고선 그림용).
# ---------------------------------------------------------------------------

def quadratic(p):
    """f(x, y) = x² + y². 모든 방향의 곡률이 같은 둥근 그릇.

    Args:
        p: 첫 축이 (x, y)인 배열.

    Returns:
        함수값. p가 점 하나면 숫자, 격자면 같은 크기의 배열.
    """
    # ** 는 거듭제곱이다. p[0] ** 2 = x².
    return p[0] ** 2 + p[1] ** 2


def quadratic_grad(p):
    """∇f = (2x, 2y).

    Args:
        p: 점 (x, y).

    Returns:
        np.ndarray: shape (2,) 기울기. (5, 5)에서는 (10, 10).
    """
    return np.array([2 * p[0], 2 * p[1]], dtype=float)


def elliptic(p):
    """f(x, y) = x² + 10y². y 방향 곡률이 10배인 좁은 골짜기.

    Args:
        p: 첫 축이 (x, y)인 배열.

    Returns:
        함수값.
    """
    return p[0] ** 2 + 10 * p[1] ** 2


def elliptic_grad(p):
    """∇f = (2x, 20y).

    Args:
        p: 점 (x, y).

    Returns:
        np.ndarray: shape (2,) 기울기. (5, 5)에서는 (10, 100). y 방향이 10배 가파르다.
    """
    return np.array([2 * p[0], 20 * p[1]], dtype=float)


def rosenbrock(p):
    """f(x, y) = (1 − x)² + 100(y − x²)². 최솟값 (1, 1), 휘어진 좁은 골짜기.

    Args:
        p: 첫 축이 (x, y)인 배열.

    Returns:
        함수값.
    """
    return (1 - p[0]) ** 2 + 100 * (p[1] - p[0] ** 2) ** 2


def rosenbrock_grad(p):
    """∇f = (−2(1 − x) − 400x(y − x²), 200(y − x²)).

    Args:
        p: 점 (x, y).

    Returns:
        np.ndarray: shape (2,) 기울기.
    """
    x, y = p
    return np.array([-2 * (1 - x) - 400 * x * (y - x ** 2), 200 * (y - x ** 2)], dtype=float)


def saddle(p):
    """f(x, y) = x² − y². 원점은 최솟값이 아니라 안장점이다.

    x 방향으로는 그릇, y 방향으로는 뒤집힌 그릇이라 원점에서 기울기는 0이지만 최솟값이 아니다.

    Args:
        p: 첫 축이 (x, y)인 배열.

    Returns:
        함수값.
    """
    return p[0] ** 2 - p[1] ** 2


def saddle_grad(p):
    """∇f = (2x, −2y).

    Args:
        p: 점 (x, y).

    Returns:
        np.ndarray: shape (2,) 기울기.
    """
    return np.array([2 * p[0], -2 * p[1]], dtype=float)


# ---------------------------------------------------------------------------
# 옵티마이저
# ---------------------------------------------------------------------------

class Optimizer:
    """옵티마이저 기본 클래스.

    직접 쓰지 않고, 공통 부분(lr 저장, 반복 횟수 t, reset)만 자식 클래스에 물려준다.

    Attributes:
        lr: 학습률 η.
        t: 지금까지 step을 부른 횟수. Adam의 편향 보정에 쓰인다.
    """

    def __init__(self, lr):
        """학습률 lr을 저장하고 상태를 초기화한다.

        Args:
            lr: 학습률. 한 번에 기울기의 몇 배만큼 움직일지 정한다.
        """
        self.lr = lr
        # self.reset()은 "이 객체의 reset"을 부른다. 자식 클래스가 reset을 다시 정의했다면
        # 그 자식의 reset이 실행되어 v, m 같은 상태도 함께 준비된다.
        self.reset()

    def reset(self):
        """반복 간 상태를 비운다."""
        self.t = 0

    def step(self, params, grad):
        """파라미터를 한 번 갱신한 새 배열을 반환한다.

        Args:
            params: 현재 위치 θ_t.
            grad: 그 위치의 기울기 ∇f(θ_t).

        Returns:
            np.ndarray: 다음 위치 θ_{t+1}.

        Raises:
            NotImplementedError: 기본 클래스에서는 갱신 규칙이 없으므로 항상 일으킨다.
        """
        raise NotImplementedError


class VanillaGD(Optimizer):
    """경사하강법:  θ_{t+1} = θ_t − η ∇f(θ_t).

    f = x² + y²에서는 θ_{t+1} = (1 − 2η) θ_t 이다.
    |1 − 2η| < 1, 즉 0 < η < 1일 때만 수렴한다 (일반적으로 η < 2 / 최대 곡률).

    시작 (5, 5), η = 0.1:  기울기 (10, 10) → (5, 5) − 0.1·(10, 10) = (4, 4).
    매번 0.8배가 되어 100회 뒤 5·0.8^100 ≈ 1.0e-9.
    """

    def step(self, params, grad):
        """기울기 반대 방향으로 lr만큼 이동한다.

        Args:
            params: 현재 위치 (2,).
            grad: 현재 기울기 (2,).

        Returns:
            np.ndarray: 새 위치 (2,). 입력 배열은 바꾸지 않는다.
        """
        self.t += 1   # += 는 "더해서 다시 저장": self.t = self.t + 1
        # 배열 − 숫자 × 배열: 좌표마다 계산한다. (5, 5) − 0.1 × (10, 10) = (4, 4).
        return np.asarray(params, dtype=float) - self.lr * np.asarray(grad, dtype=float)


class Momentum(Optimizer):
    """Momentum(heavy ball):  v_{t+1} = β v_t + ∇f(θ_t),  θ_{t+1} = θ_t − η v_{t+1}.

    v는 과거 기울기의 지수 가중 합이다. 방향이 일정한 성분은 쌓여 빨라지고,
    부호가 번갈아 바뀌는(지그재그) 성분은 서로 상쇄된다.

    같은 기울기 g가 계속 들어오면 v는 g, 1.9g, 2.71g, ... → g / (1 − β) = 10g로 커진다(β=0.9).
    부호가 +g, −g로 번갈아 오면 v는 g, −0.1g, 0.91g, ...로 크기가 g 근처에 머문다.

    Attributes:
        beta: 관성 계수 β. 과거 속도를 얼마나 남길지 (0.9 = 90%).
        v: 현재 속도. 첫 step 전에는 None.
    """

    def __init__(self, lr, beta=0.9):
        """학습률과 관성 계수 beta를 저장한다.

        Args:
            lr: 학습률.
            beta: 관성 계수. 0이면 VanillaGD와 같다.
        """
        # beta를 먼저 저장한 뒤 부모 초기화(lr 저장, reset 호출)를 실행한다.
        self.beta = beta
        super().__init__(lr)

    def reset(self):
        """속도 v를 비운다."""
        super().reset()   # 부모의 reset(t = 0)을 먼저 실행하고
        self.v = None     # Momentum만의 상태를 추가로 비운다.

    def step(self, params, grad):
        """속도를 누적한 뒤 그 방향으로 이동한다.

        Args:
            params: 현재 위치 (2,).
            grad: 현재 기울기 (2,).

        Returns:
            np.ndarray: 새 위치 (2,). 객체의 self.v(속도)는 갱신된다.
        """
        self.t += 1
        g = np.asarray(grad, dtype=float)
        # 첫 step에서는 v가 없으므로 g를 그대로 쓴다. 이후에는 β × 이전 속도 + 새 기울기.
        # 0 벡터에서 시작해 β·0 + g로 계산한 것과 결과가 같다.
        self.v = g if self.v is None else self.beta * self.v + g
        return np.asarray(params, dtype=float) - self.lr * self.v


class Adam(Optimizer):
    """Adam = Momentum(1차 모멘트) + RMSProp(2차 모멘트) + 편향 보정.

        m_t = β1 m_{t−1} + (1 − β1) g            기울기의 이동 평균
        v_t = β2 v_{t−1} + (1 − β2) g²           기울기 제곱의 이동 평균
        m̂ = m_t / (1 − β1^t),  v̂ = v_t / (1 − β2^t)
        θ_t = θ_{t−1} − η m̂ / (√v̂ + ε)

    좌표마다 기울기 크기로 나누므로 곡률이 다른 방향에서도 이동 폭이 비슷해진다.

    첫 step, g = (10, 100) (x²+10y²의 (5, 5)):
        m = 0.1·g = (1, 10),  v = 0.001·g² = (0.1, 10)
        m̂ = m / 0.1 = (10, 100),  v̂ = v / 0.001 = (100, 10000),  √v̂ = (10, 100)
        이동 = η · m̂ / √v̂ = η · (1, 1)  → 기울기가 10배 달라도 두 좌표 모두 η만큼 움직인다.

    Attributes:
        beta1, beta2: 1차·2차 이동 평균 계수.
        eps: 0으로 나누기를 막는 작은 수.
        m, v: 좌표별 1차·2차 모멘트. 첫 step 전에는 None.
    """

    def __init__(self, lr, beta1=0.9, beta2=0.999, eps=1e-8):
        """학습률과 두 이동 평균 계수, 분모 안정화 상수를 저장한다.

        Args:
            lr: 학습률(좌표마다 대략 최대 이동 폭).
            beta1: 기울기 평균의 관성. 논문 기본값 0.9.
            beta2: 기울기 제곱 평균의 관성. 논문 기본값 0.999.
            eps: 분모에 더할 작은 수.
        """
        # 오른쪽 세 값을 왼쪽 세 속성에 순서대로 한 번에 저장한다.
        self.beta1, self.beta2, self.eps = beta1, beta2, eps
        super().__init__(lr)

    def reset(self):
        """1차·2차 모멘트를 비운다."""
        super().reset()
        self.m = None
        self.v = None

    def step(self, params, grad):
        """편향 보정한 모멘트로 좌표별 적응 학습률 갱신을 한다.

        Args:
            params: 현재 위치 (2,).
            grad: 현재 기울기 (2,).

        Returns:
            np.ndarray: 새 위치 (2,). 객체의 t, m, v는 갱신된다.
        """
        self.t += 1
        g = np.asarray(grad, dtype=float)
        if self.m is None:
            # 기울기와 같은 shape의 0 배열로 시작한다.
            self.m = np.zeros_like(g)
            self.v = np.zeros_like(g)
        self.m = self.beta1 * self.m + (1 - self.beta1) * g
        # g ** 2는 좌표마다 제곱이다. 크기만 남고 부호는 사라진다.
        self.v = self.beta2 * self.v + (1 - self.beta2) * g ** 2
        # 0에서 시작한 이동 평균은 초반에 0 쪽으로 치우친다(첫 m은 g의 10%뿐).
        # 1 − β^t로 나누면 이 치우침이 보정된다. t가 커지면 β^t → 0이라 나누는 값이 1에 가까워진다.
        m_hat = self.m / (1 - self.beta1 ** self.t)
        v_hat = self.v / (1 - self.beta2 ** self.t)
        # np.sqrt는 원소별 제곱근. 배열 / 배열도 좌표마다 나눈다.
        return np.asarray(params, dtype=float) - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


class NewtonMethod(Optimizer):
    """Newton Method:  θ_{t+1} = θ_t − η H(θ_t)^{-1} ∇f(θ_t).

    2차 테일러 근사 f(θ+d) ≈ f + gᵀd + ½ dᵀHd 를 최소로 만드는 d = −H⁻¹g로 이동한다.
    이차 함수에서는 η=1로 한 번에 최적점에 도달한다. 대신 H(n×n) 계산·풀이 비용이
    크고, H가 양의 정부호가 아니면 안장점이나 최댓값 쪽으로도 이동한다.

    x² + 10y², 시작 (5, 5): g = (10, 100), H = [[2, 0], [0, 20]]
        H d = g를 풀면 d = (10/2, 100/20) = (5, 5) → (5, 5) − (5, 5) = (0, 0), 한 번에 도착.

    Attributes:
        f: 수치 Hessian을 계산할 함수 (hess_fn이 없을 때만 사용).
        hess_fn: 위치를 받아 Hessian 행렬을 돌려주는 함수.
    """

    def __init__(self, f=None, hess_fn=None, lr=1.0):
        """Hessian 함수를 받거나, 없으면 f의 수치 Hessian을 사용한다.

        Args:
            f: 최적화할 함수. hess_fn이 없을 때 numerical_hessian에 넘긴다.
            hess_fn: 정확한 Hessian 함수. 있으면 f보다 우선한다.
            lr: 이동 비율. 1.0이면 순수 Newton 이동.

        Raises:
            ValueError: f와 hess_fn이 둘 다 없는 경우.
        """
        if hess_fn is None and f is None:
            raise ValueError("f 또는 hess_fn이 필요하다")
        self.f = f
        self.hess_fn = hess_fn
        super().__init__(lr)

    def hessian(self, params):
        """현재 위치의 Hessian 행렬.

        Args:
            params: 현재 위치 (n,).

        Returns:
            np.ndarray: shape (n, n).
        """
        if self.hess_fn is not None:
            return np.asarray(self.hess_fn(params), dtype=float)
        return numerical_hessian(self.f, params)

    def step(self, params, grad):
        """H d = g를 풀어 Newton 방향 d로 이동한다 (역행렬을 직접 만들지 않는다).

        Args:
            params: 현재 위치 (n,).
            grad: 현재 기울기 (n,).

        Returns:
            np.ndarray: 새 위치 (n,).

        Raises:
            numpy.linalg.LinAlgError: Hessian이 특이 행렬(역행렬 없음)인 경우 np.linalg.solve가 일으킨다.
        """
        self.t += 1
        # np.linalg.solve(H, g)는 연립방정식 H d = g의 해 d를 구한다.
        # inv(H) @ g와 답은 같지만 역행렬을 만들지 않아 더 빠르고 수치적으로 안정적이다.
        direction = np.linalg.solve(self.hessian(params), np.asarray(grad, dtype=float))
        return np.asarray(params, dtype=float) - self.lr * direction


def optimize(optimizer, grad_fn, x0, n_iters=100, stop_tol=None):
    """옵티마이저를 n_iters번 반복하고 모든 위치를 기록한다.

    데이터 흐름: x0 (2,) → [기울기 계산 → step] × n_iters → 경로 (T+1, 2).
    VanillaGD(0.1), quadratic_grad, x0=(5, 5)라면 경로의 앞부분은
    [[5, 5], [4, 4], [3.2, 3.2], ...]이다.

    Args:
        optimizer: step 메서드가 있는 옵티마이저 객체. 시작할 때 reset()으로 상태를 비운다.
        grad_fn: 위치를 받아 기울기를 돌려주는 함수.
        x0: 시작 위치.
        n_iters: 최대 반복 횟수.
        stop_tol: 지정하면 ‖∇f‖ < stop_tol일 때 일찍 멈춘다.

    Returns:
        np.ndarray: shape (반복 수 + 1, 2) 경로. 0행이 시작점이다.
        발산해 inf·nan이 나오면 그 위치까지 기록하고 멈춘다.
    """
    optimizer.reset()   # 같은 객체를 다시 써도 이전 실험의 속도·모멘트가 섞이지 않게 한다.
    x = np.asarray(x0, dtype=float)
    # x.copy()로 저장하는 이유: 리스트에는 배열 자체(같은 메모리)가 들어가므로, 누군가 x를 제자리에서
    # 수정하면 기록도 함께 바뀐다. 지금 옵티마이저들은 새 배열을 돌려주지만, 복사본을 넣어 두면
    # 어떤 옵티마이저가 와도 그 시점의 위치가 그대로 남는다.
    path = [x.copy()]
    for _ in range(n_iters):
        g = grad_fn(x)
        if stop_tol is not None and np.linalg.norm(g) < stop_tol:
            break
        x = optimizer.step(x, g)
        path.append(x.copy())
        # np.isfinite는 inf·nan이 아닌지 원소마다 검사하고, np.all은 모두 참인지 본다.
        # 발산해서 inf가 되면 더 계산해도 의미가 없으므로 멈춘다.
        if not np.all(np.isfinite(x)):
            break
    # (2,) 배열 T+1개의 리스트 → (T+1, 2) 배열. path[:, 0]이 x 좌표 열, path[-1]이 마지막 위치.
    return np.array(path)


def iterations_to_reach(path, target, tol):
    """경로가 처음으로 ‖θ − target‖ < tol이 되는 반복 번호. 도달하지 못하면 None.

    Args:
        path: optimize가 돌려준 (T+1, 2) 경로.
        target: 목표 위치 (예: 최솟값 (0, 0)).
        tol: 도달로 인정할 거리.

    Returns:
        int | None: 처음 도달한 행 번호(= 반복 횟수) 또는 None.
    """
    # (T+1, 2) − (2,)는 브로드캐스팅으로 모든 행에서 target을 뺀다. axis=1로 행마다 길이 → (T+1,).
    dist = np.linalg.norm(np.asarray(path) - np.asarray(target), axis=1)
    # dist < tol은 참/거짓 배열. np.nonzero(...)[0]은 참인 위치들의 번호 배열이다.
    hits = np.nonzero(dist < tol)[0]
    # hits.size가 0이면(한 번도 도달 못함) None. 0이 아니면 첫 번째 번호.
    return int(hits[0]) if hits.size else None


# ---------------------------------------------------------------------------
# 시각화
# ---------------------------------------------------------------------------

# 옵티마이저 이름별 선 색·모양. dict(color=..., ls=...)는 {"color": ..., "ls": ...}와 같다.
STYLES = {
    "VanillaGD": dict(color="tab:blue", ls="--", marker="o"),
    "Momentum": dict(color="tab:red", ls="--", marker="s"),
    "Adam": dict(color="tab:green", ls="--", marker="^"),
    "Newton": dict(color="tab:purple", ls="--", marker="D"),
}


def plot_contour(f, ax, xlim=(-6, 6), ylim=(-6, 6), levels=20, log_levels=False):
    """함수 f의 등고선을 그린다.

    Args:
        f: 그릴 함수 (첫 축이 x, y인 배열을 받는다).
        ax: 그릴 좌표축.
        xlim, ylim: 그림 범위 (최소, 최대).
        levels: 등고선 개수.
        log_levels: True면 등고선 높이를 로그 간격으로 둔다. Rosenbrock처럼 값 범위가 넓은 함수용.
    """
    # *xlim은 (−6, 6)을 풀어 linspace(−6, 6, 300)으로 넘긴다.
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
        f: 등고선을 그릴 함수.
        paths: {이름: shape (T, 2) 경로}.
        ax: 그릴 좌표축. None이면 새로 만든다.
        title: 그림 제목.
        xlim, ylim: 그림 범위.
        target: 별표로 표시할 최적점.
        log_levels: 등고선 로그 간격 여부.
        target_label: 별표의 범례 이름.
        markevery: {이름: 간격}. 반복이 많은 경로는 일부 점에만 표시한다.

    Returns:
        matplotlib.axes.Axes: 그림을 그린 좌표축.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    plot_contour(f, ax, xlim, ylim, log_levels=log_levels)
    # dict.items()는 (키, 값) 쌍을 차례로 준다.
    for name, path in paths.items():
        # .get(name, 기본값)은 키가 없을 때 오류 대신 기본값을 준다. dict(...)로 복사해 원본 STYLES를 보호한다.
        style = dict(STYLES.get(name, dict(ls="--", marker=".")))
        # (markevery or {})는 markevery가 None이면 빈 dict를 쓴다는 짧은 표현이다.
        every = (markevery or {}).get(name)
        # path[:, 0]은 모든 행의 0번 열 = x 좌표들, path[:, 1]은 y 좌표들. **style은 dict를 이름=값 인자로 푼다.
        ax.plot(path[:, 0], path[:, 1], label=f"{name} ({len(path) - 1} steps)",
                markersize=3, lw=1.3, markevery=every, **style)
        ax.plot(*path[0], "ko", markersize=5)   # 시작점: 검은(k) 동그라미(o)
    ax.plot(*target, "k*", markersize=12, label=target_label)
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper left")
    return ax


def plot_distance_curves(paths, ax=None, target=(0, 0), title=""):
    """반복마다 최적점까지 거리 ‖θ_t − θ*‖를 로그 축으로 그린다.

    로그 축에서 직선으로 내려가면 "매 반복 같은 비율로 줄어든다"(선형 수렴)는 뜻이다.

    Args:
        paths: {이름: (T, 2) 경로}.
        ax: 그릴 좌표축. None이면 새로 만든다.
        target: 최적점.
        title: 그림 제목.

    Returns:
        matplotlib.axes.Axes: 그림을 그린 좌표축.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for name, path in paths.items():
        dist = np.linalg.norm(path - np.asarray(target), axis=1)
        color = STYLES.get(name, {}).get("color")
        # 거리가 정확히 0이면 log(0)을 그릴 수 없으므로 1e-16 아래는 1e-16으로 올린다(표시용).
        ax.semilogy(np.arange(len(dist)), np.maximum(dist, 1e-16), label=name, color=color)
    ax.set_xlabel("iteration")
    ax.set_ylabel("distance to minimum (log)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return ax
