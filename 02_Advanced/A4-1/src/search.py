"""코사인 유사도 기반 문서 검색.

    cos(q, d) = (q · d) / (‖q‖ × ‖d‖)

함수형 사용(안 B):

    from src.search import search
    search("space shuttle launch")  # -> List[(score, doc_id, text_snippet)]
"""
from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional

import numpy as np

from .bm25 import BM25
from .data import Corpus, load_corpus
from .inverted_index import InvertedIndex
from .preprocess import preprocess
from .tfidf import TfidfVectorizerNP

MIN_DF = 5
MAX_DF = 0.5
SNIPPET_CHARS = 160
METHODS = ("tfidf", "bm25")


class SearchHit(NamedTuple):
    score: float
    doc_id: int
    snippet: str


def cosine_similarity(
    query_vec: np.ndarray, doc_matrix: np.ndarray, doc_norms: Optional[np.ndarray] = None
) -> np.ndarray:
    """쿼리 벡터 하나와 모든 문서의 코사인 유사도 (N,). 길이가 0인 쪽이 있으면 0."""
    dots = doc_matrix @ query_vec                                  # 내적: Σ_t q_t·d_t
    if doc_norms is None:
        doc_norms = np.sqrt(np.einsum("ij,ij->i", doc_matrix, doc_matrix))
    denom = doc_norms * np.sqrt(query_vec @ query_vec)            # ‖d‖ × ‖q‖
    return np.divide(dots, denom, out=np.zeros_like(dots), where=denom > 0)


def top_k(scores: np.ndarray, k: int, positions: Optional[np.ndarray] = None) -> np.ndarray:
    """점수가 0보다 큰 것 중 상위 k개의 위치. 동점은 위치 번호가 작은 쪽이 앞선다."""
    if positions is None:
        positions = np.arange(len(scores))
    mask = scores > 0
    scores, positions = scores[mask], positions[mask]
    order = np.lexsort((positions, -scores))[:k]
    return positions[order]


def make_snippet(text: str, query_tokens: List[str], width: int = SNIPPET_CHARS) -> str:
    """원문에서 쿼리 단어가 처음 나온 곳 주변을 잘라 한 줄로 만든다."""
    flat = re.sub(r"\s+", " ", text).strip()
    lower = flat.lower()
    hits = [m.start() for tok in query_tokens for m in [re.search(rf"\b{re.escape(tok)}", lower)] if m]
    start = max(0, min(hits) - width // 4) if hits else 0
    piece = flat[start:start + width]
    return ("..." if start > 0 else "") + piece + ("..." if start + width < len(flat) else "")


class SearchEngine:
    def __init__(self, corpus: Corpus, min_df: int = MIN_DF, max_df: float = MAX_DF):
        self.corpus = corpus
        self.vectorizer = TfidfVectorizerNP(min_df=min_df, max_df=max_df)
        self.matrix = self.vectorizer.fit_transform(corpus.tokens)
        self.doc_norms = np.sqrt(np.einsum("ij,ij->i", self.matrix, self.matrix))
        self._bm25: Optional[BM25] = None
        self._indexes: Dict[str, InvertedIndex] = {}

    # --- 쿼리 표현 ----------------------------------------------------------
    def query_tokens(self, query: str) -> List[str]:
        return preprocess(query)

    def query_vector(self, query: str) -> np.ndarray:
        """쿼리를 문서와 같은 방식(같은 어휘·IDF·L2)으로 TF-IDF 벡터로 만든다."""
        return self.vectorizer.transform([self.query_tokens(query)])[0]

    def query_term_ids(self, query: str) -> List[int]:
        vocab = self.vectorizer.vocabulary_
        return sorted({vocab[t] for t in self.query_tokens(query) if t in vocab})

    # --- 점수 계산 ----------------------------------------------------------
    @property
    def bm25(self) -> BM25:
        if self._bm25 is None:
            counts = self.vectorizer.counts(self.corpus.tokens)
            lengths = np.array([len(t) for t in self.corpus.tokens], dtype=np.float64)
            self._bm25 = BM25().fit(counts, doc_lengths=lengths)
        return self._bm25

    def index(self, method: str = "tfidf") -> InvertedIndex:
        if method not in self._indexes:
            weights = self.matrix if method == "tfidf" else self.bm25.weight_matrix()
            self._indexes[method] = InvertedIndex(weights, self.vectorizer.terms_)
        return self._indexes[method]

    def scores(self, query: str, method: str = "tfidf") -> np.ndarray:
        """전체 스캔 점수 (N,)."""
        if method == "tfidf":
            return cosine_similarity(self.query_vector(query), self.matrix, self.doc_norms)
        if method == "bm25":
            return self.bm25.score(self.query_term_ids(query))
        raise ValueError(f"알 수 없는 방법: {method} (가능: {METHODS})")

    def index_query(self, query: str, method: str = "tfidf") -> Dict[int, float]:
        if method == "tfidf":
            vec = self.query_vector(query)
            return {int(j): float(vec[j]) for j in np.flatnonzero(vec)}
        return {j: 1.0 for j in self.query_term_ids(query)}

    # --- 검색 ---------------------------------------------------------------
    def search(
        self, query: str, topk: int = 5, method: str = "tfidf", use_index: bool = False
    ) -> List[SearchHit]:
        if use_index:
            positions, values, _ = self.index(method).score(self.index_query(query, method))
            best = top_k(values, topk, positions)
            lookup = dict(zip(positions.tolist(), values.tolist()))
            ranked = [(lookup[p], p) for p in best.tolist()]
        else:
            scores = self.scores(query, method)
            ranked = [(float(scores[p]), int(p)) for p in top_k(scores, topk)]
        tokens = self.query_tokens(query)
        return [
            SearchHit(score, int(self.corpus.doc_ids[p]), make_snippet(self.corpus.texts[p], tokens))
            for score, p in ranked
        ]

    def position(self, doc_id: int) -> int:
        return int(np.searchsorted(self.corpus.doc_ids, doc_id))

    def explain(self, query: str, doc_id: int) -> dict:
        """코사인 유사도 계산 과정: 겹치는 단어별 곱, 내적, 두 노름."""
        q = self.query_vector(query)
        d = self.matrix[self.position(doc_id)]
        shared = np.flatnonzero((q > 0) & (d > 0))
        terms = self.vectorizer.terms_
        dot = float(q @ d)
        q_norm, d_norm = float(np.linalg.norm(q)), float(np.linalg.norm(d))
        return {
            "query_terms": {terms[j]: float(q[j]) for j in np.flatnonzero(q)},
            "shared": [(terms[j], float(q[j]), float(d[j]), float(q[j] * d[j])) for j in shared],
            "dot": dot,
            "query_norm": q_norm,
            "doc_norm": d_norm,
            "cosine": dot / (q_norm * d_norm) if q_norm and d_norm else 0.0,
            "doc_nonzero": int(np.count_nonzero(d)),
        }


_default_engine: Optional[SearchEngine] = None


def default_engine() -> SearchEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = SearchEngine(load_corpus())
    return _default_engine


def search(query: str, topk: int = 5, method: str = "tfidf") -> List[SearchHit]:
    """search(query: str) -> List[(score, doc_id, text_snippet)] — 안 B 함수 시그니처."""
    return default_engine().search(query, topk=topk, method=method)
