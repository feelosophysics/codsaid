"""문서 검색 CLI (안 A).

    python main.py --query "space shuttle launch" --topk 5
    python main.py --query "hockey playoff goalie" --method bm25
    python main.py --query "save" --method both
    python main.py --query "space shuttle launch" --explain
    python main.py --query "nasa orbit" --index
"""
from __future__ import annotations

# import는 라이브러리를 가져온다. argparse는 --query 같은 옵션을 Python 값으로 바꾼다.
# src.data의 src는 패키지, data는 모듈(파일), load_corpus는 그 안의 함수다.
import argparse
import sys
import time

from src.data import load_corpus
from src.search import SearchEngine

LABELS = {"tfidf": "TF-IDF 코사인", "bm25": "BM25(k1=1.5, b=0.75)"}


def print_results(engine: SearchEngine, query: str, topk: int, method: str, use_index: bool) -> None:
    """검색 한 방법을 실행해 순위·ID·범주·발췌를 터미널에 쓴다.

    Args:
        engine: 미리 준비한 검색 엔진.
        query: 검색 문자열.
        topk: 양의 최대 결과 수.
        method: tfidf 또는 bm25.
        use_index: 역색인 사용 여부.

    Returns:
        None: 콘솔에 출력한다. 색인 구축 시간은 검색 시간과 따로 측정한다.
    """
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
    # enumerate(hits,1)은 1부터의 순위와 결과 h를 짝으로 준다.
    # f문자열 {h.score:.3f}는 소수 셋째 자리까지, {cat}은 범주 이름을 끼운다.
    for rank, h in enumerate(hits, 1):
        cat = names[engine.corpus.labels[engine.position(h.doc_id)]]
        print(f'{rank}. [{h.score:.3f}] doc {h.doc_id} ({cat}) "{h.snippet}"')


def print_explain(engine: SearchEngine, query: str) -> None:
    """TF-IDF 1위 문서의 코사인 계산을 단어별로 출력한다.

    Args:
        engine: 준비한 엔진.
        query: 검색어. --method bm25여도 이 해설은 TF-IDF 1위를 대상으로 한다.

    Returns:
        None: 콘솔에 출력. TF-IDF 양수 결과가 없으면 바로 끝낸다.
    """
    hits = engine.search(query, topk=1)
    if not hits:
        return
    ex = engine.explain(query, hits[0].doc_id)
    print()
    print("=== TF-IDF 코사인 유사도 계산 (TF-IDF 1위 문서) ===")
    print("Query 벡터(0이 아닌 칸): " + ", ".join(f"{t}={w:.3f}" for t, w in ex["query_terms"].items()))
    print(f"문서 doc {hits[0].doc_id}: 0이 아닌 칸 {ex['doc_nonzero']}개, 그중 쿼리와 겹치는 칸")
    for term, qw, dw, prod in ex["shared"]:
        print(f"  {term:<12} {qw:.4f} × {dw:.4f} = {prod:.4f}")
    print("코사인 유사도 = (Query · 문서) / (||Query|| × ||문서||)")
    print(f"            = {ex['dot']:.4f} / ({ex['query_norm']:.4f} × {ex['doc_norm']:.4f}) = {ex['cosine']:.4f}")


def main() -> None:
    """터미널 옵션을 읽어 데이터 준비 → 검색 → 선택 해설을 실행한다.

    --query는 필수 문자열, --topk는 int 변환, --index/--explain은 스위치다.
    --topk는 1 이상이어야 한다. 잘못된 값은 색인 구축 전에 거절한다.

    Returns:
        None: 데이터 캐시가 없으면 다운로드하고 준비·검색 결과를 출력한다.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="20 Newsgroups TF-IDF / BM25 문서 검색")
    parser.add_argument("--query", required=True, help="검색어(영어)")
    parser.add_argument("--topk", type=int, default=5, help="반환할 문서 수(기본 5)")
    parser.add_argument("--method", choices=["tfidf", "bm25", "both"], default="tfidf")
    # action="store_true"는 옵션이 있으면 True, 생략하면 False.
    # choices는 가능한 값, default는 생략 시 값이다.
    parser.add_argument("--index", action="store_true", help="역색인으로 검색")
    parser.add_argument("--explain", action="store_true", help="TF-IDF 1위 문서의 코사인 계산 과정 출력")
    args = parser.parse_args()
    if args.topk < 1:
        parser.error("--topk는 1 이상의 정수여야 합니다.")

    start = time.perf_counter()
    engine = SearchEngine(load_corpus())
    # shape의 두 값을 풀어 받는다. (문서 수 N, 어휘 수 V)의 한 행이 문서 하나다.
    # 분류 모델 학습 없이도 이 문서 행렬만으로 코사인 검색을 할 수 있다.
    n_docs, n_terms = engine.matrix.shape
    print(f"색인 준비: 문서 {n_docs}건 × 어휘 {n_terms}개, {time.perf_counter() - start:.1f}초")
    print(f"쿼리 토큰: {engine.query_tokens(args.query)}")
    print()
    for method in (["tfidf", "bm25"] if args.method == "both" else [args.method]):
        print_results(engine, args.query, args.topk, method, args.index)
        print()
    if args.explain:
        print_explain(engine, args.query)


# 이 파일을 직접 실행할 때만 main(). import main으로 가져오면 검색을 시작하지 않는다.
if __name__ == "__main__":
    main()
