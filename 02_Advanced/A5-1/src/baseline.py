"""if-else 규칙 기반 연체 예측 베이스라인.

규칙은 데이터를 학습하지 않고 심사 담당자의 직관으로 미리 정한다.
한 규칙이라도 걸리면 연체(1)로 예측하고, 걸린 규칙 수를 위험 점수로 써서 AUC를 계산한다.
"""

import operator

import numpy as np
import pandas as pd

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}

# 각 규칙의 조건은 모두 만족해야(AND) 걸린다. 학습 자료가 같은 정의를 읽어 JavaScript로 재현한다.
RULES = [
    {"id": "R1", "label": "최근 6개월 연체 2회 이상", "conditions": [("overdue_count_6m", ">=", 2)]},
    {"id": "R2", "label": "부채 비율 80% 초과", "conditions": [("debt_ratio", ">", 0.8)]},
    {"id": "R3", "label": "연 소득 3,000만원 미만", "conditions": [("annual_income", "<", 3000)]},
    {
        "id": "R4",
        "label": "연체 이력이 있고 부채 비율 60% 초과",
        "conditions": [("overdue_count_6m", ">=", 1), ("debt_ratio", ">", 0.6)],
    },
    {
        "id": "R5",
        "label": "연 소득 4,000만원 미만이고 부채 비율 50% 초과",
        "conditions": [("annual_income", "<", 4000), ("debt_ratio", ">", 0.5)],
    },
    {"id": "R6", "label": "신용카드 8장 이상 보유", "conditions": [("credit_card_count", ">=", 8)]},
]


def rule_hits(X: pd.DataFrame, rules=RULES) -> pd.DataFrame:
    """행마다 각 규칙이 걸렸는지 True/False로 반환한다."""
    hits = {}
    for rule in rules:
        mask = np.ones(len(X), dtype=bool)
        for feature, op, value in rule["conditions"]:
            mask &= OPS[op](X[feature].to_numpy(), value)
        hits[rule["id"]] = mask
    return pd.DataFrame(hits, index=X.index)


def rule_based_predict(row: pd.Series) -> int:
    """원문 예시와 같은 if-else 형태. rule_hits와 같은 판정을 한 행 단위로 보여준다."""
    if row["overdue_count_6m"] >= 2:
        return 1  # R1 연체 반복
    if row["debt_ratio"] > 0.8:
        return 1  # R2 과다 부채
    if row["annual_income"] < 3000:
        return 1  # R3 저소득
    if row["overdue_count_6m"] >= 1 and row["debt_ratio"] > 0.6:
        return 1  # R4 연체 + 부채
    if row["annual_income"] < 4000 and row["debt_ratio"] > 0.5:
        return 1  # R5 중저소득 + 부채
    if row["credit_card_count"] >= 8:
        return 1  # R6 카드 과다 보유
    return 0


class RuleBasedClassifier:
    """규칙 묶음을 scikit-learn 모델처럼 predict / predict_proba로 쓰게 하는 얇은 래퍼."""

    def __init__(self, rules=RULES):
        self.rules = rules

    def fit(self, X, y=None):
        return self  # 학습하지 않는다.

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        return rule_hits(X, self.rules).sum(axis=1).to_numpy()

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return (self.risk_score(X) > 0).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        # 확률이 아니라 순위를 매기는 점수다. AUC 계산에만 쓴다.
        score = self.risk_score(X) / len(self.rules)
        return np.column_stack([1 - score, score])
