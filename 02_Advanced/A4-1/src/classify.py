"""TF-IDF 특성 + Logistic Regression 문서 분류.

- 분할: 범주 비율을 유지한 Train/Test 8:2, random_state=42
- 벡터화: TF-IDF 어휘와 IDF는 Train 문서로만 학습하고 Test에는 transform만 한다.
  Test 문서까지 넣어 IDF를 계산하면 평가 데이터의 정보가 특성에 섞인다.
- C(규제 강도의 역수)는 Train 안에서 5-fold 교차검증으로 고른다. Test는 마지막 평가에만 쓴다.
  교차검증의 각 fold는 Train 전체로 학습한 어휘·IDF를 공유한다. 검증 fold 통계가
  반영되는 한계가 있으며 영향이 작다고 검증한 것은 아니다. select_C 설명을 참고한다.
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
    """학습한 분류기와 최종 평가 결과를 함께 보관한다.

    검색은 문서 순위를 반환하지만 분류는 범주 하나를 예측한다. 둘의 점수는 다르다.
    @dataclass는 필드를 받는 생성자를 만든다. field(default_factory=dict)는
    객체마다 별도의 빈 사전을 만들어 서로의 cv_scores를 공유하지 않게 한다.

    Attributes:
        tf: TF 방식.
        C: 선택한 규제 역수. 클수록 가중치 크기를 억제하는 힘이 약하다.
        accuracy: Test 정답 비율.
        f1_macro: 범주별 F1의 단순 평균.
        confusion: (K,K), 행은 실제·열은 예측 범주.
        per_class: 범주별 precision, recall, f1, support.
        train_idx: Corpus에서 Train의 위치.
        test_idx: Corpus에서 Test의 위치.
        y_pred: (N_test,) 예측 번호. test_idx 순서다.
        proba: (N_test,K) 모델 확률. 행 합은 약 1이나 정확성 보장은 아니다.
        vectorizer: Train만으로 만든 어휘·IDF.
        model: 학습한 LogisticRegression.
        X_test: (N_test,V_train) 특성 행렬.
        cv_scores: C별 Train 내부 평균 macro F1.
    """
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
    """학습 전 로지스틱 회귀 객체를 만든다.

    여러 범주의 선형 점수 z_k=w_k·x+b_k를 softmax로 확률로 바꾸고
    정답 확률의 -log 손실과 규제 항을 줄이도록 가중치를 학습한다.
    예: 두 점수 [0,ln(3)]이면 exp=[1,3], 확률=[.25,.75].
    실제 미션은 5범주이며 각 단어 열마다 범주별 가중치를 갖는다.

    Args:
        C: 양수 규제 역수. max_iter=2000은 최대 반복 수로 수렴 보장은 아니다.

    Returns:
        LogisticRegression: 아직 fit하지 않은 분류기.
    """
    return LogisticRegression(C=C, max_iter=2000, random_state=RANDOM_STATE)


def select_C(X: np.ndarray, y: np.ndarray, grid: Sequence[float] = C_GRID) -> Dict[float, float]:
    """Train 내부 5분할 교차검증의 평균 macro F1로 C를 비교한다.

    4개 fold로 학습하고 나머지 1개로 평가하는 일을 5번 바꿔 반복한다.
    단, X는 이미 Train 전체로 어휘·IDF를 만든 값이다. 검증 fold의 비지도 통계가
    미리 반영된 한계가 있다. 엄격한 검증은 fold마다 벡터화도 다시 fit해야 한다.
    여기서는 기존 계산을 유지한다. 이 CV 점수를 완전히 누수 없는 성능으로 읽지 않는다.

    Args:
        X: shape (N_train,V_train) 특성.
        y: shape (N_train,) 정답.
        grid: 비교할 양수 C 값들.

    Returns:
        Dict[float,float]: {C: 5개 검증 F1의 평균}. Test는 이 선택에 쓰지 않는다.
    """
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    return {C: float(cross_val_score(make_model(C), X, y, cv=folds, scoring="f1_macro").mean()) for C in grid}


def run_classification(corpus: Corpus, tf: str = "raw", C: float | None = None) -> ClassificationResult:
    """Train으로 표현·분류를 학습하고 Test에서 한 번 평가한다.

    fit_transform은 어휘와 IDF를 바꾼다. Test에 transform만 해야 Train에서
    보지 못한 단어가 새 열이 되지 않고 최종 Test 분포도 IDF에 섞이지 않는다.
    검색용 전체 corpus 어휘 V와 분류용 V_train은 다를 수 있다.

    Args:
        corpus: 문서·토큰·정답 묶음. 5개 범주가 분할 후에도 존재하는 현재 데이터 전제.
        tf: TF 방식.
        C: None이면 Train CV로 선택. 숫자면 그 값으로 바로 학습.

    Returns:
        ClassificationResult: Train 모델과 Test 지표·예측·확률. corpus는 바꾸지 않는다.
    """
    # 언패킹으로 두 위치 배열을 받는다. N개 문서 → N_train, N_test로 분리한다.
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
    # fit은 w,b를 학습하고 predict는 점수가 가장 큰 범주를 고른다.
    # predict_proba는 (Test 수,5) 확률이지만 TF-IDF 코사인은 문서별 관련도다.
    y_pred = model.predict(X_test)

    # precision=맞춘 해당 범주/그 범주라 예측한 수, recall=맞춘 해당 범주/실제 해당 범주 수.
    # TP=3, FP=1, FN=2이면 P=3/4, R=3/5, F1=2PR/(P+R)=2/3.
    # macro는 다섯 범주 F1을 같은 비중으로 평균. support는 실제 범주 표본 수.
    # zero_division=0은 분모가 0인 지표를 0으로 처리한다.
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
    """오분류의 선형 점수 차이를 단어별 기여로 분해한다.

    예측 p와 실제 a의 점수 차이는 Σ x_j*(w_pj-w_aj)+(b_p-b_a).
    x_j=.4, w_pj=2, w_aj=.5면 기여=.6이다. 양수는 예측 범주,
    음수는 실제 범주를 지지한다. 상위 일부 단어만 반환하며 절편 차이는 표시하지 않는다.
    이는 모델 점수의 산술적 기여다. 그 단어가 현실의 오분류 원인이라는 인과 증거는 아니다.

    Args:
        result: run_classification의 결과. 클래스 번호가 coef_ 행과 대응하는 현재 5범주 전제.
        corpus: 같은 순서의 원문 자료.
        top_terms: 각 방향에서 표시할 최대 단어 수.

    Returns:
        List[dict]: 오분류 ID·실제/예측·확률·단어 기여·원문. Test의 행 순서대로 반환한다.
    """
    coef = result.model.coef_
    terms = result.vectorizer.terms_
    y_true = corpus.labels[result.test_idx]
    cases = []
    # row는 X_test 안의 행, pos=result.test_idx[row]는 Corpus 안의 위치,
    # corpus.doc_ids[pos]는 원래 ID다. 세 번호를 섞으면 다른 글에 오분류 해설을 붙이게 된다.
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
