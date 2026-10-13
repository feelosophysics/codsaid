"""정보 이론(보너스): 엔트로피, Cross-Entropy, KL-Divergence.

단위는 자연로그(nat)이다. bit로 바꾸려면 log 2로 나눈다.
관계식:  H(p, q) = H(p) + KL(p ‖ q)
분류 학습에서 p(정답)는 고정이므로 Cross-Entropy 최소화 = KL 최소화이다.
"""
import numpy as np


def _validate(p):
    """확률 벡터인지 확인하고 float 배열로 반환한다."""
    p =np.asarray(p, dtype=float)
    if np.any(p < 0) or not np.isclose(p.sum(), 1.0):
        raise ValueError("확률 분포는 0 이상이고 합이 1이어야 한다")
    return p


def entropy(p):
    """엔트로피  H(p) = −Σ p_i log p_i.  (0 · log 0 = 0으로 정의)

    결과가 얼마나 불확실한지의 평균 정보량. 균등분포에서 최대 log n.
    """
    p = _validate(p)
    nz = p > 0
    return float(-np.sum(p[nz] * np.log(p[nz])))


def cross_entropy(p, q):
    """Cross-Entropy  H(p, q) = −Σ p_i log q_i.

    실제 분포 p의 사건을 모델 분포 q 기준의 부호로 표현할 때 드는 평균 정보량.
    p_i > 0인데 q_i = 0이면 무한대이다.
    """
    p, q = _validate(p), _validate(q)
    nz = p > 0
    if np.any(q[nz] == 0):
        return float("inf")
    return float(-np.sum(p[nz] * np.log(q[nz])))


def kl_divergence(p, q):
    """KL-Divergence  KL(p ‖ q) = Σ p_i log(p_i / q_i) ≥ 0.

    p = q일 때만 0이고, 일반적으로 KL(p‖q) ≠ KL(q‖p)인 비대칭 거리이다.
    """
    p, q = _validate(p), _validate(q)
    nz = p > 0
    if np.any(q[nz] == 0):
        return float("inf")
    return float(np.sum(p[nz] * np.log(p[nz] / q[nz])))


def binary_entropy(p):
    """베르누이(p)의 엔트로피 곡선. p는 배열이어도 된다."""
    p = np.asarray(p, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -(p * np.log(p) + (1 - p) * np.log(1 - p))
    return np.nan_to_num(h)
