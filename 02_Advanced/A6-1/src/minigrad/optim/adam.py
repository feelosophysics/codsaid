import numpy as np

from .optimizer import Optimizer


class Adam(Optimizer):
    """m ← β₁m + (1−β₁)g,  v ← β₂v + (1−β₂)g²,  w ← w − lr·m̂/(√v̂ + ε).

    m̂ = m/(1−β₁ᵗ), v̂ = v/(1−β₂ᵗ)는 0에서 시작한 이동 평균의 편향 보정이다.
    weight_decay는 기울기에 λw를 더하는 L2 방식이다 (AdamW의 분리형 감쇠와 다르다).
    """

    def __init__(self, params, lr=0.001, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0):
        super().__init__(params, lr, weight_decay)
        self.beta1, self.beta2 = betas
        self.eps = eps
        self.m = [np.zeros_like(p.data) for p in self.params]
        self.v = [np.zeros_like(p.data) for p in self.params]

    def _update(self, index, param, grad):
        t = self.step_count
        self.m[index] = self.beta1 * self.m[index] + (1 - self.beta1) * grad
        self.v[index] = self.beta2 * self.v[index] + (1 - self.beta2) * grad ** 2
        m_hat = self.m[index] / (1 - self.beta1 ** t)
        v_hat = self.v[index] / (1 - self.beta2 ** t)
        param.data -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)
