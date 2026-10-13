"""자동 미분 엔진: 계산 그래프를 위상 정렬한 뒤 출력에서 입력 쪽으로 기울기를 전파한다.

각 Tensor는 자신을 만든 연산의 국소 미분 규칙을 `_backward`에 담고 있다.
엔진은 그 규칙을 '출력에 가까운 노드부터' 한 번씩 호출할 뿐이며, 연쇄 법칙의
곱셈은 각 `_backward`가 상류 기울기(out.grad)에 국소 미분을 곱하는 방식으로 일어난다.
"""
import contextlib

import numpy as np

_grad_enabled = True


def is_grad_enabled():
    return _grad_enabled


@contextlib.contextmanager
def no_grad():
    """블록 안에서 만든 텐서는 그래프를 기록하지 않는다 (평가·수치 미분용)."""
    global _grad_enabled
    previous = _grad_enabled
    _grad_enabled = False
    try:
        yield
    finally:
        _grad_enabled = previous


def topological_order(root):
    """root에 이르는 노드를 '입력이 출력보다 먼저' 오는 순서로 반환한다.

    재귀 대신 명시적 스택을 써서 깊은 그래프에서도 RecursionError가 나지 않는다.
    (node, True)는 '부모를 모두 처리했으니 이제 node를 순서에 넣어라'는 표시다.
    """
    order, visited = [], set()
    stack = [(root, False)]
    while stack:
        node, parents_done = stack.pop()
        if parents_done:
            order.append(node)
            continue
        if id(node) in visited:
            continue
        visited.add(id(node))
        stack.append((node, True))
        for parent in node._prev:
            if id(parent) not in visited:
                stack.append((parent, False))
    return order


def backward(root, grad=None):
    """root에서 시작해 그래프 전체에 기울기를 전파한다.

    root가 스칼라면 시작 기울기 dL/dL = 1을 쓰고, 아니면 같은 shape의 grad를 받아야 한다.
    """
    if grad is None:
        if root.data.size != 1:
            raise RuntimeError("스칼라가 아닌 텐서에서 backward()를 부르려면 grad를 넘겨야 한다")
        grad = np.ones_like(root.data)
    grad = np.broadcast_to(np.asarray(grad, dtype=root.data.dtype), root.data.shape)
    root.grad = np.array(grad) if root.grad is None else root.grad + grad
    for node in reversed(topological_order(root)):
        if node.grad is not None:
            node._backward()
