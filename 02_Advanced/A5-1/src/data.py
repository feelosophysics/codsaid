"""데이터 적재·검증·분할."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import (
    CLASSIFICATION_TARGET,
    DATA_PATH,
    FEATURES,
    RANDOM_STATE,
    REGRESSION_TARGET,
    TEST_SIZE,
)

REQUIRED_COLUMNS = FEATURES + [REGRESSION_TARGET, CLASSIFICATION_TARGET]


@dataclass
class Split:
    """한 번의 분할 결과. 회귀와 분류가 같은 행을 Train/Test로 나눠 쓴다."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_reg_train: pd.Series
    y_reg_test: pd.Series
    y_clf_train: pd.Series
    y_clf_test: pd.Series


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path}가 없습니다. 먼저 `python data_gen.py`를 실행하세요.")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    if not set(df[CLASSIFICATION_TARGET].unique()) <= {0, 1}:
        raise ValueError(f"{CLASSIFICATION_TARGET}는 0/1이어야 합니다.")
    return df


def split_data(df: pd.DataFrame) -> Split:
    """8:2 층화 분할. 연체 비율을 Train/Test에 똑같이 유지한다."""
    X = df[FEATURES]
    X_train, X_test, yr_train, yr_test, yc_train, yc_test = train_test_split(
        X,
        df[REGRESSION_TARGET],
        df[CLASSIFICATION_TARGET],
        test_size=TEST_SIZE,
        stratify=df[CLASSIFICATION_TARGET],
        random_state=RANDOM_STATE,
    )
    return Split(X_train, X_test, yr_train, yr_test, yc_train, yc_test)


def describe(df: pd.DataFrame) -> dict:
    """데이터 요약. 원본은 수정하지 않고 관찰 결과만 기록한다."""
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "overdue_rate": float(df[CLASSIFICATION_TARGET].mean()),
        "income_floor_rows": int((df["annual_income"] == 1500).sum()),
        "credit_score_range": [float(df[REGRESSION_TARGET].min()), float(df[REGRESSION_TARGET].max())],
        "correlation_with_targets": df[FEATURES + [REGRESSION_TARGET, CLASSIFICATION_TARGET]]
        .corr()[[REGRESSION_TARGET, CLASSIFICATION_TARGET]]
        .round(4)
        .to_dict(),
    }
