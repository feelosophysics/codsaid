"""역색인(Inverted Index) — 보너스 3.

    단어 → [(문서 ID, 가중치), ...]

전체 스캔은 쿼리마다 모든 문서와 점수를 계산한다. 역색인은 쿼리 단어가 실제로 들어 있는
문서(포스팅)만 방문한다.

    전체 스캔(dense 행렬·벡터 곱)  : O(N · V)
    전체 스캔(쿼리 열만 선택)      : O(N · |q|)
    역색인                          : O(Σ_{t∈q} df(t))  + 후보 정렬 O(P log P)

점수가 Σ_t q_t · W[d, t] 꼴이면 어떤 가중치든 쓸 수 있다.
- TF-IDF 코사인: W = L2 정규화한 TF-IDF 행렬, q = L2 정규화한 쿼리 벡터
- BM25         : W = BM25 기여도 행렬,         q = 쿼리 단어 존재 여부(0/1)
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np


class InvertedIndex:
    def __init__(self, weights: np.ndarray, terms: Sequence[str]):
        """weights: (N, V) 가중치 행렬. 0이 아닌 칸만 포스팅으로 저장한다."""
        self.n_docs = weights.shape[0]
        self.terms = list(terms)
        self.term_index = {term: j for j, term in enumerate(self.terms)}
        # 전치 행렬에서 0이 아닌 칸을 찾으면 (단어, 문서) 순으로 정렬된 좌표가 나온다.
        term_pos, doc_pos = np.nonzero(weights.T)
        values = weights[doc_pos, term_pos]
        bounds = np.searchsorted(term_pos, np.arange(len(self.terms) + 1))
        self.postings: List[Tuple[np.ndarray, np.ndarray]] = [
            (doc_pos[bounds[j]:bounds[j + 1]].astype(np.int32), values[bounds[j]:bounds[j + 1]])
            for j in range(len(self.terms))
        ]

    def documents(self, term: str) -> np.ndarray:
        """단어 → 문서 위치 번호 리스트."""
        j = self.term_index.get(term)
        return self.postings[j][0] if j is not None else np.empty(0, dtype=np.int32)

    def posting_lengths(self) -> np.ndarray:
        return np.array([len(ids) for ids, _ in self.postings])

    def score(self, query: Dict[int, float]) -> Tuple[np.ndarray, np.ndarray, int]:
        """{단어 번호: 쿼리 가중치} → (후보 문서 번호, 점수, 방문한 포스팅 수)."""
        doc_parts, score_parts = [], []
        for j, q_weight in query.items():
            ids, values = self.postings[j]
            doc_parts.append(ids)
            score_parts.append(q_weight * values)
        if not doc_parts:
            return np.empty(0, dtype=np.int32), np.empty(0), 0
        docs = np.concatenate(doc_parts)
        contrib = np.concatenate(score_parts)
        candidates, inverse = np.unique(docs, return_inverse=True)
        scores = np.bincount(inverse, weights=contrib, minlength=len(candidates))
        return candidates, scores, len(docs)
