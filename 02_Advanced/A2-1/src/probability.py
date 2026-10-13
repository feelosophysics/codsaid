"""확률/통계: 분포, 소프트맥스, 손실 함수와 MLE(최대우도추정)의 연결.

표기: N(μ, σ²)의 두 번째 값은 **분산**이다. 따라서 N(2, 0.5)는 σ = √0.5 ≈ 0.707이다.
"""
import numpy as np
import matplotlib.pyplot as plt


def normal_pdf(x, mu=0.0, var=1.0):
    """정규분포 확률밀도  p(x) = 1/√(2πσ²) · exp(−(x − μ)² / 2σ²).

    Args:
        var: 분산 σ². 표준편차가 아니다.
    """
    x = np.asarray(x, dtype=float)
    return np.exp(-(x - mu) ** 2 / (2 * var)) / np.sqrt(2 * np.pi * var)


def bernoulli_pmf(k, p):
    """베르누이 확률질량  P(X = k) = p^k (1 − p)^{1−k},  k ∈ {0, 1}."""
    k = np.asarray(k)
    if np.any((k != 0) & (k != 1)):
        raise ValueError("베르누이 분포의 값은 0 또는 1이다")
    return np.power(p, k) * np.power(1 - p, 1 - k)


def softmax(z, axis=-1):
    """소프트맥스  softmax(z)_i = e^{z_i} / Σ_j e^{z_j}.

    모든 z_i에서 max(z)를 빼도 결과는 같다(분자·분모에 같은 e^{−max}가 곱해짐).
    이렇게 하면 e^{1000} 같은 overflow 없이 계산할 수 있다.
    """
    z = np.asarray(z, dtype=float)
    shifted = z - np.max(z, axis=axis, keepdims=True)
    e = np.exp(shifted)
    return e / np.sum(e, axis=axis, keepdims=True)


def mse(y_true, y_pred):
    """평균제곱오차  MSE = (1/n) Σ (y_i − ŷ_i)²."""
    return float(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2))


def gaussian_nll(y_true, y_pred, var=1.0):
    """y ~ N(ŷ, σ²) 가정의 음의 로그우도 합.

    −Σ log p(y_i | x_i) = (1 / 2σ²) Σ (y_i − ŷ_i)² + (n/2) log(2πσ²)
                       = (n / 2σ²) · MSE + 상수
    """
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(-np.sum(np.log(normal_pdf(y_true, y_pred, var))))


def bernoulli_nll(y_true, p_pred, eps=1e-12):
    """y ~ Bernoulli(p) 가정의 음의 로그우도 합 = BCE의 합.

    −Σ log[p_i^{y_i} (1 − p_i)^{1−y_i}] = −Σ [y_i log p_i + (1 − y_i) log(1 − p_i)]
    """
    p = np.clip(np.asarray(p_pred, dtype=float), eps, 1 - eps)
    y = np.asarray(y_true, dtype=float)
    return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def categorical_cross_entropy(y_onehot, logits):
    """카테고리 분포 가정의 음의 로그우도 = −Σ_i Σ_c y_ic log softmax(z_i)_c."""
    probs = softmax(logits, axis=-1)
    return float(-np.sum(np.asarray(y_onehot) * np.log(probs)))


def plot_normal_pdfs(params=((0.0, 1.0), (2.0, 0.5)), ax=None):
    """여러 정규분포 PDF를 한 Figure에 겹쳐 그린다. params는 (μ, σ²) 쌍."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    x = np.linspace(-4, 5, 500)
    for mu, var in params:
        y = normal_pdf(x, mu, var)
        line, = ax.plot(x, y, lw=2, label=f"N(μ={mu:g}, σ²={var:g}), σ={np.sqrt(var):.3f}")
        ax.fill_between(x, y, alpha=0.15, color=line.get_color())
        ax.axvline(mu, color=line.get_color(), ls=":", lw=1)
    ax.set_xlabel("x")
    ax.set_ylabel("probability density p(x)")
    ax.set_title("Normal distribution PDF")
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


def plot_bernoulli_pmfs(ps=(0.3, 0.7), ax=None):
    """여러 베르누이 PMF를 한 Figure에 막대그래프로 나란히 그린다."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    k = np.array([0, 1])
    width = 0.8 / len(ps)
    for i, p in enumerate(ps):
        probs = bernoulli_pmf(k, p)
        bars = ax.bar(k + (i - (len(ps) - 1) / 2) * width, probs, width, label=f"Bernoulli(p={p:g})")
        ax.bar_label(bars, fmt="%.2f", fontsize=9)
    ax.set_xticks(k)
    ax.set_xticklabels(["k=0 (failure)", "k=1 (success)"])
    ax.set_ylabel("P(X = k)")
    ax.set_ylim(0, 1)
    ax.set_title("Bernoulli distribution PMF")
    ax.legend()
    return ax
