import unittest

import numpy as np

from minigrad import Tensor, no_grad
from minigrad.core import unbroadcast
from minigrad.gradcheck import check_gradients


class TensorBasics(unittest.TestCase):
    def test_attributes(self):
        t = Tensor([1, 2, 3])
        self.assertEqual(t.data.dtype, np.float64)          # 정수 입력도 실수로 저장
        self.assertIsNone(t.grad)
        self.assertTrue(callable(t._backward))

    def test_chain_rule_scalar(self):
        # L = (x·y + y)² → dL/dx = 2(xy+y)·y, dL/dy = 2(xy+y)(x+1)
        x, y = Tensor(2.0, requires_grad=True), Tensor(3.0, requires_grad=True)
        loss = (x * y + y) ** 2
        loss.backward()
        self.assertAlmostEqual(loss.item(), 81.0)
        self.assertAlmostEqual(x.grad.item(), 54.0)
        self.assertAlmostEqual(y.grad.item(), 54.0)

    def test_four_operations(self):
        a, b = Tensor(6.0, requires_grad=True), Tensor(2.0, requires_grad=True)
        for expr, value, da, db in [
            (lambda: a + b, 8.0, 1.0, 1.0),
            (lambda: a - b, 4.0, 1.0, -1.0),
            (lambda: a * b, 12.0, 2.0, 6.0),
            (lambda: a / b, 3.0, 0.5, -1.5),
        ]:
            a.grad = b.grad = None
            out = expr()
            out.backward()
            self.assertAlmostEqual(out.item(), value)
            self.assertAlmostEqual(a.grad.item(), da)
            self.assertAlmostEqual(b.grad.item(), db)

    def test_matmul_gradient_shapes_and_values(self):
        A = Tensor(np.arange(6.0).reshape(2, 3), requires_grad=True)
        B = Tensor(np.ones((3, 4)), requires_grad=True)
        (A @ B).sum().backward()
        np.testing.assert_allclose(A.grad, np.full((2, 3), 4.0))         # dC/dA = 1 @ Bᵀ
        np.testing.assert_allclose(B.grad, np.repeat(A.data.sum(0)[:, None], 4, 1))  # Aᵀ @ 1

    def test_broadcast_gradient_is_summed(self):
        x = Tensor(np.ones((5, 3)), requires_grad=True)
        b = Tensor(np.zeros(3), requires_grad=True)
        (x + b).sum().backward()
        np.testing.assert_allclose(b.grad, [5.0, 5.0, 5.0])  # 5개 행에 복사되었으므로 5
        np.testing.assert_allclose(unbroadcast(np.ones((2, 4, 1)), (4, 1)), [[2.0]] * 4)

    def test_reused_node_accumulates(self):
        x = Tensor(3.0, requires_grad=True)
        (x * x + x).backward()          # d/dx (x² + x) = 2x + 1
        self.assertAlmostEqual(x.grad.item(), 7.0)

    def test_no_grad_and_constants(self):
        x = Tensor(2.0, requires_grad=True)
        with no_grad():
            y = x * 3
        self.assertFalse(y.requires_grad)
        self.assertEqual(y._prev, ())
        z = Tensor(5.0) * 2             # 상수끼리는 그래프를 만들지 않는다
        self.assertFalse(z.requires_grad)
        with self.assertRaises(RuntimeError):
            z.backward()

    def test_non_scalar_backward_needs_grad(self):
        x = Tensor(np.ones(3), requires_grad=True)
        with self.assertRaises(RuntimeError):
            (x * 2).backward()
        (x * 2).backward(np.array([1.0, 2.0, 3.0]))
        np.testing.assert_allclose(x.grad, [2.0, 4.0, 6.0])

    def test_deep_graph_has_no_recursion_limit(self):
        x = Tensor(1.0, requires_grad=True)
        y = x
        for _ in range(5000):
            y = y * 1.0 + 0.0
        y.backward()
        self.assertAlmostEqual(x.grad.item(), 1.0)

    def test_softmax_is_stable_and_sums_to_one(self):
        x = Tensor(np.array([[1000.0, 1001.0, 1002.0]]))
        s = x.softmax().data
        self.assertTrue(np.isfinite(s).all())
        self.assertAlmostEqual(s.sum(), 1.0)
        self.assertTrue(np.isfinite(Tensor([-1000.0, 1000.0]).sigmoid().data).all())


class GradientCheckDetectsBugs(unittest.TestCase):
    def test_wrong_backward_fails_the_check(self):
        """음성 대조: 일부러 틀린 미분(2x 대신 x)을 넣으면 검사가 실패해야 한다."""
        rng = np.random.default_rng(0)
        x = Tensor(rng.standard_normal((3, 3)), requires_grad=True)

        def buggy_square(t):
            out = t._result(t.data ** 2, (t,), "buggy")

            def _backward():
                t._accumulate(out.grad * t.data)  # 정답은 2 * t.data
            out._backward = _backward
            return out

        good = check_gradients(lambda: (x ** 2).sum(), [x])[0]
        bad = check_gradients(lambda: buggy_square(x).sum(), [x])[0]
        self.assertTrue(good.passed)
        self.assertFalse(bad.passed)
        self.assertAlmostEqual(bad.difference, 1 / 3, places=6)  # ‖x−2x‖/(‖x‖+‖2x‖)


if __name__ == "__main__":
    unittest.main()
