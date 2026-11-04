"""모델 진단: 특징 중요도와 학습 곡선(보너스 3)."""

import numpy as np
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.model_selection import KFold, learning_curve

from .classification import cv_splitter
from .config import CV_FOLDS, FEATURES, RANDOM_STATE

TRAIN_SIZES = np.linspace(0.1, 1.0, 8)


def tree_importance(pipe) -> dict:
    """트리 모델의 불순도 감소 중요도. 전처리 뒤 변수(원-핫 포함) 기준이다."""
    names = pipe.named_steps["columns"].get_feature_names_out()
    values = pipe.named_steps["model"].feature_importances_
    return dict(sorted(((str(n), float(v)) for n, v in zip(names, values)), key=lambda t: -t[1]))


def permutation_on_test(pipe, X_test, y_test) -> dict:
    """원본 변수 하나를 Test에서 섞었을 때 PR-AUC가 얼마나 떨어지는지.

    파생 변수(age_group, debt_amount)는 원본 변수에서 다시 계산되므로 원본 6개 기준으로 해석한다.
    """
    result = permutation_importance(
        pipe,
        X_test,
        y_test,
        scoring="average_precision",
        n_repeats=10,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    rows = {
        f: {"mean": float(m), "std": float(s)}
        for f, m, s in zip(FEATURES, result.importances_mean, result.importances_std)
    }
    return dict(sorted(rows.items(), key=lambda t: -t[1]["mean"]))


def classification_learning_curve(pipe, X, y) -> dict:
    sizes, train, valid = learning_curve(
        clone(pipe), X, y, train_sizes=TRAIN_SIZES, cv=cv_splitter(), scoring="f1", n_jobs=1
    )
    return _curve(sizes, train, valid, "f1")


def regression_learning_curve(pipe, X, y) -> dict:
    sizes, train, valid = learning_curve(
        clone(pipe),
        X,
        y,
        train_sizes=TRAIN_SIZES,
        cv=KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        scoring="neg_root_mean_squared_error",
        n_jobs=1,
    )
    return _curve(sizes, -train, -valid, "rmse")


def _curve(sizes, train, valid, metric) -> dict:
    return {
        "metric": metric,
        "train_sizes": [int(s) for s in sizes],
        "train_mean": train.mean(axis=1).tolist(),
        "train_std": train.std(axis=1).tolist(),
        "valid_mean": valid.mean(axis=1).tolist(),
        "valid_std": valid.std(axis=1).tolist(),
        "final_gap": float(train.mean(axis=1)[-1] - valid.mean(axis=1)[-1]),
    }
