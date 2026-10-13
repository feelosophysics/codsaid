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
"""
import numpy as np


def sigmoid(z):
    """σ(z) = 1 / (1 + e^{−z}). 출력 범위 (0, 1)."""
    return 1.0 / (1.0 + np.exp(-z))


def sigmoid_derivative(z):
    """σ'(z) = σ(z)(1 − σ(z)). 최댓값은 z=0에서 0.25."""
    s = sigmoid(z)
    return s * (1.0 - s)


def binary_cross_entropy(y_pred, y_true, eps=1e-12):
    """BCE L = −[y log ŷ + (1 − y) log(1 − ŷ)].

    log(0)을 피하려고 ŷ를 [eps, 1 − eps]로 자른다.
    """
    p = np.clip(y_pred, eps, 1.0 - eps)
    return float(-(y_true * np.log(p) + (1.0 - y_true) * np.log(1.0 - p)))


class TwoLayerNet:
    """입력 2 → 은닉 2 → 출력 1, 두 층 모두 Sigmoid인 신경망.

    Attributes:
        W1: shape (2, 2). W1[i, j]는 입력 j → 은닉 i 연결의 가중치.
        b1: shape (2,).
        W2: shape (2,). 은닉 i → 출력 연결의 가중치.
        b2: 스칼라.
    """

    def __init__(self, W1, b1, W2, b2):
        """가중치를 float 배열로 복사해 저장한다."""
        self.W1 = np.array(W1, dtype=float)
        self.b1 = np.array(b1, dtype=float)
        self.W2 = np.array(W2, dtype=float)
        self.b2 = float(b2)
        if self.W1.shape != (2, 2) or self.b1.shape != (2,) or self.W2.shape != (2,):
            raise ValueError("W1 (2,2), b1 (2,), W2 (2,) shape이 필요하다")

    def forward(self, x, y_true):
        """순전파 중간값과 손실을 모두 반환한다.

        Returns:
            dict: x, z1, a1, z2, y_pred, loss.
        """
        x = np.asarray(x, dtype=float)
        z1 = self.W1 @ x + self.b1
        a1 = sigmoid(z1)
        z2 = float(self.W2 @ a1 + self.b2)
        y_pred = float(sigmoid(z2))
        return {"x": x, "z1": z1, "a1": a1, "z2": z2, "y_pred": y_pred,
                "loss": binary_cross_entropy(y_pred, y_true)}

    def backward(self, cache, y_true):
        """forward의 중간값으로 모든 기울기를 연쇄 법칙으로 계산한다.

        Returns:
            dict: dL_dy_pred, dL_dz2, dL_dW2, dL_db2, dL_da1, dL_dz1, dL_dW1, dL_db1.
        """
        y_pred, a1, x = cache["y_pred"], cache["a1"], cache["x"]
        dL_dy_pred = -y_true / y_pred + (1.0 - y_true) / (1.0 - y_pred)
        dL_dz2 = dL_dy_pred * y_pred * (1.0 - y_pred)   # = y_pred − y_true
        dL_dW2 = dL_dz2 * a1
        dL_da1 = dL_dz2 * self.W2
        dL_dz1 = dL_da1 * a1 * (1.0 - a1)
        dL_dW1 = np.outer(dL_dz1, x)
        return {"dL_dy_pred": float(dL_dy_pred), "dL_dz2": float(dL_dz2),
                "dL_dW2": dL_dW2, "dL_db2": float(dL_dz2), "dL_da1": dL_da1,
                "dL_dz1": dL_dz1, "dL_dW1": dL_dW1, "dL_db1": dL_dz1.copy()}

    def loss_with(self, x, y_true, **overrides):
        """일부 파라미터를 바꿨을 때의 손실. 수치 미분 검증에 사용한다."""
        params = {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2}
        params.update(overrides)
        return TwoLayerNet(**params).forward(x, y_true)["loss"]

    def sgd_step(self, grads, lr):
        """θ ← θ − lr · ∂L/∂θ 로 파라미터를 한 번 갱신한다."""
        self.W1 -= lr * grads["dL_dW1"]
        self.b1 -= lr * grads["dL_db1"]
        self.W2 -= lr * grads["dL_dW2"]
        self.b2 -= lr * grads["dL_db2"]


# 미션에서 고정한 손계산 예제. y_true는 미션 결과 예시와 같이 1을 사용한다.
EXAMPLE = {
    "x": [1.0, 0.0],
    "W1": [[0.1, 0.2], [0.3, 0.4]],
    "b1": [0.0, 0.0],
    "W2": [0.5, 0.6],
    "b2": 0.0,
    "y_true": 1.0,
}


def example_network():
    """고정 예제의 신경망, 입력, 정답을 반환한다."""
    net = TwoLayerNet(EXAMPLE["W1"], EXAMPLE["b1"], EXAMPLE["W2"], EXAMPLE["b2"])
    return net, np.array(EXAMPLE["x"]), EXAMPLE["y_true"]
