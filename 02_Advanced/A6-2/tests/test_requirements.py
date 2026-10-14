"""미션 요구 사항과 누수 방지 체크포인트를 코드로 검사한다.

실행: uv run python -m unittest discover -s tests -v
결과 파일(results/)이나 꽃 데이터(data/flowers_subset/)가 없으면 해당 테스트만 건너뛴다.
"""
import csv
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import torch

from perfdiag.common import FLOWERS, RESULTS, ROOT
from perfdiag.diagnosis import diagnose_classification, diagnose_forecast
from perfdiag.metrics import diebold_mariano, improvement, mae, mape, rmse
from perfdiag.timeseries import baselines as bl
from perfdiag.timeseries.data import (MAX_WINDOW, SERIES, build_features, load_frame, make_dataset, prepare,
                                      window_indices)
from perfdiag.timeseries.models import build_model

TAGS_CSV = ROOT / "annotations" / "error_tags.csv"
TAG_CATEGORIES = {"데이터 품질", "배경/잡음", "클래스 유사성", "라벨 오류", "모델 한계"}


class TimeSeriesLeakage(unittest.TestCase):
    """reports/LEAKAGE.md의 체크포인트 1~4."""

    @classmethod
    def setUpClass(cls):
        cls.preps = {name: prepare(name) for name in SERIES}

    def test_1_chronological_split_7_1_2(self):
        for prep in self.preps.values():
            s = prep.splits
            self.assertLess(s["train"].max(), s["validation"].min())
            self.assertLess(s["validation"].max(), s["test"].min())
            for part in s.values():                      # 구간 안에 빈 시점이 없다
                self.assertTrue(np.all(np.diff(part) == 1))
            n = sum(len(p) for p in s.values())
            self.assertAlmostEqual(len(s["train"]) / n, 0.7, delta=0.005)
            self.assertAlmostEqual(len(s["validation"]) / n, 0.1, delta=0.005)
            self.assertAlmostEqual(len(s["test"]) / n, 0.2, delta=0.005)
            days = (prep.dates[s["test"][-1]] - prep.dates[prep.first_target]).days
            self.assertGreaterEqual(days, 3 * 365)       # 최소 3년

    def test_2_scaler_fit_on_train_rows_only(self):
        prep = self.preps["aapl"]
        ds = make_dataset(prep, "delta", 30)
        rows = prep.train_rows()
        self.assertEqual(rows.max(), prep.splits["train"][-1])
        np.testing.assert_allclose(ds.input_scaler.mean_, prep.features[rows].mean(0))
        # Validation·Test 구간 값을 바꿔도 Scaler 통계는 그대로다
        prep.features[prep.splits["validation"][0]:] *= 10
        try:
            again = make_dataset(prep, "delta", 30)
            np.testing.assert_allclose(again.input_scaler.mean_, ds.input_scaler.mean_)
            np.testing.assert_allclose(again.input_scaler.scale_, ds.input_scaler.scale_)
        finally:
            prep.features[prep.splits["validation"][0]:] /= 10

    def test_3_window_has_no_future(self):
        for window in (7, 30, MAX_WINDOW):
            targets = np.arange(200, 260)
            idx = window_indices(targets, window)
            self.assertTrue(np.all(idx.max(axis=1) == targets - 1))
            self.assertTrue(np.all(idx.min(axis=1) == targets - window))
        # 실제 데이터셋: 입력 마지막 행이 t-1의 피처와 같다
        prep = self.preps["seoul"]
        ds = make_dataset(prep, "delta", 30)
        ws = ds.sets["test"]
        np.testing.assert_allclose(ws.X[0, -1], ds.input_scaler.transform(prep.features[ws.t[0] - 1]), rtol=1e-5)

    def test_4_features_use_only_past(self):
        """d일 이후 값을 바꿔도 d일 이전 피처는 그대로다 → 분할 전에 만들어도 미래가 섞이지 않는다."""
        for name, cfg in SERIES.items():
            df = load_frame(cfg)
            before = build_features(df, cfg)
            cut = len(df) // 2
            changed = df.astype(float)
            changed.iloc[cut:] = changed.iloc[cut:] * 1.7 + 3
            after = build_features(changed, cfg)
            np.testing.assert_allclose(before.iloc[:cut].to_numpy(), after.iloc[:cut].to_numpy(), equal_nan=True)


class Baselines(unittest.TestCase):
    def test_formulas_on_toy_series(self):
        y = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
        t = np.array([3, 4, 5])
        np.testing.assert_allclose(bl.naive(y, t), [4, 8, 16])
        np.testing.assert_allclose(bl.sma(y, t, 2), [3, 6, 12])
        s = [1.0]
        for k in range(1, 6):
            s.append(0.5 * y[k - 1] + 0.5 * s[-1])
        np.testing.assert_allclose(bl.ema(y, t, 0.5), np.array(s)[t])
        line = np.arange(10) * 2.0 + 1
        pred, params = bl.linear_trend(line, np.arange(5), np.arange(5, 10))
        np.testing.assert_allclose(pred, line[5:])
        self.assertAlmostEqual(params["a"], 2.0)

    def test_baselines_read_only_the_past(self):
        prep = prepare("aapl")
        t = prep.splits["test"][:50]
        y2 = prep.y.copy()
        y2[t[0]:] *= 3        # 예측 대상 시점부터 뒤를 바꾼다
        for fn in (lambda y: bl.naive(y, t[:1]), lambda y: bl.sma(y, t[:1], 20), lambda y: bl.ema(y, t[:1], 0.3),
                   lambda y: bl.linear_lag(y, prep.splits["train"], t[:1])[0]):
            np.testing.assert_allclose(fn(prep.y), fn(y2))

    def test_mission_parameter_guide(self):
        self.assertEqual(bl.SMA_WINDOWS, (5, 10, 20))
        self.assertEqual(bl.EMA_ALPHAS, (0.1, 0.3, 0.5))


@unittest.skipUnless((RESULTS / "ts_deep_aapl.json").exists(), "scripts/ts_deep.py 결과가 없다")
class TimeSeriesResults(unittest.TestCase):
    def test_baselines_measured_before_deep_learning(self):
        for name in SERIES:
            base = json.loads((RESULTS / f"ts_baselines_{name}.json").read_text(encoding="utf-8"))
            deep = json.loads((RESULTS / f"ts_deep_{name}.json").read_text(encoding="utf-8"))
            self.assertLess(base["measured_at"], deep["deep_started_at"])
            self.assertEqual(base["test_fingerprint"], deep["test_fingerprint"])   # 같은 Test 구간

    def test_at_least_two_baselines_and_all_metrics(self):
        for name in SERIES:
            deep = json.loads((RESULTS / f"ts_deep_{name}.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(deep["improvement_vs_baselines"]), 2)
            for key in ("MAE", "RMSE"):
                self.assertIn(key, deep["final_test"])
        aapl = json.loads((RESULTS / "ts_deep_aapl.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(aapl["final_test"]["MAPE"])
        self.assertIn("lstm_delta", aapl["experiments"])
        self.assertIn("gru_delta", aapl["experiments"])


class Metrics(unittest.TestCase):
    def test_values(self):
        y, p = np.array([100.0, 200.0]), np.array([110.0, 180.0])
        self.assertAlmostEqual(mae(y, p), 15.0)
        self.assertAlmostEqual(rmse(y, p), np.sqrt((100 + 400) / 2))
        self.assertAlmostEqual(mape(y, p), 10.0)
        self.assertAlmostEqual(improvement(2.0, 1.5), 25.0)
        self.assertLess(improvement(2.0, 2.5), 0)

    def test_diebold_mariano(self):
        rng = np.random.default_rng(0)
        e = rng.normal(size=500)
        self.assertEqual(diebold_mariano(e, e), (0.0, 1.0))
        stat, p = diebold_mariano(e * 0.5, e)
        self.assertLess(stat, 0)
        self.assertLess(p, 0.01)


class Diagnosis(unittest.TestCase):
    def test_mission_table(self):
        self.assertEqual(diagnose_classification(0.30, 0.32).state, "high_bias")
        self.assertEqual(diagnose_classification(0.01, 0.25).state, "high_variance")
        self.assertEqual(diagnose_classification(0.02, 0.04).state, "good_fit")
        self.assertEqual(diagnose_classification(0.20, 0.40).state, "high_bias_and_variance")
        self.assertEqual(diagnose_forecast(1.0, 1.0, 1.0, 1.0).state, "high_bias")      # Naive와 같다
        self.assertEqual(diagnose_forecast(0.5, 0.9, 1.0, 1.0).state, "high_variance")
        self.assertEqual(diagnose_forecast(0.8, 0.82, 1.0, 1.0).state, "good_fit")


class Models(unittest.TestCase):
    def test_forecasters(self):
        x = torch.randn(4, 30, 5)
        for arch in ("lstm", "gru", "lstm_attention", "transformer"):
            model = build_model(5, arch)
            self.assertEqual(model(x).shape, (4,))
        model = build_model(5, "lstm_attention")
        model(x)
        torch.testing.assert_close(model.last_attention.sum(1), torch.ones(4))

    def test_freezing_strategies(self):
        from perfdiag.vision.models import TransferNet, count_parameters
        trainable = {s: count_parameters(TransferNet(8, s))[0] for s in ("linear_probe", "partial", "full")}
        self.assertEqual(trainable["linear_probe"], 512 * 8 + 8)
        self.assertLess(trainable["linear_probe"], trainable["partial"])
        self.assertLess(trainable["partial"], trainable["full"])
        net = TransferNet(8, "partial").train()
        self.assertFalse(net.net.layer1.training)          # 얼린 블록의 BatchNorm은 eval
        self.assertTrue(net.net.layer4.training)


@unittest.skipUnless((FLOWERS / "manifest.csv").exists(), "data/flowers_subset이 없다 (scripts/prepare_flowers.py)")
class FewShotData(unittest.TestCase):
    def test_fewer_than_50_per_class_and_disjoint(self):
        with open(FLOWERS / "manifest.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        per_class = {}
        for r in rows:
            per_class.setdefault((r["class"], r["split"]), []).append(r["file"])
        for (cls, split), files in per_class.items():
            if split == "train":
                self.assertLess(len(files), 50, cls)
        files = [r["file"] for r in rows]
        self.assertEqual(len(files), len(set(files)))


@unittest.skipUnless(TAGS_CSV.exists(), "annotations/error_tags.csv가 없다")
class ErrorAnalysis(unittest.TestCase):
    def test_at_least_30_tagged_errors(self):
        with open(TAGS_CSV, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 30)
        for r in rows:
            self.assertIn(r["primary_tag"], TAG_CATEGORIES)
            self.assertNotEqual(r["true"], r["pred"])


class _Text(HTMLParser):
    """<script>·<style>·<pre>·<code> 밖의 보이는 글자만 모은다."""

    def __init__(self):
        super().__init__()
        self.skip, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "pre", "code"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "pre", "code"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


class Terminology(unittest.TestCase):
    """제약: 문서 전반에서 Train/Validation/Test로 통일 (Dev, Val 혼용 금지)."""

    FORBIDDEN = re.compile(r"\b(Val|val|VAL|Dev|dev|DEV)\b|\bval[_ ]loss\b|\bdev[_ ]set\b")

    def prose(self, path):
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            parser = _Text()
            parser.feed(text)
            return "".join(parser.parts)
        text = re.sub(r"```.*?```", "", text, flags=re.S)        # 코드 블록 제외
        return re.sub(r"`[^`]*`", "", text)                      # 인라인 코드 제외

    def test_documents(self):
        docs = [ROOT / "README.md", *sorted((ROOT / "reports").glob("*.md")), *sorted((ROOT / "study").glob("*.html"))]
        docs = [d for d in docs if d.exists() and "template" not in d.name]
        self.assertTrue(docs)
        for doc in docs:
            hits = self.FORBIDDEN.findall(self.prose(doc))
            self.assertFalse(hits, f"{doc.name}: {hits[:5]}")


if __name__ == "__main__":
    unittest.main()
