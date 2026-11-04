"""데이터 적재부터 회귀·분류·진단·보고서까지 한 번에 실행한다.

    python -m src.run_all [--data finance_data.csv] [--output results]
"""

import argparse
import json
import time
import warnings
from pathlib import Path

from sklearn.linear_model import Lasso

from . import classification, diagnostics, regression, report
from .config import DATA_PATH, FEATURES, RESULTS_DIR
from .data import describe, load_data, split_data

# 연체 생성 기준(하위 15% 점수). 참고 상한 계산에만 쓴다.
SCORE_QUANTILE = 0.15


def _strip(models):
    return {k: {kk: vv for kk, vv in v.items() if kk not in ("estimator", "proba")} for k, v in models.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)

    out, fig = args.output, args.output / "figures"
    fig.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore", category=UserWarning)
    started = time.time()

    def step(msg):
        print(f"[{time.time() - started:6.1f}s] {msg}", flush=True)

    df = load_data(args.data)
    split = split_data(df)
    step(f"데이터 {len(df):,}행, Train {len(split.X_train):,} / Test {len(split.X_test):,}")
    report.data_overview(df, fig / "01_data_overview.png")

    # 회귀
    paths = regression.coefficient_paths(split)
    extended = regression.extended_ridge_path(split)
    reg = regression.tune_and_compare(split)
    best_reg = min(("Ridge", "Lasso"), key=lambda k: reg["results"][k]["test"]["rmse"])
    report.coefficient_paths(paths, fig / "02_coefficient_paths.png")
    report.ridge_extended(extended, fig / "03_ridge_extended_alpha.png")
    report.regression_fit(split.y_reg_test, reg["predictions"][best_reg],
                          f"{best_reg} (alpha={reg['results'][best_reg]['alpha']})", fig / "04_regression_fit.png")
    step("회귀 완료")

    # 분류
    models = classification.fit_models(split)
    selection = classification.select_final(models)
    final = selection["final"]
    step(f"분류 완료, 최종 모델 {final}")
    policy = classification.decision_policy(models[final]["estimator"], split)
    oracle = classification.oracle_ceiling(
        df.loc[split.X_test.index, "credit_score"].to_numpy(),
        split.y_clf_test,
        df["credit_score"].quantile(SCORE_QUANTILE),
    )
    compare = classification.comparison_models(models, final)
    contrast = compare["contrast"]
    report.confusion_matrices(models, ["Rule baseline", final, contrast], fig / "05_confusion_matrices.png")
    report.roc_pr_curves(models, split.y_clf_test, fig / "06_roc_pr_curves.png")
    report.model_comparison(models, fig / "07_model_comparison.png")
    report.decision_policy(models[final]["proba"], split.y_clf_test, policy, fig / "10_decision_policy.png")
    step("정책·그래프 완료")

    # 진단: 최종 모델과 성격이 다른 모델(contrast)을 나란히 본다.
    permutation = {
        k: diagnostics.permutation_on_test(models[k]["estimator"], split.X_test, split.y_clf_test)
        for k in (final, contrast)
    }
    tree_imp = diagnostics.tree_importance(models[compare["tree"]]["estimator"])
    report.feature_importance(tree_imp, permutation, fig / "08_feature_importance.png")
    lasso_alpha = reg["results"]["Lasso"]["alpha"]
    roles = {
        "final": f"{final} (F1)",
        "contrast": f"{contrast} (F1)",
        "lasso": f"Lasso alpha={lasso_alpha} (RMSE)",
    }
    curves = {
        roles["final"]: diagnostics.classification_learning_curve(
            models[final]["estimator"], split.X_train, split.y_clf_train),
        roles["contrast"]: diagnostics.classification_learning_curve(
            models[contrast]["estimator"], split.X_train, split.y_clf_train),
        roles["lasso"]: diagnostics.regression_learning_curve(
            regression.make_pipeline(Lasso(alpha=lasso_alpha, max_iter=50_000)), split.X_train, split.y_reg_train),
    }
    report.learning_curves(curves, fig / "09_learning_curves.png")
    step("진단 완료")

    summary = {
        "data": describe(df),
        "split": {"train": len(split.X_train), "test": len(split.X_test),
                  "train_overdue_rate": float(split.y_clf_train.mean()),
                  "test_overdue_rate": float(split.y_clf_test.mean())},
        "regression": {"paths": paths, "extended_ridge": extended, "comparison": reg["results"], "best": best_reg},
        "classification": {
            "models": _strip(models),
            "selection": selection,
            "comparison": compare,
            "policy": policy,
            "oracle_ceiling": oracle,
        },
        "diagnostics": {"tree_model": compare["tree"], "tree_importance": tree_imp, "permutation": permutation,
                        "learning_curves": curves, "learning_curve_roles": roles},
    }
    (out / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(report.markdown_report(summary), encoding="utf-8")

    # 학습 자료가 Test 결과를 다시 계산할 수 있도록 Test 행과 예측 확률을 저장한다(CSV는 저장소 제외 대상).
    test = split.X_test.copy()
    predictions = {
        "features": FEATURES,
        "rows": test[FEATURES].to_numpy().tolist(),
        "is_overdue": split.y_clf_test.astype(int).tolist(),
        "credit_score": split.y_reg_test.tolist(),
        "proba": {k: [round(float(p), 6) for p in v["proba"]] for k, v in models.items() if k != "Rule baseline"},
        "final": final,
        "policy": {"hold": policy["hold_threshold"], "reject": policy["reject_threshold"]},
    }
    (out / "test_predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
    step(f"저장 완료: {out}")
    return summary


if __name__ == "__main__":
    main()
