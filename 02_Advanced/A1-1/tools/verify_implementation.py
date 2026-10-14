"""Run analysis and notebook, then cross-check outputs; --saved-only rechecks saved evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".notebook-runtime" / "matplotlib")
os.environ["IPYTHONDIR"] = str(ROOT / ".notebook-runtime" / "ipython")
os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".notebook-runtime")


def main():
    if '--saved-only' not in sys.argv:
        for args in [["-m", "unittest", "discover", "-s", "tests", "-v"],
                     ["-m", "src.run_analysis"], ["tools/execute_notebook.py"]]:
            subprocess.run([sys.executable, *args], cwd=ROOT, check=True)
    import nbformat
    import numpy as np
    import pandas as pd
    from matplotlib.image import imread

    result = ROOT / "results"
    notebook = nbformat.read(ROOT / "notebooks" / "analysis_report.ipynb", as_version=4)
    nbformat.validate(notebook)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(code) == 18
    assert [cell.execution_count for cell in code] == list(range(1, 19))
    assert not any(output.output_type == "error" for cell in code for output in cell.outputs)
    assert sum("image/png" in output.get("data", {}) for cell in code for output in cell.outputs) == 8

    df = pd.read_csv(result / "processed_transactions.csv")
    rfm = pd.read_csv(result / "rfm_customers.csv")
    summary = pd.read_csv(result / "segment_summary.csv")
    audit = json.loads((result / "audit.json").read_text(encoding="utf-8"))
    assert len(df) == 2842 and len(df.columns) == 22
    assert len(rfm) == 240 and summary.segment.nunique() == 4
    assert np.isclose(rfm.monetary.sum(), df.amount.sum())
    assert rfm.frequency.sum() == df.order_id.nunique() == 1389
    assert summary.customers.sum() == len(rfm)
    assert np.isclose(summary.revenue_share_pct.sum(), 100)
    assert audit["rfm"]["reference_date"] == "2026-10-10"
    assert audit["outliers"]["shipping_days"]["count"] == 15
    assert not df[["catalog_price", "rating", "product_name", "shipping_days", "image_mean", "image_std"]].isna().any().any()
    charts = sorted((result / "figures").glob("*.png"))
    assert len(charts) == 6
    for chart in charts:
        pixels = imread(chart)
        assert pixels.shape[0] >= 500 and pixels.shape[1] >= 900
        assert np.isfinite(pixels).all() and pixels.std() > 0.01
    bonus = result / 'bonus'
    features = pd.read_csv(bonus / 'image_features.csv')
    np.testing.assert_allclose(features.filter(like='image_hist_').sum(axis=1), 1)
    assert len(features) == 80
    rates = pd.read_csv(bonus / 'cohort_retention.csv', index_col=0)
    assert rates.shape[0] == 12 and rates.notna().sum().sum() == 66
    assert rates.isna().sum().sum() == 78
    observed = rates.stack().dropna()
    assert ((observed >= 0) & (observed <= 1)).all()
    assert len(pd.read_csv(bonus / 'transactions_with_image_features.csv').columns) == 32
    page = (bonus / 'rfm_interactive.html').read_text(encoding='utf-8')
    assert 'rfm-plot' in page and '<script src=' not in page
    print(json.dumps({"verified": True, "semantic_tests": 21, "notebook_code_cells": len(code),
                      "embedded_charts": 8, "bonus": 3, "rows": len(df), "orders": 1389,
                      "customers": len(rfm), "segments": summary.segment.to_list()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
