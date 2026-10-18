"""study/a4-1.template.html + 실제 색인·실험 결과·소스 발췌 → study/a4-1.html (오프라인 단일 파일).

    python tools/build_study_guide.py      (먼저 python -m src.run_all 로 outputs/ 를 만든다)

HTML에 넣는 것
- 전체 문서 4,631건의 단어 빈도 포스팅(단어 → 문서 위치·빈도). 브라우저가 이것으로 TF-IDF·BM25를 다시 계산한다.
- 문서별 앞부분 발췌(이메일·URL은 가림), 범주, 길이
- outputs/*.json 의 검증·분류·보너스 결과
- src/ 의 핵심 함수 원문과 줄 번호
"""
from __future__ import annotations

import ast
import hashlib
import html as html_lib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import preprocess as pp  # noqa: E402
from src.data import load_corpus  # noqa: E402
from src.experiments import HAND_QUERIES  # noqa: E402
from src.search import MAX_DF, MIN_DF, SearchEngine  # noqa: E402
from src.stopwords import STOPWORDS  # noqa: E402

STUDY = ROOT / "study"
OUT = ROOT / "outputs"
EXCERPT_CHARS = 280

# 오분류 해설 사례(README '오분류 원인 분석'과 같은 문서)
CASES = {
    400: ("다의어", "\"in the space of 9 months\"의 space는 '9개월 동안'이라는 시간 표현이다. 그런데 우주 범주의 가장 강한 단어로 세어졌다."),
    4893: ("다의어", "\"space is at a premium\"은 디스크 공간이 부족하다는 뜻이다. 이 space 하나가 X 범주 단서보다 크게 작용했다."),
    221: ("다의어", "\"4 points in 3-space\"는 3차원 기하 공간이다. points와 sphere라는 그래픽 단서가 있었지만 space의 가중치가 더 컸다."),
    3125: ("문맥 부재", "하키 골리 장비 이야기다. 그런데 glove와 jerseys는 야구에서 더 자주 쓰여 야구 쪽으로 끌려갔다. 누구의 글러브인지는 BoW로 표현되지 않는다."),
    3111: ("문맥 부재", "\"r.s.baseball로 갔다\"처럼 다른 게시판을 언급한 글이다. 단어가 나왔다고 그 주제에 대한 글인 것은 아니다."),
    552: ("범주 중첩", "X-Windows 기반 client-server 가상현실 소프트웨어 공지다. 두 게시판에 모두 맞는 교차 게시글이다."),
    1880: ("증거 부족", "토큰 7개 중 어휘에 걸린 단어가 later와 steve 2개뿐이다. 우연한 단어가 결정을 좌우했다."),
    780: ("전처리 누수", "http:// 없이 쓴 호스트명 export.lcs.mit.edu가 남았다. 그래서 mit, lcs, export가 X 범주 신호가 됐다."),
}

# 화면에 보여 줄 핵심 함수: (파일, 정규화된 이름)
EXCERPTS = [
    ("main.py", "main"),
    ("main.py", "print_explain"),
    ("src/preprocess.py", "clean"),
    ("src/preprocess.py", "tokenize"),
    ("src/preprocess.py", "normalize"),
    ("src/preprocess.py", "remove_stopwords"),
    ("src/preprocess.py", "preprocess"),
    ("src/tfidf.py", "build_vocabulary"),
    ("src/tfidf.py", "count_matrix"),
    ("src/tfidf.py", "term_frequency"),
    ("src/tfidf.py", "document_frequency"),
    ("src/tfidf.py", "inverse_document_frequency"),
    ("src/tfidf.py", "normalize_rows"),
    ("src/tfidf.py", "TfidfVectorizerNP._weight"),
    ("src/tfidf.py", "TfidfVectorizerNP.fit_transform"),
    ("src/tfidf.py", "TfidfVectorizerNP.transform"),
    ("src/data.py", "load_corpus"),
    ("src/data.py", "train_test_indices"),
    ("src/search.py", "cosine_similarity"),
    ("src/search.py", "top_k"),
    ("src/search.py", "SearchEngine.search"),
    ("src/search.py", "SearchEngine.position"),
    ("src/classify.py", "make_model"),
    ("src/classify.py", "select_C"),
    ("src/classify.py", "run_classification"),
    ("src/classify.py", "explain_errors"),
    ("src/bm25.py", "BM25.fit"),
    ("src/bm25.py", "BM25.score"),
    ("src/bm25.py", "BM25.weight_matrix"),
    ("src/inverted_index.py", "InvertedIndex.__init__"),
    ("src/inverted_index.py", "InvertedIndex.score"),
    ("src/experiments.py", "RetrievalSplit.tfidf"),
    ("src/experiments.py", "benchmark_index"),
    ("src/experiments.py", "bow_limits"),
    ("src/experiments.py", "verify_against_sklearn"),
    ("src/run_all.py", "step_verification"),
    ("src/run_all.py", "step_tf_variants"),
    ("src/run_all.py", "step_bm25"),
    ("src/run_all.py", "step_index"),
]


def code_excerpts() -> dict:
    out = {}
    for rel, name in EXCERPTS:
        path = ROOT / rel
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        parts = name.split(".")
        node = None
        for top in tree.body:
            if getattr(top, "name", None) == parts[0]:
                node = top
                if len(parts) == 2:
                    node = next(n for n in top.body if getattr(n, "name", None) == parts[1])
                break
        if node is None:
            raise KeyError(f"{rel}:{name} 를 찾지 못함")
        start = node.lineno - len(getattr(node, "decorator_list", []))
        out[name] = {"file": rel, "start": start, "end": node.end_lineno,
                     "code": "\n".join(lines[start - 1:node.end_lineno])}
    return out


def excerpt(text: str) -> str:
    text = pp.EMAIL_RE.sub("[email]", text)
    text = pp.URL_RE.sub("[url]", text)
    flat = re.sub(r"\s+", " ", text).strip()
    return flat[:EXCERPT_CHARS] + ("…" if len(flat) > EXCERPT_CHARS else "")


def index_payload(engine: SearchEngine) -> dict:
    """빈도 행렬을 단어별 포스팅으로 바꿔 넣는다. 문서 위치는 앞 위치와의 차이로 줄인다."""
    corpus = engine.corpus
    counts = engine.vectorizer.counts(corpus.tokens)
    term_pos, doc_pos = np.nonzero(counts.T)
    values = counts[doc_pos, term_pos].astype(int)
    bounds = np.searchsorted(term_pos, np.arange(counts.shape[1] + 1))
    postings = []
    for j in range(counts.shape[1]):
        docs = doc_pos[bounds[j]:bounds[j + 1]]
        postings.append([np.diff(docs, prepend=0).tolist(), values[bounds[j]:bounds[j + 1]].tolist()])
    return {
        "terms": engine.vectorizer.terms_,
        "postings": postings,
        "docs": {
            "id": corpus.doc_ids.tolist(),
            "cat": corpus.labels.tolist(),
            "len": [len(t) for t in corpus.tokens],
            "text": [excerpt(t) for t in corpus.texts],
        },
    }


def read_json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def learning_panels() -> tuple[dict[str, str], str]:
    """같은 설명 원본으로 HTML 패널과 Markdown 읽기 가이드를 만든다."""
    notes = json.loads((STUDY / "learning-notes.json").read_text(encoding="utf-8"))
    panels = {}
    md = ["# A4-1 코드 읽기 가이드", "", "설명용 두 문서를 끝까지 추적한다. 실제 데이터 실행 결과와 구분해 읽는다.",
          "설명 원본은 learning-notes.json이고 이 문서는 build_study_guide.py가 생성한다.",
          "HTML의 각 장에도 같은 설명과 답 펼치기가 있다. 코드는 HTML 11장 또는 src 원본에서 읽는다.", ""]
    available = {name for _, name in EXCERPTS}
    for note in notes:
        if not set(note["sources"]) <= available:
            raise ValueError(f"코드 지도에 없는 참조: {note['sources']}")
        esc = html_lib.escape
        refs = " · ".join(f'<code>{esc(n)}</code>' for n in note["sources"])
        paragraphs = "".join(f"<p>{esc(p)}</p>" for p in note["paragraphs"])
        panels[note["section"]] = (
            f'<aside class="read learning-panel" id="learn-{note["section"]}">'
            f'<h3>{esc(note["title"])}</h3>{paragraphs}'
            f'<p class="note">계산 추적: {esc(note["trace"])}</p>'
            f'<details><summary>먼저 예상하기: {esc(note["question"])}</summary>'
            f'<p>{esc(note["answer"])}</p></details>'
            f'<p class="small">11장 코드 지도: {refs}</p></aside>'
        )
        md.extend([f'## {note["title"]}', "", *sum(([p, ""] for p in note["paragraphs"]), []),
                   f'계산 추적: {note["trace"]}', "", f'**먼저 예상하기:** {note["question"]}', "",
                   '<details><summary>답과 이유</summary>', "", note["answer"], "", '</details>', "",
                   "코드 지도: " + ", ".join(f'`{n}`' for n in note["sources"]), ""])
    return panels, "\n".join(md)


def main() -> None:
    corpus = load_corpus()
    engine = SearchEngine(corpus)
    summary = read_json("summary.json")
    verification = read_json("tfidf_verification.json")
    classification = read_json("classification.json")
    bm25 = read_json("bm25_vs_tfidf.json")
    bow = read_json("bow_limits.json")
    errors = {c["doc_id"]: c for c in read_json("misclassified.json")}
    index = index_payload(engine)
    explain_q = "space shuttle launch"
    top = engine.search(explain_q, topk=1)[0]

    data = {
        "meta": {**summary["data"], "min_df": MIN_DF, "max_df": MAX_DF,
                 "nonzero": sum(len(p[0]) for p in index["postings"])},
        "stopwords": sorted(STOPWORDS),
        "variants": pp.SPELLING_VARIANTS,
        "index": index,
        "handQueries": HAND_QUERIES,
        "verification": verification,
        "classification": classification,
        "tfVariants": summary["tf_variants"],
        "bm25": {k: bm25[k] for k in ("grid_k1", "grid_b", "grid_doc_map10", "grid_hand_p10",
                                       "mean_result_length", "examples")}
                | {"table": {m: {"doc": bm25[m]["doc_queries"], "handP5": bm25[m]["hand_queries"]["P@5"],
                                 "handP10": bm25[m]["hand_queries"]["P@10"]} for m in ("tfidf", "bm25")}},
        "indexBench": summary["index_benchmark"],
        "bow": bow,
        "cases": [
            {**{k: v for k, v in errors[d].items() if k != "text"}, "kind": kind, "note": note,
             "text": excerpt(errors[d]["text"])}
            for d, (kind, note) in CASES.items()
        ],
        "explain": {"query": explain_q, "doc_id": top.doc_id, **engine.explain(explain_q, top.doc_id)},
        "code": code_excerpts(),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (STUDY / "a4-1.template.html").read_text(encoding="utf-8")
    panels, walkthrough = learning_panels()
    for section, panel in panels.items():
        marker = f"__LEARNING_{section.upper()}__"
        if template.count(marker) != 1:
            raise ValueError(f"학습 설명 위치가 없거나 중복됨: {marker}")
        template = template.replace(marker, panel)
    html = template.replace("__STUDY_DATA__", payload)
    (STUDY / "a4-1.html").write_text(html, encoding="utf-8")
    (STUDY / "code-walkthrough.md").write_text(walkthrough, encoding="utf-8")
    sources = [ROOT / "main.py", *sorted((ROOT / "src").glob("*.py")),
               *sorted((ROOT / "tools").glob("*.py")), STUDY / "learning-notes.json",
               STUDY / "a4-1.template.html", ROOT / "pyproject.toml", ROOT / "uv.lock",
               *sorted(OUT.glob("*.json"))]
    # 등록 대상은 UTF-8 텍스트다. Git의 LF/CRLF 변환으로 검증이 깨지지 않게 정규화한다.
    manifest = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                for p in sources}
    (STUDY / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"study/a4-1.html {len(html.encode('utf-8')) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
