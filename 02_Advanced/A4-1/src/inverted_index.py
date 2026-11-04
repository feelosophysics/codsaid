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
    """단어에서 문서 위치와 가중치를 찾는 역방향 조회 구조.

    일반 행렬은 문서→단어를 읽는다. 역색인은 단어→문서 목록(포스팅)을 저장한다.
    모듈 앞의 '문서 ID' 표기는 여기서는 Corpus 행 위치를 뜻한다. 최종 원래 ID 변환은
    SearchEngine.search에서 한다. 빈도·정규화·BM25를 새로 학습하는 단계가 아니다.

    Attributes:
        n_docs: 전체 문서 수.
        terms: 열 순서의 단어 목록.
        term_index: 단어에서 열 번호를 찾는 dict.
        postings: 열마다 (문서 위치 배열, 가중치 배열) 튜플.
    """
    def __init__(self, weights: np.ndarray, terms: Sequence[str]):
        """가중치 행렬을 단어별 포스팅 목록으로 재배치한다.

        W=[[.6,0],[.8,1],[0,.5]]이면 열0→([0,1],[.6,.8]),
        열1→([1,2],[1,.5]). 원래 행렬을 전치해 단어 순서로 0 아닌 좌표를 읽는다.
        전치는 행·열의 역할을 바꾸는 것으로 값을 재학습하거나 정규화하지 않는다.

        Args:
            weights: shape (N,V) 점수 기여도. 코사인 등가에는 L2 TF-IDF를 사용한다.
            terms: 길이 V의 단어 목록. 열 순서와 정확히 일치해야 한다.
        """
        self.n_docs = weights.shape[0]
        self.terms = list(terms)
        self.term_index = {term: j for j, term in enumerate(self.terms)}
        # 전치 행렬에서 0이 아닌 칸을 찾으면 (단어, 문서) 순으로 정렬된 좌표가 나온다.
        term_pos, doc_pos = np.nonzero(weights.T)
        values = weights[doc_pos, term_pos]
        # term_pos=[0,0,1,1]에서 0,1,2의 삽입 위치는 [0,2,4].
        # 단어 j의 구간은 bounds[j]:bounds[j+1]. 슬라이스 끝은 포함하지 않는다.
        bounds = np.searchsorted(term_pos, np.arange(len(self.terms) + 1))
        self.postings: List[Tuple[np.ndarray, np.ndarray]] = [
            (doc_pos[bounds[j]:bounds[j + 1]].astype(np.int32), values[bounds[j]:bounds[j + 1]])
            for j in range(len(self.terms))
        ]

    def documents(self, term: str) -> np.ndarray:
        """단어가 나타나는 문서 위치만 조회한다.

        Args:
            term: 이미 전처리된 정확한 어휘 문자열. 여기서는 전처리하지 않는다.

        Returns:
            np.ndarray: 위치 목록. 미등록 단어는 빈 int32 배열.
        """
        j = self.term_index.get(term)
        return self.postings[j][0] if j is not None else np.empty(0, dtype=np.int32)

    def posting_lengths(self) -> np.ndarray:
        """단어별 포스팅 수를 반환한다.

        Returns:
            np.ndarray: shape (V,). 비음수 TF-IDF에서 단어별 출현 문서 수에 대응한다.
        """
        return np.array([len(ids) for ids, _ in self.postings])

    def score(self, query: Dict[int, float]) -> Tuple[np.ndarray, np.ndarray, int]:
        """질의 단어 포스팅만 방문해 후보별 곱의 합을 구한다.

        위 W에서 query={0:.5,1:1}이면 docs=[0,1,1,2], 기여=[.3,.4,1,.5].
        unique의 candidates=[0,1,2], inverse=[0,1,1,2]이고 bincount로
        같은 문서의 기여를 합쳐 scores=[.3,1.4,.5]가 된다.
        예상 질문: 방문 수는 후보 수 3일까? 답: 포스팅 4개다. 문서1을 두 번 방문한다.

        Args:
            query: {유효한 열 번호: 질의 가중치}. TF-IDF는 정규화값, BM25는 1.

        Returns:
            tuple: (후보 위치 shape (P,), 점수 shape (P,), 방문 포스팅 수).
            빈 질의는 빈 배열 두 개와 0. 정렬은 위치순이며 점수 순위는 top_k가 정한다.
        """
        doc_parts, score_parts = [], []
        for j, q_weight in query.items():
            ids, values = self.postings[j]
            doc_parts.append(ids)
            score_parts.append(q_weight * values)
        if not doc_parts:
            return np.empty(0, dtype=np.int32), np.empty(0), 0
        docs = np.concatenate(doc_parts)
        contrib = np.concatenate(score_parts)
        # return_inverse=True는 각 방문 문서가 candidates의 몇 번째인지도 반환한다.
        # bincount의 weights는 빈도 대신 실제 점수 기여를 합산하게 한다.
        candidates, inverse = np.unique(docs, return_inverse=True)
        scores = np.bincount(inverse, weights=contrib, minlength=len(candidates))
        return candidates, scores, len(docs)
