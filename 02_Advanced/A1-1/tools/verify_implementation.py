"""Run semantic tests, the complete analysis and the notebook, then cross-check outputs."""
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
    assert len(code) == 15
    assert [cell.execution_count for cell in code] == list(range(1, 16))
    assert not any(output.output_type == "error" for cell in code for output in cell.outputs)
    assert sum("image/png" in output.get("data", {}) for cell in code for output in cell.outputs) == 6

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
    print(json.dumps({"verified": True, "semantic_tests": 12, "notebook_code_cells": len(code),
                      "embedded_charts": 6, "rows": len(df), "orders": 1389,
                      "customers": len(rfm), "segments": summary.segment.to_list()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
