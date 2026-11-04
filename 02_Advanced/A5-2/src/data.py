"""데이터 적재·검증·분할. 분할 방식은 A5-1과 같아서 Test 2,000명이 A5-1과 같은 고객이다."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import CLASSIFICATION_TARGET, DATA_PATH, FEATURES, RANDOM_STATE, TARGETS, TEST_SIZE


@dataclass
class Split:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path}가 없습니다. 먼저 `python data_gen.py`를 실행하세요.")
    df = pd.read_csv(path)
    missing = [c for c in FEATURES + TARGETS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    if not set(df[CLASSIFICATION_TARGET].unique()) <= {0, 1}:
        raise ValueError(f"{CLASSIFICATION_TARGET}는 0/1이어야 합니다.")
    return df


def features_only(df: pd.DataFrame) -> pd.DataFrame:
    """군집화 입력. 타깃(신용 점수, 연체 여부)은 넣지 않는다."""
    return df[FEATURES].copy()


def split_data(df: pd.DataFrame) -> Split:
    """A5-1과 같은 8:2 층화 분할(random_state=42)."""
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES],
        df[CLASSIFICATION_TARGET],
        test_size=TEST_SIZE,
        stratify=df[CLASSIFICATION_TARGET],
        random_state=RANDOM_STATE,
    )
    return Split(X_train, X_test, y_train, y_test)


def describe(df: pd.DataFrame) -> dict:
    """데이터 요약. 원본은 수정하지 않고 관찰 결과만 기록한다."""
    return {
        "rows": int(len(df)),
        "missing_values": int(df.isna().sum().sum()),
        "overdue_rate": float(df[CLASSIFICATION_TARGET].mean()),
        "feature_correlation_max": float(
            df[FEATURES].corr().where(lambda c: c < 1).abs().max().max()
        ),
        "overdue_count_distribution": {
            int(k): int(v) for k, v in df["overdue_count_6m"].value_counts().sort_index().items()
        },
    }
