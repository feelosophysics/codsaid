"""2단계: 분류 모델 학습과 SHAP 해석. 1단계 군집 결과와 연결해 페르소나별 예측 근거를 설명한다.

    python -m src.analysis_shap
"""

import json
import time

import numpy as np

from . import explain, model as clf, personas, report
from .analysis_clustering import assign_clusters, load_result
from .config import FEATURES, FIGURES_DIR, RESULTS_DIR, limit_threads
from .data import load_data, split_data

SHAP_JSON = RESULTS_DIR / "shap.json"
TEST_JSON = RESULTS_DIR / "test_explanations.json"
FORCE_DIR = RESULTS_DIR / "force_plots"
# 연체 라벨 생성 기준(신용 점수 하위 15%). 소득 Dependence Plot에 이론 경계를 그리는 데만 쓴다.
SCORE_QUANTILE = 0.15


def theoretical_income_boundary(df, overdue_level, debt_ratio=0.5) -> float:
    """data_gen.py 공식에서 노이즈를 뺀 신용 점수가 연체 기준 점수와 같아지는 소득.

    300 + 3·소득/100 − 50·연체 − 100·부채 = 기준 점수  →  소득 = (기준 − 300 + 50·연체 + 100·부채) / 0.03
    """
    threshold = df["credit_score"].quantile(SCORE_QUANTILE)
    return float((threshold - 300 + 50 * overdue_level + 100 * debt_ratio) / 0.03)


def run(df=None, verbose=True):
    limit_threads()
    started = time.time()

    def step(msg):
        if verbose:
            print(f"[{time.time() - started:6.1f}s] {msg}", flush=True)

    df = load_data() if df is None else df
    clustering = load_result()
    tf = clustering["transform"]
    k = len(tf["centers"])
    names = clustering["personas"]
    labels_en = [personas.short_label(p) for p in names]

    split = split_data(df)
    clusters_test = np.asarray(clustering["labels"])[split.X_test.index]
    if not np.array_equal(clusters_test, assign_clusters(split.X_test, tf)):
        raise RuntimeError("저장된 군집 배정과 중심 거리 계산이 다릅니다. analysis_clustering을 다시 실행하세요.")
    step(f"Train {len(split.X_train):,} / Test {len(split.X_test):,}, 군집 {k}개 불러옴")

    model, metrics = clf.train_and_evaluate(split)
    bands = clf.decision_bands(model, split)
    proba = model.predict_proba(split.X_test)[:, 1]
    step(f"모델 학습 완료: Test F1 {metrics['test']['f1']:.3f}, 보류 임계값 {bands['hold']:.3f}")

    sv = explain.explain(model, split.X_test)
    additivity = explain.additivity_error(sv, proba)
    step(f"SHAP 계산 완료(Test {len(split.X_test):,}명), 가법성 오차 {additivity:.1e}")

    importance = explain.global_importance(sv)
    dep_features = explain.dependence_features(importance)
    y = split.y_test.to_numpy()
    Z_test = (split.X_test[FEATURES].to_numpy(float) - tf["scaler_mean"]) / tf["scaler_scale"]
    reps = explain.representatives(Z_test, np.asarray(tf["centers"]), clusters_test, proba, bands)
    cases = {
        "reject_case": explain.case_detail(sv, reps["reject_case"], proba, y),
        "approve_case": explain.case_detail(sv, reps["approve_case"], proba, y),
        "cluster_representatives": [explain.case_detail(sv, i, proba, y)
                                    for i in reps["cluster_representatives"].values()],
    }
    band = clf.band_of(proba, bands)
    for case in [cases["reject_case"], cases["approve_case"], *cases["cluster_representatives"]]:
        case["cluster"] = int(clusters_test[case["row"]])
        case["band"] = str(band[case["row"]])
        case["test_index"] = int(split.X_test.index[case["row"]])
        case["credit_score"] = float(df.loc[case["test_index"], "credit_score"])

    boundaries = {o: theoretical_income_boundary(df, o) for o in (1, 2)}
    dependence = {
        "features": dep_features,
        "income_by_overdue": explain.binned_dependence(sv, "annual_income", by="overdue_count_6m"),
        "overdue_levels": explain.binned_dependence(sv, "overdue_count_6m"),
        "debt_ratio": explain.binned_dependence(sv, "debt_ratio"),
        "income_crossing": {str(o): explain.income_crossing(sv, o) for o in (0, 1, 2)},
        "theoretical_income_boundary": {str(o): v for o, v in boundaries.items()},
    }
    per_cluster = explain.cluster_shap(sv, clusters_test, k)
    crosstab = {str(c): {b: int(((clusters_test == c) & (band == b)).sum()) for b in ("approve", "review", "reject")}
                for c in range(k)}
    step("Global·Local·Dependence 요약 완료")

    report.shap_summary(sv, FIGURES_DIR / "04_shap_summary.png")
    report.shap_bar(sv, FIGURES_DIR / "05_shap_importance_bar.png")
    rej, app = cases["reject_case"], cases["approve_case"]
    report.waterfall(sv[rej["row"]], f"Reject case: {labels_en[rej['cluster']]}, p = {rej['proba']:.2f}",
                     FIGURES_DIR / "06_waterfall_reject.png")
    report.waterfall(sv[app["row"]], f"Approve case: {labels_en[app['cluster']]}, p = {app['proba']:.2f}",
                     FIGURES_DIR / "07_waterfall_approve.png")
    FORCE_DIR.mkdir(parents=True, exist_ok=True)
    report.force_html(sv[rej["row"]], FORCE_DIR / "reject_case.html")
    report.force_html(sv[app["row"]], FORCE_DIR / "approve_case.html")
    for n, f in enumerate(dep_features, start=8):
        boundary = [(v, f"overdue={o}, debt=0.5: score=292") for o, v in boundaries.items()] if f == "annual_income" else None
        report.dependence(sv, f, FIGURES_DIR / f"{n:02d}_dependence_{f}.png", boundary)
    report.cluster_shap(per_cluster, labels_en, FIGURES_DIR / "11_cluster_shap.png")
    report.persona_cases(cases["cluster_representatives"], labels_en, FIGURES_DIR / "12_persona_cases.png")
    step("그래프 저장 완료")

    summary = {
        "model": metrics,
        "bands": bands,
        "base_value": float(sv.base_values[0]),
        "additivity_error": additivity,
        "global": importance,
        "dependence": dependence,
        "cluster_shap": per_cluster,
        "cluster_band_crosstab": crosstab,
        "cases": cases,
        "test_band_counts": {b: int((band == b).sum()) for b in ("approve", "review", "reject")},
        "test_overdue_by_band": {b: int(y[band == b].sum()) for b in ("approve", "review", "reject")},
    }
    SHAP_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    # 학습 자료가 Test 고객마다 SHAP을 보여 주고 검증할 수 있도록 원자료를 저장한다(CSV는 저장소 제외 대상).
    coords = (Z_test - tf["pca_mean"]) @ np.asarray(tf["pca_components"]).T
    TEST_JSON.write_text(json.dumps({
        "features": FEATURES,
        "rows": split.X_test[FEATURES].to_numpy().tolist(),
        "y": y.astype(int).tolist(),
        "proba": [round(float(p), 6) for p in proba],
        "base_value": float(sv.base_values[0]),
        "shap": np.round(sv.values, 6).tolist(),
        "cluster": clusters_test.tolist(),
        "pca": np.round(coords, 5).tolist(),
        "bands": bands,
    }), encoding="utf-8")
    step(f"저장 완료: {SHAP_JSON.name}, {TEST_JSON.name}")
    return summary


if __name__ == "__main__":
    run()
