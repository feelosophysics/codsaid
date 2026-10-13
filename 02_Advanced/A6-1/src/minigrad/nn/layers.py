"""레이어 모듈. 각 레이어는 Tensor 연산을 조합할 뿐이고, 역전파는 Tensor가 기록한 그래프가 맡는다."""
import numpy as np

from ..core.tensor import Tensor
from . import init as initializers


class Parameter(Tensor):
    """학습 대상 텐서. 항상 requires_grad=True다."""

    def __init__(self, data, name=None):
        super().__init__(data, requires_grad=True)
        self.name = name


class Module:
    training = True

    def __call__(self, *args):
        return self.forward(*args)

    def forward(self, *args):
        raise NotImplementedError

    def children(self):
        for value in vars(self).values():
            if isinstance(value, Module):
                yield value
            elif isinstance(value, (list, tuple)):
                yield from (v for v in value if isinstance(v, Module))

    def parameters(self):
        for value in vars(self).values():
            if isinstance(value, Parameter):
                yield value
        for child in self.children():
            yield from child.parameters()

    def zero_grad(self):
        for p in self.parameters():
            p.grad = None

    def train(self, mode=True):
        self.training = mode
        for child in self.children():
            child.train(mode)
        return self

    def eval(self):
        return self.train(False)

    def __repr__(self):
        return f"{type(self).__name__}()"


class Linear(Module):
    """y = x @ W + b,  W: (in_features, out_features), b: (out_features,)"""

    def __init__(self, in_features, out_features, init="he", bias=True, rng=None, name=None):
        self.in_features, self.out_features, self.init = in_features, out_features, init
        self.name = name or "Linear"
        self.W = Parameter(initializers.initialize((in_features, out_features), init, rng), f"{self.name}.W")
        self.b = Parameter(np.zeros(out_features), f"{self.name}.b") if bias else None

    def forward(self, x):
        out = x @ self.W
        return out + self.b if self.b is not None else out

    def __repr__(self):
        return f"Linear({self.in_features}, {self.out_features}, init='{self.init}')"


class ReLU(Module):
    def forward(self, x):
        return x.relu()


class LeakyReLU(Module):
    def __init__(self, alpha=0.01):
        self.alpha = alpha

    def forward(self, x):
        return x.leaky_relu(self.alpha)

    def __repr__(self):
        return f"LeakyReLU(alpha={self.alpha})"


class ELU(Module):
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def forward(self, x):
        return x.elu(self.alpha)

    def __repr__(self):
        return f"ELU(alpha={self.alpha})"


class Sigmoid(Module):
    def forward(self, x):
        return x.sigmoid()


class Tanh(Module):
    def forward(self, x):
        return x.tanh()


class Softmax(Module):
    def __init__(self, axis=-1):
        self.axis = axis

    def forward(self, x):
        return x.softmax(self.axis)


class Dropout(Module):
    """Inverted Dropout.

    학습 때는 각 원소를 확률 p로 0으로 만들고 남은 값을 1/(1−p)배 키운다. 그래서
    기댓값이 그대로이고, 평가 때는 아무것도 하지 않아도 된다.
    """

    def __init__(self, p=0.5, rng=None):
        if not 0.0 <= p < 1.0:
            raise ValueError("p는 0 이상 1 미만이어야 한다")
        self.p = p
        self.rng = np.random.default_rng() if rng is None else rng

    def forward(self, x):
        if not self.training or self.p == 0.0:
            return x
        keep = (self.rng.random(x.shape) >= self.p) / (1.0 - self.p)
        return x * keep

    def __repr__(self):
        return f"Dropout(p={self.p})"


class Sequential(Module):
    def __init__(self, *layers):
        self.layers = list(layers)

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

    def __getitem__(self, index):
        return self.layers[index]

    def __len__(self):
        return len(self.layers)

    def __iter__(self):
        return iter(self.layers)

    def __repr__(self):
        inner = "\n".join(f"  ({i}) {layer!r}" for i, layer in enumerate(self.layers))
        return f"Sequential(\n{inner}\n)"


def mlp(sizes, activation=ReLU, init="he", output=None, rng=None):
    """sizes=[2, 8, 1]이면 Linear(2,8) → activation → Linear(8,1) [→ output]."""
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:]), start=1):
        layers.append(Linear(n_in, n_out, init=init, rng=rng, name=f"Linear_{i}"))
        if i < len(sizes) - 1:
            layers.append(activation())
    if output is not None:
        layers.append(output())
    return Sequential(*layers)
