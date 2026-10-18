"""정보 이론(보너스): 엔트로피, Cross-Entropy, KL-Divergence.

단위는 자연로그(nat)이다. bit로 바꾸려면 log 2로 나눈다.
관계식:  H(p, q) = H(p) + KL(p ‖ q)
분류 학습에서 p(정답)는 고정이므로 Cross-Entropy 최소화 = KL 최소화이다.

미션에서 이 파일이 맡는 문제(보너스):
    분류 손실로 쓰는 Cross-Entropy가 "모델 분포 q가 정답 분포 p와 얼마나 다른가"를
    재는 양과 어떻게 연결되는지 보인다. probability.py의 손실 함수들과 짝을 이룬다.

모든 함수에서 p, q는 확률 벡터(0 이상, 합 1)이며 shape (클래스 수,)인 1차원 배열이다.
"""
import numpy as np


def _validate(p):
    """확률 벡터인지 확인하고 float 배열로 반환한다.

    Args:
        p: 확률 벡터로 쓸 리스트 또는 배열.

    Returns:
        np.ndarray: float 배열.

    Raises:
        ValueError: 음수가 있거나 합이 1이 아닌 경우.
    """
    p = np.asarray(p, dtype=float)
    # np.isclose(a, b)는 "거의 같은가"를 본다. 0.1 + 0.2 + 0.7처럼 소수 합은 정확히 1.0이 아닐 수 있다.
    if np.any(p < 0) or not np.isclose(p.sum(), 1.0):
        raise ValueError("확률 분포는 0 이상이고 합이 1이어야 한다")
    return p


def entropy(p):
    """엔트로피  H(p) = −Σ p_i log p_i.  (0 · log 0 = 0으로 정의)

    결과가 얼마나 불확실한지의 평균 정보량. 균등분포에서 최대 log n.

    p = [0.5, 0.5] → log 2 ≈ 0.693 (가장 불확실), p = [1, 0] → 0 (결과가 확실).

    Args:
        p: 확률 벡터.

    Returns:
        float: 엔트로피(nat).
    """
    p = _validate(p)
    # p > 0은 참/거짓 배열(마스크). p[nz]처럼 마스크로 인덱싱하면 참인 칸만 골라낸다.
    # [0.7, 0.3, 0.0]이면 nz = [True, True, False], p[nz] = [0.7, 0.3]. log(0)을 계산하지 않게 한다.
    nz = p > 0
    return float(-np.sum(p[nz] * np.log(p[nz])))


def cross_entropy(p, q):
    """Cross-Entropy  H(p, q) = −Σ p_i log q_i.

    실제 분포 p의 사건을 모델 분포 q 기준의 부호로 표현할 때 드는 평균 정보량.
    p_i > 0인데 q_i = 0이면 무한대이다.

    정답이 one-hot p = [0, 1, 0]이면 −log q_1만 남는다. 분류 손실이 "정답 클래스 확률의 −log"인 이유다.

    Args:
        p: 실제(정답) 분포.
        q: 모델 분포.

    Returns:
        float: Cross-Entropy(nat). 무한대일 수 있다.
    """
    p, q = _validate(p), _validate(q)
    nz = p > 0
    # q[nz]: p가 양수인 칸의 q 값만 본다. 그중 0이 하나라도 있으면 log 0 = −∞이다.
    if np.any(q[nz] == 0):
        return float("inf")
    return float(-np.sum(p[nz] * np.log(q[nz])))


def kl_divergence(p, q):
    """KL-Divergence  KL(p ‖ q) = Σ p_i log(p_i / q_i) ≥ 0.

    p = q일 때만 0이고, 일반적으로 KL(p‖q) ≠ KL(q‖p)인 비대칭 거리이다.

    p = [0.7, 0.3], q = [0.4, 0.6]이면 0.7·log(1.75) + 0.3·log(0.5) = 0.392 − 0.208 = 0.184.

    Args:
        p: 기준 분포.
        q: 비교할 분포.

    Returns:
        float: KL(p ‖ q) (nat). 무한대일 수 있다.
    """
    p, q = _validate(p), _validate(q)
    nz = p > 0
    if np.any(q[nz] == 0):
        return float("inf")
    # p[nz] / q[nz]는 같은 위치끼리 나눈다. 비율이 1이면 log 1 = 0이라 그 칸은 기여하지 않는다.
    return float(np.sum(p[nz] * np.log(p[nz] / q[nz])))


def binary_entropy(p):
    """베르누이(p)의 엔트로피 곡선. p는 배열이어도 된다.

    Args:
        p: 1이 나올 확률. 0~1 사이 숫자 또는 배열.

    Returns:
        np.ndarray: p와 같은 shape의 엔트로피. p = 0, 1에서는 0이다.
    """
    p = np.asarray(p, dtype=float)
    # with np.errstate(...): 이 블록 안에서만 0으로 나누기·log(0) 경고를 숨긴다.
    # p=0이면 0·log 0이 nan으로 계산되는데, 정의상 0이므로 아래에서 바로잡는다.
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -(p * np.log(p) + (1 - p) * np.log(1 - p))
    # nan_to_num은 nan을 0으로 바꾼다. 양 끝 p=0, 1의 엔트로피가 0이 된다.
    return np.nan_to_num(h)
