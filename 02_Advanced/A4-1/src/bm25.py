"""BM25(Okapi) NumPy 구현 — 보너스 2.

    score(q, d) = Σ_{t ∈ q} idf(t) · f(t,d)·(k1 + 1) / (f(t,d) + k1·(1 − b + b·|d|/avgdl))
    idf(t)      = ln((N − df(t) + 0.5) / (df(t) + 0.5) + 1)

- f(t,d): 문서 d에서 t의 빈도, |d|: 문서 길이(토큰 수), avgdl: 평균 문서 길이
- k1: 빈도 포화 정도. f가 커져도 점수는 (k1 + 1)에 수렴한다. TF-IDF의 raw TF는 선형으로 커진다.
- b : 문서 길이 보정 강도. b=0이면 길이를 무시하고, b=1이면 평균 대비 길이로 완전히 나눈다.
- idf 안의 +1은 절반 이상 문서에 나오는 단어의 idf가 음수가 되는 것을 막는다(Lucene 방식).
- 쿼리 안에서 같은 단어가 반복돼도 한 번만 센다(쿼리 빈도 항 k3를 쓰지 않는 형태).
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def fit(self, counts: np.ndarray, doc_lengths: Optional[np.ndarray] = None) -> "BM25":
        """counts: (N, V) 빈도 행렬. doc_lengths를 주지 않으면 어휘 안 토큰 수를 길이로 쓴다."""
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
        """쿼리 단어 번호들에 대한 모든 문서의 점수 (N,). 쿼리 열만 꺼내 계산한다: O(N·|q|)."""
        ids = np.unique(np.asarray(term_ids, dtype=np.intp))
        if ids.size == 0:
            return np.zeros(self.counts_.shape[0])
        tf = self.counts_[:, ids]                                   # (N, |q|)
        saturated = tf * (self.k1 + 1.0) / (tf + self.length_norm_[:, None])
        return saturated @ self.idf_[ids]

    def weight_matrix(self) -> np.ndarray:
        """모든 (문서, 단어) 칸의 BM25 기여도 W. 점수 = 이진 쿼리 벡터 · W[d].

        빈도가 0인 칸의 기여도는 0이므로, 0이 아닌 칸만 계산해 큰 임시 행렬을 만들지 않는다.
        """
        rows, cols = np.nonzero(self.counts_)
        tf = self.counts_[rows, cols]
        weights = np.zeros_like(self.counts_)
        weights[rows, cols] = (
            self.idf_[cols] * tf * (self.k1 + 1.0) / (tf + self.length_norm_[rows])
        )
        return weights
