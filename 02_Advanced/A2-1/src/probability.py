"""확률/통계: 분포, 소프트맥스, 손실 함수와 MLE(최대우도추정)의 연결.

표기: N(μ, σ²)의 두 번째 값은 **분산**이다. 따라서 N(2, 0.5)는 σ = √0.5 ≈ 0.707이다.

미션에서 이 파일이 맡는 문제:
    "왜 회귀는 MSE, 분류는 Cross-Entropy를 쓰는가?"에 답한다. 데이터가 어떤 분포에서
    나왔다고 가정하면, 그 분포의 음의 로그우도(NLL)가 곧 손실 함수가 된다.
        정규분포 가정  → gaussian_nll  = (상수배) × MSE + 상수
        베르누이 가정  → bernoulli_nll = BCE의 합
        카테고리 가정  → categorical_cross_entropy
    유도 과정은 notebooks/probability_loss.ipynb, 작은 숫자 예제는 study/code-walkthrough.md에 있다.
"""
import numpy as np
import matplotlib.pyplot as plt


def normal_pdf(x, mu=0.0, var=1.0):
    """정규분포 확률밀도  p(x) = 1/√(2πσ²) · exp(−(x − μ)² / 2σ²).

    x = μ에서 가장 크고, μ에서 멀어질수록 빠르게 줄어든다.
    N(0, 1)에서 p(0) = 1/√(2π) ≈ 0.399, p(1) ≈ 0.242.
    밀도는 확률이 아니라서 분산이 작으면 1보다 커질 수도 있다(넓이가 1이다).

    Args:
        x: 위치. 숫자 또는 배열(배열이면 원소마다 계산).
        mu: 평균 μ.
        var: 분산 σ². 표준편차가 아니다.

    Returns:
        x와 같은 shape의 밀도 값.
    """
    x = np.asarray(x, dtype=float)
    return np.exp(-(x - mu) ** 2 / (2 * var)) / np.sqrt(2 * np.pi * var)


def bernoulli_pmf(k, p):
    """베르누이 확률질량  P(X = k) = p^k (1 − p)^{1−k},  k ∈ {0, 1}.

    k=1이면 p^1·(1−p)^0 = p, k=0이면 p^0·(1−p)^1 = 1 − p. 두 경우를 지수로 한 식에 담았다.
    B(0.3): P(1) = 0.3, P(0) = 0.7.

    Args:
        k: 결과 0 또는 1. 배열이면 원소마다 계산한다.
        p: 1이 나올 확률. 숫자 또는 k와 같은 shape의 배열.

    Returns:
        k와 같은 shape의 확률.

    Raises:
        ValueError: k에 0, 1 이외의 값이 있는 경우.
    """
    k = np.asarray(k)
    # (k != 0) & (k != 1): 원소마다 "0도 아니고 1도 아님"을 참/거짓으로 계산한다.
    # 배열의 '그리고'는 and가 아니라 &를 쓴다. np.any는 하나라도 참인지 본다.
    if np.any((k != 0) & (k != 1)):
        raise ValueError("베르누이 분포의 값은 0 또는 1이다")
    # np.power(밑, 지수)는 원소별 거듭제곱이다.
    return np.power(p, k) * np.power(1 - p, 1 - k)


def softmax(z, axis=-1):
    """소프트맥스  softmax(z)_i = e^{z_i} / Σ_j e^{z_j}.

    모든 z_i에서 max(z)를 빼도 결과는 같다(분자·분모에 같은 e^{−max}가 곱해짐).
    이렇게 하면 e^{1000} 같은 overflow 없이 계산할 수 있다.

    z = [1, 2, 3]을 따라가면
        shifted = [−2, −1, 0] → e = [0.135, 0.368, 1.0] → 합 1.503
        → [0.090, 0.245, 0.665]. 모두 양수이고 합이 1, 점수가 클수록 확률이 크다.

    Args:
        z: 점수(logit) 배열. 2차원이면 행 하나가 샘플 하나다.
        axis: 확률로 바꿀 축. -1은 "마지막 축"이라 (샘플 수, 클래스 수) 배열에서 행마다 계산한다.

    Returns:
        np.ndarray: z와 같은 shape의 확률.
    """
    z = np.asarray(z, dtype=float)
    # keepdims=True: 줄어든 축을 길이 1로 남긴다. (4, 6) 배열이면 max 결과가 (4,)가 아니라 (4, 1)이 되어
    # (4, 6) − (4, 1)이 브로드캐스팅으로 "각 행에서 그 행의 최댓값을 빼기"가 된다.
    shifted = z - np.max(z, axis=axis, keepdims=True)
    # shifted의 최댓값은 0이므로 e의 최댓값은 1이다. overflow가 일어날 수 없다.
    e = np.exp(shifted)
    return e / np.sum(e, axis=axis, keepdims=True)


def mse(y_true, y_pred):
    """평균제곱오차  MSE = (1/n) Σ (y_i − ŷ_i)².

    y = [1, 2, 3], ŷ = [1, 2, 5]이면 (0 + 0 + 4) / 3 = 1.333.

    Args:
        y_true: 정답 배열.
        y_pred: 예측 배열 (같은 shape).

    Returns:
        float: 평균제곱오차.
    """
    return float(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2))


def gaussian_nll(y_true, y_pred, var=1.0):
    """y ~ N(ŷ, σ²) 가정의 음의 로그우도 합.

    −Σ log p(y_i | x_i) = (1 / 2σ²) Σ (y_i − ŷ_i)² + (n/2) log(2πσ²)
                       = (n / 2σ²) · MSE + 상수

    "정답 y는 예측 ŷ를 중심으로 한 정규분포에서 나왔다"고 보고, 실제 정답이 나올 확률(밀도)을
    샘플마다 구해 log를 씌워 더한 뒤 부호를 바꾼다. 예측이 정답에 가까울수록 값이 작다.

    Args:
        y_true: 정답 배열.
        y_pred: 예측 배열(정규분포의 평균으로 쓴다).
        var: 가정한 잡음 분산 σ².

    Returns:
        float: 음의 로그우도 합.
    """
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    # normal_pdf(y_true, y_pred, var): 샘플마다 "평균 ŷ_i인 정규분포에서 y_i의 밀도" (n,).
    # log → 합 → 부호 반전. 곱 대신 log의 합을 쓰면 아주 작은 수끼리 곱해 0이 되는 문제를 피한다.
    return float(-np.sum(np.log(normal_pdf(y_true, y_pred, var))))


def bernoulli_nll(y_true, p_pred, eps=1e-12):
    """y ~ Bernoulli(p) 가정의 음의 로그우도 합 = BCE의 합.

    −Σ log[p_i^{y_i} (1 − p_i)^{1−y_i}] = −Σ [y_i log p_i + (1 − y_i) log(1 − p_i)]

    y = [1, 0], p = [0.9, 0.2]이면 −[log 0.9 + log 0.8] = 0.105 + 0.223 = 0.329.

    Args:
        y_true: 정답 0/1 배열.
        p_pred: 예측 확률 배열.
        eps: log(0)을 피하기 위한 자르기 여유값.

    Returns:
        float: 음의 로그우도 합(평균이 아니라 합).
    """
    p = np.clip(np.asarray(p_pred, dtype=float), eps, 1 - eps)
    y = np.asarray(y_true, dtype=float)
    return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def categorical_cross_entropy(y_onehot, logits):
    """카테고리 분포 가정의 음의 로그우도 = −Σ_i Σ_c y_ic log softmax(z_i)_c.

    one-hot 정답은 정답 칸만 1이라 결국 "정답 클래스 확률의 −log"만 더해진다.

    Args:
        y_onehot: shape (샘플 수, 클래스 수) one-hot 정답. 예: 정답이 0번이면 [1, 0, 0].
        logits: 같은 shape의 점수. softmax로 확률로 바꾼 뒤 사용한다.

    Returns:
        float: 샘플 전체의 합.
    """
    probs = softmax(logits, axis=-1)
    # y_onehot * log(probs): 정답 칸만 log 확률이 남고 나머지는 0. np.sum으로 모든 칸을 더한다.
    return float(-np.sum(np.asarray(y_onehot) * np.log(probs)))


def plot_normal_pdfs(params=((0.0, 1.0), (2.0, 0.5)), ax=None):
    """여러 정규분포 PDF를 한 Figure에 겹쳐 그린다. params는 (μ, σ²) 쌍.

    Args:
        params: (평균, 분산) 쌍들의 튜플.
        ax: 그릴 좌표축. None이면 새로 만든다.

    Returns:
        matplotlib.axes.Axes: 그림을 그린 좌표축.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    x = np.linspace(-4, 5, 500)
    # for mu, var in params: 쌍 하나씩 꺼내 두 변수에 나눠 담는다.
    for mu, var in params:
        y = normal_pdf(x, mu, var)
        # ax.plot은 선 객체 리스트를 돌려준다. `line, =`은 길이 1인 리스트에서 그 하나를 꺼내는 언패킹이다.
        line, = ax.plot(x, y, lw=2, label=f"N(μ={mu:g}, σ²={var:g}), σ={np.sqrt(var):.3f}")
        # 곡선 아래를 같은 색으로 옅게 칠해 "넓이 = 1"을 눈으로 보이게 한다.
        ax.fill_between(x, y, alpha=0.15, color=line.get_color())
        ax.axvline(mu, color=line.get_color(), ls=":", lw=1)
    ax.set_xlabel("x")
    ax.set_ylabel("probability density p(x)")
    ax.set_title("Normal distribution PDF")
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


def plot_bernoulli_pmfs(ps=(0.3, 0.7), ax=None):
    """여러 베르누이 PMF를 한 Figure에 막대그래프로 나란히 그린다.

    Args:
        ps: 그릴 p 값들.
        ax: 그릴 좌표축. None이면 새로 만든다.

    Returns:
        matplotlib.axes.Axes: 그림을 그린 좌표축.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    k = np.array([0, 1])
    width = 0.8 / len(ps)
    # enumerate(ps)는 (번호, 값) 쌍을 준다: (0, 0.3), (1, 0.7).
    for i, p in enumerate(ps):
        probs = bernoulli_pmf(k, p)
        # 막대들이 겹치지 않게 i에 따라 x 위치를 좌우로 조금씩 옮긴다. ps가 2개면 −0.2, +0.2.
        bars = ax.bar(k + (i - (len(ps) - 1) / 2) * width, probs, width, label=f"Bernoulli(p={p:g})")
        ax.bar_label(bars, fmt="%.2f", fontsize=9)
    ax.set_xticks(k)
    ax.set_xticklabels(["k=0 (failure)", "k=1 (success)"])
    ax.set_ylabel("P(X = k)")
    ax.set_ylim(0, 1)
    ax.set_title("Bernoulli distribution PMF")
    ax.legend()
    return ax
