"""파생 변수 생성기(Custom Transformer)와 전처리 파이프라인."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

from .config import FEATURES

AGE_BINS = (20, 30, 40, 50, 60, 70)


class DerivedFeatures(BaseEstimator, TransformerMixin):
    """원본 6개 변수에 파생 변수를 붙인다.

    - age_group: 나이를 연령대 문자열(범주형)로 바꾼다. 원본에 범주형 변수가 없어서
      범주형 인코딩 경로를 실제로 쓰기 위해 만든다.
    - debt_amount: 연 소득 × 부채 비율(만원). 비율만으로는 보이지 않는 부채 규모다.

    생성자에서는 인자를 저장만 하고(get_params/set_params 규약), 검사와 학습은 fit에서 한다.
    fit은 입력 컬럼 이름만 기억하므로 Train에서 배운 정보가 Test로 새지 않는다.
    """

    def __init__(self, age_bins=AGE_BINS, add_debt_amount=True):
        self.age_bins = age_bins
        self.add_debt_amount = add_debt_amount

    def fit(self, X, y=None):
        X = self._as_frame(X)
        needed = {"age"} | ({"annual_income", "debt_ratio"} if self.add_debt_amount else set())
        missing = needed - set(X.columns)
        if missing:
            raise ValueError(f"파생 변수에 필요한 컬럼이 없습니다: {sorted(missing)}")
        bins = list(self.age_bins)
        if len(bins) < 2 or bins != sorted(bins):
            raise ValueError("age_bins는 오름차순 경계 2개 이상이어야 합니다.")
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        check_is_fitted(self, "feature_names_in_")
        X = self._as_frame(X).copy()
        bins = list(self.age_bins)
        labels = [f"{lo}-{hi - 1}" for lo, hi in zip(bins[:-1], bins[1:])]
        # 경계 밖 나이와 결측 나이는 NaN으로 두고, 뒤의 범주형 대치가 처리한다.
        group = pd.cut(X["age"], bins=bins, labels=labels, right=False)
        X["age_group"] = group.astype(object).where(group.notna(), np.nan)
        if self.add_debt_amount:
            X["debt_amount"] = X["annual_income"] * X["debt_ratio"]
        return X

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_in_")
        names = list(self.feature_names_in_) + ["age_group"]
        if self.add_debt_amount:
            names.append("debt_amount")
        return np.asarray(names, dtype=object)

    @staticmethod
    def _as_frame(X):
        if isinstance(X, pd.DataFrame):
            return X
        return pd.DataFrame(X, columns=FEATURES)


def numeric_columns(add_debt_amount=True):
    return FEATURES + (["debt_amount"] if add_debt_amount else [])


def build_preprocessor(add_debt_amount=True) -> Pipeline:
    """파생 → (수치: 중앙값 대치 → 표준화) + (범주: 최빈값 대치 → 원-핫).

    이 객체 전체를 모델 Pipeline 안에 넣으므로, fit은 언제나 그 시점의 학습 데이터에서만 일어난다.
    교차 검증에서도 각 fold의 학습 부분에서만 대치값·평균·표준편차·범주 목록을 배운다.
    """
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    columns = ColumnTransformer(
        [
            ("num", numeric, numeric_columns(add_debt_amount)),
            ("cat", categorical, ["age_group"]),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            ("derive", DerivedFeatures(add_debt_amount=add_debt_amount)),
            ("columns", columns),
        ]
    )
