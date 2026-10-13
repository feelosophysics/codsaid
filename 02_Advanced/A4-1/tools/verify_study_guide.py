"""study/a4-1.html 의 JavaScript 계산이 Python 구현과 같은지 Node.js로 대조한다.

    python tools/verify_study_guide.py

1. 전처리: 원본 4,941건 전부의 토큰이 Python preprocess()와 같은가
2. 검색: 평가 쿼리 20개 + 예시 쿼리 × (TF-IDF 4가지 TF 변형, BM25 2가지 설정)의 top-5 순위·점수
3. 03장 장난감 계산기: 12가지 설정의 TF-IDF 행렬이 TfidfVectorizerNP와 같은가
4. 페이지 구조: getElementById / href="#..." 가 가리키는 id가 실제로 있는가
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.bm25 import BM25  # noqa: E402
from src.data import CATEGORIES, DATA_HOME, load_corpus  # noqa: E402
from src.experiments import HAND_QUERIES  # noqa: E402
from src.preprocess import preprocess  # noqa: E402
from src.search import MAX_DF, MIN_DF, cosine_similarity, top_k  # noqa: E402
from src.tfidf import TF_VARIANTS, TfidfVectorizerNP  # noqa: E402

HTML = ROOT / "study" / "a4-1.html"
EXTRA_QUERIES = ["save", "run", "goaltender", "the and of", "Shuttle's LAUNCH!!", "x11 r5 motif"]
BM25_SETTINGS = [(1.5, 0.75), (1.2, 0.5)]
TOY = ["space shuttle launch launch", "hockey goalie playoff", "space station orbit", "baseball pitcher launch"]

NODE_RUNNER = r"""
const fs = require("fs");
const [htmlPath, inPath, outPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, "utf8");
const data = JSON.parse(html.match(/<script id="study-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const engineSrc = html.match(/<script id="engine">([\s\S]*?)<\/script>/)[1];
new Function(engineSrc)();
const E = globalThis.A41.makeEngine(data);
const input = JSON.parse(fs.readFileSync(inPath, "utf8"));
const out = { tokens: input.texts.map(t => E.P.preprocess(t)), search: [], toy: [] };
for (const q of input.queries) {
  for (const v of input.variants) out.search.push({ q, method: "tfidf", v, hits: E.searchTfidf(q, 5, v).hits });
  for (const [k1, b] of input.bm25) out.search.push({ q, method: "bm25", v: `${k1},${b}`, hits: E.searchBm25(q, 5, k1, b).hits });
}
for (const opt of input.toyOpts) out.toy.push(globalThis.A41.toyTfidf(input.toy.map(l => l.split(" ")), opt).normed);
fs.writeFileSync(outPath, JSON.stringify(out));
"""


def run_node(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "runner.js").write_text(NODE_RUNNER, encoding="utf-8")
        (tmp / "in.json").write_text(json.dumps(payload), encoding="utf-8")
        subprocess.run(["node", str(tmp / "runner.js"), str(HTML), str(tmp / "in.json"), str(tmp / "out.json")], check=True)
        return json.loads((tmp / "out.json").read_text(encoding="utf-8"))


def python_hits(scores: np.ndarray) -> list:
    return [(float(scores[p]), int(p)) for p in top_k(scores, 5)]


def same_hits(a: list, b: list, tol: float = 1e-9) -> bool:
    return len(a) == len(b) and all(pa == pb and abs(sa - sb) < tol for (sa, pa), (sb, pb) in zip(a, b))


def main() -> int:
    from sklearn.datasets import fetch_20newsgroups

    raw = fetch_20newsgroups(subset="all", categories=CATEGORIES, remove=("headers", "footers", "quotes"),
                             data_home=str(DATA_HOME), shuffle=False).data
    corpus = load_corpus()
    queries = [q for q, _ in HAND_QUERIES] + EXTRA_QUERIES
    toy_opts = [{"tf": tf, "smooth": s, "norm": n} for tf, s, n in product(TF_VARIANTS[:2] + ("double",), (True, False), ("l2", "l1", "none"))]
    js = run_node({"texts": raw, "queries": queries, "variants": list(TF_VARIANTS), "bm25": BM25_SETTINGS,
                   "toy": TOY, "toyOpts": toy_opts})
    failures = []

    # 1. 전처리
    bad = [i for i, (t, toks) in enumerate(zip(raw, js["tokens"])) if preprocess(t) != toks]
    print(f"[전처리] 원본 {len(raw)}건 중 Python과 다른 문서 {len(bad)}건")
    if bad:
        failures.append(f"전처리 불일치 {bad[:5]}")

    # 2. 검색
    expected = {}
    lengths = np.array([len(t) for t in corpus.tokens], dtype=np.float64)
    for v in TF_VARIANTS:
        vec = TfidfVectorizerNP(tf=v, min_df=MIN_DF, max_df=MAX_DF)
        X = vec.fit_transform(corpus.tokens)
        norms = np.sqrt(np.einsum("ij,ij->i", X, X))
        for q in queries:
            qv = vec.transform([preprocess(q)])[0]
            expected[(q, "tfidf", v)] = python_hits(cosine_similarity(qv, X, norms))
        if v == "raw":
            counts = vec.counts(corpus.tokens)
            for k1, b in BM25_SETTINGS:
                model = BM25(k1, b).fit(counts, doc_lengths=lengths)
                for q in queries:
                    ids = [vec.vocabulary_[t] for t in preprocess(q) if t in vec.vocabulary_]
                    expected[(q, "bm25", f"{k1},{b}")] = python_hits(model.score(ids))
            del counts
        del X
    mism = [r for r in js["search"] if not same_hits([tuple(h) for h in r["hits"]], expected[(r["q"], r["method"], r["v"])])]
    print(f"[검색] {len(js['search'])}개 (쿼리 {len(queries)} × 방법 {len(TF_VARIANTS) + len(BM25_SETTINGS)}) top-5 순위·점수 불일치 {len(mism)}개")
    if mism:
        failures.append(f"검색 불일치 예: {mism[0]['q']} {mism[0]['method']} {mism[0]['v']}")

    # 3. 장난감 계산기
    toy_tokens = [line.split() for line in TOY]
    worst = 0.0
    for opt, mat in zip(toy_opts, js["toy"]):
        ref = TfidfVectorizerNP(tf=opt["tf"], smooth_idf=opt["smooth"], norm=None if opt["norm"] == "none" else opt["norm"]).fit_transform(toy_tokens)
        worst = max(worst, float(np.abs(ref - np.array(mat)).max()))
    print(f"[장난감 TF-IDF] {len(toy_opts)}개 설정 최대 오차 {worst:.2e}")
    if worst > 1e-12:
        failures.append("장난감 계산기 불일치")

    # 4. 페이지 구조
    html = HTML.read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    used = set(re.findall(r'\$\("([^"]+)"\)', html)) | set(re.findall(r'href="#([^"]+)"', html))
    missing = sorted(used - ids)
    print(f"[구조] 참조한 id {len(used)}개 중 없는 id {len(missing)}개 {missing}")
    if missing:
        failures.append(f"없는 id {missing}")

    print("결과:", "PASS" if not failures else "FAIL — " + "; ".join(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
