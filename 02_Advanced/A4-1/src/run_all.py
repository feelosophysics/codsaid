"""전체 실험을 실행하고 결과를 outputs/에 저장한다.

    python -m src.run_all
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .classify import explain_errors, run_classification
from .data import CATEGORIES, MIN_TOKENS, ROOT, load_corpus
from .preprocess import EMAIL_RE
from .experiments import (
    HAND_QUERIES, RetrievalSplit, benchmark_index, bow_limits, compare_bm25_tfidf,
    mean_result_length, sample_short_queries, verify_against_sklearn, verify_cosine,
)
from .search import MAX_DF, MIN_DF, SearchEngine
from .tfidf import TF_VARIANTS

OUT = ROOT / "outputs"
SHORT = {name: name.split(".")[-1] for name in CATEGORIES}  # graphics, x, baseball, hockey, space
EXAMPLE_QUERIES = ["space shuttle launch", "hockey playoff goalie", "x window server display",
                   "3d rendering image format", "baseball pitcher"]


class Log:
    """콘솔과 파일에 같은 내용을 쓴다."""

    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []

    def __call__(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def save_json(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- 단계별
def step_verification(corpus, engine) -> dict:
    log = Log(OUT / "tfidf_verification.txt")
    rows = verify_against_sklearn(corpus.tokens)
    log("=== TF-IDF 구현 검증 결과 ===")
    log(f"데이터: 20 Newsgroups {len(CATEGORIES)}개 범주, 전처리 후 문서 {len(corpus)}건")
    log(f"TF-IDF 행렬 shape: {tuple(rows[0]['shape'])}  (min_df={MIN_DF}, max_df={MAX_DF})")
    log("sklearn 공통 설정: TfidfVectorizer(analyzer=<같은 토큰 리스트>, "
        f"min_df={MIN_DF}, max_df={MAX_DF}, dtype=float64)")
    log()
    for r in rows:
        s = r["sklearn"]
        log(f"[검증] 직접 구현(tf={r['ours']['tf']}) vs Scikit-learn")
        log(f"  - sklearn 설정: smooth_idf={s['smooth_idf']}, sublinear_tf={s['sublinear_tf']}, "
            f"norm={s['norm']!r}, binary={s['binary']}")
        log(f"  - 어휘 일치: {r['vocabulary_equal']}, IDF 최대 오차: {r['idf_max_error']:.2e}")
        log(f"  - 최대 오차: {r['max_error']:.2e}")
        log(f"  - 평균 오차: {r['mean_error']:.2e}")
        log(f"  - 결과: {'PASS' if r['pass'] else 'FAIL'} (허용 오차 1e-6 이내)")
    cos_err = verify_cosine(engine, [q for q, _ in HAND_QUERIES])
    log()
    log(f"[검증] 코사인 유사도 직접 구현 vs sklearn.metrics.pairwise.cosine_similarity "
        f"(평가 쿼리 {len(HAND_QUERIES)}개): 최대 오차 {cos_err:.2e}")
    log(f"전체 {len(rows)}개 설정 PASS: {all(r['pass'] for r in rows)}")
    log.save()
    save_json("tfidf_verification.json", {"configs": rows, "cosine_max_error": cos_err})
    return {"all_pass": all(r["pass"] for r in rows), "n_configs": len(rows),
            "max_error": max(r["max_error"] for r in rows), "cosine_max_error": cos_err,
            "shape": rows[0]["shape"]}


def step_search_examples(engine) -> None:
    log = Log(OUT / "search_examples.txt")
    names = engine.corpus.target_names
    for q in EXAMPLE_QUERIES:
        log("=== 검색 결과 (TF-IDF 코사인) ===")
        log(f'Query: "{q}"  →  토큰 {engine.query_tokens(q)}')
        log("Top 5 결과:")
        for rank, h in enumerate(engine.search(q), 1):
            cat = names[engine.corpus.labels[engine.position(h.doc_id)]]
            log(f'{rank}. [{h.score:.3f}] doc {h.doc_id} ({cat}) "{h.snippet[:90]}"')
        log()
    q = EXAMPLE_QUERIES[0]
    top = engine.search(q, topk=1)[0]
    ex = engine.explain(q, top.doc_id)
    log("=== 코사인 유사도 계산 예시 ===")
    log(f'Query: "{q}"  /  문서 doc {top.doc_id}')
    log("겹치는 단어: q_t × d_t")
    for term, qw, dw, prod in ex["shared"]:
        log(f"  {term:<10} {qw:.4f} × {dw:.4f} = {prod:.4f}")
    log(f"코사인 유사도 = (Query · 문서) / (||Query|| × ||문서||)")
    log(f"            = {ex['dot']:.4f} / ({ex['query_norm']:.4f} × {ex['doc_norm']:.4f}) = {ex['cosine']:.4f}")
    log(f"(문서 벡터의 0이 아닌 칸 {ex['doc_nonzero']}개 중 쿼리와 겹치는 칸만 내적에 기여한다."
        " 두 벡터 모두 L2 정규화돼 노름이 1이므로 내적이 곧 코사인이다)")
    log.save()


def plot_confusion(cm: np.ndarray, labels: list[str], path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 5.4), dpi=130)
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def step_classification(corpus) -> tuple:
    log = Log(OUT / "classification.txt")
    res = run_classification(corpus, tf="raw")
    labels = [SHORT[n] for n in corpus.target_names]
    log("=== 분류 성능 평가 ===")
    log("모델: Logistic Regression (sklearn, lbfgs, max_iter=2000, random_state=42)")
    log(f"특성: 직접 구현 TF-IDF (tf=raw, smooth_idf=True, norm='l2', min_df={MIN_DF}, max_df={MAX_DF}), "
        f"Train으로만 학습한 어휘 {len(res.vectorizer.terms_)}개")
    log(f"데이터: Train {len(res.train_idx)} / Test {len(res.test_idx)} (8:2, stratify, random_state=42)")
    log("C 선택(Train 5-fold 교차검증, macro F1): "
        + ", ".join(f"C={c:g}: {s:.4f}" for c, s in res.cv_scores.items()) + f" → C={res.C:g}")
    log()
    log(f"정확도: {res.accuracy:.4f}")
    log(f"F1-Score (macro): {res.f1_macro:.4f}")
    log()
    log(f"{'범주':<20}{'precision':>10}{'recall':>10}{'f1':>10}{'support':>9}")
    for name, m in res.per_class.items():
        log(f"{name:<20}{m['precision']:>10.4f}{m['recall']:>10.4f}{m['f1']:>10.4f}{m['support']:>9}")
    log()
    log("혼동 행렬 (행=실제, 열=예측): " + ", ".join(labels))
    for name, row in zip(labels, res.confusion):
        log(f"  {name:<9}" + "".join(f"{v:>6}" for v in row))
    log.save()
    plot_confusion(res.confusion, labels, OUT / "confusion_matrix.png",
                   f"TF-IDF + Logistic Regression (acc {res.accuracy:.3f}, macro F1 {res.f1_macro:.3f})")

    cases = explain_errors(res, corpus)
    for c in cases:  # 공개 저장소에 올라가는 결과물이므로 게시글 작성자의 이메일 주소는 가린다
        c["text"] = EMAIL_RE.sub("[email]", c["text"])
    save_json("misclassified.json", [{k: v for k, v in c.items() if k != "text"} | {"text": c["text"][:1500]}
                                     for c in cases])
    lines = [f"# 오분류 문서 {len(cases)}건 (Test {len(res.test_idx)}건 중)", "",
             "toward_predicted: x_j·(w_예측 − w_실제)가 큰 단어 — 예측 범주 쪽으로 끌어당긴 단어",
             "toward_actual: 반대로 실제 범주 쪽을 지지한 단어", ""]
    for c in cases:
        text = " ".join(c["text"].split())
        lines += [
            f"## doc {c['doc_id']}: 실제 {c['actual']} → 예측 {c['predicted']} (확률 {c['confidence']:.2f})",
            f"- 토큰 {c['n_tokens']}개, 어휘에 걸린 단어 {c['n_known_terms']}개",
            "- toward_predicted: " + ", ".join(f"{t}({w})" for t, w in c["toward_predicted"]),
            "- toward_actual: " + ", ".join(f"{t}({w})" for t, w in c["toward_actual"]),
            f"- 본문: {text[:400]}{'...' if len(text) > 400 else ''}", "",
        ]
    (OUT / "misclassified.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {"accuracy": res.accuracy, "f1_macro": res.f1_macro, "C": res.C, "cv_scores": res.cv_scores,
               "n_train": len(res.train_idx), "n_test": len(res.test_idx), "n_terms": len(res.vectorizer.terms_),
               "per_class": res.per_class, "confusion": res.confusion.tolist(), "n_errors": len(cases)}
    save_json("classification.json", summary)
    return res, summary


def step_tf_variants(corpus, base, split: RetrievalSplit) -> list:
    log = Log(OUT / "tf_variants.txt")
    rows = []
    for tf in TF_VARIANTS:
        res = base if tf == "raw" else run_classification(corpus, tf=tf, C=base.C)
        ret = split.tfidf(tf)
        rows.append({"tf": tf, "accuracy": res.accuracy, "f1_macro": res.f1_macro,
                     "doc_P@10": ret["doc_queries"]["P@10"], "doc_MAP@10": ret["doc_queries"]["MAP@10"],
                     "hand_P@5": ret["hand_queries"]["P@5"], "hand_P@10": ret["hand_queries"]["P@10"]})
    log("=== TF 변형 비교 (보너스 1) ===")
    log(f"분류: 같은 분할·같은 C={base.C:g}. 검색: Train {len(split.d_labels)}건 색인, "
        f"Test {len(split.q_labels)}건을 쿼리로(같은 범주=관련), 평가 쿼리 {len(HAND_QUERIES)}개")
    log(f"{'tf':<8}{'acc':>8}{'F1':>8}{'docP@10':>10}{'docMAP@10':>11}{'handP@5':>9}{'handP@10':>10}")
    for r in rows:
        log(f"{r['tf']:<8}{r['accuracy']:>8.4f}{r['f1_macro']:>8.4f}{r['doc_P@10']:>10.4f}"
            f"{r['doc_MAP@10']:>11.4f}{r['hand_P@5']:>9.3f}{r['hand_P@10']:>10.3f}")
    log.save()
    with open(OUT / "tf_variants.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metrics = [("accuracy", "Accuracy"), ("f1_macro", "Macro F1"), ("doc_MAP@10", "Doc-query MAP@10"),
               ("hand_P@10", "Hand-query P@10")]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=130)
    width = 0.2
    x = np.arange(len(metrics))
    for i, r in enumerate(rows):
        ax.bar(x + (i - 1.5) * width, [r[m] for m, _ in metrics], width, label=r["tf"])
    ax.set_xticks(x, [label for _, label in metrics])
    lo = min(r[m] for r in rows for m, _ in metrics)
    ax.set_ylim(max(0.0, lo - 0.08), 1.0)
    ax.set_title("TF variants: classification and retrieval")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "tf_variants.png")
    plt.close(fig)
    return rows


def step_bm25(engine, split: RetrievalSplit, tfidf_raw: dict) -> dict:
    log = Log(OUT / "bm25_vs_tfidf.txt")
    base = split.bm25()
    grid_k1, grid_b = (0.5, 1.2, 1.5, 2.0), (0.0, 0.25, 0.5, 0.75, 1.0)
    grid = np.zeros((len(grid_k1), len(grid_b)))
    grid_hand = np.zeros_like(grid)
    for i, k1 in enumerate(grid_k1):
        for j, b in enumerate(grid_b):
            r = split.bm25(k1, b)
            grid[i, j] = r["doc_queries"]["MAP@10"]
            grid_hand[i, j] = r["hand_queries"]["P@10"]
    lengths = mean_result_length(engine, [q for q, _ in HAND_QUERIES])
    compare = compare_bm25_tfidf(engine, EXAMPLE_QUERIES)

    log("=== BM25 vs TF-IDF (보너스 2) ===")
    log("BM25 설정: k1=1.5, b=0.75, idf=ln((N-df+0.5)/(df+0.5)+1), 문서 길이=전처리 후 토큰 수")
    log(f"{'방법':<8}{'docP@10':>10}{'docMAP@10':>11}{'handP@5':>9}{'handP@10':>10}")
    for name, r in (("TF-IDF", tfidf_raw), ("BM25", base)):
        log(f"{name:<8}{r['doc_queries']['P@10']:>10.4f}{r['doc_queries']['MAP@10']:>11.4f}"
            f"{r['hand_queries']['P@5']:>9.3f}{r['hand_queries']['P@10']:>10.3f}")
    log()
    log("상위 10개 결과 문서의 토큰 수(평가 쿼리 20개, 평균 / 중앙값): "
        f"TF-IDF {lengths['tfidf']:.1f} / {lengths['tfidf_median']:.0f}, "
        f"BM25 {lengths['bm25']:.1f} / {lengths['bm25_median']:.0f}, "
        f"전체 문서 {lengths['corpus_mean']:.1f} / {lengths['corpus_median']:.0f}")
    log()
    log("k1 × b 격자 — Doc-query MAP@10 (행 k1, 열 b)")
    log("        " + "".join(f"b={b:<6g}" for b in grid_b))
    for k1, row in zip(grid_k1, grid):
        log(f"k1={k1:<4g}" + "".join(f"{v:<8.4f}" for v in row))
    log("k1 × b 격자 — Hand-query P@10")
    for k1, row in zip(grid_k1, grid_hand):
        log(f"k1={k1:<4g}" + "".join(f"{v:<8.3f}" for v in row))
    log()
    for c in compare:
        log(f'Query: "{c["query"]}"  (top-5 겹침 {c["overlap"]}/5)')
        for rank, (a, b) in enumerate(zip(c["tfidf"], c["bm25"]), 1):
            log(f"  {rank}. TF-IDF doc {a['doc_id']:<5}({SHORT[a['category']]:<8}, {a['n_tokens']:>4} tok)"
                f"   BM25 doc {b['doc_id']:<5}({SHORT[b['category']]:<8}, {b['n_tokens']:>4} tok)")
        log()
    log.save()

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), dpi=130)
    for ax, data, title in ((axes[0], grid, "Doc-query MAP@10"), (axes[1], grid_hand, "Hand-query P@10")):
        im = ax.imshow(data, cmap="viridis", aspect="auto")
        ax.set_xticks(range(len(grid_b)), [f"{b:g}" for b in grid_b])
        ax.set_yticks(range(len(grid_k1)), [f"{k:g}" for k in grid_k1])
        ax.set_xlabel("b")
        ax.set_ylabel("k1")
        ax.set_title(f"BM25 {title}")
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, f"{data[i, j]:.3f}", ha="center", va="center", fontsize=8,
                        color="white" if data[i, j] < data.mean() else "black")
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(OUT / "bm25_grid.png")
    plt.close(fig)
    out = {"bm25": base, "tfidf": tfidf_raw, "grid_k1": grid_k1, "grid_b": grid_b,
           "grid_doc_map10": grid.tolist(), "grid_hand_p10": grid_hand.tolist(),
           "mean_result_length": lengths, "examples": compare}
    save_json("bm25_vs_tfidf.json", out)
    return out


def step_index(engine) -> list:
    log = Log(OUT / "index_benchmark.txt")
    queries = [q for q, _ in HAND_QUERIES] + sample_short_queries(engine, 180)
    sizes = [500, 1000, 2000, len(engine.corpus)]
    rows = benchmark_index(engine, queries, sizes)
    idx = engine.index("tfidf")
    lengths = idx.posting_lengths()
    log("=== 역색인 vs 전체 스캔 (보너스 3) ===")
    log(f"쿼리 {len(queries)}개(평가 쿼리 20 + 문서에서 뽑은 3단어 쿼리 180), 5회 반복 중 최솟값, top-5")
    log(f"전체 색인: 단어 {len(lengths)}개, 포스팅 {lengths.sum()}개, 포스팅 길이 평균 {lengths.mean():.1f} / "
        f"최대 {lengths.max()} ('{idx.terms[int(lengths.argmax())]}')")
    log(f"예: '{'shuttle'}' → 문서 {len(idx.documents('shuttle'))}개, 앞 5개 위치 {idx.documents('shuttle')[:5].tolist()}")
    log()
    log(f"{'N':>6}{'full ms':>10}{'column ms':>11}{'index ms':>10}{'N·V':>12}{'N·|q|':>9}{'Σdf(q)':>9}{'build ms':>10}  same")
    for r in rows:
        log(f"{r['n_docs']:>6}{r['full_scan_ms']:>10.3f}{r['column_scan_ms']:>11.3f}{r['index_ms']:>10.3f}"
            f"{r['ops_full']:>12}{r['ops_column']:>9.0f}{r['ops_index']:>9.1f}{r['index_build_ms']:>10.1f}  {r['same_top_k']}")
    log.save()
    with open(OUT / "index_benchmark.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), dpi=130)
    n = [r["n_docs"] for r in rows]
    for key, label in (("full_scan_ms", "full scan O(N·V)"), ("column_scan_ms", "column scan O(N·|q|)"),
                       ("index_ms", "inverted index O(Σdf)")):
        axes[0].plot(n, [r[key] for r in rows], marker="o", label=label)
    axes[0].set_xlabel("documents N")
    axes[0].set_ylabel("ms / query")
    axes[0].set_yscale("log")
    axes[0].set_title("Query time")
    axes[0].legend()
    for key, label in (("ops_full", "N·V"), ("ops_column", "N·|q|"), ("ops_index", "Σ df(q)")):
        axes[1].plot(n, [r[key] for r in rows], marker="o", label=label)
    axes[1].set_xlabel("documents N")
    axes[1].set_ylabel("multiply-adds / query")
    axes[1].set_yscale("log")
    axes[1].set_title("Work per query")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(OUT / "index_benchmark.png")
    plt.close(fig)
    save_json("index_benchmark.json", rows)
    return rows


def step_bow(engine) -> dict:
    log = Log(OUT / "bow_limits.txt")
    b = bow_limits(engine)
    log("=== BoW 한계 분석 ===")
    titles = {"word_order": "문제 1: 어순 무시", "negation": "문제 2: 부정어 소실(불용어 'not')",
              "synonym": "문제 3: 동의어 불일치"}
    for key, title in titles.items():
        d = b[key]
        log(f"[{title}]")
        log(f'"{d["a"]}" → {d["tokens_a"]}')
        log(f'"{d["b"]}" → {d["tokens_b"]}')
        extra = f", 각 검색 top-10 겹침 {d['top10_overlap']}/10" if key == "synonym" else ""
        log(f"→ 두 TF-IDF 벡터의 코사인 유사도 = {d['cosine']:.4f}{extra}")
        log()
    log("[문제 4: 다의어]")
    for word, hits in b["polysemy"].items():
        cats = [SHORT[h["category"]] for h in hits]
        log(f'"{word}" top-10 범주: {cats}')
        for h in hits[:4]:
            log(f"    doc {h['doc_id']} ({SHORT[h['category']]}): {h['snippet'][:90]}")
    log()
    ko = b["korean"]
    log("[언어별 토큰화: 한국어 공백 토큰화 vs 형태소 토큰화(손으로 나눈 예)]")
    for name in ("whitespace", "morpheme"):
        log(f"{name}: {ko[name]['tokens']} → 코사인 {ko[name]['cosine']:.4f}")
    log.save()
    save_json("bow_limits.json", b)
    return b


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    started = time.perf_counter()
    corpus = load_corpus()
    counts = np.bincount(corpus.labels, minlength=len(corpus.target_names))
    print(f"문서 {corpus.n_raw}건 중 토큰 {MIN_TOKENS}개 미만 {corpus.n_raw - len(corpus)}건 제거 → {len(corpus)}건")
    engine = SearchEngine(corpus)

    summary = {
        "data": {"categories": corpus.target_names, "n_raw": corpus.n_raw, "n_docs": len(corpus),
                 "per_category": dict(zip(corpus.target_names, counts.tolist())),
                 "median_tokens": float(np.median([len(t) for t in corpus.tokens])),
                 "vocabulary": len(engine.vectorizer.terms_)},
        "verification": step_verification(corpus, engine),
    }
    step_search_examples(engine)
    base, summary["classification"] = step_classification(corpus)
    split = RetrievalSplit(corpus, base.train_idx, base.test_idx)
    summary["tf_variants"] = step_tf_variants(corpus, base, split)
    bm = step_bm25(engine, split, split.tfidf("raw"))
    summary["bm25"] = {k: bm[k] for k in ("mean_result_length",)} | {
        "bm25": {k: v for k, v in bm["bm25"]["doc_queries"].items()} | {"hand_P@10": bm["bm25"]["hand_queries"]["P@10"]},
        "tfidf": {k: v for k, v in bm["tfidf"]["doc_queries"].items()} | {"hand_P@10": bm["tfidf"]["hand_queries"]["P@10"]},
    }
    summary["index_benchmark"] = step_index(engine)
    step_bow(engine)
    summary["elapsed_sec"] = round(time.perf_counter() - started, 1)
    save_json("summary.json", summary)
    print(f"\n완료: {summary['elapsed_sec']}초, 결과는 {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
