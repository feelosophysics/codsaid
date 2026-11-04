"""신용 점수 회귀: Ridge(L2)와 Lasso(L1)의 규제 강도 비교."""

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import Pipeline

from .config import ALPHAS, CV_FOLDS, RANDOM_STATE
from .features import build_preprocessor

MODELS = {
    "Ridge": lambda alpha: Ridge(alpha=alpha),
    "Lasso": lambda alpha: Lasso(alpha=alpha, max_iter=50_000),
}


def make_pipeline(estimator) -> Pipeline:
    return Pipeline([("prep", build_preprocessor()), ("model", estimator)])


def regression_metrics(y_true, y_pred) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def coefficient_paths(split) -> dict:
    """모델·Alpha마다 Train에서 학습한 계수와 Test 지표를 기록한다."""
    paths = {}
    for name, factory in MODELS.items():
        rows = []
        for alpha in ALPHAS:
            pipe = make_pipeline(factory(alpha)).fit(split.X_train, split.y_reg_train)
            names = pipe.named_steps["prep"].get_feature_names_out()
            coefs = pipe.named_steps["model"].coef_
            rows.append(
                {
                    "alpha": alpha,
                    "coefficients": {str(n): float(c) for n, c in zip(names, coefs)},
                    "zero_coefficients": [str(n) for n, c in zip(names, coefs) if c == 0],
                    "test": regression_metrics(split.y_reg_test, pipe.predict(split.X_test)),
                }
            )
        paths[name] = rows
    return paths


def extended_ridge_path(split, alphas=None) -> dict:
    """Ridge의 Alpha를 넓은 범위로 늘려 계수가 0을 향해 줄어드는 모습을 기록한다.

    scikit-learn의 Ridge는 오차 제곱의 '합'에, Lasso는 '평균의 1/2'에 규제를 더한다.
    표본이 8,000개면 같은 Alpha라도 Ridge 규제가 상대적으로 훨씬 약하다.
    """
    alphas = list(np.logspace(-2, 6, 17)) if alphas is None else list(alphas)
    rows = []
    for alpha in alphas:
        pipe = make_pipeline(Ridge(alpha=alpha)).fit(split.X_train, split.y_reg_train)
        names = pipe.named_steps["prep"].get_feature_names_out()
        rows.append(
            {
                "alpha": float(alpha),
                "coefficients": {str(n): float(c) for n, c in zip(names, pipe.named_steps["model"].coef_)},
                "test_rmse": regression_metrics(split.y_reg_test, pipe.predict(split.X_test))["rmse"],
            }
        )
    return {"n_train": int(len(split.X_train)), "rows": rows}


def tune_and_compare(split) -> dict:
    """Train에서 5-fold CV로 Alpha를 고르고, 고른 모델만 Test로 평가한다."""
    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    results = {}
    predictions = {}

    for name, estimator in {
        "Mean baseline": DummyRegressor(strategy="mean"),
        "LinearRegression": LinearRegression(),
    }.items():
        pipe = make_pipeline(estimator).fit(split.X_train, split.y_reg_train)
        pred = pipe.predict(split.X_test)
        results[name] = {"alpha": None, "test": regression_metrics(split.y_reg_test, pred)}
        predictions[name] = pred

    for name, factory in MODELS.items():
        search = GridSearchCV(
            make_pipeline(factory(1.0)),
            {"model__alpha": ALPHAS},
            scoring="neg_root_mean_squared_error",
            cv=cv,
        )
        search.fit(split.X_train, split.y_reg_train)
        pred = search.predict(split.X_test)
        results[name] = {
            "alpha": float(search.best_params_["model__alpha"]),
            "cv_rmse_by_alpha": {
                str(a): float(-s)
                for a, s in zip(ALPHAS, search.cv_results_["mean_test_score"])
            },
            "test": regression_metrics(split.y_reg_test, pred),
        }
        predictions[name] = pred

    return {"results": results, "predictions": predictions}
