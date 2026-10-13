import numpy as np

from .optimizer import Optimizer


class SGD(Optimizer):
    """w ← w − lr·g.  momentum>0이면 v ← μv + g,  w ← w − lr·v."""

    def __init__(self, params, lr=0.01, momentum=0.0, weight_decay=0.0):
        super().__init__(params, lr, weight_decay)
        self.momentum = momentum
        self.velocity = [np.zeros_like(p.data) for p in self.params]

    def _update(self, index, param, grad):
        if self.momentum:
            self.velocity[index] = self.momentum * self.velocity[index] + grad
            grad = self.velocity[index]
        param.data -= self.lr * grad
