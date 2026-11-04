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
    """검색 결과 한 건을 담는 이름 있는 튜플.

    h.score처럼 이름으로 읽거나 score, doc_id, snippet = h로 세 값을 나눠 받는다.
    score는 방법별 관련도 수치이며 정답 확률이 아니다.

    Attributes:
        score: TF-IDF 코사인 또는 BM25 점수. 두 방법의 절대 크기는 직접 비교하지 않는다.
        doc_id: 필터링 전 원래 ID. 행렬의 행 번호와 구분한다.
        snippet: 본문 일부 문자열. 요약 모델의 생성 문장이 아니다.
    """
    score: float
    doc_id: int
    snippet: str


def cosine_similarity(
    query_vec: np.ndarray, doc_matrix: np.ndarray, doc_norms: Optional[np.ndarray] = None
) -> np.ndarray:
    """한 질의와 모든 문서의 방향 유사도를 계산한다.

    q=[1,2,0], d=[2,4,0]이면 내적=10, 길이는 sqrt(5), sqrt(20).
    10/(sqrt(5)*sqrt(20))=1. d=[0,0,3]이면 겹친 칸이 없어 0이다.
    비음수 TF-IDF에서는 0~1 범위지만 의미가 같을 확률은 아니다.

    Args:
        query_vec: shape (V,) 질의. 문서와 같은 열 순서여야 한다.
        doc_matrix: shape (N,V) 문서 행렬. L2가 아니어도 길이로 나누어 계산한다.
        doc_norms: 미리 계산한 shape (N,) 문서 L2 길이. None이면 여기서 계산한다.

    Returns:
        np.ndarray: shape (N,) 점수. 수학상 정의되지 않는 0벡터의 코사인은 0으로 처리한다.
    """
    # @는 행렬 곱. 각 문서 행과 질의의 같은 열끼리 곱해 합한다: (N,V) @ (V,) → (N,).
    dots = doc_matrix @ query_vec                                  # 내적: Σ_t q_t·d_t
    if doc_norms is None:
        doc_norms = np.sqrt(np.einsum("ij,ij->i", doc_matrix, doc_matrix))
    denom = doc_norms * np.sqrt(query_vec @ query_vec)            # ‖d‖ × ‖q‖
    return np.divide(dots, denom, out=np.zeros_like(dots), where=denom > 0)


def top_k(scores: np.ndarray, k: int, positions: Optional[np.ndarray] = None) -> np.ndarray:
    """양수 점수의 문서 위치를 높은 점수 순으로 최대 k개 반환한다.

    scores=[.2,.9,0,.9]이면 k=3 결과는 [1,3,0]. 0점은 빼고 동점은 작은 위치 먼저다.
    역색인은 후보만 주므로 positions로 후보 배열의 칸을 실제 문서 위치에 연결한다.

    Args:
        scores: shape (M,) 전체 문서 또는 후보 점수.
        k: 최대 결과 수. 호출자는 양의 정수를 준다(음수 검증은 없다).
        positions: shape (M,) scores 각 칸에 대응하는 문서 위치. None이면 0..M-1.

    Returns:
        np.ndarray: 최대 k개의 문서 위치. 이 값은 원래 doc_id가 아니다.
    """
    if positions is None:
        positions = np.arange(len(scores))
    mask = scores > 0
    scores, positions = scores[mask], positions[mask]
    # lexsort는 마지막 키를 우선한다. -scores로 큰 점수를 먼저, 동점이면 positions로 작은 위치 먼저.
    order = np.lexsort((positions, -scores))[:k]
    return positions[order]


def make_snippet(text: str, query_tokens: List[str], width: int = SNIPPET_CHARS) -> str:
    """원문의 첫 질의 단어 근처를 한 줄 발췌한다.

    정제 토큰의 시작을 원문에서 다시 찾는 단순 방식이다. colour→color 변형은
    원문에 color가 없어 위치를 놓칠 수 있다. 의미상 가장 좋은 문장을 고르는 기능은 아니다.

    Args:
        text: 원문. 여기서는 이메일 가리기를 하지 않는다.
        query_tokens: 전처리한 질의 단어 목록.
        width: 본문에서 가져올 최대 문자 수. ... 표시는 별도로 더해질 수 있다.

    Returns:
        str: 찾은 위치 앞쪽 여유를 둔 발췌. 매칭이 없으면 처음부터 자른다.
    """
    flat = re.sub(r"\s+", " ", text).strip()
    lower = flat.lower()
    # 중첩 컴프리헨션: 토큰마다 정규식 결과 m을 얻고 성공한 것의 시작 위치만 모은다.
    # rf"..."는 raw 문자열에 {값}도 삽입한다. re.escape는 토큰의 특수문자를 문자 그대로 찾게 한다.
    hits = [m.start() for tok in query_tokens for m in [re.search(rf"\b{re.escape(tok)}", lower)] if m]
    start = max(0, min(hits) - width // 4) if hits else 0
    piece = flat[start:start + width]
    return ("..." if start > 0 else "") + piece + ("..." if start + width < len(flat) else "")


class SearchEngine:
    """공통 어휘·문서 행렬을 한 번 준비해 여러 검색에서 재사용한다.

    일반 검색은 전체 corpus로 어휘·IDF를 만든다. 분류·검색 성능 평가는 별도 학습
    분할로 준비하므로 여기의 전체 문서 검색과 혼동하지 않는다.
    BM25와 역색인은 실제 요청할 때 만들고 객체 안에 보관한다(지연 생성).

    Attributes:
        corpus: 위치로 연결된 문서·정답·ID 묶음.
        vectorizer: 어휘와 IDF를 보관하는 객체.
        matrix: shape (N,V) L2 정규화 문서 TF-IDF.
        doc_norms: shape (N,) 문서 길이. 0벡터는 0, 나머지는 약 1.
    """
    def __init__(self, corpus: Corpus, min_df: int = MIN_DF, max_df: float = MAX_DF):
        """문서 전부의 어휘·TF-IDF·길이를 계산해 검색 준비를 한다.

        Args:
            corpus: 전처리된 Corpus. 원래 ID는 오름차순이어야 position이 동작한다.
            min_df: 최소 출현 문서 수. 기본 5.
            max_df: 최대 출현 비율. 기본 .5.
        """
        self.corpus = corpus
        self.vectorizer = TfidfVectorizerNP(min_df=min_df, max_df=max_df)
        self.matrix = self.vectorizer.fit_transform(corpus.tokens)
        self.doc_norms = np.sqrt(np.einsum("ij,ij->i", self.matrix, self.matrix))
        self._bm25: Optional[BM25] = None
        self._indexes: Dict[str, InvertedIndex] = {}

    # --- 쿼리 표현 ----------------------------------------------------------
    def query_tokens(self, query: str) -> List[str]:
        """문서와 같은 전처리 함수를 질의에도 적용한다.

        Args:
            query: 영어 검색어 문자열.

        Returns:
            List[str]: 중복을 유지하는 토큰 목록.
        """
        return preprocess(query)

    def query_vector(self, query: str) -> np.ndarray:
        """질의를 문서와 같은 어휘·IDF·L2 기준으로 바꾼다.

        Args:
            query: 영어 검색어.

        Returns:
            np.ndarray: shape (V,). [tokens]로 한 문서 묶음 (1,V)을 만든 뒤
            [0]으로 첫 행을 꺼낸다. 새 단어만 있으면 0벡터다.
        """
        return self.vectorizer.transform([self.query_tokens(query)])[0]

    def query_term_ids(self, query: str) -> List[int]:
        """어휘에 있는 질의 단어의 열 번호를 중복 없이 모은다.

        Args:
            query: 검색어. BM25는 같은 단어 반복을 한 번만 센다.

        Returns:
            List[int]: 정렬된 열 번호. {} 안의 식과 for는 집합 컴프리헨션이다.
        """
        vocab = self.vectorizer.vocabulary_
        return sorted({vocab[t] for t in self.query_tokens(query) if t in vocab})

    # --- 점수 계산 ----------------------------------------------------------
    @property
    def bm25(self) -> BM25:
        """필요한 첫 접근 때 BM25 통계를 만들고 이후에는 재사용한다.

        @property 덕분에 engine.bm25처럼 괄호 없이 읽지만 이 메서드가 실행된다.
        길이는 min_df/max_df로 어휘를 거르기 전, 전처리 후 전체 토큰 수다.

        Returns:
            BM25: counts와 전체 전처리 길이로 학습한 객체.
        """
        if self._bm25 is None:
            counts = self.vectorizer.counts(self.corpus.tokens)
            lengths = np.array([len(t) for t in self.corpus.tokens], dtype=np.float64)
            self._bm25 = BM25().fit(counts, doc_lengths=lengths)
        return self._bm25

    def index(self, method: str = "tfidf") -> InvertedIndex:
        """선택한 점수 행렬에서 역색인을 만들거나 재사용한다.

        Args:
            method: tfidf 또는 bm25. 이 내부 경로는 값 검증을 별도로 하지 않으므로
                지정된 두 값만 준다. scores와 달리 다른 문자열도 BM25 분기로 들어간다.

        Returns:
            InvertedIndex: 문서 위치·가중치 목록을 단어별로 보관한 객체.
        """
        if method not in self._indexes:
            weights = self.matrix if method == "tfidf" else self.bm25.weight_matrix()
            self._indexes[method] = InvertedIndex(weights, self.vectorizer.terms_)
        return self._indexes[method]

    def scores(self, query: str, method: str = "tfidf") -> np.ndarray:
        """전체 문서의 점수를 계산한다.

        Args:
            query: 검색어 문자열.
            method: tfidf 또는 bm25.

        Returns:
            np.ndarray: shape (N,) 문서 위치별 점수. 아직 정렬하지 않았다.

        Raises:
            ValueError: 지원하지 않는 method.
        """
        if method == "tfidf":
            return cosine_similarity(self.query_vector(query), self.matrix, self.doc_norms)
        if method == "bm25":
            return self.bm25.score(self.query_term_ids(query))
        raise ValueError(f"알 수 없는 방법: {method} (가능: {METHODS})")

    def index_query(self, query: str, method: str = "tfidf") -> Dict[int, float]:
        """역색인에 전달할 질의의 0 아닌 열만 모은다.

        Args:
            query: 영어 검색어.
            method: tfidf 또는 bm25만 사용한다. 별도 값 검증은 없다.

        Returns:
            Dict[int,float]: TF-IDF는 {열: 정규화 가중치}, BM25는 {열: 1.0}.
            예: [0,.6,.8] → {1:.6,2:.8}.
        """
        if method == "tfidf":
            vec = self.query_vector(query)
            return {int(j): float(vec[j]) for j in np.flatnonzero(vec)}
        return {j: 1.0 for j in self.query_term_ids(query)}

    # --- 검색 ---------------------------------------------------------------
    def search(
        self, query: str, topk: int = 5, method: str = "tfidf", use_index: bool = False
    ) -> List[SearchHit]:
        """점수 계산 → top-k → 원래 ID·본문 연결을 수행한다.

        예상 질문: corpus.doc_ids=[0,2]에서 best=[1]이면 결과 ID는?
        답: 2다. 1은 남은 문서 행렬의 위치이고 원래 ID와 다르다.

        Args:
            query: 영어 검색어.
            topk: 최대 반환 수. 양의 정수를 사용한다.
            method: tfidf 또는 bm25.
            use_index: True면 후보 포스팅만, False면 전체 문서를 계산한다.

        Returns:
            List[SearchHit]: 순위별 (점수, 원래 ID, 발췌). 양수 결과가 없으면 [].
            index의 합산과 전체 계산은 부동소수점 마지막 자리에서 차이가 날 수 있다.
        """
        if use_index:
            positions, values, _ = self.index(method).score(self.index_query(query, method))
            best = top_k(values, topk, positions)
            # zip은 위치와 점수를 짝짓고 dict는 {위치:점수} 조회표를 만든다.
            # 후보 배열에서의 순번이 아닌 실제 문서 위치 p로 결과를 다시 연결한다.
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
        """오름차순 원래 ID 목록에서 ID의 위치를 찾는다.

        Args:
            doc_id: 반드시 corpus에 존재하는 ID를 준다.

        Returns:
            int: searchsorted가 찾는 삽입 위치. ID 존재 여부는 검사하지 않는다.
            미등록 ID도 이웃의 위치를 줄 수 있으므로 일반 ID 검증 함수로 쓰지 않는다.
        """
        return int(np.searchsorted(self.corpus.doc_ids, doc_id))

    def explain(self, query: str, doc_id: int) -> dict:
        """질의와 한 문서의 코사인을 단어별 곱으로 분해한다.

        Args:
            query: 검색어.
            doc_id: corpus에 실제 존재하는 원래 ID.

        Returns:
            dict: query_terms, shared(단어·질의값·문서값·곱), dot(곱의 합),
            query_norm, doc_norm, cosine, doc_nonzero. BM25 해설과는 별도다.
        """
        q = self.query_vector(query)
        d = self.matrix[self.position(doc_id)]
        # &는 배열의 원소별 AND. flatnonzero는 True/0 아닌 칸의 위치를 반환한다.
        # 겹치지 않는 칸의 곱은 0이므로 shared만 표시해도 내적의 양수 기여를 전부 볼 수 있다.
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
    """함수형 검색을 위한 기본 엔진을 최초 한 번만 만든다.

    global은 모듈 바깥이 아닌 이 모듈의 _default_engine 변수에 대입하겠다는 선언이다.
    이후 search 호출도 이 엔진을 재사용한다. 캐시를 자동 갱신하는 기능은 없다.

    Returns:
        SearchEngine: 같은 프로세스에서 재사용하는 객체.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = SearchEngine(load_corpus())
    return _default_engine


def search(query: str, topk: int = 5, method: str = "tfidf") -> List[SearchHit]:
    """문자열만으로 검색하는 함수형 진입점이다.

    Args:
        query: 검색어.
        topk: 최대 결과 수(양의 정수).
        method: tfidf 또는 bm25.

    Returns:
        List[SearchHit]: 기본 엔진이 반환한 검색 결과.
    """
    return default_engine().search(query, topk=topk, method=method)
