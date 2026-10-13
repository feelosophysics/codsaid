"""Check analysis semantics, not merely that methods return something."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from src.pipeline import DataAnalyzer, iqr_bounds
from src.sample_data import generate_sample_data


def temporary_directory():
    # Keep tests inside the repository, including in restricted environments.
    base = Path(__file__).resolve().parents[1] / ".notebook-runtime" / "tests"
    base.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=base)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        products = pd.DataFrame({"product_id": ["P1", "P2", "P3"],
                                 "product_name": ["Red mug", None, "Phone"],
                                 "category": ["Home", "Home", "Tech"],
                                 "catalog_price": [10., np.nan, 100.],
                                 "rating": [4., 2., np.nan], "image_index": [0, 1, 2]})
        transactions = pd.DataFrame({
            "line_id": ["L1", "L2", "L3", "L4", "L5"],
            "customer_id": ["A", "A", "A", "B", "C"],
            "order_id": ["O1", "O1", "O2", "O3", "O4"],
            "order_date": ["2026-10-01", "2026-10-01", "2026-10-08", "2026-09-01", "2026-10-09"],
            "product_id": ["P1", "P2", "P1", "P3", "P2"],
            "unit_price": [20., 10., 20., 100., 5.], "quantity": [1, 1, 1, 1, 1],
            "amount": [20., 10., 20., 100., 5.], "shipping_days": [2., np.nan, 2., 60., 4.]})
        products.to_csv(self.path / "products.csv", index=False)
        transactions.to_csv(self.path / "transactions.csv", index=False)
        images = np.array([[[[0, 0, 0], [10, 10, 10]]],
                           [[[20, 20, 20], [20, 20, 20]]],
                           [[[100, 100, 100], [100, 100, 100]]]], dtype=np.uint8)
        np.save(self.path / "images.npy", images)

    def analyzer(self):
        analyzer = DataAnalyzer(self.path / "transactions.csv")
        analyzer.load_data()
        return analyzer

    def edit_transactions(self, callback):
        file = self.path / "transactions.csv"
        df = pd.read_csv(file)
        callback(df)
        df.to_csv(file, index=False)

    def test_rfm_counts_orders_not_lines_and_uses_fixed_date(self):
        analyzer = self.analyzer()
        rfm = analyzer.calculate_rfm(reference_date="2026-10-10")
        self.assertEqual(rfm.loc["A", "recency"], 2)
        self.assertEqual(rfm.loc["A", "frequency"], 2)
        self.assertEqual(rfm.loc["A", "monetary"], 50)
        self.assertEqual(rfm.loc["B", "recency"], 39)
        self.assertEqual(rfm.loc["C", "segment"], "New")
        self.assertEqual(analyzer.calculate_rfm().loc["A", "recency"], 2)
        analyzer.load_data()
        self.assertIsNone(analyzer.rfm)
        with self.assertRaisesRegex(RuntimeError, "calculate_rfm"):
            analyzer.segment_summary()

    def test_reference_cannot_precede_purchase(self):
        with self.assertRaisesRegex(ValueError, "reference_date"):
            self.analyzer().calculate_rfm(reference_date="2026-10-01")

    def test_group_imputation_uses_product_grain_and_global_fallback(self):
        analyzer = self.analyzer()
        amounts = analyzer.df.amount.copy()
        analyzer.handle_missing_values()
        self.assertEqual(analyzer.products.set_index("product_id").loc["P2", "catalog_price"], 10)
        self.assertEqual(analyzer.products.set_index("product_id").loc["P3", "rating"], 3)
        self.assertEqual(analyzer.df.loc[1, "shipping_days"], 2)
        pd.testing.assert_series_equal(analyzer.df.amount, amounts)
        self.assertFalse(analyzer.df[["catalog_price", "rating", "product_name", "shipping_days"]].isna().any().any())
        before = analyzer.df.copy(deep=True)
        with self.assertRaisesRegex(ValueError, "purchase facts"):
            analyzer.handle_missing_values(transaction_columns=("amount",))
        pd.testing.assert_frame_equal(analyzer.df, before)

    def test_all_missing_numeric_column_fails(self):
        analyzer = self.analyzer()
        analyzer.products["rating"] = np.nan
        with self.assertRaisesRegex(ValueError, "all-missing"):
            analyzer.handle_missing_values()

    def test_image_reduction_preserves_product_axis(self):
        analyzer = self.analyzer()
        analyzer.handle_missing_values()
        df = analyzer.engineer_features()
        self.assertEqual(df.loc[0, "image_mean"], 5)
        self.assertEqual(df.loc[0, "image_std"], 5)
        self.assertEqual(df.loc[1, "image_mean"], 20)
        self.assertEqual(df.loc[1, "image_std"], 0)
        self.assertEqual(df.loc[0, "name_word_count"], 2)
        np.save(self.path / "images.npy", analyzer.images[..., 0])
        grayscale = self.analyzer()
        grayscale.handle_missing_values()
        self.assertEqual(grayscale.engineer_features().loc[0, "image_mean"], 5)

    def test_iqr_flags_and_treatment_do_not_alter_purchases(self):
        self.assertEqual(iqr_bounds(pd.Series([1, 2, 3, 4, 100])), (-1, 7))
        analyzer = self.analyzer()
        before = analyzer.df.unit_price.copy()
        rfm_before = analyzer.calculate_rfm().copy()
        self.assertEqual(len(analyzer.detect_outliers("unit_price")), 1)
        treated = analyzer.treat_outliers("unit_price")
        self.assertLess(treated.max(), before.max())
        pd.testing.assert_series_equal(analyzer.df.unit_price, before)
        pd.testing.assert_frame_equal(analyzer.calculate_rfm(), rfm_before)
        with self.assertRaises(ValueError):
            iqr_bounds(before, threshold=0)

    def test_equal_measurements_receive_equal_scores(self):
        analyzer = self.analyzer()
        analyzer.df["order_date"] = pd.Timestamp("2026-10-09")
        analyzer.df["unit_price"] = [10, 10, 10, 30, 30]
        analyzer.df["amount"] = analyzer.df.unit_price
        analyzer.df["order_id"] = analyzer.df.customer_id
        rfm = analyzer.calculate_rfm()
        self.assertEqual(rfm.recency.nunique(), 1)
        self.assertEqual(rfm.r_score.nunique(), 1)
        self.assertEqual(rfm.f_score.nunique(), 1)
        self.assertEqual(rfm.m_score.nunique(), 1)

    def test_refund_and_missing_identity_excluded_not_imputed(self):
        analyzer = self.analyzer()
        analyzer.df.loc[3, "quantity"] = -1
        analyzer.df.loc[3, "amount"] = -100
        analyzer.df.loc[4, "customer_id"] = pd.NA
        rfm = analyzer.calculate_rfm()
        self.assertEqual(list(rfm.index), ["A"])
        self.assertEqual(analyzer.audit["rfm"]["excluded_rows"], 2)

    def test_reject_duplicate_lines_unknown_products_and_inconsistent_orders(self):
        self.edit_transactions(lambda df: df.__setitem__("line_id", ["L1", "L1", "L3", "L4", "L5"]))
        with self.assertRaisesRegex(ValueError, "line_id"):
            self.analyzer()
        self.edit_transactions(lambda df: df.__setitem__("line_id", ["L1", "L2", "L3", "L4", "L5"]))
        self.edit_transactions(lambda df: df.loc.__setitem__((0, "product_id"), "UNKNOWN"))
        with self.assertRaisesRegex(ValueError, "known product"):
            self.analyzer()
        self.edit_transactions(lambda df: df.loc.__setitem__((0, "product_id"), "P1"))
        self.edit_transactions(lambda df: df.loc.__setitem__((1, "customer_id"), "B"))
        with self.assertRaisesRegex(ValueError, "one customer_id"):
            self.analyzer()

    def test_line_amount_mismatch_rejected(self):
        self.edit_transactions(lambda df: df.loc.__setitem__((0, "amount"), 999))
        with self.assertRaisesRegex(ValueError, "line total"):
            self.analyzer()

    def test_image_index_out_of_bounds_rejected(self):
        path = self.path / "products.csv"
        products = pd.read_csv(path)
        products.loc[0, "image_index"] = 3
        products.to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "image_index"):
            self.analyzer()


class SampleDataTests(unittest.TestCase):
    def test_seed_reproduction_and_mission_size(self):
        with temporary_directory() as temp:
            a, b = Path(temp) / "a", Path(temp) / "b"
            generate_sample_data(a)
            generate_sample_data(b)
            for name in ["transactions.csv", "products.csv", "images.npy", "metadata.json"]:
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
            analyzer = DataAnalyzer(a / "transactions.csv")
            analyzer.load_data()
            self.assertGreaterEqual(len(analyzer.df), 1000)
            self.assertGreaterEqual(len(analyzer.df.columns), 8)
            analyzer.handle_missing_values()
            analyzer.engineer_features()
            rfm = analyzer.calculate_rfm()
            self.assertGreaterEqual(rfm.segment.nunique(), 4)
            self.assertEqual(len(rfm), 240)
            self.assertAlmostEqual(rfm.monetary.sum(), analyzer.df.amount.sum())
            self.assertEqual(rfm.frequency.sum(), analyzer.df.order_id.nunique())


if __name__ == "__main__":
    unittest.main()
