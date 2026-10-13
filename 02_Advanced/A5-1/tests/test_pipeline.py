import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.base import clone
from sklearn.linear_model import Lasso, LogisticRegression

from src import classification, regression
from src.baseline import RULES, RuleBasedClassifier, rule_based_predict, rule_hits
from src.config import CLASSIFICATION_TARGET, FEATURES, REGRESSION_TARGET
from src.data import load_data, split_data
from src.features import DerivedFeatures, build_preprocessor

ROOT = Path(__file__).resolve().parent.parent


def tiny_frame():
    return pd.DataFrame(
        {
            "age": [20, 29, 30, 69, 45],
            "annual_income": [1500.0, 3000.0, 5000.0, 8000.0, 4000.0],
            "spending_score": [1, 50, 99, 10, 20],
            "debt_ratio": [0.9, 0.5, 0.1, 0.0, 0.61],
            "credit_card_count": [1, 8, 3, 9, 2],
            "overdue_count_6m": [0, 2, 0, 1, 1],
        }
    )


class DataGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        subprocess.run(
            [sys.executable, str(ROOT / "data_gen.py")],
            cwd=cls.tmp.name, check=True, capture_output=True, env={**os.environ, "PYTHONUTF8": "1"},
        )
        cls.df = pd.read_csv(Path(cls.tmp.name) / "finance_data.csv")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_generated_shape_and_imbalance(self):
        self.assertEqual(self.df.shape, (10000, 8))
        self.assertAlmostEqual(self.df[CLASSIFICATION_TARGET].mean(), 0.1201, places=4)
        self.assertEqual(int(self.df.isna().sum().sum()), 0)

    def test_generation_is_reproducible(self):
        again = load_data(Path(self.tmp.name) / "finance_data.csv")
        pd.testing.assert_frame_equal(self.df, again)
        self.assertEqual(int((self.df["annual_income"] == 1500).sum()), 408)


class SplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = _data_or_skip()

    def test_stratified_80_20_and_deterministic(self):
        a, b = split_data(self.df), split_data(self.df)
        self.assertEqual((len(a.X_train), len(a.X_test)), (8000, 2000))
        self.assertAlmostEqual(a.y_clf_train.mean(), a.y_clf_test.mean(), places=2)
        self.assertTrue(a.X_test.index.equals(b.X_test.index))

    def test_targets_are_not_inputs(self):
        self.assertNotIn(REGRESSION_TARGET, FEATURES)
        self.assertNotIn(CLASSIFICATION_TARGET, FEATURES)
        self.assertEqual(list(split_data(self.df).X_train.columns), FEATURES)


class BaselineTest(unittest.TestCase):
    def test_at_least_five_rules(self):
        self.assertGreaterEqual(len(RULES), 5)

    def test_if_else_matches_vectorized_rules(self):
        X = tiny_frame()
        row_wise = X.apply(rule_based_predict, axis=1).to_numpy()
        np.testing.assert_array_equal(row_wise, RuleBasedClassifier().predict(X))

    def test_hits_on_known_rows(self):
        hits = rule_hits(tiny_frame())
        self.assertTrue(hits.loc[0, ["R2", "R3", "R5"]].all())  # 부채 0.9, 소득 1500
        self.assertTrue(hits.loc[1, "R1"] and hits.loc[1, "R6"])  # 연체 2회, 카드 8장
        self.assertFalse(hits.loc[2].any())
        self.assertTrue(hits.loc[4, "R4"])  # 연체 1회 + 부채 0.61
        self.assertFalse(hits.loc[4, "R5"])  # 소득 4000은 '4000 미만'이 아니다
        self.assertEqual(RuleBasedClassifier().risk_score(tiny_frame()).tolist(), [3, 2, 0, 1, 1])


class CustomTransformerTest(unittest.TestCase):
    def test_age_groups_and_debt_amount(self):
        out = DerivedFeatures().fit(tiny_frame()).transform(tiny_frame())
        self.assertEqual(out["age_group"].tolist(), ["20-29", "20-29", "30-39", "60-69", "40-49"])
        np.testing.assert_allclose(out["debt_amount"], [1350, 1500, 500, 0, 2440])

    def test_out_of_range_age_becomes_missing(self):
        X = tiny_frame().assign(age=[19, 70, 30, 40, np.nan])
        groups = DerivedFeatures().fit(X).transform(X)["age_group"]
        self.assertTrue(pd.isna(groups[0]) and pd.isna(groups[1]) and pd.isna(groups[4]))

    def test_sklearn_contract(self):
        t = DerivedFeatures(add_debt_amount=False)
        self.assertEqual(clone(t).get_params()["add_debt_amount"], False)
        t.fit(tiny_frame())
        self.assertEqual(list(t.get_feature_names_out())[-1], "age_group")
        with self.assertRaises(ValueError):
            DerivedFeatures().fit(tiny_frame().drop(columns="age"))
        with self.assertRaises(ValueError):
            DerivedFeatures(age_bins=(50, 20)).fit(tiny_frame())


class PreprocessorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split = split_data(_data_or_skip())

    def test_fit_uses_train_only(self):
        prep = build_preprocessor().fit(self.split.X_train)
        num = prep.named_steps["columns"].named_transformers_["num"]
        derived = DerivedFeatures().fit(self.split.X_train).transform(self.split.X_train)
        cols = FEATURES + ["debt_amount"]
        np.testing.assert_allclose(num.named_steps["scale"].mean_, derived[cols].mean().to_numpy())
        np.testing.assert_allclose(num.named_steps["impute"].statistics_, derived[cols].median().to_numpy())
        both = build_preprocessor().fit(pd.concat([self.split.X_train, self.split.X_test]))
        self.assertFalse(np.allclose(
            both.named_steps["columns"].named_transformers_["num"].named_steps["scale"].mean_,
            num.named_steps["scale"].mean_,
        ))

    def test_missing_values_are_imputed(self):
        prep = build_preprocessor().fit(self.split.X_train)
        X = self.split.X_test.head(5).copy()
        X.iloc[0, FEATURES.index("annual_income")] = np.nan
        X.iloc[1, FEATURES.index("age")] = np.nan
        X.iloc[2, FEATURES.index("age")] = 90  # 학습에 없던 연령대
        out = prep.transform(X)
        self.assertEqual(out.shape, (5, 12))
        self.assertFalse(np.isnan(out).any())


class ModelingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split = split_data(_data_or_skip())

    def test_metrics_from_confusion(self):
        m = classification.classification_metrics([0, 0, 1, 1, 1], [0, 1, 1, 1, 0], [0.1, 0.6, 0.9, 0.8, 0.2])
        self.assertEqual(m["confusion"], {"tn": 1, "fp": 1, "fn": 1, "tp": 2})
        self.assertAlmostEqual(m["precision"], 2 / 3)
        self.assertAlmostEqual(m["recall"], 2 / 3)
        r = regression.regression_metrics([1, 2, 3], [1, 2, 5])
        self.assertAlmostEqual(r["mae"], 2 / 3)
        self.assertAlmostEqual(r["rmse"], np.sqrt(4 / 3))

    def test_smote_lives_inside_imblearn_pipeline(self):
        pipe = classification.make_pipeline(LogisticRegression(max_iter=500), "smote")
        self.assertIsInstance(pipe, ImbPipeline)
        self.assertEqual([n for n, _ in pipe.steps], ["derive", "columns", "smote", "model"])
        X, y = self.split.X_train.head(1500), self.split.y_clf_train.head(1500)
        pipe.fit(X, y)
        self.assertEqual(len(pipe.predict_proba(self.split.X_test)), len(self.split.X_test))

    def test_strong_lasso_removes_all_features(self):
        pipe = regression.make_pipeline(Lasso(alpha=100)).fit(self.split.X_train, self.split.y_reg_train)
        self.assertTrue(np.all(pipe.named_steps["model"].coef_ == 0))

    def test_one_standard_error_selection(self):
        fake = {
            "Rule baseline": {"cv": None},
            "XGB + scale_pos_weight": {"cv": {"f1_mean": 0.70, "f1_std": 0.0447}},
            "RF + SMOTE": {"cv": {"f1_mean": 0.69, "f1_std": 0.01}},
            "LogReg + class_weight": {"cv": {"f1_mean": 0.60, "f1_std": 0.01}},
        }
        sel = classification.select_final(fake)
        self.assertEqual(sel["best_cv"], "XGB + scale_pos_weight")
        self.assertEqual(sel["final"], "RF + SMOTE")  # 0.70 - 0.0447/√5 ≈ 0.68 이상 중 가장 단순

    def test_policy_thresholds_are_ordered(self):
        X, y = self.split.X_train.head(3000), self.split.y_clf_train.head(3000)
        sub = type(self.split)(X, self.split.X_test, None, None, y, self.split.y_clf_test)
        pipe = classification.make_pipeline(LogisticRegression(max_iter=500, class_weight="balanced"), "balanced")
        pipe.fit(X, y)
        policy = classification.decision_policy(pipe, sub)
        self.assertLessEqual(policy["hold_threshold"], policy["reject_threshold"])
        bands = policy["test_bands"]
        self.assertEqual(sum(b["customers"] for b in bands.values()), len(self.split.X_test))
        self.assertLessEqual(bands["approve"]["overdue_rate"], bands["reject"]["overdue_rate"])


def _data_or_skip():
    path = ROOT / "finance_data.csv"
    if not path.exists():
        raise unittest.SkipTest("finance_data.csv가 없습니다. 먼저 python data_gen.py를 실행하세요.")
    return load_data(path)


if __name__ == "__main__":
    unittest.main()
