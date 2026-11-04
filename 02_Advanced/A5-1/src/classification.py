"""연체 위험 분류: 규칙 베이스라인, 불균형 처리 비교, 앙상블 튜닝, 승인·보류·거절 정책."""

import numpy as np
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from .baseline import RuleBasedClassifier
from .config import CV_FOLDS, N_JOBS, RANDOM_STATE
from .features import build_preprocessor

# 파라미터당 후보 5개 이하, 조합 100개 이하(미션 탐색 가이드).
RF_GRID = {
    "model__n_estimators": [200, 400],
    "model__max_depth": [4, 8, 12, 16, None],
    "model__min_samples_leaf": [1, 5, 20],
}  # 30개
XGB_GRID = {
    "model__n_estimators": [200, 400],
    "model__max_depth": [2, 3, 4, 6],
    "model__learning_rate": [0.03, 0.1],
}  # 16개

# 승인·보류·거절 정책: 연체를 놓치지 않기 위해 보류 구간은 재현율 기준으로 정한다.
HOLD_RECALL_TARGET = 0.95


def cv_splitter():
    return StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def make_pipeline(estimator, imbalance="none"):
    """imbalance: none | balanced | smote.

    SMOTE는 imblearn Pipeline 안에서만 쓴다. 이 Pipeline은 fit할 때만 표본을 합성하고
    predict에서는 건너뛰므로, 교차 검증의 검증 fold와 Test Set에는 합성 표본이 들어가지 않는다.
    전처리 뒤에 두어 대치·표준화가 끝난 공간에서 이웃을 찾는다.
    imblearn Pipeline은 중간 단계로 Pipeline을 받지 않으므로 전처리 단계(derive, columns)를 펼쳐 넣는다.
    """
    steps = list(build_preprocessor().steps)
    if imbalance == "smote":
        steps.append(("smote", SMOTE(random_state=RANDOM_STATE)))
        steps.append(("model", estimator))
        return ImbPipeline(steps)
    steps.append(("model", estimator))
    return Pipeline(steps)


def classification_metrics(y_true, y_pred, y_score) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def _positive_weight(y) -> float:
    return float((y == 0).sum() / (y == 1).sum())


def candidate_models(y_train) -> dict:
    """이름 → (Pipeline, 탐색 격자 또는 None)."""
    lr = lambda **kw: LogisticRegression(max_iter=2000, **kw)
    rf = lambda **kw: RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=N_JOBS, **kw)
    xgb = lambda **kw: XGBClassifier(
        random_state=RANDOM_STATE, n_jobs=N_JOBS, eval_metric="logloss", tree_method="hist", **kw
    )
    return {
        "LogReg (no handling)": (make_pipeline(lr()), None),
        "LogReg + class_weight": (make_pipeline(lr(class_weight="balanced"), "balanced"), None),
        "LogReg + SMOTE": (make_pipeline(lr(), "smote"), None),
        "RF + class_weight": (make_pipeline(rf(class_weight="balanced"), "balanced"), RF_GRID),
        "RF + SMOTE": (make_pipeline(rf(), "smote"), RF_GRID),
        "XGB + scale_pos_weight": (
            make_pipeline(xgb(scale_pos_weight=_positive_weight(y_train)), "balanced"),
            XGB_GRID,
        ),
    }


def fit_models(split) -> dict:
    """모든 후보를 Train에서만 학습·튜닝하고 Test로 한 번 평가한다."""
    cv = cv_splitter()
    X_tr, y_tr, X_te, y_te = split.X_train, split.y_clf_train, split.X_test, split.y_clf_test
    out = {}

    baseline = RuleBasedClassifier().fit(X_tr)
    out["Rule baseline"] = {
        "estimator": baseline,
        "best_params": None,
        "cv": None,
        "test": classification_metrics(y_te, baseline.predict(X_te), baseline.predict_proba(X_te)[:, 1]),
        "proba": baseline.predict_proba(X_te)[:, 1],
    }

    for name, (pipe, grid) in candidate_models(y_tr).items():
        if grid:
            search = GridSearchCV(
                pipe, grid, scoring={"f1": "f1", "roc_auc": "roc_auc"}, refit="f1", cv=cv, n_jobs=1
            )
            search.fit(X_tr, y_tr)
            best = search.best_estimator_
            i = search.best_index_
            cv_scores = {
                "f1_mean": float(search.cv_results_["mean_test_f1"][i]),
                "f1_std": float(search.cv_results_["std_test_f1"][i]),
                "roc_auc_mean": float(search.cv_results_["mean_test_roc_auc"][i]),
            }
            params = {k.replace("model__", ""): v for k, v in search.best_params_.items()}
            n_candidates = len(search.cv_results_["params"])
        else:
            scores = cross_validate(pipe, X_tr, y_tr, cv=cv, scoring=["f1", "roc_auc"])
            cv_scores = {
                "f1_mean": float(scores["test_f1"].mean()),
                "f1_std": float(scores["test_f1"].std()),
                "roc_auc_mean": float(scores["test_roc_auc"].mean()),
            }
            best = pipe.fit(X_tr, y_tr)
            params, n_candidates = None, 1
        proba = best.predict_proba(X_te)[:, 1]
        out[name] = {
            "estimator": best,
            "best_params": params,
            "grid_candidates": n_candidates,
            "cv": cv_scores,
            "test": classification_metrics(y_te, best.predict(X_te), proba),
            "proba": proba,
        }
    return out


# 해석·운영이 쉬운 순서. 성능이 비슷하면 앞쪽을 고른다.
SIMPLICITY_ORDER = [
    "LogReg + class_weight",
    "LogReg (no handling)",
    "LogReg + SMOTE",
    "RF + class_weight",
    "RF + SMOTE",
    "XGB + scale_pos_weight",
]


def select_final(models: dict) -> dict:
    """Test가 아니라 Train 교차 검증 F1로 최종 모델을 고른다.

    1-표준오차 규칙: CV F1 최고 모델의 (평균 − 표준오차) 이상인 후보는 최고 모델과 차이를 주장하기
    어렵다고 보고, 그중 가장 단순한 모델을 고른다. 표준오차 = fold 간 표준편차 / √fold 수.
    """
    ml = {k: v for k, v in models.items() if v["cv"] is not None}
    best = max(ml, key=lambda k: ml[k]["cv"]["f1_mean"])
    cutoff = ml[best]["cv"]["f1_mean"] - ml[best]["cv"]["f1_std"] / np.sqrt(CV_FOLDS)
    within = [k for k in SIMPLICITY_ORDER if k in ml and ml[k]["cv"]["f1_mean"] >= cutoff]
    return {"best_cv": best, "cutoff": float(cutoff), "within_one_std": within, "final": within[0]}


def comparison_models(models: dict, final: str) -> dict:
    """진단·그래프에서 최종 모델과 나란히 볼 모델을 정한다.

    - contrast: 성격이 다른 모델. 최종이 트리 계열이면 단순 선형(LogReg + class_weight),
      최종이 선형이면 CV F1이 가장 높은 앙상블.
    - tree: 불순도 중요도를 그릴 트리 모델. 최종이 트리면 최종, 아니면 CV F1 최고 RF.
    """
    rfs = [k for k in ("RF + class_weight", "RF + SMOTE") if k in models]
    best_rf = max(rfs, key=lambda k: models[k]["cv"]["f1_mean"])
    ensembles = rfs + [k for k in ("XGB + scale_pos_weight",) if k in models]
    final_is_tree = final in ensembles
    best_ensemble = max(ensembles, key=lambda k: models[k]["cv"]["f1_mean"])
    return {
        "contrast": "LogReg + class_weight" if final_is_tree else best_ensemble,
        "tree": final if final in rfs else best_rf,
    }


def oracle_ceiling(df_test_scores, y_test, score_threshold) -> dict:
    """생성 규칙(신용 점수 하위 15%)을 그대로 아는 경우의 성능.

    실제 입력에는 없는 credit_score와 생성 임계값을 쓰므로 모델과 비교할 수 있는 후보가 아니라
    라벨에 섞인 무작위성(하위 15% 중 20%를 정상으로 둠) 때문에 생기는 상한을 확인하는 참고값이다.
    """
    pred = (df_test_scores < score_threshold).astype(int)
    return classification_metrics(y_test, pred, -df_test_scores)


def decision_policy(estimator, split) -> dict:
    """Train의 교차 검증 예측(out-of-fold)으로 임계값을 정하고 Test에서 결과를 확인한다.

    - 거절: OOF F1이 가장 높은 임계값 이상
    - 보류: 재현율 HOLD_RECALL_TARGET를 지키는 가장 높은 임계값 이상
    - 승인: 그 아래
    """
    oof = cross_val_predict(
        estimator, split.X_train, split.y_clf_train, cv=cv_splitter(), method="predict_proba"
    )[:, 1]
    precision, recall, thresholds = precision_recall_curve(split.y_clf_train, oof)
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    reject_t = float(thresholds[np.argmax(f1)])
    ok = recall[:-1] >= HOLD_RECALL_TARGET
    hold_t = float(thresholds[ok].max()) if ok.any() else float(thresholds.min())
    hold_t = min(hold_t, reject_t)

    proba = estimator.predict_proba(split.X_test)[:, 1]
    y = split.y_clf_test.to_numpy()
    bands = {
        "approve": proba < hold_t,
        "hold": (proba >= hold_t) & (proba < reject_t),
        "reject": proba >= reject_t,
    }
    summary = {
        name: {
            "customers": int(mask.sum()),
            "share": float(mask.mean()),
            "overdue": int(y[mask].sum()),
            "overdue_rate": float(y[mask].mean()) if mask.any() else 0.0,
        }
        for name, mask in bands.items()
    }
    return {
        "hold_threshold": hold_t,
        "reject_threshold": reject_t,
        "hold_recall_target": HOLD_RECALL_TARGET,
        "oof_f1_at_reject": float(f1.max()),
        "test_bands": summary,
        "test_missed_overdue_in_approve": summary["approve"]["overdue"],
        "test_total_overdue": int(y.sum()),
    }
