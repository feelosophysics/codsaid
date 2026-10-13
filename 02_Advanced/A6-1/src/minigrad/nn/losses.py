"""손실 함수. 모두 배치 평균을 반환한다."""
import numpy as np

from ..core.tensor import Tensor
from .layers import Module


def _as_tensor(value):
    return value if isinstance(value, Tensor) else Tensor(value)


def mse_loss(pred, target):
    return ((pred - _as_tensor(target)) ** 2).mean()


def binary_cross_entropy(prob, target, eps=1e-12):
    """prob는 Sigmoid를 거친 확률. log(0)을 막으려고 [eps, 1−eps]로 자른다."""
    target = _as_tensor(target)
    prob = prob.clip(eps, 1.0 - eps)
    return -(target * prob.log() + (1.0 - target) * (1.0 - prob).log()).mean()


def binary_cross_entropy_with_logits(logits, target):
    """Sigmoid와 BCE를 합친 안정형. logits z에 대해 L = mean(max(z,0) − z·y + log(1+e^−|z|)).

    분리형(Sigmoid → clip → log)은 |z|가 커서 σ(z)가 0이나 1로 반올림되면 clip 구간 밖이 되어
    기울기가 0이 된다. 합친 식의 기울기는 항상 (σ(z) − y)/N이라 틀린 쪽으로 포화돼도 학습이 계속된다.
    """
    y = np.asarray(target.data if isinstance(target, Tensor) else target, dtype=logits.dtype)
    z = logits.data
    loss = np.maximum(z, 0) - z * y + np.log1p(np.exp(-np.abs(z)))
    out = logits._result(loss.mean(), (logits,), "bce_with_logits")
    if out.requires_grad:
        def _backward():
            prob = np.exp(-np.logaddexp(0.0, -z))
            logits._accumulate(out.grad * (prob - y) / z.size)
        out._backward = _backward
    return out


def one_hot(labels, num_classes):
    labels = np.asarray(labels, dtype=np.int64)
    out = np.zeros((labels.size, num_classes))
    out[np.arange(labels.size), labels] = 1.0
    return out


def cross_entropy(logits, labels):
    """logits: (N, C), labels: 정수 (N,). log_softmax로 계산해 수치적으로 안정하다.

    logits에 대한 기울기는 (softmax − one_hot) / N 이 된다.
    """
    target = Tensor(one_hot(labels, logits.shape[-1]), dtype=logits.dtype)
    return -(target * logits.log_softmax(axis=-1)).sum(axis=-1).mean()


def nll_loss(probs, labels, eps=1e-12):
    """Softmax 레이어를 거친 확률 (N, C)에 대한 음의 로그 우도."""
    target = Tensor(one_hot(labels, probs.shape[-1]), dtype=probs.dtype)
    return -(target * probs.clip(eps, 1.0).log()).sum(axis=-1).mean()


class MSELoss(Module):
    def forward(self, pred, target):
        return mse_loss(pred, target)


class BCELoss(Module):
    def forward(self, prob, target):
        return binary_cross_entropy(prob, target)


class BCEWithLogitsLoss(Module):
    def forward(self, logits, target):
        return binary_cross_entropy_with_logits(logits, target)


class CrossEntropyLoss(Module):
    def forward(self, logits, labels):
        return cross_entropy(logits, labels)


class NLLLoss(Module):
    def forward(self, probs, labels):
        return nll_loss(probs, labels)
