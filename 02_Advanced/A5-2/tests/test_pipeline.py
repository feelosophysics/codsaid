import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src import clustering, compare, explain, personas
from src import model as clf
from src.analysis_clustering import CLUSTERING_JSON, assign_clusters
from src.analysis_shap import SHAP_JSON
from src.config import A5_1_METRICS, CLASSIFICATION_TARGET, FEATURES, RF_PARAMS, TARGETS
from src.data import features_only, load_data, split_data

ROOT = Path(__file__).resolve().parent.parent
A5_1_DATA = ROOT.parent / "A5-1" / "finance_data.csv"


class DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        subprocess.run([sys.executable, str(ROOT / "data_gen.py")], cwd=cls.tmp.name, check=True,
                       capture_output=True, env={**os.environ, "PYTHONUTF8": "1"})
        cls.df = load_data(Path(cls.tmp.name) / "finance_data.csv")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_generated_data_matches_mission(self):
        self.assertEqual(self.df.shape, (10000, 8))
        self.assertAlmostEqual(self.df[CLASSIFICATION_TARGET].mean(), 0.1201, places=4)

    @unittest.skipUnless(A5_1_DATA.exists(), "A5-1 데이터가 없음")
    def test_same_data_as_a5_1(self):
        """미션 조건: A5-1(Mission 23)에서 만든 데이터와 같은 데이터를 쓴다."""
        pd.testing.assert_frame_equal(self.df, pd.read_csv(A5_1_DATA))

    def test_clustering_input_excludes_targets(self):
        X = features_only(self.df)
        self.assertEqual(list(X.columns), FEATURES)
        self.assertTrue(set(TARGETS).isdisjoint(X.columns))

    def test_split_matches_a5_1(self):
        split = split_data(self.df)
        self.assertEqual((len(split.X_train), len(split.X_test)), (8000, 2000))
        self.assertAlmostEqual(split.y_test.mean(), 0.12, places=3)


def blobs(n=100, seed=0):
    """6차원에서 중심이 확실히 떨어진 3개 덩어리. 군집 구조가 있는 데이터의 대조군이다."""
    rng = np.random.RandomState(seed)
    centers = np.array([[3, 0, 0, 0, 0, 0], [-3, 3, 0, 0, 0, 0], [0, -3, 3, 0, 0, 0]], dtype=float)
    Z = np.vstack([c + rng.normal(0, 0.4, (n, 6)) for c in centers])
    return Z, np.repeat([0, 1, 2], n)


class ClusteringTest(unittest.TestCase):
    def test_scaler_standardizes(self):
        X = pd.DataFrame(np.random.RandomState(0).normal(5, 3, (500, 6)), columns=FEATURES)
        Z = clustering.fit_scaler(X).transform(X)
        np.testing.assert_allclose(Z.mean(axis=0), 0, atol=1e-12)
        np.testing.assert_allclose(Z.std(axis=0), 1, atol=1e-12)

    def test_select_k_finds_real_clusters(self):
        Z, _ = blobs()
        scan = clustering.scan_k(Z, k_range=range(2, 6), seeds=range(3))
        by_k = {r["k"]: r for r in scan}
        self.assertGreater(by_k[3]["silhouette_mean"], 0.6)
        self.assertGreater(by_k[3]["ari_mean"], 0.99)
        self.assertEqual(clustering.select_k(scan, Z)["final_k"], 3)

    def test_select_k_rule(self):
        """1-표준오차 안 → 안정성 → 구별 변수 수. 표준오차 밖 K(4)는 구별 변수가 많아도 고르지 않는다."""
        Z, _ = blobs()
        scan = [
            {"k": 2, "silhouette_mean": 0.50, "silhouette_se": 0.02, "ari_mean": 0.9},
            {"k": 3, "silhouette_mean": 0.49, "silhouette_se": 0.01, "ari_mean": 0.9},
            {"k": 4, "silhouette_mean": 0.40, "silhouette_se": 0.01, "ari_mean": 0.9},
            {"k": 5, "silhouette_mean": 0.49, "silhouette_se": 0.01, "ari_mean": 0.2},
        ]
        sel = clustering.select_k(scan, Z)
        self.assertEqual(sel["within_one_se"], [2, 3, 5])
        self.assertEqual(sel["stable"], [2, 3])
        # 구별 변수가 가장 많은 K, 같으면 작은 K
        counts = {int(k): len(v) for k, v in sel["distinguishing_features"].items()}
        self.assertEqual(sel["final_k"], min(counts, key=lambda k: (-counts[k], k)))

    def test_relabel_orders_by_overdue_rate(self):
        Z, truth = blobs()
        df = pd.DataFrame({CLASSIFICATION_TARGET: (truth == 2).astype(int)})
        model = clustering.fit_final(Z, df, 3)
        rates = df[CLASSIFICATION_TARGET].groupby(model.labels_).mean().to_numpy()
        self.assertTrue(np.all(np.diff(rates) <= 0))
        nearest = np.argmin(((Z[:, None] - model.cluster_centers_[None]) ** 2).sum(axis=2), axis=1)
        np.testing.assert_array_equal(nearest, model.labels_)

    def test_knee(self):
        curve = np.r_[np.linspace(0, 1, 90), np.linspace(1.5, 10, 10)]
        self.assertAlmostEqual(compare.knee(curve), 1.0)


class PersonaTest(unittest.TestCase):
    def profile(self, cluster, **z):
        return {"cluster": cluster, "z": {f: z.get(f, 0.0) for f in FEATURES}}

    def test_signature_match(self):
        out = personas.assign([self.profile(0, overdue_count_6m=2.3), self.profile(1, debt_ratio=-1.0, spending_score=0.9)])
        self.assertEqual([p["key"] for p in out], ["repeat_delinquent", "low_debt_spender"])

    def test_unmatched_cluster_raises(self):
        with self.assertRaises(ValueError):
            personas.assign([self.profile(0, age=0.1)])


class ModelTest(unittest.TestCase):
    @unittest.skipUnless(A5_1_METRICS.exists(), "A5-1 결과가 없음")
    def test_params_come_from_a5_1(self):
        ref = clf.a5_1_reference()
        self.assertTrue(ref["params_match"], ref)

    def test_model_settings(self):
        m = clf.build_model()
        self.assertEqual(m.class_weight, "balanced")
        self.assertEqual({k: getattr(m, k) for k in RF_PARAMS}, RF_PARAMS)

    def test_bands(self):
        bands = {"hold": 0.2, "reject": 0.5}
        self.assertEqual(list(clf.band_of([0.1, 0.2, 0.49, 0.5, 0.9], bands)),
                         ["approve", "review", "review", "reject", "reject"])


class ShapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.RandomState(0)
        X = pd.DataFrame(rng.normal(size=(400, 6)), columns=FEATURES)
        y = (X["overdue_count_6m"] - X["annual_income"] + rng.normal(0, 0.5, 400) > 1).astype(int)
        cls.X, cls.model = X, clf.build_model(n_estimators=20, max_depth=4).fit(X, y)
        cls.sv = explain.explain(cls.model, X.iloc[:100])
        cls.proba = cls.model.predict_proba(X.iloc[:100])[:, 1]

    def test_additivity(self):
        self.assertLess(explain.additivity_error(self.sv, self.proba), 1e-10)

    def test_explains_overdue_class(self):
        imp = explain.global_importance(self.sv)
        top = {r["feature"]: r for r in imp[:2]}
        self.assertEqual(set(top), {"overdue_count_6m", "annual_income"})
        self.assertGreater(top["overdue_count_6m"]["direction"], 0)
        self.assertLess(top["annual_income"]["direction"], 0)

    def test_dependence_feature_rule(self):
        imp = [{"feature": f} for f in ["annual_income", "overdue_count_6m", "debt_ratio", "age"]]
        self.assertEqual(explain.dependence_features(imp), ["annual_income", "overdue_count_6m", "debt_ratio"])
        imp = [{"feature": f} for f in ["debt_ratio", "age", "annual_income"]]
        self.assertEqual(explain.dependence_features(imp), ["debt_ratio", "age", "annual_income"])

    def test_case_selection(self):
        Z = np.array([[0.0], [0.1], [5.0], [0.2], [9.0], [9.1]])
        centers = np.array([[0.0], [5.0], [9.0]])
        clusters = np.array([0, 0, 1, 0, 2, 2])
        proba = np.array([0.4, 0.7, 0.3, 0.9, 0.05, 0.3])
        reps = explain.representatives(Z, centers, clusters, proba, {"hold": 0.2, "reject": 0.5})
        self.assertEqual(reps["cluster_representatives"], {"0": 0, "1": 2, "2": 4})
        self.assertEqual(reps["reject_case"], 1)   # 0번 고객은 중심이지만 확률 0.4라 거절이 아니다
        self.assertEqual(reps["approve_case"], 4)

    def test_narrate(self):
        case = explain.case_detail(self.sv, 0, self.proba, np.zeros(100, int))
        lines = explain.narrate(case)
        self.assertEqual(len(lines), 4)
        self.assertTrue(all("%p" in line for line in lines[1:]))


@unittest.skipUnless(CLUSTERING_JSON.exists() and SHAP_JSON.exists(), "src.run_all 결과가 없음")
class ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cl = json.loads(CLUSTERING_JSON.read_text(encoding="utf-8"))
        cls.sh = json.loads(SHAP_JSON.read_text(encoding="utf-8"))

    def test_saved_transform_reproduces_labels(self):
        df = load_data()
        np.testing.assert_array_equal(assign_clusters(df, self.cl["transform"]), self.cl["labels"])

    def test_cases_follow_mission_definition(self):
        self.assertGreaterEqual(self.sh["cases"]["reject_case"]["proba"], 0.5)
        self.assertLess(self.sh["cases"]["approve_case"]["proba"], self.sh["bands"]["hold"])
        self.assertLess(self.sh["additivity_error"], 1e-10)

    def test_required_figures_exist(self):
        figures = ROOT / "results" / "figures"
        for name in ["02_pca_clusters", "04_shap_summary", "06_waterfall_reject", "07_waterfall_approve",
                     "08_dependence_annual_income"]:
            self.assertTrue((figures / f"{name}.png").exists(), name)


if __name__ == "__main__":
    unittest.main()
