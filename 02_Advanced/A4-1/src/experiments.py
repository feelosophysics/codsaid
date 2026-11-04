"""검증과 실험: sklearn 대조, 검색 평가, TF 변형, BM25, 역색인, BoW 한계."""
from __future__ import annotations

import time
from itertools import product
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np

from .bm25 import BM25
from .data import RANDOM_STATE, Corpus
from .inverted_index import InvertedIndex
from .search import MAX_DF, MIN_DF, SearchEngine, cosine_similarity, top_k
from .tfidf import TF_VARIANTS, TfidfVectorizerNP

# 직접 만든 평가 쿼리 20개(범주당 4개). 결과 문서의 범주가 의도한 범주와 같으면 관련 문서로 본다.
HAND_QUERIES: List[Tuple[str, str]] = [
    ("3d rendering software", "comp.graphics"),
    ("convert gif to jpeg image format", "comp.graphics"),
    ("polygon shading algorithm", "comp.graphics"),
    ("vga graphics card driver", "comp.graphics"),
    ("x window server display", "comp.windows.x"),
    ("motif widget toolkit", "comp.windows.x"),
    ("xterm font resource", "comp.windows.x"),
    ("window manager configuration", "comp.windows.x"),
    ("pitcher earned run average", "rec.sport.baseball"),
    ("home run hitter batting", "rec.sport.baseball"),
    ("world series yankees", "rec.sport.baseball"),
    ("spring training roster", "rec.sport.baseball"),
    ("hockey playoff goalie", "rec.sport.hockey"),
    ("stanley cup finals", "rec.sport.hockey"),
    ("power play penalty", "rec.sport.hockey"),
    ("nhl draft pick", "rec.sport.hockey"),
    ("space shuttle launch", "sci.space"),
    ("nasa orbit satellite", "sci.space"),
    ("moon base mission cost", "sci.space"),
    ("rocket engine propulsion", "sci.space"),
]

SKLEARN_CONFIGS = [
    dict(smooth_idf=s, sublinear_tf=sub, norm=n, binary=False)
    for s, sub, n in product((True, False), (False, True), ("l2", "l1", None))
] + [dict(smooth_idf=True, sublinear_tf=False, norm="l2", binary=True)]


# --------------------------------------------------------------------------- 검증
def verify_against_sklearn(tokens: Sequence[Sequence[str]], tol: float = 1e-6) -> List[dict]:
    """동일 토큰·설정으로 직접 구현과 sklearn을 대조한다.

    product는 평활화 2×TF 2×정규화 3=12조합을 만들고 binary 한 조합을 더한다.
    analyzer=lambda doc: doc는 이미 전처리한 토큰을 그대로 반환하는 익명 함수다.
    toarray는 sklearn 희소 행렬을 직접 구현과 같은 dense 배열로 바꾼다.

    Args:
        tokens: 실제 문서의 토큰 목록. 빈 어휘가 되지 않을 만큼 문서가 있어야 한다.
        tol: 허용 최대 오차.

    Returns:
        List[dict]: 13개 설정의 어휘 동일 여부·IDF/행렬 오차·pass.
        pass 필드는 행렬 최대 오차 기준이며 어휘·IDF 비교값도 함께 확인한다.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    rows = []
    for cfg in SKLEARN_CONFIGS:
        tf = "binary" if cfg["binary"] else ("log" if cfg["sublinear_tf"] else "raw")
        ours = TfidfVectorizerNP(tf=tf, smooth_idf=cfg["smooth_idf"], norm=cfg["norm"],
                                 min_df=MIN_DF, max_df=MAX_DF)
        X = ours.fit_transform(tokens)
        ref = TfidfVectorizer(analyzer=lambda doc: doc, min_df=MIN_DF, max_df=MAX_DF,
                              dtype=np.float64, **cfg)
        R = ref.fit_transform(tokens).toarray()
        diff = np.abs(X - R)
        rows.append({
            "ours": {"tf": tf, "smooth_idf": cfg["smooth_idf"], "norm": cfg["norm"]},
            "sklearn": {**cfg, "analyzer": "같은 토큰 리스트", "min_df": MIN_DF, "max_df": MAX_DF},
            "shape": list(X.shape),
            "vocabulary_equal": list(ref.get_feature_names_out()) == ours.terms_,
            "idf_max_error": float(np.abs(ours.idf_ - ref.idf_).max()),
            "max_error": float(diff.max()),
            "mean_error": float(diff.mean()),
            "pass": bool(diff.max() < tol),
        })
        del X, R, diff
    return rows


def verify_cosine(engine: SearchEngine, queries: Sequence[str]) -> float:
    """같은 문서·질의 벡터에서 sklearn 코사인과 최대 차이를 잰다.

    Args:
        engine: 준비한 전체 문서 검색 엔진.
        queries: 비교할 문자열 목록.

    Returns:
        float: 모든 질의·문서 점수 차이 중 최댓값.
    """
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

    worst = 0.0
    for q in queries:
        vec = engine.query_vector(q)
        ours = cosine_similarity(vec, engine.matrix, engine.doc_norms)
        ref = sk_cosine(vec[None, :], engine.matrix)[0]
        worst = max(worst, float(np.abs(ours - ref).max()))
    return worst


# --------------------------------------------------------------------------- 검색 평가
def precision_at(retrieved: np.ndarray, relevant: np.ndarray, k: int) -> float:
    """검색된 범주 중 relevant와 같은 비율을 구한다.

    Args:
        retrieved: 순위순 범주 번호 배열.
        relevant: 이름과 달리 보통 비교할 범주 번호 하나(브로드캐스팅 가능 값).
        k: 앞에서 볼 개수.

    Returns:
        float: 앞 min(k,결과 수)개의 일치율. k=0이면 0.
        결과가 k개보다 적어도 분모는 k가 아닌 실제 반환 수다. 빈 결과에 k>0이면 nan 가능.
    """
    return float(np.mean(retrieved[:k] == relevant)) if k else 0.0


def average_precision_at(hits: np.ndarray, n_relevant: int, k: int) -> float:
    """관련 문서가 일찍 나올수록 높은 AP@k를 계산한다.

    hits=[1,0,1], n_relevant=2, k=3이면 누적 정밀도=[1,1/2,2/3].
    관련 위치만 합쳐 (1+2/3)/min(3,2)=5/6이다. 관련 순서 [0,1,1]보다 높다.

    Args:
        hits: 순위순 관련 여부 0/1 배열.
        n_relevant: 전체 검색 대상에서 관련 문서 수.
        k: 양의 평가 순위 한도. 함수는 k=0을 별도로 방어하지 않는다.

    Returns:
        float: AP@k. n_relevant=0이면 0.
    """
    hits = hits[:k]
    if n_relevant == 0:
        return 0.0
    cum = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float((cum * hits).sum() / min(k, n_relevant))


def rank_matrix(scores: np.ndarray, k: int) -> np.ndarray:
    """여러 질의 점수에서 행마다 상위 k개 문서 열 번호를 구한다.

    Args:
        scores: (질의 수 Q, 문서 수 D) 점수. 검색어가 아닌 문서 전체를 질의로 쓸 때도 같다.
        k: 0<k<D 전제. argpartition의 kth=k가 범위 안이어야 한다.

    Returns:
        np.ndarray: (Q,k) 위치. argpartition은 상위 후보만 분리하고 그 안을 재정렬한다.
        top_k와 달리 0점도 포함하며 경계 동점의 문서 위치 순서를 보장하지 않는다.
    """
    # argpartition은 전체 정렬 대신 상위 k개 후보를 앞에 모은다.
    # take_along_axis는 행마다 서로 다른 후보 열 위치로 값을 꺼낸다.
    part = np.argpartition(-scores, k, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(scores, part, axis=1), axis=1, kind="stable")
    return np.take_along_axis(part, order, axis=1)


def evaluate_doc_queries(scores: np.ndarray, q_labels: np.ndarray, d_labels: np.ndarray, k: int = 10) -> dict:
    """Test 문서를 질의로 삼아 Train 문서 검색 성능을 집계한다.

    같은 범주면 관련 있다고 간주한다. 실제 질의 의도별 관련성 판정이 아니므로 대리 지표다.
    Q @ D.T는 (Q,V) @ (V,D) → (Q,D). 문서·질의가 L2면 내적이 코사인이다.

    Args:
        scores: (Test 문서 수, Train 문서 수) 점수.
        q_labels: (Q,) Test 정답 범주.
        d_labels: (D,) Train 정답 범주.
        k: 기본 10. 반환 키 P@10, MAP@10 이름은 고정이라 여기서는 10을 사용한다.

    Returns:
        dict: P@5, P@10, MAP@10. MAP는 질의별 AP의 평균이다.
    """
    ranked = rank_matrix(scores, k)
    # d_labels[ranked]는 (Q,k) 결과 범주. q_labels[:,None]은 (Q,1)로
    # 각 질의 정답을 k개 결과와 비교한다. astype(float)는 True/False를 1/0으로 바꾼다.
    hits = (d_labels[ranked] == q_labels[:, None]).astype(float)
    n_rel = np.array([(d_labels == y).sum() for y in q_labels])
    return {
        "P@5": float(hits[:, :5].mean()),
        "P@10": float(hits.mean()),
        "MAP@10": float(np.mean([average_precision_at(h, r, k) for h, r in zip(hits, n_rel)])),
    }


def evaluate_hand_queries(score_fn: Callable[[str], np.ndarray], d_labels: np.ndarray,
                          target_names: Sequence[str], k: int = 10) -> dict:
    """직접 만든 20개 짧은 질의의 범주 일치율을 평균낸다.

    Args:
        score_fn: 질의 문자열을 받아 (D,) 점수를 주는 함수. 함수도 인자로 넘길 수 있다.
        d_labels: 검색 대상 문서 범주.
        target_names: 번호순 범주 이름.
        k: 최대 검색 결과 수. 기본 10.

    Returns:
        dict: P@5, P@10과 질의별 값. 양수 결과만 쓰므로 10개 미만이면
        실제 반환 개수가 분모다. 고정 k의 표준 P@k와 차이가 있다.
    """
    p5, p10, per_query = [], [], []
    for query, category in HAND_QUERIES:
        scores = score_fn(query)
        ranked = top_k(scores, k)
        target = target_names.index(category)
        rel = d_labels[ranked] == target
        p5.append(float(rel[:5].mean()) if len(rel) else 0.0)
        p10.append(float(rel.mean()) if len(rel) else 0.0)
        per_query.append({"query": query, "category": category, "P@5": p5[-1], "P@10": p10[-1]})
    return {"P@5": float(np.mean(p5)), "P@10": float(np.mean(p10)), "queries": per_query}


class RetrievalSplit:
    """검색 평가의 학습 문서와 질의 문서를 분리해 보관한다.

    Attributes:
        corpus: 전체 원자료.
        train_tokens: 색인할 Train 문서.
        test_tokens: 질의로 사용할 Test 문서.
        d_labels: 색인 문서의 정답 범주.
        q_labels: 질의 문서의 정답 범주.
    """

    def __init__(self, corpus: Corpus, train_idx: np.ndarray, test_idx: np.ndarray):
        """같은 분할 위치로 토큰과 정답을 함께 꺼낸다.

        Args:
            corpus: 전체 Corpus.
            train_idx: 검색 대상으로 사용할 위치.
            test_idx: 질의로 사용할 별도 위치.
        """
        self.corpus = corpus
        self.train_tokens = [corpus.tokens[i] for i in train_idx]
        self.test_tokens = [corpus.tokens[i] for i in test_idx]
        self.d_labels = corpus.labels[train_idx]
        self.q_labels = corpus.labels[test_idx]

    def tfidf(self, tf: str) -> dict:
        """Train에서 TF-IDF를 배우고 Test·수작업 질의를 변환해 평가한다.

        Args:
            tf: raw, log, double, binary 중 TF 방식.

        Returns:
            dict: doc_queries와 hand_queries 지표. 질의에서 IDF를 다시 배우지 않는다.
        """
        vec = TfidfVectorizerNP(tf=tf, min_df=MIN_DF, max_df=MAX_DF)
        D = vec.fit_transform(self.train_tokens)
        Q = vec.transform(self.test_tokens)
        from .preprocess import preprocess
        doc = evaluate_doc_queries(Q @ D.T, self.q_labels, self.d_labels)  # 둘 다 L2 정규화 → 내적 = 코사인
        hand = evaluate_hand_queries(
            lambda q: D @ vec.transform([preprocess(q)])[0], self.d_labels, self.corpus.target_names)
        return {"doc_queries": doc, "hand_queries": hand}

    def bm25(self, k1: float = 1.5, b: float = 0.75) -> dict:
        """같은 Train 어휘·길이로 BM25를 만들고 동일 질의들을 평가한다.

        Args:
            k1: 빈도 포화 계수.
            b: 길이 보정 강도.

        Returns:
            dict: 문서 질의·수작업 질의 지표. Qbin은 (Q,V) 이진 질의,
            W는 (D,V) BM25 기여도이므로 Qbin @ W.T는 (Q,D)다.
        """
        from .preprocess import preprocess
        vec = TfidfVectorizerNP(min_df=MIN_DF, max_df=MAX_DF)
        vec.fit(self.train_tokens)
        counts = vec.counts(self.train_tokens)
        lengths = np.array([len(t) for t in self.train_tokens], dtype=np.float64)
        model = BM25(k1, b).fit(counts, doc_lengths=lengths)
        W = model.weight_matrix()
        Qbin = (vec.counts(self.test_tokens) > 0).astype(np.float64)
        doc = evaluate_doc_queries(Qbin @ W.T, self.q_labels, self.d_labels)
        vocab = vec.vocabulary_
        hand = evaluate_hand_queries(
            lambda q: model.score([vocab[t] for t in preprocess(q) if t in vocab]),
            self.d_labels, self.corpus.target_names)
        return {"doc_queries": doc, "hand_queries": hand}


# --------------------------------------------------------------------------- BM25 vs TF-IDF
def compare_bm25_tfidf(engine: SearchEngine, queries: Sequence[str], k: int = 5) -> List[dict]:
    """같은 질의의 두 검색 순위와 겹친 문서 수를 비교한다.

    Args:
        engine: 전체 문서 검색 엔진.
        queries: 문자열 질의 목록.
        k: 각 방법에서 볼 최대 문서 수.

    Returns:
        List[dict]: 질의·겹침 수·방법별 점수/ID/범주/길이/발췌.
        점수 단위가 달라 'BM25 점수가 크니 더 정확하다'로 해석하지 않는다.
    """
    names = engine.corpus.target_names
    lengths = np.array([len(t) for t in engine.corpus.tokens])
    rows = []
    for q in queries:
        lists = {}
        for method in ("tfidf", "bm25"):
            hits = engine.search(q, topk=k, method=method)
            lists[method] = [{
                "doc_id": h.doc_id,
                "score": round(h.score, 4),
                "category": names[engine.corpus.labels[engine.position(h.doc_id)]],
                "n_tokens": int(lengths[engine.position(h.doc_id)]),
                "snippet": h.snippet[:110],
            } for h in hits]
        a = {d["doc_id"] for d in lists["tfidf"]}
        b = {d["doc_id"] for d in lists["bm25"]}
        rows.append({"query": q, "overlap": len(a & b), **lists})
    return rows


def mean_result_length(engine: SearchEngine, queries: Sequence[str], k: int = 10) -> Dict[str, float]:
    """방법별 상위 결과의 문서 길이를 비교한다.

    Args:
        engine: 전체 문서 엔진.
        queries: 결과가 존재하는 질의 목록.
        k: 질의당 최대 결과 수.

    Returns:
        Dict[str,float]: 전체·방법별 평균/중앙값 길이. 여러 질의에 같은 문서가 나오면
        반복해서 센다. 이 길이 차이만으로 검색 품질 우열을 결론내릴 수 없다.
    """
    lengths = np.array([len(t) for t in engine.corpus.tokens])
    out = {"corpus_mean": float(lengths.mean()), "corpus_median": float(np.median(lengths))}
    for method in ("tfidf", "bm25"):
        picked = np.concatenate([
            lengths[[engine.position(h.doc_id) for h in engine.search(q, topk=k, method=method)]]
            for q in queries])
        out[method] = float(picked.mean())
        out[f"{method}_median"] = float(np.median(picked))
    return out


# --------------------------------------------------------------------------- 역색인
def sample_short_queries(engine: SearchEngine, n: int, terms_per_query: int = 3) -> List[str]:
    """문서에 있는 서로 다른 어휘를 뽑아 시간 측정용 질의를 만든다.

    Args:
        engine: 어휘가 준비된 검색 엔진.
        n: 만들 질의 수.
        terms_per_query: 서로 다른 단어 수. 조건을 충족하는 문서가 있어야 종료한다.

    Returns:
        List[str]: 고정 난수로 뽑은 질의. 사람의 검색 의도 표본은 아니다.
    """
    rng = np.random.default_rng(RANDOM_STATE)
    vocab = engine.vectorizer.vocabulary_
    queries = []
    while len(queries) < n:
        tokens = sorted({t for t in engine.corpus.tokens[rng.integers(len(engine.corpus))] if t in vocab})
        if len(tokens) >= terms_per_query:
            queries.append(" ".join(rng.choice(tokens, terms_per_query, replace=False)))
    return queries


def _time_per_query(fn: Callable[[], None], n_queries: int, repeat: int = 5) -> float:
    """반복 실행 중 가장 짧은 총시간을 질의 수로 나눈다.

    Args:
        fn: 여러 질의를 한꺼번에 처리하는 인자 없는 함수.
        n_queries: 양의 질의 수.
        repeat: 반복 횟수, 기본 5.

    Returns:
        float: 쿼리당 ms. 평균적인 사용자 지연이 아니라 좋은 실행 조건의 최솟값이다.
    """
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best / n_queries * 1000.0


def benchmark_index(engine: SearchEngine, queries: Sequence[str], sizes: Sequence[int], k: int = 5) -> List[dict]:
    """문서 수를 바꿔 전체·질의 열·역색인 스캔을 비교한다.

    전체 어휘·IDF와 질의 벡터는 고정하고 문서 행만 일부 고른다. 규모마다 IDF를
    다시 학습하는 실험이 아니다. 질의 벡터화와 색인 구축은 검색 측정 시간에서 뺀다.

    Args:
        engine: 전체 문서 엔진.
        queries: 시간 측정 질의들. 양수 개수.
        sizes: 고를 문서 수들. 실제 문서 수 이하를 준다.
        k: 상위 결과 수.

    Returns:
        List[dict]: 시간·연산량 대용치·포스팅 수·동등성. same_top_k는 순위를 정렬해
        집합과 후보 점수를 비교하므로 동점까지의 전체 순서 보장은 아니다.
        Python 반복·정렬·메모리 비용도 있어 연산량 감소비와 속도 향상비는 다르다.
    """
    rng = np.random.default_rng(RANDOM_STATE)
    vecs = [engine.query_vector(q) for q in queries]
    qdicts = [{int(j): float(v[j]) for j in np.flatnonzero(v)} for v in vecs]
    order = rng.permutation(len(engine.corpus))
    rows = []
    for n in sizes:
        pick = np.sort(order[:n])
        W = np.ascontiguousarray(engine.matrix[pick])
        norms = engine.doc_norms[pick]
        n_terms = W.shape[1]
        start = time.perf_counter()
        index = InvertedIndex(W, engine.vectorizer.terms_)
        build_ms = (time.perf_counter() - start) * 1000.0

        # 함수 안에 정의한 함수는 바깥의 W·vecs·k를 읽는다(클로저).
        # 세 함수를 즉시 호출하지 않고 시간 측정 함수에 값으로 전달할 수 있다.
        def full_scan():
            for v in vecs:
                top_k(cosine_similarity(v, W, norms), k)

        def column_scan():
            for d in qdicts:
                ids = np.fromiter(d.keys(), dtype=np.intp)
                top_k(W[:, ids] @ np.fromiter(d.values(), dtype=np.float64), k)

        def index_scan():
            for d in qdicts:
                cand, scores, _ = index.score(d)
                top_k(scores, k, cand)

        # same &= 조건은 지금까지의 모든 비교가 참인지 누적한다.
        # 방문량 Σdf는 점수 곱셈의 대용치이며 후보 결합·정렬 비용은 별도다.
        same, touched = True, []
        for v, d in zip(vecs, qdicts):
            cand, scores, visited = index.score(d)
            full = cosine_similarity(v, W, norms)
            # 같은 문서 집합인지, 점수가 부동소수점 오차 안에서 같은지 확인한다.
            same &= np.array_equal(np.sort(top_k(full, k)), np.sort(top_k(scores, k, cand)))
            same &= np.allclose(full[cand], scores, atol=1e-12)
            touched.append(visited)
        touched = float(np.mean(touched))
        rows.append({
            "n_docs": int(n),
            "n_terms": int(n_terms),
            "full_scan_ms": _time_per_query(full_scan, len(queries)),
            "column_scan_ms": _time_per_query(column_scan, len(queries)),
            "index_ms": _time_per_query(index_scan, len(queries)),
            "index_build_ms": build_ms,
            "ops_full": int(n * n_terms),
            "ops_column": float(n * np.mean([len(d) for d in qdicts])),
            "ops_index": float(touched),
            "postings_total": int(index.posting_lengths().sum()),
            "same_top_k": bool(same),
        })
    return rows


# --------------------------------------------------------------------------- BoW 한계
def _cos(a: np.ndarray, b: np.ndarray) -> float:
    """작은 설명 예제 두 벡터의 코사인을 계산한다.

    Args:
        a: 첫 벡터.
        b: 같은 길이의 둘째 벡터.

    Returns:
        float: 코사인. 한쪽이 0이면 0.
    """
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / denom) if denom else 0.0


def bow_limits(engine: SearchEngine) -> dict:
    """단어 묶음(BoW) 표현이 잃는 정보를 작은 문장으로 드러낸다.

    Args:
        engine: 영어 어휘로 학습한 검색 엔진.

    Returns:
        dict: 어순·부정어·동의어·다의어·한국어 예제. 한국어는 영어 preprocess를
        쓰면 모두 사라지므로 손으로 나눈 토큰을 벡터화기에 직접 넘긴다.
        형태소로 나눠도 같은 단어 묶음이면 주어·목적어 역할은 복원하지 못한다.
    """
    from .preprocess import preprocess

    pairs = {
        "word_order": ("the pitcher hit the batter", "the batter hit the pitcher"),
        "negation": ("this is a good team", "this is not a good team"),
        "synonym": ("goalie", "goaltender"),
    }
    out = {}
    for key, (a, b) in pairs.items():
        out[key] = {
            "a": a, "b": b,
            "tokens_a": preprocess(a), "tokens_b": preprocess(b),
            "cosine": _cos(engine.query_vector(a), engine.query_vector(b)),
        }
    ga = {h.doc_id for h in engine.search("goalie", topk=10)}
    gb = {h.doc_id for h in engine.search("goaltender", topk=10)}
    out["synonym"]["top10_overlap"] = len(ga & gb)

    names = engine.corpus.target_names
    out["polysemy"] = {}
    for word in ("save", "run"):
        hits = engine.search(word, topk=10)
        out["polysemy"][word] = [
            {"doc_id": h.doc_id, "category": names[engine.corpus.labels[engine.position(h.doc_id)]],
             "snippet": h.snippet[:110]} for h in hits
        ]

    # 한국어: 공백 토큰화 vs (손으로 나눈) 형태소 토큰화
    ko = ["고양이가 쥐를 잡았다", "쥐가 고양이를 잡았다"]
    space = [s.split() for s in ko]
    # 이 토큰들은 형태소 분석기를 실행한 결과가 아니라 설명용으로 손으로 나눈 입력이다.
    morph = [["고양이", "가", "쥐", "를", "잡", "았", "다"], ["쥐", "가", "고양이", "를", "잡", "았", "다"]]
    ko_out = {"sentences": ko}
    for name, toks in (("whitespace", space), ("morpheme", morph)):
        vec = TfidfVectorizerNP(smooth_idf=True)
        X = vec.fit_transform(toks)
        ko_out[name] = {"tokens": toks, "vocabulary": vec.terms_, "cosine": _cos(X[0], X[1])}
    out["korean"] = ko_out
    return out
