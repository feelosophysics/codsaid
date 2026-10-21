"""선행 군집 결과와 입력을 잘못 연결하지 않는지 검증한다."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("learning_notebooks", ROOT / "tools/build_notebook.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
LOAD_SOURCE = next(source for kind, source in generator.SHAP
                   if kind == "code" and source.startswith("metadata_path ="))


class ArtifactBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.features = ["a", "b"]
        self.metadata = {"data_sha256": "current-data", "features": self.features, "selected_k": 2}

    def write_artifacts(self):
        (self.folder / "clustering_metadata.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        np.savez_compressed(self.folder / "clustering.npz", labels=np.array([0, 0, 1]),
                            centers=np.array([[0.0, 0.0], [1.0, 1.0]]),
                            scaler_mean=np.array([0.0, 0.0]), scaler_scale=np.array([1.0, 1.0]))

    def run_loader(self):
        namespace = {"learning_dir": self.folder, "json": json, "np": np,
                     "data_fingerprint": "current-data", "feature_columns": self.features,
                     "customers": pd.DataFrame(np.zeros((3, 2)))}
        exec(compile(LOAD_SOURCE, "notebook-artifact-loader", "exec"), namespace)
        return namespace

    def test_missing_predecessor_stops(self):
        with self.assertRaises(FileNotFoundError):
            self.run_loader()

    def test_changed_dataset_stops(self):
        self.metadata["data_sha256"] = "old-data"
        self.write_artifacts()
        with self.assertRaises(ValueError):
            self.run_loader()

    def test_changed_feature_order_stops(self):
        self.metadata["features"] = list(reversed(self.features))
        self.write_artifacts()
        with self.assertRaises(ValueError):
            self.run_loader()

    def test_matching_artifacts_load_without_pickle(self):
        self.write_artifacts()
        result = self.run_loader()
        np.testing.assert_array_equal(result["cluster_labels_all"], [0, 0, 1])
        self.assertEqual(result["cluster_centers"].shape, (2, 2))


if __name__ == "__main__":
    unittest.main()
