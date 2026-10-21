"""Tensor: NumPy 배열(data)에 기울기(grad)와 생성 연산 정보(_backward, _prev, _op)를 붙인 값.

연산을 할 때마다 결과 Tensor가 입력 Tensor를 `_prev`로 기억하므로 계산 그래프가
순전파와 동시에 동적으로 만들어진다 (define-by-run). 각 연산은 결과의 `_backward`에
"상류 기울기 out.grad를 받아 입력의 grad에 국소 미분을 곱해 더한다"는 규칙을 남긴다.
"""
import numpy as np

from . import autograd


def _as_array(value, dtype=None):
    array = np.asarray(value, dtype=dtype)
    if dtype is None and not np.issubdtype(array.dtype, np.floating):
        array = array.astype(np.float64)
    return array


def unbroadcast(grad, shape):
    """브로드캐스팅으로 복제된 축의 기울기를 합쳐 원래 shape로 되돌린다.

    순전파에서 값 하나가 여러 위치로 복사되었다면, 역전파에서는 그 위치들의
    기울기를 모두 더해야 한다 (다변수 연쇄 법칙). 예: (3,) 편향이 (N, 3)에 더해지면
    편향의 기울기는 (N, 3) 기울기를 축 0으로 합한 값이다.
    """
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    for axis, size in enumerate(shape):
        if size == 1 and grad.shape[axis] != 1:
            grad = grad.sum(axis=axis, keepdims=True)
    return grad


def _normalize_axes(axis, ndim):
    if axis is None:
        return tuple(range(ndim))
    axes = axis if isinstance(axis, tuple) else (axis,)
    return tuple(a % ndim for a in axes)


class Tensor:
    # ndarray + Tensor처럼 왼쪽이 ndarray여도 Tensor의 __radd__ 등이 불리게 한다.
    __array_priority__ = 1000

    def __init__(self, data, requires_grad=False, dtype=None, _prev=(), _op=""):
        if isinstance(data, Tensor):
            data = data.data
        self.data = _as_array(data, dtype)
        self.grad = None
        self.requires_grad = requires_grad
        self._backward = lambda: None
        self._prev = tuple(_prev)
        self._op = _op

    # ------------------------------------------------------------------ 기본 정보
    @property
    def shape(self):
        return self.data.shape

    @property
    def ndim(self):
        return self.data.ndim

    @property
    def size(self):
        return self.data.size

    @property
    def dtype(self):
        return self.data.dtype

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        grad = ", requires_grad=True" if self.requires_grad else ""
        op = f", op='{self._op}'" if self._op else ""
        return f"Tensor({np.array2string(self.data, precision=4)}{grad}{op})"

    def item(self):
        return self.data.item()

    def numpy(self):
        return self.data

    def detach(self):
        return Tensor(self.data.copy())

    # ------------------------------------------------------------------ 그래프 도우미
    def _ensure(self, other):
        return other if isinstance(other, Tensor) else Tensor(other, dtype=self.data.dtype)

    def _result(self, data, parents, op):
        """연산 결과 Tensor를 만든다. 입력 중 하나라도 기울기가 필요할 때만 그래프에 연결한다."""
        track = autograd.is_grad_enabled() and any(p.requires_grad for p in parents)
        return Tensor(data, requires_grad=track, _prev=parents if track else (), _op=op)

    def _accumulate(self, grad):
        """상류에서 온 기울기를 더한다. 같은 텐서가 여러 번 쓰이면 기울기가 합쳐진다."""
        if not self.requires_grad:
            return
        grad = unbroadcast(grad, self.data.shape)
        if self.grad is None:
            self.grad = np.array(grad, dtype=self.data.dtype)
        else:
            self.grad = self.grad + grad

    def backward(self, grad=None):
        if not self.requires_grad:
            raise RuntimeError("requires_grad=False인 텐서는 backward()를 부를 수 없다")
        autograd.backward(self, grad)

    def zero_grad(self):
        self.grad = None

    # ------------------------------------------------------------------ 사칙연산
    def __add__(self, other):
        other = self._ensure(other)
        out = self._result(self.data + other.data, (self, other), "+")
        if out.requires_grad:
            def _backward():
                # d(a+b)/da = 1, d(a+b)/db = 1
                self._accumulate(out.grad)
                other._accumulate(out.grad)
            out._backward = _backward
        return out

    def __sub__(self, other):
        other = self._ensure(other)
        out = self._result(self.data - other.data, (self, other), "-")
        if out.requires_grad:
            def _backward():
                # d(a-b)/da = 1, d(a-b)/db = -1
                self._accumulate(out.grad)
                other._accumulate(-out.grad)
            out._backward = _backward
        return out

    def __mul__(self, other):
        other = self._ensure(other)
        out = self._result(self.data * other.data, (self, other), "*")
        if out.requires_grad:
            def _backward():
                # d(ab)/da = b, d(ab)/db = a
                self._accumulate(out.grad * other.data)
                other._accumulate(out.grad * self.data)
            out._backward = _backward
        return out

    def __truediv__(self, other):
        other = self._ensure(other)
        out = self._result(self.data / other.data, (self, other), "/")
        if out.requires_grad:
            def _backward():
                # d(a/b)/da = 1/b, d(a/b)/db = -a/b²
                self._accumulate(out.grad / other.data)
                other._accumulate(-out.grad * self.data / other.data ** 2)
            out._backward = _backward
        return out

    def __neg__(self):
        out = self._result(-self.data, (self,), "neg")
        if out.requires_grad:
            def _backward():
                self._accumulate(-out.grad)
            out._backward = _backward
        return out

    def __pow__(self, exponent):
        if isinstance(exponent, Tensor):
            raise TypeError("지수는 상수(int/float)만 지원한다")
        out = self._result(self.data ** exponent, (self,), f"**{exponent}")
        if out.requires_grad:
            def _backward():
                # d(xⁿ)/dx = n·xⁿ⁻¹
                self._accumulate(out.grad * exponent * self.data ** (exponent - 1))
            out._backward = _backward
        return out

    def __radd__(self, other):
        return self._ensure(other) + self

    def __rsub__(self, other):
        return self._ensure(other) - self

    def __rmul__(self, other):
        return self._ensure(other) * self

    def __rtruediv__(self, other):
        return self._ensure(other) / self

    # ------------------------------------------------------------------ 행렬 곱
    def __matmul__(self, other):
        other = self._ensure(other)
        a, b = self.data, other.data
        out = self._result(a @ b, (self, other), "@")
        if out.requires_grad:
            def _backward():
                # C = A @ B 이면 dA = dC @ Bᵀ, dB = Aᵀ @ dC.
                # 1차원 피연산자는 행/열 벡터로 올려 계산한 뒤 다시 내린다.
                grad = out.grad
                a2 = a[None, :] if a.ndim == 1 else a
                b2 = b[:, None] if b.ndim == 1 else b
                if a.ndim == 1 and b.ndim == 1:
                    # 내적 출력은 0차원이므로 두 축을 한꺼번에 복원한다.
                    grad = grad.reshape(1, 1)
                elif a.ndim == 1:
                    grad = np.expand_dims(grad, -2)
                elif b.ndim == 1:
                    grad = np.expand_dims(grad, -1)
                grad_a = grad @ np.swapaxes(b2, -1, -2)
                grad_b = np.swapaxes(a2, -1, -2) @ grad
                if a.ndim == 1:
                    grad_a = grad_a.squeeze(-2)
                if b.ndim == 1:
                    grad_b = grad_b.squeeze(-1)
                self._accumulate(grad_a)
                other._accumulate(grad_b)
            out._backward = _backward
        return out

    def __rmatmul__(self, other):
        return self._ensure(other) @ self

    # ------------------------------------------------------------------ 축소·모양 연산
    def sum(self, axis=None, keepdims=False):
        out = self._result(self.data.sum(axis=axis, keepdims=keepdims), (self,), "sum")
        if out.requires_grad:
            def _backward():
                # 합의 미분은 1이므로 기울기를 합쳐진 축 방향으로 그대로 복제한다.
                grad = out.grad
                if not keepdims:
                    grad = np.expand_dims(grad, _normalize_axes(axis, self.ndim))
                self._accumulate(np.broadcast_to(grad, self.shape))
            out._backward = _backward
        return out

    def mean(self, axis=None, keepdims=False):
        count = np.prod([self.shape[a] for a in _normalize_axes(axis, self.ndim)])
        return self.sum(axis=axis, keepdims=keepdims) / float(count)

    def reshape(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])
        out = self._result(self.data.reshape(shape), (self,), "reshape")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.reshape(self.shape))
            out._backward = _backward
        return out

    def transpose(self, *axes):
        axes = axes[0] if len(axes) == 1 and isinstance(axes[0], (tuple, list)) else axes
        axes = tuple(axes) if axes else tuple(reversed(range(self.ndim)))
        out = self._result(self.data.transpose(axes), (self,), "transpose")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.transpose(np.argsort(axes)))
            out._backward = _backward
        return out

    @property
    def T(self):
        return self.transpose()

    def __getitem__(self, index):
        index = index.data if isinstance(index, Tensor) else index
        out = self._result(self.data[index], (self,), "getitem")
        if out.requires_grad:
            def _backward():
                # 같은 위치를 여러 번 뽑았을 수 있으므로 np.add.at으로 누적한다.
                grad = np.zeros_like(self.data)
                np.add.at(grad, index, out.grad)
                self._accumulate(grad)
            out._backward = _backward
        return out

    # ------------------------------------------------------------------ 원소별 함수
    def exp(self):
        out = self._result(np.exp(self.data), (self,), "exp")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad * out.data)  # d(eˣ)/dx = eˣ
            out._backward = _backward
        return out

    def log(self):
        out = self._result(np.log(self.data), (self,), "log")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad / self.data)  # d(ln x)/dx = 1/x
            out._backward = _backward
        return out

    def clip(self, low, high):
        out = self._result(np.clip(self.data, low, high), (self,), "clip")
        if out.requires_grad:
            def _backward():
                inside = (self.data >= low) & (self.data <= high)
                self._accumulate(out.grad * inside)
            out._backward = _backward
        return out

    def relu(self):
        out = self._result(np.maximum(self.data, 0.0), (self,), "relu")
        if out.requires_grad:
            def _backward():
                # x=0에서는 미분이 없으므로 관례대로 0을 쓴다.
                self._accumulate(out.grad * (self.data > 0))
            out._backward = _backward
        return out

    def leaky_relu(self, alpha=0.01):
        out = self._result(np.where(self.data > 0, self.data, alpha * self.data), (self,), "leaky_relu")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad * np.where(self.data > 0, 1.0, alpha))
            out._backward = _backward
        return out

    def elu(self, alpha=1.0):
        negative = alpha * np.expm1(np.minimum(self.data, 0.0))
        out = self._result(np.where(self.data > 0, self.data, negative), (self,), "elu")
        if out.requires_grad:
            def _backward():
                # x≤0: d/dx α(eˣ−1) = αeˣ = out + α
                self._accumulate(out.grad * np.where(self.data > 0, 1.0, out.data + alpha))
            out._backward = _backward
        return out

    def sigmoid(self):
        # σ(x) = exp(−log(1+e⁻ˣ)): 큰 |x|에서도 overflow가 나지 않는 형태
        out = self._result(np.exp(-np.logaddexp(0.0, -self.data)), (self,), "sigmoid")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad * out.data * (1.0 - out.data))  # σ' = σ(1−σ)
            out._backward = _backward
        return out

    def tanh(self):
        out = self._result(np.tanh(self.data), (self,), "tanh")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad * (1.0 - out.data ** 2))  # tanh' = 1 − tanh²
            out._backward = _backward
        return out

    def softmax(self, axis=-1):
        shifted = self.data - self.data.max(axis=axis, keepdims=True)
        exps = np.exp(shifted)
        out = self._result(exps / exps.sum(axis=axis, keepdims=True), (self,), "softmax")
        if out.requires_grad:
            def _backward():
                # 야코비안 J = diag(s) − s sᵀ 를 직접 만들지 않고 Jᵀg = s ⊙ (g − ⟨g, s⟩)로 계산
                s, grad = out.data, out.grad
                self._accumulate(s * (grad - (grad * s).sum(axis=axis, keepdims=True)))
            out._backward = _backward
        return out

    def log_softmax(self, axis=-1):
        shifted = self.data - self.data.max(axis=axis, keepdims=True)
        log_z = np.log(np.exp(shifted).sum(axis=axis, keepdims=True))
        out = self._result(shifted - log_z, (self,), "log_softmax")
        if out.requires_grad:
            def _backward():
                # d(log softmax)ᵀ g = g − softmax · Σg
                grad = out.grad
                self._accumulate(grad - np.exp(out.data) * grad.sum(axis=axis, keepdims=True))
            out._backward = _backward
        return out


def tensor(data, requires_grad=False, dtype=None):
    return Tensor(data, requires_grad=requires_grad, dtype=dtype)
