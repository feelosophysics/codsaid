"""미션 자가 체크리스트와 성공 판정 기준을 그대로 검사한다.

MNIST 테스트는 data/mnist/에 파일이 있을 때만 돈다 (없으면 scripts/download_mnist.py).
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gradient_check import build_cases  # noqa: E402
from minigrad import Tensor, nn, no_grad, optim  # noqa: E402
from minigrad.data import DataLoader, load_mnist  # noqa: E402
from minigrad.data.mnist import FILES  # noqa: E402
from minigrad.gradcheck import EPSILON, THRESHOLD, check_gradients  # noqa: E402
from train_xor import train_xor  # noqa: E402

MNIST_DIR = ROOT / "data" / "mnist"
HAS_MNIST = all((MNIST_DIR / name).exists() for name, _ in FILES.values())


class Checklist(unittest.TestCase):
    def test_gradient_check_all_layers_below_1e7(self):
        self.assertEqual(EPSILON, 1e-5)
        self.assertEqual(THRESHOLD, 1e-7)
        checked = set()
        for case, loss_fn, tensors, names in build_cases():
            for r in check_gradients(loss_fn, tensors, names):
                self.assertLess(r.difference, 1e-7, f"{case}: {r.name}")
            checked.add(case)
        for layer in ("Linear", "ReLU", "Sigmoid", "Softmax", "Tanh", "LeakyReLU", "ELU", "Dropout"):
            self.assertIn(layer, checked)

    def test_zero_init_fails_to_learn(self):
        """Zero Init: 50 epoch 후에도 loss가 ln 2에서 전혀 줄지 않는다 (대칭성 문제)."""
        losses, accs, model = train_xor("zero", seed=0, epochs=50)
        self.assertAlmostEqual(losses[0], np.log(2), places=6)
        self.assertEqual(np.abs(losses - losses[0]).max(), 0.0)
        W1 = model[0].W.data
        self.assertTrue(np.all(W1 == W1[:, :1]))        # 모든 은닉 뉴런이 같은 가중치

    def test_he_init_solves_xor_within_100_epochs(self):
        losses, accs, _ = train_xor("he", seed=0, epochs=100)
        self.assertLess(losses.min(), 0.1)
        self.assertGreaterEqual(accs[-1], 0.95)

    def test_he_init_is_robust_across_seeds(self):
        reached = [train_xor("he", seed=s, epochs=100)[0].min() < 0.1 for s in range(10)]
        self.assertTrue(all(reached))

    def test_xavier_is_available(self):
        losses, _, _ = train_xor("xavier", seed=0, epochs=100)
        self.assertLess(losses.min(), 0.1)

    @unittest.skipUnless(HAS_MNIST, "data/mnist에 MNIST 파일이 없다")
    def test_mnist_one_epoch_above_80_percent(self):
        X_train, y_train, X_test, y_test = load_mnist(MNIST_DIR, download_if_missing=False)
        self.assertEqual(X_train.shape, (60000, 784))
        self.assertEqual(X_test.shape, (10000, 784))
        rng = np.random.default_rng(0)
        model = nn.mlp([784, 128, 10], init="he", rng=rng)
        opt = optim.SGD(model.parameters(), lr=0.1)
        for xb, yb in DataLoader(X_train, y_train, 64, rng=rng):
            loss = nn.cross_entropy(model(Tensor(xb)), yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
        with no_grad():
            acc = (model(Tensor(X_test)).data.argmax(axis=1) == y_test).mean()
        self.assertGreaterEqual(acc, 0.8)

    def test_numpy_only(self):
        """구현 패키지는 NumPy와 표준 라이브러리만 import한다."""
        allowed = {"numpy", "contextlib", "dataclasses", "gzip", "hashlib", "os", "struct", "urllib", "pathlib"}
        for path in (ROOT / "src" / "minigrad").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                words = line.split()
                if words[:1] == ["import"] or (words[:1] == ["from"] and not words[1].startswith(".")):
                    self.assertIn(words[1].split(".")[0], allowed, f"{path.name}: {line}")


if __name__ == "__main__":
    unittest.main()
