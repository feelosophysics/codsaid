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
    """같은 토큰·같은 설정으로 sklearn TfidfVectorizer와 행렬·IDF·어휘를 비교한다."""
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
    """직접 구현한 코사인 유사도와 sklearn cosine_similarity의 최대 오차."""
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
    return float(np.mean(retrieved[:k] == relevant)) if k else 0.0


def average_precision_at(hits: np.ndarray, n_relevant: int, k: int) -> float:
    """hits: 상위 k개의 관련 여부(0/1). AP@k = Σ P@i·rel_i / min(k, 관련 문서 수)."""
    hits = hits[:k]
    if n_relevant == 0:
        return 0.0
    cum = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float((cum * hits).sum() / min(k, n_relevant))


def rank_matrix(scores: np.ndarray, k: int) -> np.ndarray:
    """각 행에서 점수 상위 k개의 열 번호(내림차순)."""
    part = np.argpartition(-scores, k, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(scores, part, axis=1), axis=1, kind="stable")
    return np.take_along_axis(part, order, axis=1)


def evaluate_doc_queries(scores: np.ndarray, q_labels: np.ndarray, d_labels: np.ndarray, k: int = 10) -> dict:
    """Test 문서를 쿼리로 Train 문서를 검색. 같은 범주면 관련 문서."""
    ranked = rank_matrix(scores, k)
    hits = (d_labels[ranked] == q_labels[:, None]).astype(float)
    n_rel = np.array([(d_labels == y).sum() for y in q_labels])
    return {
        "P@5": float(hits[:, :5].mean()),
        "P@10": float(hits.mean()),
        "MAP@10": float(np.mean([average_precision_at(h, r, k) for h, r in zip(hits, n_rel)])),
    }


def evaluate_hand_queries(score_fn: Callable[[str], np.ndarray], d_labels: np.ndarray,
                          target_names: Sequence[str], k: int = 10) -> dict:
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
    """Train 문서를 색인, Test 문서를 쿼리로 쓰는 검색 평가 공통 준비."""

    def __init__(self, corpus: Corpus, train_idx: np.ndarray, test_idx: np.ndarray):
        self.corpus = corpus
        self.train_tokens = [corpus.tokens[i] for i in train_idx]
        self.test_tokens = [corpus.tokens[i] for i in test_idx]
        self.d_labels = corpus.labels[train_idx]
        self.q_labels = corpus.labels[test_idx]

    def tfidf(self, tf: str) -> dict:
        vec = TfidfVectorizerNP(tf=tf, min_df=MIN_DF, max_df=MAX_DF)
        D = vec.fit_transform(self.train_tokens)
        Q = vec.transform(self.test_tokens)
        from .preprocess import preprocess
        doc = evaluate_doc_queries(Q @ D.T, self.q_labels, self.d_labels)  # 둘 다 L2 정규화 → 내적 = 코사인
        hand = evaluate_hand_queries(
            lambda q: D @ vec.transform([preprocess(q)])[0], self.d_labels, self.corpus.target_names)
        return {"doc_queries": doc, "hand_queries": hand}

    def bm25(self, k1: float = 1.5, b: float = 0.75) -> dict:
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
    """상위 k개 결과 문서의 토큰 수(평균·중앙값). L2 정규화와 BM25 길이 보정의 차이를 본다."""
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
    """임의 문서에서 어휘에 있는 단어 3개를 뽑아 짧은 쿼리를 만든다(시간 측정용)."""
    rng = np.random.default_rng(RANDOM_STATE)
    vocab = engine.vectorizer.vocabulary_
    queries = []
    while len(queries) < n:
        tokens = sorted({t for t in engine.corpus.tokens[rng.integers(len(engine.corpus))] if t in vocab})
        if len(tokens) >= terms_per_query:
            queries.append(" ".join(rng.choice(tokens, terms_per_query, replace=False)))
    return queries


def _time_per_query(fn: Callable[[], None], n_queries: int, repeat: int = 5) -> float:
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best / n_queries * 1000.0


def benchmark_index(engine: SearchEngine, queries: Sequence[str], sizes: Sequence[int], k: int = 5) -> List[dict]:
    """문서 수 N을 바꿔 가며 세 가지 검색의 쿼리당 시간(ms)과 연산량을 잰다."""
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
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / denom) if denom else 0.0


def bow_limits(engine: SearchEngine) -> dict:
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
    morph = [["고양이", "가", "쥐", "를", "잡", "았", "다"], ["쥐", "가", "고양이", "를", "잡", "았", "다"]]
    ko_out = {"sentences": ko}
    for name, toks in (("whitespace", space), ("morpheme", morph)):
        vec = TfidfVectorizerNP(smooth_idf=True)
        X = vec.fit_transform(toks)
        ko_out[name] = {"tokens": toks, "vocabulary": vec.terms_, "cosine": _cos(X[0], X[1])}
    out["korean"] = ko_out
    return out
