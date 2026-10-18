"""Build the regression half of the teaching scene from the existing Train split.

Reuses the saved Lasso alpha and final classifier scores; no grid search.
Run from A5-1 with: uv run python tools/anatomy/export_dual_predictions.py
"""
import hashlib
import json
import os
import sys
from pathlib import Path

MISSION = Path(__file__).resolve().parents[2]
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(name, "2")
sys.path.insert(0, str(MISSION))
site = MISSION / ".venv/Lib/site-packages"
if site.exists():
    sys.path.append(str(site))

import numpy as np
from sklearn.linear_model import Lasso
from src.data import load_data, split_data
from src.regression import make_pipeline, regression_metrics

raw = (MISSION / "results/test_predictions.json").read_bytes()
saved = json.loads(raw)
metrics = json.loads((MISSION / "results/metrics.json").read_text(encoding="utf-8"))
split = split_data(load_data())
np.testing.assert_array_equal(split.X_test.to_numpy(), saved["rows"])
np.testing.assert_array_equal(split.y_reg_test, saved["credit_score"])
np.testing.assert_array_equal(split.y_clf_test, saved["is_overdue"])
alpha = metrics["regression"]["comparison"]["Lasso"]["alpha"]
pipe = make_pipeline(Lasso(alpha=alpha, max_iter=50_000)).fit(split.X_train, split.y_reg_train)
pred = pipe.predict(split.X_test)
observed = regression_metrics(split.y_reg_test, pred)
reference = metrics["regression"]["comparison"]["Lasso"]["test"]
for name, value in reference.items():
    np.testing.assert_allclose(observed[name], value, rtol=0, atol=1e-9)
out = {
    "regression_model": "Lasso", "alpha": alpha,
    "classification_model": saved["final"],
    "source_sha256": hashlib.sha256(raw).hexdigest(),
    "test_row_indices": [int(i) for i in split.X_test.index],
    "regression_predictions": pred.tolist(), "metrics": observed,
    "method": "Train-only fit with saved alpha; Test row order and saved metrics verified"
}
(MISSION / "results/dual_predictions.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"rows": len(pred), "model": "Lasso", "alpha": alpha, "metrics": observed, "saved_metrics_match": True}, ensure_ascii=False))
