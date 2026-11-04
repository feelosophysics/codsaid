"""설명할 분류 모델: A5-1 최종 설정(RF + class_weight)을 원본 6개 변수로 다시 학습한다."""

import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
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
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate

from .config import A5_1_METRICS, CV_FOLDS, HOLD_RECALL_TARGET, N_JOBS, RANDOM_STATE, REJECT_THRESHOLD, RF_PARAMS


def build_model(**overrides) -> RandomForestClassifier:
    """트리 모델은 거리나 기울기를 쓰지 않으므로 스케일링 없이 원래 단위로 학습한다.

    그래서 SHAP 그래프의 x축도 만원·비율·횟수 같은 원래 단위로 읽을 수 있다.
    """
    params = {**RF_PARAMS, "random_state": RANDOM_STATE, "n_jobs": N_JOBS, **overrides}
    return RandomForestClassifier(**params)


def cv_splitter():
    return StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def classification_metrics(y_true, proba, threshold=REJECT_THRESHOLD) -> dict:
    y_pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def a5_1_reference() -> dict:
    """A5-1 결과 파일이 있으면 최종 모델 설정과 성능을 읽어 온다. 없으면 비교를 건너뛴다."""
    if not A5_1_METRICS.exists():
        return {"available": False}
    m = json.loads(A5_1_METRICS.read_text(encoding="utf-8"))
    final = m["classification"]["selection"]["final"]
    info = m["classification"]["models"][final]
    expected = {k: v for k, v in RF_PARAMS.items() if k != "class_weight"}
    return {
        "available": True,
        "final_model": final,
        "best_params": info["best_params"],
        "params_match": final == "RF + class_weight" and info["best_params"] == expected,
        "cv": info["cv"],
        "test": {k: info["test"][k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc")},
        "input_features": "원본 6개 + 파생 2개(age_group 원-핫, debt_amount)",
    }


def train_and_evaluate(split) -> tuple[RandomForestClassifier, dict]:
    """Train 5-fold CV로 A5-1과 같은 방식의 성능을 재고, Train 전체로 학습해 Test에서 한 번 평가한다."""
    model = build_model()
    scores = cross_validate(model, split.X_train, split.y_train, cv=cv_splitter(), scoring=["f1", "roc_auc"])
    model.fit(split.X_train, split.y_train)
    proba = model.predict_proba(split.X_test)[:, 1]
    return model, {
        "params": RF_PARAMS,
        "cv": {
            "f1_mean": float(scores["test_f1"].mean()),
            "f1_std": float(scores["test_f1"].std()),
            "roc_auc_mean": float(scores["test_roc_auc"].mean()),
        },
        "test": classification_metrics(split.y_test, proba),
        "a5_1": a5_1_reference(),
    }


def decision_bands(model, split) -> dict:
    """A5-1의 승인·보류·거절 정책을 미션 정의에 맞춰 다시 정한다.

    - 거절: 연체 확률 ≥ 0.5 (미션 정의)
    - 보류: Train 교차 검증 예측(out-of-fold)에서 연체자의 95%를 보류 이상으로 보내는 가장 높은 임계값 이상
    - 승인: 그 아래
    Test는 임계값을 정하는 데 쓰지 않는다.
    """
    oof = cross_val_predict(build_model(), split.X_train, split.y_train, cv=cv_splitter(), method="predict_proba")[:, 1]
    _, recall, thresholds = precision_recall_curve(split.y_train, oof)
    ok = recall[:-1] >= HOLD_RECALL_TARGET
    hold = float(thresholds[ok].max()) if ok.any() else float(thresholds.min())
    return {"hold": min(hold, REJECT_THRESHOLD), "reject": REJECT_THRESHOLD, "hold_recall_target": HOLD_RECALL_TARGET}


def band_of(proba, bands) -> np.ndarray:
    p = np.asarray(proba)
    return np.where(p >= bands["reject"], "reject", np.where(p >= bands["hold"], "review", "approve"))
