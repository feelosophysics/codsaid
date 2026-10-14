"""딥러닝 학습 전에 먼저 측정하는 베이스라인 예측기.

모두 '시점 t를 예측할 때 t-1까지의 실제값만' 쓴다. 입력 y는 전체 시계열이지만 각 함수는
y[:t]만 읽는다(테스트에서 y[t:]를 바꿔도 예측이 그대로인지 확인한다).
"""
import numpy as np


def naive(y, targets):
    """ŷ(t) = y(t−1)"""
    return y[np.asarray(targets) - 1]


def sma(y, targets, window):
    """ŷ(t) = (1/n) Σ_{i=1..n} y(t−i)"""
    csum = np.concatenate([[0.0], np.cumsum(y)])
    targets = np.asarray(targets)
    return (csum[targets] - csum[targets - window]) / window


def ema_path(y, alpha):
    """s(t) = α·y(t−1) + (1−α)·s(t−1), s(1) = y(0). s[t]는 y[:t]만으로 정해진다."""
    s = np.empty_like(y, dtype=float)
    s[0] = y[0]
    for t in range(1, len(y)):
        s[t] = alpha * y[t - 1] + (1 - alpha) * s[t - 1]
    return s


def ema(y, targets, alpha):
    """ŷ(t) = α·y(t−1) + (1−α)·ŷ(t−1)"""
    return ema_path(y, alpha)[np.asarray(targets)]


def linear_trend(y, train_targets, targets):
    """ŷ(t) = a·t + b. a, b는 Train 시점의 (t, y(t))로만 최소제곱 적합한다."""
    a, b = np.polyfit(np.asarray(train_targets, dtype=float), y[train_targets], 1)
    return a * np.asarray(targets, dtype=float) + b, {"a": float(a), "b": float(b)}


def lag_matrix(y, targets, lags):
    targets = np.asarray(targets)
    return np.column_stack([y[targets - k] for k in range(1, lags + 1)] + [np.ones(len(targets))])


def linear_lag(y, train_targets, targets, lags=5):
    """ŷ(t) = w1·y(t−1) + … + wp·y(t−p) + b. Train 시점으로만 최소제곱 적합한다."""
    w, *_ = np.linalg.lstsq(lag_matrix(y, train_targets, lags), y[train_targets], rcond=None)
    return lag_matrix(y, targets, lags) @ w, {"weights": w.tolist()}


SMA_WINDOWS = (5, 10, 20)
EMA_ALPHAS = (0.1, 0.3, 0.5)


def all_baselines(y, splits):
    """{이름: {split: 예측 배열}}과 적합된 계수. 미션의 파라미터 가이드를 모두 실험한다."""
    preds, params = {}, {}
    train = splits["train"]

    def add(name, fn):
        preds[name] = {split: fn(targets) for split, targets in splits.items()}

    add("Naive", lambda t: naive(y, t))
    for n in SMA_WINDOWS:
        add(f"SMA({n})", lambda t, n=n: sma(y, t, n))
    for a in EMA_ALPHAS:
        add(f"EMA({a})", lambda t, a=a: ema(y, t, a))
    add("LinearTrend", lambda t: linear_trend(y, train, t)[0])
    params["LinearTrend"] = linear_trend(y, train, train)[1]
    add("LinearLag(5)", lambda t: linear_lag(y, train, t)[0])
    params["LinearLag(5)"] = linear_lag(y, train, train)[1]
    return preds, params
