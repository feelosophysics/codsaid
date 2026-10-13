"""가중치 초기화 전략.

N(0, σ)의 두 번째 값은 표준편차다. Linear의 가중치 shape는 (n_in, n_out)이다.

| 방법 | 표준편차 | 쓰임 |
| --- | --- | --- |
| zero | 0 | 대칭성 문제 재현용 (학습 실패) |
| random | 1 | 표준정규분포. 층이 넓을수록 출력 분산이 n_in배씩 커진다 |
| he | √(2/n_in) | ReLU: 절반이 0이 되어 줄어드는 분산을 2배로 보정 |
| xavier | √(2/(n_in+n_out)) | Sigmoid/Tanh: 순전파·역전파 분산을 함께 보존 |
"""
import numpy as np

METHODS = ("zero", "random", "he", "xavier")


def init_std(method, n_in, n_out):
    if method == "zero":
        return 0.0
    if method == "random":
        return 1.0
    if method == "he":
        return np.sqrt(2.0 / n_in)
    if method == "xavier":
        return np.sqrt(2.0 / (n_in + n_out))
    raise ValueError(f"알 수 없는 초기화 방법: {method!r} (가능: {', '.join(METHODS)})")


def initialize(shape, method, rng=None):
    """shape=(n_in, n_out) 가중치를 method 방식으로 샘플링한다."""
    n_in, n_out = shape
    std = init_std(method, n_in, n_out)
    if std == 0.0:
        return np.zeros(shape)
    rng = np.random.default_rng() if rng is None else rng
    return rng.standard_normal(shape) * std


def zeros(shape, rng=None):
    return initialize(shape, "zero", rng)


def random_normal(shape, rng=None):
    return initialize(shape, "random", rng)


def he_normal(shape, rng=None):
    return initialize(shape, "he", rng)


def xavier_normal(shape, rng=None):
    return initialize(shape, "xavier", rng)
