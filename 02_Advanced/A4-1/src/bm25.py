"""BM25(Okapi) NumPy 구현 — 보너스 2.

    score(q, d) = Σ_{t ∈ q} idf(t) · f(t,d)·(k1 + 1) / (f(t,d) + k1·(1 − b + b·|d|/avgdl))
    idf(t)      = ln((N − df(t) + 0.5) / (df(t) + 0.5) + 1)

- f(t,d): 문서 d에서 t의 빈도, |d|: 문서 길이(토큰 수), avgdl: 평균 문서 길이
- k1: 빈도 포화 정도. 고정 길이에서 빈도 항이 (k1 + 1)에 수렴한다. 단어 기여에는 IDF도 곱한다.
- b : 문서 길이 보정 강도. b=0이면 길이를 무시하고, b=1이면 분모 보정 항이 길이/평균길이에 비례한다.
- idf 안의 +1은 절반 이상 문서에 나오는 단어의 idf가 음수가 되는 것을 막는다(Lucene 방식).
- 쿼리 안에서 같은 단어가 반복돼도 한 번만 센다(쿼리 빈도 항 k3를 쓰지 않는 형태).
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


class BM25:
    """단어 빈도 포화와 문서 길이 보정을 함께 적용하는 검색 점수 모델.

    TF-IDF와 달리 L2 정규화를 하지 않고 단어별 기여도를 합한다.
    빈도 항 f*(k1+1)/(f+k1*(1-b+b*길이/평균길이))이 핵심이다.
    b=0은 길이 보정 없음, b=1은 분모의 길이 기준을 길이/평균길이에 비례시킨다.
    전체 점수를 단순히 문서 길이로 나누는 공식은 아니다.

    Attributes:
        counts_: shape (N,V) 빈도(입력 배열 참조를 보관).
        doc_len_: shape (N,) 문서 길이.
        avgdl_: 평균 문서 길이.
        df_: shape (V,) 출현 문서 수.
        idf_: shape (V,) BM25용 IDF. TF-IDF용 공식과 다르다.
        length_norm_: shape (N,) 문서마다 고정한 분모 보정 항.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """BM25의 빈도 포화·길이 보정 설정을 저장한다.

        Args:
            k1: 양수 포화 계수. 기본 1.5. 여기서는 유효성 검사를 따로 하지 않는다.
            b: 0~1 길이 보정 강도. 기본 .75.
        """
        self.k1 = k1
        self.b = b

    def fit(self, counts: np.ndarray, doc_lengths: Optional[np.ndarray] = None) -> "BM25":
        """빈도 행렬에서 IDF와 문서별 길이 보정 항을 저장한다.

        작은 예 counts=[[2,0],[1,1],[0,3]], 길이=[2,2,3], 평균=7/3.
        두 단어 df=2라 IDF=ln((3-2+.5)/(2+.5)+1)=ln(1.6)≈.470004.
        첫 문서 length_norm=1.5*(.25+.75*2/(7/3))≈1.339286.

        Args:
            counts: shape (N,V) 비음수 빈도. N>0, 평균 길이>0, k1>0을 전제한다.
            doc_lengths: shape (N,) 길이. 생략하면 counts 행 합을 사용한다.
                검색 엔진은 어휘 필터 전의 전처리 토큰 수를 별도로 넘긴다.

        Returns:
            BM25: self. 통계를 객체 안에 저장한다. 입력 counts는 복사하지 않는다.
        """
        self.counts_ = counts
        self.doc_len_ = (
            counts.sum(axis=1) if doc_lengths is None else np.asarray(doc_lengths, dtype=np.float64)
        )
        self.avgdl_ = float(self.doc_len_.mean())
        n_docs = counts.shape[0]
        self.df_ = (counts > 0).sum(axis=0)
        self.idf_ = np.log((n_docs - self.df_ + 0.5) / (self.df_ + 0.5) + 1.0)
        # 문서마다 고정인 분모 항 k1·(1 − b + b·|d|/avgdl)
        self.length_norm_ = self.k1 * (1.0 - self.b + self.b * self.doc_len_ / self.avgdl_)
        return self

    def score(self, term_ids: Sequence[int]) -> np.ndarray:
        """질의의 서로 다른 단어에 대한 기여도를 모든 문서에서 더한다.

        fit 예의 첫 문서·첫 단어: .470004*2*2.5/(2+1.339286)≈.703749.
        같은 단어를 질의에 두 번 써도 unique가 한 번으로 만든다.
        고정 길이에서 f가 커지면 빈도 항이 k1+1에 접근하며, IDF 곱까지 한
        단어 기여도의 상한은 IDF*(k1+1)이다. 전체 점수는 여러 단어의 합이다.

        Args:
            term_ids: 학습 어휘의 유효한 열 번호들. 먼저 fit을 호출한다.

        Returns:
            np.ndarray: shape (N,) 점수. 빈 질의는 전부 0. 확률이나 코사인이 아니다.
        """
        ids = np.unique(np.asarray(term_ids, dtype=np.intp))
        if ids.size == 0:
            return np.zeros(self.counts_.shape[0])
        # [:,ids]는 모든 문서에서 질의 열만 꺼낸다. (N,V) → (N,서로 다른 질의 단어 수).
        tf = self.counts_[:, ids]                                   # (N, |q|)
        # length_norm_[:,None]은 (N,) → (N,1). 각 문서의 같은 보정 항을 질의의 모든 열에 적용한다.
        saturated = tf * (self.k1 + 1.0) / (tf + self.length_norm_[:, None])
        return saturated @ self.idf_[ids]

    def weight_matrix(self) -> np.ndarray:
        """모든 문서·단어 기여도를 한 번 계산해 역색인 입력으로 만든다.

        Args 없이 학습한 통계를 사용한다. 0 아닌 좌표만 계산하되 반환 행렬 자체는
        (N,V)의 dense 배열이다. 메모리 전체를 희소 형식으로 줄인 구현은 아니다.

        Returns:
            np.ndarray: shape (N,V) 기여도 W. 이진 질의 q와 W @ q가 score와 같다.
        """
        # nonzero는 0 아닌 칸의 행·열 위치를 따로 준다. counts_[rows,cols]는
        # 좌표를 하나씩 짝지어 읽는 방식이며 counts_[:,ids]의 열 선택과 다르다.
        rows, cols = np.nonzero(self.counts_)
        tf = self.counts_[rows, cols]
        weights = np.zeros_like(self.counts_)
        weights[rows, cols] = (
            self.idf_[cols] * tf * (self.k1 + 1.0) / (tf + self.length_norm_[rows])
        )
        return weights
