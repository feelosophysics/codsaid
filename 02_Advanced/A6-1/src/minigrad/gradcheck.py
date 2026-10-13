"""Gradient Checking: 역전파로 구한 기울기(analytic)를 중심차분 수치 기울기(numerical)와 비교한다.

    numerical = [f(x+ε) − f(x−ε)] / (2ε),  ε = 1e-5
    relative difference = ‖analytic − numerical‖₂ / (‖analytic‖₂ + ‖numerical‖₂)

상대 오차는 기울기 크기에 상관없이 비교할 수 있다. 중심차분의 절단 오차는 O(ε²)이므로
float64에서 구현이 맞으면 보통 1e-9 아래, 틀리면 1e-3 이상으로 크게 벌어진다.
"""
from dataclasses import dataclass

import numpy as np

from .core.autograd import no_grad

EPSILON = 1e-5
THRESHOLD = 1e-7


def numerical_gradient(f, x, eps=EPSILON):
    """스칼라 함수 f()가 배열 x(제자리 변경)에 대해 갖는 기울기를 원소마다 중심차분으로 구한다."""
    grad = np.zeros_like(x)
    it = np.nditer(x, flags=["multi_index"])
    for _ in it:
        i = it.multi_index
        original = x[i]
        x[i] = original + eps
        f_plus = f()
        x[i] = original - eps
        f_minus = f()
        x[i] = original
        grad[i] = (f_plus - f_minus) / (2 * eps)
    return grad


def relative_difference(analytic, numerical):
    numerator = np.linalg.norm(analytic - numerical)
    denominator = np.linalg.norm(analytic) + np.linalg.norm(numerical)
    return 0.0 if denominator == 0 else numerator / denominator


@dataclass
class CheckResult:
    name: str
    analytic: float      # 대표값: |analytic|이 가장 큰 원소
    numerical: float
    difference: float    # 텐서 전체의 상대 오차
    threshold: float = THRESHOLD

    @property
    def passed(self):
        return bool(self.difference < self.threshold)

    def line(self):
        status = "Pass" if self.passed else "FAIL"
        return (f"[{status}] {self.name:<28} Gradient Check - Analytic: {self.analytic: .6f}, "
                f"Numerical: {self.numerical: .6f}, Diff: {self.difference:.1e}")


def check_gradients(loss_fn, tensors, names=None, eps=EPSILON, threshold=THRESHOLD):
    """loss_fn()은 tensors를 읽어 스칼라 Tensor를 새로 계산하는 함수다.

    한 번 역전파해 analytic 기울기를 얻은 뒤, 각 텐서의 원소를 ±ε 움직여 수치 기울기를 구한다.
    """
    tensors = list(tensors)
    names = names or [getattr(t, "name", None) or f"tensor_{i}" for i, t in enumerate(tensors)]
    for t in tensors:
        t.grad = None
    loss_fn().backward()
    analytic = [np.array(t.grad) for t in tensors]

    def scalar():
        with no_grad():
            return float(loss_fn().data)

    results = []
    for name, t, grad in zip(names, tensors, analytic):
        numerical = numerical_gradient(scalar, t.data, eps)
        k = np.unravel_index(np.argmax(np.abs(grad)), grad.shape)
        results.append(CheckResult(name, float(grad[k]), float(numerical[k]),
                                   float(relative_difference(grad, numerical)), threshold))
    return results
