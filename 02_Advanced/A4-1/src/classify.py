"""TF-IDF 특성 + Logistic Regression 문서 분류.

- 분할: 범주 비율을 유지한 Train/Test 8:2, random_state=42
- 벡터화: TF-IDF 어휘와 IDF는 Train 문서로만 학습하고 Test에는 transform만 한다.
  Test 문서까지 넣어 IDF를 계산하면 평가 데이터의 정보가 특성에 섞인다.
- C(규제 강도의 역수)는 Train 안에서 5-fold 교차검증으로 고른다. Test는 마지막 평가에만 쓴다.
  교차검증의 각 fold는 Train 전체로 학습한 IDF를 공유한다(비지도 통계라 영향이 작다고 보고 단순화).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score

from .data import RANDOM_STATE, Corpus, train_test_indices
from .search import MAX_DF, MIN_DF
from .tfidf import TfidfVectorizerNP

C_GRID = (1.0, 10.0, 100.0)


@dataclass
class ClassificationResult:
    tf: str
    C: float
    accuracy: float
    f1_macro: float
    confusion: np.ndarray
    per_class: Dict[str, Dict[str, float]]
    train_idx: np.ndarray
    test_idx: np.ndarray
    y_pred: np.ndarray
    proba: np.ndarray
    vectorizer: TfidfVectorizerNP
    model: LogisticRegression
    X_test: np.ndarray
    cv_scores: Dict[float, float] = field(default_factory=dict)


def make_model(C: float) -> LogisticRegression:
    return LogisticRegression(C=C, max_iter=2000, random_state=RANDOM_STATE)


def select_C(X: np.ndarray, y: np.ndarray, grid: Sequence[float] = C_GRID) -> Dict[float, float]:
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    return {C: float(cross_val_score(make_model(C), X, y, cv=folds, scoring="f1_macro").mean()) for C in grid}


def run_classification(corpus: Corpus, tf: str = "raw", C: float | None = None) -> ClassificationResult:
    """C를 주지 않으면 교차검증으로 고른다."""
    train_idx, test_idx = train_test_indices(corpus.labels)
    vectorizer = TfidfVectorizerNP(tf=tf, min_df=MIN_DF, max_df=MAX_DF)
    X_train = vectorizer.fit_transform([corpus.tokens[i] for i in train_idx])
    X_test = vectorizer.transform([corpus.tokens[i] for i in test_idx])
    y_train, y_test = corpus.labels[train_idx], corpus.labels[test_idx]

    cv_scores: Dict[float, float] = {}
    if C is None:
        cv_scores = select_C(X_train, y_train)
        C = max(cv_scores, key=lambda c: (cv_scores[c], -c))  # 동점이면 규제가 강한(작은) C
    model = make_model(C).fit(X_train, y_train)
    y_pred = model.predict(X_test)

    p, r, f, s = precision_recall_fscore_support(y_test, y_pred, zero_division=0)
    per_class = {
        name: {"precision": float(p[k]), "recall": float(r[k]), "f1": float(f[k]), "support": int(s[k])}
        for k, name in enumerate(corpus.target_names)
    }
    return ClassificationResult(
        tf=tf,
        C=C,
        accuracy=float(accuracy_score(y_test, y_pred)),
        f1_macro=float(f1_score(y_test, y_pred, average="macro")),
        confusion=confusion_matrix(y_test, y_pred),
        per_class=per_class,
        train_idx=train_idx,
        test_idx=test_idx,
        y_pred=y_pred,
        proba=model.predict_proba(X_test),
        vectorizer=vectorizer,
        model=model,
        X_test=X_test,
        cv_scores=cv_scores,
    )


def explain_errors(result: ClassificationResult, corpus: Corpus, top_terms: int = 6) -> List[dict]:
    """오분류 문서마다 '예측 범주 쪽으로 끌어당긴 단어'를 계산한다.

    로지스틱 회귀의 범주 k 점수는 w_k · x + b_k 다. 단어 j가 예측 범주 p를 실제 범주 a보다
    밀어준 정도는 x_j · (w_pj − w_aj) 이고, 이 값이 큰 단어가 오분류의 직접 원인이다.
    """
    coef = result.model.coef_
    terms = result.vectorizer.terms_
    y_true = corpus.labels[result.test_idx]
    cases = []
    for row in np.flatnonzero(result.y_pred != y_true):
        pos = int(result.test_idx[row])
        pred, actual = int(result.y_pred[row]), int(y_true[row])
        x = result.X_test[row]
        push = x * (coef[pred] - coef[actual])
        order = np.argsort(-push)
        cases.append({
            "doc_id": int(corpus.doc_ids[pos]),
            "actual": corpus.target_names[actual],
            "predicted": corpus.target_names[pred],
            "confidence": float(result.proba[row, pred]),
            "n_tokens": len(corpus.tokens[pos]),
            "n_known_terms": int(np.count_nonzero(x)),
            "toward_predicted": [(terms[j], round(float(push[j]), 4)) for j in order[:top_terms] if push[j] > 0],
            "toward_actual": [(terms[j], round(float(-push[j]), 4)) for j in order[::-1][:top_terms] if push[j] < 0],
            "text": corpus.texts[pos],
        })
    return cases
