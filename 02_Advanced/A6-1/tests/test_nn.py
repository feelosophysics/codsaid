import gzip
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from minigrad import Tensor, nn, optim
from minigrad.data import DataLoader, parse_idx


class Initialization(unittest.TestCase):
    def test_std_matches_formula(self):
        rng = np.random.default_rng(0)
        n_in, n_out = 400, 200
        expected = {"zero": 0.0, "random": 1.0, "he": np.sqrt(2 / n_in), "xavier": np.sqrt(2 / (n_in + n_out))}
        for method, std in expected.items():
            W = nn.Linear(n_in, n_out, init=method, rng=rng).W.data
            self.assertAlmostEqual(W.std(), std, delta=0.02 * max(std, 1e-9) + 1e-12, msg=method)
            self.assertAlmostEqual(W.mean(), 0.0, delta=0.01)

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            nn.Linear(2, 2, init="orthogonal")


class Layers(unittest.TestCase):
    def test_linear_shapes_and_parameters(self):
        layer = nn.Linear(4, 3, rng=np.random.default_rng(0))
        self.assertEqual(layer(Tensor(np.ones((5, 4)))).shape, (5, 3))
        self.assertEqual([p.shape for p in layer.parameters()], [(4, 3), (3,)])

    def test_sequential_collects_parameters_and_zero_grad(self):
        model = nn.mlp([3, 4, 2], rng=np.random.default_rng(0))
        params = list(model.parameters())
        self.assertEqual(len(params), 4)
        nn.cross_entropy(model(Tensor(np.ones((2, 3)))), np.array([0, 1])).backward()
        self.assertTrue(all(p.grad is not None for p in params))
        model.zero_grad()
        self.assertTrue(all(p.grad is None for p in params))

    def test_inverted_dropout(self):
        layer = nn.Dropout(0.5, rng=np.random.default_rng(0))
        x = Tensor(np.ones((200, 200)))
        out = layer(x).data
        self.assertAlmostEqual((out == 0).mean(), 0.5, delta=0.01)
        self.assertEqual(set(np.unique(out)), {0.0, 2.0})        # 남은 값은 1/(1−p)
        self.assertAlmostEqual(out.mean(), 1.0, delta=0.02)      # 기댓값 유지
        model = nn.Sequential(nn.ReLU(), layer)
        model.eval()                                             # eval()이 하위 모듈까지 전파된다
        np.testing.assert_array_equal(model(x).data, x.data)

    def test_activations_values(self):
        x = Tensor([-2.0, 0.0, 3.0])
        np.testing.assert_allclose(nn.ReLU()(x).data, [0, 0, 3])
        np.testing.assert_allclose(nn.LeakyReLU(0.1)(x).data, [-0.2, 0, 3])
        np.testing.assert_allclose(nn.ELU(1.0)(x).data, [np.exp(-2) - 1, 0, 3])
        np.testing.assert_allclose(nn.Tanh()(x).data, np.tanh(x.data))
        np.testing.assert_allclose(nn.Sigmoid()(x).data, 1 / (1 + np.exp(-x.data)))

    def test_bce_with_logits_matches_and_survives_saturation(self):
        z_values, y = np.array([[-2.0], [0.5], [3.0]]), np.array([[0.0], [1.0], [0.0]])
        a = nn.binary_cross_entropy_with_logits(Tensor(z_values), y).item()
        b = nn.binary_cross_entropy(Tensor(z_values).sigmoid(), y).item()
        self.assertAlmostEqual(a, b, places=10)
        # 정답이 1인데 로짓이 −50으로 포화: 분리형은 clip 때문에 기울기 0, 안정형은 (σ−y)/N = −1
        z = Tensor(np.array([[-50.0]]), requires_grad=True)
        nn.binary_cross_entropy(z.sigmoid(), [[1.0]]).backward()
        self.assertEqual(z.grad.item(), 0.0)
        z.grad = None
        nn.binary_cross_entropy_with_logits(z, [[1.0]]).backward()
        self.assertAlmostEqual(z.grad.item(), -1.0)

    def test_cross_entropy_gradient_is_softmax_minus_onehot(self):
        logits = Tensor(np.array([[1.0, 2.0, 0.5], [0.0, 0.0, 0.0]]), requires_grad=True)
        labels = np.array([1, 2])
        nn.cross_entropy(logits, labels).backward()
        expected = (logits.softmax().data - nn.one_hot(labels, 3)) / 2
        np.testing.assert_allclose(logits.grad, expected)


class Optimizers(unittest.TestCase):
    def test_sgd_step(self):
        w = nn.Parameter(np.array([1.0, -2.0]))
        w.grad = np.array([0.5, 0.5])
        optim.SGD([w], lr=0.1).step()
        np.testing.assert_allclose(w.data, [0.95, -2.05])

    def test_sgd_momentum_and_weight_decay(self):
        w = nn.Parameter(np.array([1.0]))
        opt = optim.SGD([w], lr=0.1, momentum=0.9, weight_decay=0.5)
        for _ in range(2):
            w.grad = np.array([0.0])                 # 기울기 0이어도 감쇠 λw가 작용한다
            opt.step()
        # v1 = 0.5 → w1 = 0.95,  v2 = 0.9·0.5 + 0.5·0.95 = 0.925 → w2 = 0.8575
        np.testing.assert_allclose(w.data, [0.8575])

    def test_adam_first_step_is_lr_times_sign(self):
        w = nn.Parameter(np.array([1.0, 1.0]))
        w.grad = np.array([3.0, -0.001])
        optim.Adam([w], lr=0.01).step()              # 편향 보정 후 m̂/√v̂ = sign(g)
        np.testing.assert_allclose(w.data, [0.99, 1.01], atol=1e-6)

    def test_adam_minimizes_quadratic(self):
        w = nn.Parameter(np.array([5.0, -3.0]))
        opt = optim.Adam([w], lr=0.1)
        for _ in range(500):
            opt.zero_grad()
            (w * w).sum().backward()
            opt.step()
        np.testing.assert_allclose(w.data, [0.0, 0.0], atol=1e-3)


class Data(unittest.TestCase):
    def test_parse_idx_roundtrip(self):
        images = np.arange(2 * 3 * 4, dtype=np.uint8).reshape(2, 3, 4)
        header = struct.pack(">HBB", 0, 0x08, 3) + struct.pack(">3I", *images.shape)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x-idx3-ubyte.gz"
            with gzip.open(path, "wb") as f:
                f.write(header + images.tobytes())
            np.testing.assert_array_equal(parse_idx(path), images)
            bad = Path(tmp) / "bad"
            bad.write_bytes(b"\x01\x02\x03\x04")
            with self.assertRaises(ValueError):
                parse_idx(bad)

    def test_dataloader_covers_every_sample_once(self):
        X, y = np.arange(10)[:, None], np.arange(10)
        loader = DataLoader(X, y, batch_size=4, rng=np.random.default_rng(0))
        batches = list(loader)
        self.assertEqual(len(loader), 3)
        self.assertEqual([len(b[1]) for b in batches], [4, 4, 2])
        self.assertEqual(sorted(np.concatenate([b[1] for b in batches])), list(range(10)))
        self.assertEqual(len(list(DataLoader(X, y, 4, drop_last=True))), 2)


if __name__ == "__main__":
    unittest.main()
