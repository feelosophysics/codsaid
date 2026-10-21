"""내적 축, 공유 중간 노드, 호출 간 누적과 학습 경계의 회귀 검사."""
import unittest

import numpy as np

from minigrad import Tensor, nn, no_grad, optim
from minigrad.core.autograd import topological_order
from minigrad.gradcheck import check_gradients


class LearningBoundaries(unittest.TestCase):
    def test_logits_loss_rejects_accidental_target_broadcast(self):
        logits = Tensor([[1.], [2.]], requires_grad=True)
        with self.assertRaises(ValueError):
            nn.binary_cross_entropy_with_logits(logits, [0., 1.])

    def test_matmul_vector_matrix_and_batch_axes(self):
        rng = np.random.default_rng(42)
        for a_shape, b_shape in [((3,), (3,)), ((3,), (3, 2)),
                                 ((2, 3), (3,)), ((2, 1, 1, 3), (4, 3, 2)),
                                 ((3,), (4, 3, 2)), ((4, 2, 3), (3,))]:
            with self.subTest(a=a_shape, b=b_shape):
                a = Tensor(rng.normal(size=a_shape), requires_grad=True)
                b = Tensor(rng.normal(size=b_shape), requires_grad=True)
                weights = rng.normal(size=np.shape(a.data @ b.data))
                for result in check_gradients(lambda: ((a @ b) * weights).sum(), [a, b]):
                    self.assertTrue(result.passed, result.line())
                self.assertEqual(a.grad.shape, a.shape)
                self.assertEqual(b.grad.shape, b.shape)

    def test_shared_intermediate_and_repeated_backward(self):
        x = Tensor(2.0, requires_grad=True)
        square = x * x
        loss = square * square + square  # x**4 + x**2; derivative = 36
        order = topological_order(loss)
        self.assertEqual(len(order), len({id(node) for node in order}))
        positions = {id(node): i for i, node in enumerate(order)}
        for node in order:
            for parent in node._prev:
                self.assertLess(positions[id(parent)], positions[id(node)])
        loss.backward()
        self.assertEqual(x.grad.item(), 36)
        loss.backward()
        self.assertEqual(x.grad.item(), 72)
        x.zero_grad()
        loss.backward()
        self.assertEqual(x.grad.item(), 36)

    def test_explicit_seed_requires_exact_shape(self):
        x = Tensor([1., 2.], requires_grad=True)
        for seed in (1., [[1., 1.]]):
            with self.assertRaises(ValueError):
                (x * 2).backward(seed)
        (x * 2).backward([1., 3.])
        np.testing.assert_allclose(x.grad, [2, 6])

    def test_batch_mean_broadcast_bias_and_update(self):
        x = Tensor([[1., 2.], [3., 4.]])
        layer = nn.Linear(2, 1, init='zero')
        layer.W.data[:] = [[1.], [-1.]]
        residual = layer(x) - Tensor([[0.], [1.]])
        loss = (residual ** 2).mean()
        loss.backward()
        np.testing.assert_allclose(layer.W.grad, [[-7.], [-10.]])
        np.testing.assert_allclose(layer.b.grad, [-3.])
        opt = optim.SGD(layer.parameters(), lr=.01)
        opt.step()
        self.assertLess(nn.mse_loss(layer(x), [[0.], [1.]]).item(), loss.item())
        opt.zero_grad()
        self.assertTrue(all(p.grad is None for p in opt.params))

    def test_eval_and_no_grad_are_independent(self):
        dropout = nn.Dropout(.5, rng=np.random.default_rng(0))
        x = Tensor(np.ones(30), requires_grad=True)
        dropout.eval()
        self.assertIs(dropout(x), x)
        (dropout(x) * 2).sum().backward()
        np.testing.assert_allclose(x.grad, 2)
        dropout.train()
        with no_grad():
            out = dropout(x)
        self.assertFalse(out.requires_grad)
        self.assertTrue(np.any(out.data == 0))


if __name__ == '__main__':
    unittest.main()
