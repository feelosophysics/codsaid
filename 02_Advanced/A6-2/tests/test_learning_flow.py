"""배열 정렬·복원·동결 상태 등 학습 설명의 핵심 불변식을 확인한다."""
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torchvision import models

from perfdiag.timeseries.data import MinMaxScaler, make_dataset, prepare, window_indices
from perfdiag.vision.models import TransferNet


class Reconstruction(unittest.TestCase):
    def test_delta_zero_is_naive_in_both_units(self):
        for name in ("aapl", "seoul"):
            prep = prepare(name)
            ds = make_dataset(prep, "delta", 30)
            for split, ws in ds.sets.items():
                zero = ds.target_scaler.transform(np.zeros((len(ws.t), 1))).ravel()
                np.testing.assert_allclose(ds.reconstruct(split, zero), prep.y[ws.t - 1])

    def test_true_targets_restore_in_level_and_delta(self):
        for name in ("aapl", "seoul"):
            for mode in ("level", "delta"):
                ds = make_dataset(prepare(name), mode, 30)
                for split, ws in ds.sets.items():
                    np.testing.assert_allclose(ds.reconstruct(split, ws.target), ds.actual(split), rtol=2e-6, atol=2e-6)

    def test_wrong_length_and_axes_do_not_broadcast(self):
        ds = make_dataset(prepare("seoul"))
        n = len(ds.sets["test"].t)
        for bad in (0., [0.], np.zeros((1, n)), np.zeros((n, 2))):
            with self.assertRaises(ValueError):
                ds.reconstruct("test", bad)
        np.testing.assert_allclose(ds.reconstruct("test", np.zeros(n)),
                                   ds.reconstruct("test", np.zeros((n, 1))))

    def test_constant_minmax_is_finite_and_reversible(self):
        values = np.array([[5., 1.], [5., 3.]])
        scaler = MinMaxScaler().fit(values)
        transformed = scaler.transform(values)
        self.assertTrue(np.isfinite(transformed).all())
        np.testing.assert_allclose(transformed[:, 0], 0.)
        np.testing.assert_allclose(scaler.inverse_transform(transformed), values)

    def test_invalid_window(self):
        for window in (0, -1, 2.5):
            with self.assertRaises(ValueError):
                window_indices([5], window)

    def test_first_validation_uses_past_train_context(self):
        prep = prepare("seoul")
        ds = make_dataset(prep, window=30)
        ws = ds.sets["validation"]
        t = ws.t[0]
        self.assertEqual(t - 1, prep.splits["train"][-1])
        indices = window_indices([t], 30)[0]
        np.testing.assert_allclose(ws.X[0], ds.input_scaler.transform(prep.features[indices]), atol=1e-6)


class FrozenState(unittest.TestCase):
    def test_freeze_and_eval_are_separate_and_parts_match(self):
        # 상태 불변식은 다운로드나 학습된 값과 독립이다. 구조만 동일한 무작위 몸통을 쓴다.
        original = models.resnet18
        with patch("perfdiag.vision.models.models.resnet18", side_effect=lambda **_: original(weights=None)):
            net = TransferNet(8, "linear_probe", dropout=0.2)
        torch.set_num_threads(2)
        net.train()
        self.assertFalse(net.net.bn1.training)
        self.assertTrue(net.net.fc.training)
        before = net.net.bn1.running_mean.clone()
        x = torch.randn(2, 3, 32, 32)
        loss = net(x).sum()
        loss.backward()
        self.assertIsNone(net.net.conv1.weight.grad)
        self.assertIsNotNone(net.net.fc[1].weight.grad)
        torch.testing.assert_close(net.net.bn1.running_mean, before)
        net.eval()
        with torch.no_grad():
            torch.testing.assert_close(net(x), net.net.fc(net.features(x)))


if __name__ == "__main__":
    unittest.main()
