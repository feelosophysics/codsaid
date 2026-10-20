"""분석 노트북(notebooks/analysis_report.ipynb)의 셀 구성을 만든다. 실행은 execute_notebook.py가 한다."""
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]

CELLS = [
    ("md", """# A5-1 신용 점수 회귀와 연체 위험 분류

이 노트북은 `src/`의 모듈을 단계별로 불러 실행 결과를 보여주는 보고서다. 계산 로직은 노트북에 두지 않고 `.py` 파일에 둔다(보너스 2: 모듈화).
같은 결과를 한 번에 만들려면 `uv run python -m src.run_all`을 실행한다.

데이터는 `python data_gen.py`로 만든 **합성 데이터**이며, 결과는 실제 금융 고객에 대한 결론이 아니다."""),
    ("code", """import sys
from pathlib import Path

# VS Code/Jupyter가 notebooks/에서 시작해도 프로젝트 모듈을 찾는다.
ROOT = next((path for path in (Path.cwd(), *Path.cwd().parents)
             if (path / "src/__init__.py").is_file()
             and (path / "pyproject.toml").is_file()), None)
if ROOT is None:
    raise RuntimeError("A5-1 프로젝트 폴더를 열고 노트북을 실행하세요.")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print(f"Python: {sys.executable}")
print(f"프로젝트: {ROOT}")

import warnings
import pandas as pd
from IPython.display import Image, display

from src import baseline, classification, diagnostics, regression, report
from src.config import FIGURES_DIR, FEATURES
from src.data import describe, load_data, split_data

warnings.filterwarnings("ignore", category=UserWarning)
pd.set_option("display.precision", 4)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

df = load_data()
info = describe(df)
print(f"{info['rows']:,}행, 결측치 {info['missing_values']}개, 연체 비율 {info['overdue_rate']:.2%}")
print(f"소득 하한 1,500으로 잘린 행: {info['income_floor_rows']}개")
df.head()"""),
    ("md", """## 1. 데이터 관찰

- `credit_score`는 소득·연체 횟수·부채 비율의 **선형 결합 + 표준편차 30 노이즈**로 만들어진다.
- `is_overdue`는 점수 하위 15%(292점 미만) 중 **무작위 80%만** 1이다. 나머지 20%는 같은 조건이어도 0이다.
- `age`, `spending_score`, `credit_card_count`는 어떤 타깃에도 쓰이지 않은 노이즈 변수다."""),
    ("code", """corr = pd.DataFrame(info["correlation_with_targets"]).loc[FEATURES]
display(corr)
report.data_overview(df, FIGURES_DIR / "01_data_overview.png")
display(Image(FIGURES_DIR / "01_data_overview.png"))"""),
    ("md", """## 2. 분할

8:2 층화 분할(`random_state=42`). 이후 모든 `fit`은 Train에서만 일어나고 Test는 마지막 평가에만 쓴다."""),
    ("code", """split = split_data(df)
pd.DataFrame({
    "rows": [len(split.X_train), len(split.X_test)],
    "overdue_rate": [split.y_clf_train.mean(), split.y_clf_test.mean()],
}, index=["train", "test"])"""),
    ("md", """## 3. 규칙 기반 베이스라인

학습 없이 심사 직관으로 정한 규칙 6개. 하나라도 걸리면 연체로 예측한다. 걸린 규칙 수를 위험 점수로 써서 AUC를 계산한다."""),
    ("code", """hits = baseline.rule_hits(split.X_test)
rule_table = pd.DataFrame({
    "rule": [r["label"] for r in baseline.RULES],
    "flagged_share": hits.mean().to_numpy(),
    "overdue_rate_when_flagged": [split.y_clf_test[hits[r["id"]]].mean() for r in baseline.RULES],
}, index=hits.columns)
display(rule_table)
rb = baseline.RuleBasedClassifier()
pd.Series(classification.classification_metrics(
    split.y_clf_test, rb.predict(split.X_test), rb.predict_proba(split.X_test)[:, 1]))"""),
    ("md", """## 4. 전처리 파이프라인

`DerivedFeatures`(보너스 1)로 연령대·부채액을 만들고, 수치형은 중앙값 대치 → 표준화, 범주형은 최빈값 대치 → 원-핫 인코딩한다.
아래 평균값이 Train 평균과 일치하면, 스케일러가 Train에서만 학습됐다는 뜻이다."""),
    ("code", """from src.features import build_preprocessor
prep = build_preprocessor().fit(split.X_train)
print(list(prep.get_feature_names_out()))
scaler = prep.named_steps["columns"].named_transformers_["num"].named_steps["scale"]
pd.DataFrame({"scaler_mean": scaler.mean_[:6], "train_mean": split.X_train.mean().to_numpy(),
              "test_mean": split.X_test.mean().to_numpy()}, index=FEATURES)"""),
    ("md", """## 5. 회귀: Ridge와 Lasso

Alpha 0.01, 0.1, 1, 10, 100에서 계수 변화를 본다. 계수는 표준화된 변수 1 표준편차당 점수 변화다."""),
    ("code", """paths = regression.coefficient_paths(split)
coef = pd.DataFrame({(m, r["alpha"]): r["coefficients"] for m, rows in paths.items() for r in rows}).round(2)
display(coef)
for m, rows in paths.items():
    for r in rows:
        print(m, r["alpha"], "→ 0이 된 변수:", r["zero_coefficients"] or "없음")
report.coefficient_paths(paths, FIGURES_DIR / "02_coefficient_paths.png")
display(Image(FIGURES_DIR / "02_coefficient_paths.png"))"""),
    ("code", """extended = regression.extended_ridge_path(split)
report.ridge_extended(extended, FIGURES_DIR / "03_ridge_extended_alpha.png")
display(Image(FIGURES_DIR / "03_ridge_extended_alpha.png"))
reg = regression.tune_and_compare(split)
pd.DataFrame({k: {"alpha": v["alpha"], **v["test"]} for k, v in reg["results"].items()}).T"""),
    ("md", """같은 Alpha라도 scikit-learn의 Ridge는 오차 제곱의 **합**, Lasso는 **평균의 1/2**에 규제를 더한다.
Train이 8,000건이므로 Ridge는 Alpha가 수천 이상이 되어야 눈에 띄게 줄어든다. RMSE 약 30은 생성 노이즈 표준편차 30과 같아서, 선형 모델이 줄일 수 있는 오차를 거의 다 줄였다는 뜻이다."""),
    ("code", """report.regression_fit(split.y_reg_test, reg["predictions"]["Lasso"],
                      f"Lasso (alpha={reg['results']['Lasso']['alpha']})", FIGURES_DIR / "04_regression_fit.png")
display(Image(FIGURES_DIR / "04_regression_fit.png"))"""),
    ("md", """## 6. 분류: 불균형 처리와 앙상블

로지스틱 회귀에 처리 없음 / `class_weight='balanced'` / SMOTE를 비교하고, Random Forest(class_weight, SMOTE)와 XGBoost(scale_pos_weight)를 GridSearchCV로 튜닝한다.
수 분이 걸린다."""),
    ("code", """models = classification.fit_models(split)
table = pd.DataFrame({
    k: {"cv_f1": None if v["cv"] is None else v["cv"]["f1_mean"],
        "cv_f1_std": None if v["cv"] is None else v["cv"]["f1_std"],
        **{m: v["test"][m] for m in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]}}
    for k, v in models.items()}).T
display(table)
for k, v in models.items():
    if v.get("best_params"):
        print(k, v["best_params"])"""),
    ("code", """selection = classification.select_final(models)
final = selection["final"]
print(selection)
oracle = classification.oracle_ceiling(df.loc[split.X_test.index, "credit_score"].to_numpy(),
                                       split.y_clf_test, df["credit_score"].quantile(0.15))
print("생성 규칙을 아는 경우의 상한:", {k: round(v, 3) for k, v in oracle.items() if k != "confusion"})"""),
    ("code", """compare = classification.comparison_models(models, final)
contrast = compare["contrast"]
print("비교 모델:", contrast, "/ 불순도 중요도 모델:", compare["tree"])
report.confusion_matrices(models, ["Rule baseline", final, contrast], FIGURES_DIR / "05_confusion_matrices.png")
report.roc_pr_curves(models, split.y_clf_test, FIGURES_DIR / "06_roc_pr_curves.png")
report.model_comparison(models, FIGURES_DIR / "07_model_comparison.png")
for name in ["05_confusion_matrices", "06_roc_pr_curves", "07_model_comparison"]:
    display(Image(FIGURES_DIR / f"{name}.png"))"""),
    ("md", """## 7. 특징 중요도

불순도 중요도는 학습 데이터 기준이고 원-핫 변수를 따로 센다. Permutation 중요도는 Test에서 원본 변수 하나를 섞었을 때 PR-AUC가 떨어지는 정도다."""),
    ("code", """permutation = {k: diagnostics.permutation_on_test(models[k]["estimator"], split.X_test, split.y_clf_test)
               for k in (final, contrast)}
tree_imp = diagnostics.tree_importance(models[compare["tree"]]["estimator"])
report.feature_importance(tree_imp, permutation, FIGURES_DIR / "08_feature_importance.png")
display(Image(FIGURES_DIR / "08_feature_importance.png"))
pd.DataFrame({k: {f: v["mean"] for f, v in p.items()} for k, p in permutation.items()})"""),
    ("md", """## 8. 학습 곡선 (보너스 3)

Train과 Validation 곡선의 간격은 분산(과대적합), 두 곡선이 함께 머무는 높이는 편향을 보여준다."""),
    ("code", """from sklearn.linear_model import Lasso
lasso_alpha = reg["results"]["Lasso"]["alpha"]
curves = {
    f"{final} (F1)": diagnostics.classification_learning_curve(models[final]["estimator"], split.X_train, split.y_clf_train),
    f"{contrast} (F1)": diagnostics.classification_learning_curve(models[contrast]["estimator"], split.X_train, split.y_clf_train),
    f"Lasso alpha={lasso_alpha} (RMSE)": diagnostics.regression_learning_curve(
        regression.make_pipeline(Lasso(alpha=lasso_alpha, max_iter=50_000)), split.X_train, split.y_reg_train),
}
report.learning_curves(curves, FIGURES_DIR / "09_learning_curves.png")
display(Image(FIGURES_DIR / "09_learning_curves.png"))
{k: round(c["final_gap"], 4) for k, c in curves.items()}"""),
    ("md", """## 9. 승인·보류·거절 정책

임계값은 Test가 아니라 Train의 교차 검증 예측(out-of-fold)으로 정한다. 보류 임계값은 연체자의 95%를 보류 이상으로 보내는 가장 높은 값, 거절 임계값은 F1이 가장 높은 값이다."""),
    ("code", """policy = classification.decision_policy(models[final]["estimator"], split)
report.decision_policy(models[final]["proba"], split.y_clf_test, policy, FIGURES_DIR / "10_decision_policy.png")
display(Image(FIGURES_DIR / "10_decision_policy.png"))
print(f"보류 ≥ {policy['hold_threshold']:.3f}, 거절 ≥ {policy['reject_threshold']:.3f}")
pd.DataFrame(policy["test_bands"]).T"""),
    ("md", """## 정리

결과 수치와 해석은 `README.md`와 `results/report.md`에, 개념 설명과 직접 조작 실험은 `study/a5-1.html`에 있다."""),
]


def main():
    nb = new_notebook()
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python"}
    nb.cells = [new_markdown_cell(src) if kind == "md" else new_code_cell(src) for kind, src in CELLS]
    path = ROOT / "notebooks" / "analysis_report.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, path)
    print(f"Wrote {len(nb.cells)} cells: {path}")


if __name__ == "__main__":
    main()
