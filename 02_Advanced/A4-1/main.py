"""문서 검색 CLI (안 A).

    python main.py --query "space shuttle launch" --topk 5
    python main.py --query "hockey playoff goalie" --method bm25
    python main.py --query "save" --method both
    python main.py --query "space shuttle launch" --explain
    python main.py --query "nasa orbit" --index
"""
from __future__ import annotations

import argparse
import sys
import time

from src.data import load_corpus
from src.search import SearchEngine

LABELS = {"tfidf": "TF-IDF 코사인", "bm25": "BM25(k1=1.5, b=0.75)"}


def print_results(engine: SearchEngine, query: str, topk: int, method: str, use_index: bool) -> None:
    names = engine.corpus.target_names
    if use_index:  # 색인 구축은 한 번만 하는 준비 작업이라 검색 시간에서 뺀다
        start = time.perf_counter()
        index = engine.index(method)
        print(f"역색인 구축({method}): 포스팅 {index.posting_lengths().sum()}개, "
              f"{(time.perf_counter() - start) * 1000:.0f} ms")
    start = time.perf_counter()
    hits = engine.search(query, topk=topk, method=method, use_index=use_index)
    elapsed = (time.perf_counter() - start) * 1000
    how = "역색인" if use_index else "전체 스캔"
    print(f"=== 검색 결과: {LABELS[method]}, {how}, {elapsed:.1f} ms ===")
    print(f'Query: "{query}"')
    if not hits:
        print("일치하는 문서가 없습니다(쿼리 단어가 모두 불용어이거나 어휘에 없음).")
        return
    print(f"Top {len(hits)} 결과:")
    for rank, h in enumerate(hits, 1):
        cat = names[engine.corpus.labels[engine.position(h.doc_id)]]
        print(f'{rank}. [{h.score:.3f}] doc {h.doc_id} ({cat}) "{h.snippet}"')


def print_explain(engine: SearchEngine, query: str) -> None:
    hits = engine.search(query, topk=1)
    if not hits:
        return
    ex = engine.explain(query, hits[0].doc_id)
    print()
    print("=== 코사인 유사도 계산 (1위 문서) ===")
    print("Query 벡터(0이 아닌 칸): " + ", ".join(f"{t}={w:.3f}" for t, w in ex["query_terms"].items()))
    print(f"문서 doc {hits[0].doc_id}: 0이 아닌 칸 {ex['doc_nonzero']}개, 그중 쿼리와 겹치는 칸")
    for term, qw, dw, prod in ex["shared"]:
        print(f"  {term:<12} {qw:.4f} × {dw:.4f} = {prod:.4f}")
    print("코사인 유사도 = (Query · 문서) / (||Query|| × ||문서||)")
    print(f"            = {ex['dot']:.4f} / ({ex['query_norm']:.4f} × {ex['doc_norm']:.4f}) = {ex['cosine']:.4f}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="20 Newsgroups TF-IDF / BM25 문서 검색")
    parser.add_argument("--query", required=True, help="검색어(영어)")
    parser.add_argument("--topk", type=int, default=5, help="반환할 문서 수(기본 5)")
    parser.add_argument("--method", choices=["tfidf", "bm25", "both"], default="tfidf")
    parser.add_argument("--index", action="store_true", help="역색인으로 검색")
    parser.add_argument("--explain", action="store_true", help="1위 문서의 코사인 계산 과정 출력")
    args = parser.parse_args()

    start = time.perf_counter()
    engine = SearchEngine(load_corpus())
    n_docs, n_terms = engine.matrix.shape
    print(f"색인 준비: 문서 {n_docs}건 × 어휘 {n_terms}개, {time.perf_counter() - start:.1f}초")
    print(f"쿼리 토큰: {engine.query_tokens(args.query)}")
    print()
    for method in (["tfidf", "bm25"] if args.method == "both" else [args.method]):
        print_results(engine, args.query, args.topk, method, args.index)
        print()
    if args.explain:
        print_explain(engine, args.query)


if __name__ == "__main__":
    main()
