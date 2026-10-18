"""2층 신경망(입력 2 → 은닉 2 → 출력 1)의 순전파·역전파를 NumPy로 직접 계산한다.

순전파                                   shape
    z1 = W1 @ x + b1                     (2,) = (2,2) @ (2,) + (2,)
    a1 = σ(z1)                           (2,)
    z2 = W2 @ a1 + b2                    ()   = (2,) @ (2,) + ()
    ŷ  = σ(z2)                           ()
    L  = −[y log ŷ + (1 − y) log(1 − ŷ)] ()

역전파 (연쇄 법칙)
    ∂L/∂ŷ  = −y/ŷ + (1 − y)/(1 − ŷ)
    ∂L/∂z2 = ∂L/∂ŷ · σ'(z2) = ŷ − y            σ'(z) = σ(z)(1 − σ(z))
    ∂L/∂W2 = ∂L/∂z2 · a1                       (2,)
    ∂L/∂b2 = ∂L/∂z2                            ()
    ∂L/∂a1 = ∂L/∂z2 · W2                       (2,)
    ∂L/∂z1 = ∂L/∂a1 ⊙ a1(1 − a1)               (2,)
    ∂L/∂W1 = outer(∂L/∂z1, x)                  (2,2)
    ∂L/∂b1 = ∂L/∂z1                            (2,)

shape 표기: (2,)는 숫자 2개짜리 1차원 배열(벡터), (2,2)는 2행 2열 행렬, ()는 숫자 하나(스칼라)다.

미션에서 이 파일이 맡는 문제:
    고정 예제(x=[1,0], y=1)로 역전파를 손계산하고, 같은 식을 코드로 옮겨 NumPy 결과와
    소수점 4자리까지 맞춰 본다. 기울기는 "손실을 줄이려면 각 가중치를 어느 방향으로 얼마나
    움직여야 하는가"를 알려 주며, sgd_step이 그 방향으로 한 걸음 움직인다.
    수식 유도는 notebooks/backprop_derivation.ipynb, 중간값 표는 study/code-walkthrough.md에 있다.
"""
import numpy as np


def sigmoid(z):
    """σ(z) = 1 / (1 + e^{−z}). 출력 범위 (0, 1).

    아무 실수를 0과 1 사이로 눌러 "확률처럼" 읽을 수 있게 한다.
    σ(0) = 0.5, σ(0.1) ≈ 0.525, σ(−6) ≈ 0.0025.

    Args:
        z: 숫자 또는 배열. 배열이면 원소마다 계산한다.

    Returns:
        z와 같은 shape의 값.
    """
    # np.exp(-z)는 e^(−z)를 원소마다 계산한다. 1.0 / 배열도 원소마다 나눈다.
    return 1.0 / (1.0 + np.exp(-z))


def sigmoid_derivative(z):
    """σ'(z) = σ(z)(1 − σ(z)). 최댓값은 z=0에서 0.25.

    Args:
        z: 숫자 또는 배열.

    Returns:
        z와 같은 shape의 기울기. 예: z=0.1이면 0.525 × 0.475 ≈ 0.2494.
    """
    s = sigmoid(z)
    return s * (1.0 - s)


def binary_cross_entropy(y_pred, y_true, eps=1e-12):
    """BCE L = −[y log ŷ + (1 − y) log(1 − ŷ)].

    log(0)을 피하려고 ŷ를 [eps, 1 − eps]로 자른다.

    정답 y=1이면 −log ŷ만 남는다. ŷ=0.647이면 L = −log 0.647 ≈ 0.435,
    ŷ=0.99면 0.01, ŷ=0.01이면 4.6. 확신을 갖고 틀릴수록 손실이 크게 늘어난다.

    Args:
        y_pred: 예측 확률 ŷ (0~1).
        y_true: 정답 0 또는 1.
        eps: 잘라 낼 아주 작은 여유값.

    Returns:
        float: 손실 값(0 이상).
    """
    # np.clip(값, 최솟값, 최댓값)은 범위를 벗어난 값을 경계로 바꾼 새 값을 돌려준다.
    p = np.clip(y_pred, eps, 1.0 - eps)
    # np.log는 자연로그(밑 e)다.
    return float(-(y_true * np.log(p) + (1.0 - y_true) * np.log(1.0 - p)))


class TwoLayerNet:
    """입력 2 → 은닉 2 → 출력 1, 두 층 모두 Sigmoid인 신경망.

    class는 데이터(가중치)와 그 데이터로 하는 일(forward, backward)을 묶은 설계도다.
    ``net = TwoLayerNet(W1, b1, W2, b2)``처럼 호출하면 객체가 만들어지고,
    ``net.forward(x, y)``처럼 점(.)으로 메서드를 부른다.

    Attributes:
        W1: shape (2, 2). W1[i, j]는 입력 j → 은닉 i 연결의 가중치.
        b1: shape (2,).
        W2: shape (2,). 은닉 i → 출력 연결의 가중치.
        b2: 스칼라.
    """

    def __init__(self, W1, b1, W2, b2):
        """가중치를 float 배열로 복사해 저장한다.

        __init__은 객체를 만들 때 자동으로 실행되는 초기화 메서드다.
        self는 "지금 만들어지는 그 객체 자신"이며, self.W1 = ...은 객체 안에 값을 보관한다.
        메서드의 첫 인자로 self를 받지만, 호출할 때는 net.forward(x, y)처럼 생략한다.

        Args:
            W1: 은닉층 가중치, 리스트 또는 배열 (2, 2).
            b1: 은닉층 편향 (2,).
            W2: 출력층 가중치 (2,).
            b2: 출력층 편향, 숫자 하나.

        Raises:
            ValueError: 가중치 shape이 이 신경망 구조와 맞지 않는 경우.
        """
        # np.array는 항상 새 복사본을 만든다. 나중에 sgd_step이 self.W1을 바꿔도
        # 호출한 쪽이 넘긴 원래 리스트·배열(예: EXAMPLE["W1"])은 바뀌지 않는다.
        self.W1 = np.array(W1, dtype=float)
        self.b1 = np.array(b1, dtype=float)
        self.W2 = np.array(W2, dtype=float)
        self.b2 = float(b2)
        # 튜플 비교 (2, 2) != (2, 2)로 shape이 정확히 맞는지 확인한다.
        if self.W1.shape != (2, 2) or self.b1.shape != (2,) or self.W2.shape != (2,):
            raise ValueError("W1 (2,2), b1 (2,), W2 (2,) shape이 필요하다")

    def forward(self, x, y_true):
        """순전파 중간값과 손실을 모두 반환한다.

        입력에서 출력 방향으로 계산한다. 중간값(z1, a1, ...)을 버리지 않고 돌려주는 이유는
        backward가 이 값들을 다시 쓰기 때문이다(다시 계산하지 않아도 된다).

        고정 예제 x=[1, 0], W1=[[0.1, 0.2], [0.3, 0.4]], b1=0, W2=[0.5, 0.6], b2=0, y=1:
            z1 = [0.1, 0.3] → a1 = [0.5250, 0.5744] → z2 = 0.6072 → ŷ = 0.6473 → L = 0.4350

        Args:
            x: 입력 (2,).
            y_true: 정답 0 또는 1.

        Returns:
            dict: x, z1, a1, z2, y_pred, loss. 객체의 가중치는 바꾸지 않는다.
        """
        x = np.asarray(x, dtype=float)
        # (2, 2) @ (2,) → (2,). 은닉 뉴런 i마다 Σ_j W1[i, j]·x_j를 계산한 뒤 편향 b1을 더한다.
        # 예제: [0.1·1 + 0.2·0, 0.3·1 + 0.4·0] + [0, 0] = [0.1, 0.3]
        z1 = self.W1 @ x + self.b1
        a1 = sigmoid(z1)                       # (2,) 원소마다 σ
        # (2,) @ (2,)는 벡터 내적 → 숫자 하나. float()로 파이썬 실수로 바꾼다.
        # 예제: 0.5·0.5250 + 0.6·0.5744 + 0 = 0.6072
        z2 = float(self.W2 @ a1 + self.b2)
        y_pred = float(sigmoid(z2))
        return {"x": x, "z1": z1, "a1": a1, "z2": z2, "y_pred": y_pred,
                "loss": binary_cross_entropy(y_pred, y_true)}

    def backward(self, cache, y_true):
        """forward의 중간값으로 모든 기울기를 연쇄 법칙으로 계산한다.

        손실에서 입력 방향으로 거꾸로 가며 "뒤에서 온 기울기 × 이 단계의 국소 미분"을 반복한다.
        각 기울기의 shape은 그것이 가리키는 값의 shape과 같다(dL_dW1은 W1처럼 (2, 2)).

        Args:
            cache: forward가 돌려준 dict.
            y_true: 정답 0 또는 1. forward에 넣은 값과 같아야 한다.

        Returns:
            dict: dL_dy_pred, dL_dz2, dL_dW2, dL_db2, dL_da1, dL_dz1, dL_dW1, dL_db1.
            객체의 가중치는 바꾸지 않는다. 실제 갱신은 sgd_step이 한다.
        """
        # dict에서 이름으로 값을 꺼내 세 변수에 나눠 담는다.
        y_pred, a1, x = cache["y_pred"], cache["a1"], cache["x"]
        # 예제(y=1): −1 / 0.6473 = −1.5449. 음수 → ŷ를 키우면 손실이 준다.
        dL_dy_pred = -y_true / y_pred + (1.0 - y_true) / (1.0 - y_pred)
        # σ'(z2) = ŷ(1 − ŷ)를 곱한다. 약분하면 ŷ − y = 0.6473 − 1 = −0.3527.
        dL_dz2 = dL_dy_pred * y_pred * (1.0 - y_pred)   # = y_pred − y_true
        # 숫자 × (2,) 배열 → (2,). z2 = Σ W2_i·a1_i이므로 ∂z2/∂W2_i = a1_i.
        # 예제: −0.3527 × [0.5250, 0.5744] = [−0.1852, −0.2026]
        dL_dW2 = dL_dz2 * a1
        # 같은 이유로 ∂z2/∂a1_i = W2_i. 출력층의 오차를 은닉층으로 "나눠 보낸다".
        # 예제: −0.3527 × [0.5, 0.6] = [−0.1764, −0.2116]
        dL_da1 = dL_dz2 * self.W2
        # (2,) * (2,) * (2,)는 같은 위치끼리 곱(⊙, 원소별 곱)이다. 행렬 곱이 아니다.
        # a1 × (1 − a1)은 은닉층 σ의 기울기. 예제: [−0.1764·0.2494, −0.2116·0.2445] = [−0.0440, −0.0517]
        dL_dz1 = dL_da1 * a1 * (1.0 - a1)
        # np.outer(u, v)[i, j] = u_i · v_j → (2,) 와 (2,)로 (2, 2). ∂z1_i/∂W1[i, j] = x_j이기 때문이다.
        # 예제는 x = [1, 0]이라 둘째 열이 0이다. 쓰이지 않은 입력의 가중치는 갱신되지 않는다.
        dL_dW1 = np.outer(dL_dz1, x)
        # 편향은 ∂z/∂b = 1이라 dL_db = dL_dz다. dL_db1은 .copy()로 별도 배열을 만들어
        # 한쪽을 수정해도 다른 쪽이 따라 바뀌지 않게 한다.
        return {"dL_dy_pred": float(dL_dy_pred), "dL_dz2": float(dL_dz2),
                "dL_dW2": dL_dW2, "dL_db2": float(dL_dz2), "dL_da1": dL_da1,
                "dL_dz1": dL_dz1, "dL_dW1": dL_dW1, "dL_db1": dL_dz1.copy()}

    def loss_with(self, x, y_true, **overrides):
        """일부 파라미터를 바꿨을 때의 손실. 수치 미분 검증에 사용한다.

        예: ``net.loss_with(x, y, W1=새_W1)``은 W1만 바꾼 임시 신경망의 손실이다.
        numerical_gradient가 W1 원소를 ±h씩 움직여 이 함수를 부르면, 역전파 없이
        "가중치를 조금 바꾸면 손실이 얼마나 변하는가"를 직접 잴 수 있다.

        Args:
            x: 입력 (2,).
            y_true: 정답.
            **overrides: 바꿀 파라미터를 이름=값으로 받는다. **는 받은 이름=값들을 dict로 모은다.

        Returns:
            float: 손실. 이 객체(self)의 가중치는 바꾸지 않는다.
        """
        params = {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2}
        # update는 같은 이름의 값을 덮어쓴다. W1=새값을 넘겼다면 params["W1"]만 바뀐다.
        params.update(overrides)
        # TwoLayerNet(**params)는 dict를 W1=..., b1=... 인자로 풀어 넣는다. 새 객체를 만들어 계산한다.
        return TwoLayerNet(**params).forward(x, y_true)["loss"]

    def sgd_step(self, grads, lr):
        """θ ← θ − lr · ∂L/∂θ 로 파라미터를 한 번 갱신한다.

        기울기는 손실이 커지는 방향이므로 빼야 손실이 준다.
        예제에서 dL_dW2 = [−0.1852, −0.2026], lr = 0.5이면 W2는 [0.5926, 0.7013]이 된다.

        Args:
            grads: backward가 돌려준 dict.
            lr: 학습률(한 걸음의 크기).

        Returns:
            None. 반환값 없이 이 객체의 가중치(self.W1 등)를 직접 바꾼다.
        """
        # -=는 "빼서 다시 저장"이다. NumPy 배열에서는 기존 배열의 값을 그 자리에서 바꾼다.
        self.W1 -= lr * grads["dL_dW1"]
        self.b1 -= lr * grads["dL_db1"]
        self.W2 -= lr * grads["dL_dW2"]
        self.b2 -= lr * grads["dL_db2"]


# 미션에서 고정한 손계산 예제. y_true는 미션 결과 예시와 같이 1을 사용한다.
# 대문자 이름은 "바꾸지 않고 참고만 하는 값(상수)"이라는 관례다.
EXAMPLE = {
    "x": [1.0, 0.0],
    "W1": [[0.1, 0.2], [0.3, 0.4]],
    "b1": [0.0, 0.0],
    "W2": [0.5, 0.6],
    "b2": 0.0,
    "y_true": 1.0,
}


def example_network():
    """고정 예제의 신경망, 입력, 정답을 반환한다.

    Returns:
        tuple: (TwoLayerNet, 입력 x (2,), 정답 y). 호출한 쪽에서
        ``net, x, y = example_network()``처럼 세 변수로 나눠 받는다.
    """
    net = TwoLayerNet(EXAMPLE["W1"], EXAMPLE["b1"], EXAMPLE["W2"], EXAMPLE["b2"])
    return net, np.array(EXAMPLE["x"]), EXAMPLE["y_true"]
