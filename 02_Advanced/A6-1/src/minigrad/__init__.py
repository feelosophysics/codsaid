"""minigrad: NumPy만으로 만든 미니 딥러닝 프레임워크.

    core   Tensor와 자동 미분 엔진
    nn     레이어, 초기화, 손실 함수
    optim  SGD, Adam
    data   MNIST 파서, DataLoader, 합성 데이터
"""
from . import data, nn, optim
from .core import Tensor, no_grad, tensor
from .gradcheck import check_gradients

__all__ = ["Tensor", "tensor", "no_grad", "nn", "optim", "data", "check_gradients"]
__version__ = "0.1.0"
