"""미션 실행 순서대로 군집화 → SHAP 해석 → 결과 요약을 한 번에 실행한다.

    python -m src.run_all
"""

import json

from . import analysis_clustering, analysis_shap, report
from .config import RESULTS_DIR
from .data import load_data


def main():
    df = load_data()
    clustering = analysis_clustering.run(df)
    shap_summary = analysis_shap.run(df)
    summary = {"clustering": clustering, "shap": shap_summary}
    (RESULTS_DIR / "report.md").write_text(report.markdown_report(summary), encoding="utf-8")
    print(json.dumps({"final_k": clustering["selection"]["final_k"],
                      "test_f1": round(shap_summary["model"]["test"]["f1"], 4),
                      "top_features": [r["feature"] for r in shap_summary["global"][:3]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
