"""Saved A5-1 predictions -> independent scikit-learn reference, no training."""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
mission = here.parent.parent
sys.path.insert(0, str(mission / ".venv/Lib/site-packages"))
import numpy as np
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, accuracy_score

data = json.loads((mission / "results/test_predictions.json").read_text(encoding="utf-8"))
y = np.array(data["is_overdue"])
p = np.array(data["proba"][data["final"]])
thresholds = sorted(set([i / 1000 for i in range(1001)] + p.tolist()))
rows = []
for t in thresholds:
    pred = p >= t
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    rows.append({"threshold": t, "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                 "precision": precision_score(y, pred, zero_division=0),
                 "recall": recall_score(y, pred, zero_division=0),
                 "f1": f1_score(y, pred, zero_division=0), "accuracy": accuracy_score(y, pred)})
(here / "sklearn-reference.json").write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
print(f"scikit-learn reference: {len(rows)} thresholds, including each distinct stored score")
