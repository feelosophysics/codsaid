"""오프라인 HTML 학습 자료를 만든다.

템플릿(study/a5-2.template.html)에 다음을 채운다.
- @@CODE:이름@@  원본 소스의 정확한 발췌(줄 번호 포함)
- @@NUM:이름@@   results/*.json에서 읽은 수치
- @@IMAGE:이름@@ results/figures의 PNG(base64)
- @@DATA@@       화면 조작용 Test 고객·SHAP·군집 변환 정보·소스 사본

브라우저 계산을 검증할 Python 기준값은 study/calculation-evidence.json에 저장한다.
먼저 `python -m src.run_all`을 실행해야 한다.
"""
import ast
import base64
import hashlib
import html
import json
import re
import sys
from itertools import permutations
from math import factorial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

STUDY = ROOT / "study"
RESULTS = ROOT / "results"
SOURCE_FILES = [
    "data_gen.py",
    "src/config.py",
    "src/data.py",
    "src/clustering.py",
    "src/personas.py",
    "src/compare.py",
    "src/model.py",
    "src/explain.py",
    "src/analysis_clustering.py",
    "src/analysis_shap.py",
    "src/report.py",
    "src/run_all.py",
    "app.py",
    "tests/test_pipeline.py",
]
# 이름: (파일, 시작 줄 접두어, 끝 줄 접두어). 끝 줄은 시작 이후 처음 나오는 줄이다.
EXCERPTS = {
    "datagen_features": ("data_gen.py", "data = {", "}"),
    "features_only": ("src/data.py", "def features_only(", "    return df[FEATURES]"),
    "scaler": ("src/clustering.py", "def fit_scaler(", "    return StandardScaler()"),
    "scan_k": ("src/clustering.py", "    rows = []\n    for k in k_range:", "    return rows"),
    "select_k": ("src/clustering.py", "    by_k = {r[\"k\"]: r for r in scan}", "    final = max("),
    "fit_final": ("src/clustering.py", "    model = kmeans(k).fit(Z)\n    rate", "    model.labels_ = remap"),
    "pca": ("src/clustering.py", "def pca_summary(", "    evr = pca"),
    "persona_sig": ("src/personas.py", "def _matches(", "    return all("),
    "rf_params": ("src/config.py", "# A5-1 최종 모델(RF + class_weight)", "}"),
    "a5_1_ref": ("src/model.py", "    expected = {k: v", "        \"params_match\":"),
    "explain": ("src/explain.py", "def explain(", "    return explanation[:, :, 1]"),
    "additivity": ("src/explain.py", "def additivity_error(", "    return float("),
    "representatives": ("src/explain.py", "    k = len(centers)\n    reps", "    approve = nearest("),
    "bands": ("src/model.py", "    oof = cross_val_predict(", "    return {\"hold\""),
    "dbscan": ("src/compare.py", "def run_dbscan(", "    labels = DBSCAN("),
    "knee": ("src/compare.py", "def knee(", "    return float("),
    "app_core": ("app.py", "x = pd.DataFrame([values]", "case = explain.case_detail("),
    "test_rule": ("tests/test_pipeline.py", "    def test_select_k_rule(", "        self.assertEqual(sel[\"final_k\"]"),
}
# 페이지의 Shapley 장난감 실험 기준값(Python으로 순열을 모두 세어 계산)
TOY_GAMES = [
    {"": 0.50, "A": 0.40, "B": 0.70, "C": 0.55, "AB": 0.62, "AC": 0.45, "BC": 0.80, "ABC": 0.72},
    {"": 0.50, "A": 0.50, "B": 0.50, "C": 0.50, "AB": 0.50, "AC": 0.50, "BC": 0.50, "ABC": 0.90},
    {"": 0.20, "A": 0.30, "B": 0.20, "C": 0.20, "AB": 0.30, "AC": 0.30, "BC": 0.20, "ABC": 0.30},
]


def digest(data: bytes, text=False) -> str:
    # Git 체크아웃의 LF/CRLF 차이는 무시하고, 이미지 등 바이너리는 원래 바이트로 비교한다.
    if text:
        data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def find_block(lines, begin, end):
    """begin/end 접두어는 여러 줄일 수 있다(\\n으로 연결)."""
    b = begin.split("\n")
    start = next(i for i in range(len(lines)) if all(lines[i + k].startswith(b[k]) for k in range(len(b))))
    finish = next(i for i in range(start + 1, len(lines)) if lines[i].startswith(end))
    return start, finish


def render_excerpt(name, file, lines, start, finish):
    # 줄마다 블록(flex) 요소이므로 사이에 줄바꿈 문자를 넣으면 <pre> 안에서 빈 줄이 생긴다.
    body = "".join(
        f'<span class="code-line"><span class="line-num" aria-hidden="true">{i + 1}</span>'
        f"<span>{html.escape(lines[i]) or ' '}</span></span>"
        for i in range(start, finish + 1)
    )
    return (
        f'<figure class="code-block" data-excerpt="{name}"><figcaption>'
        f"<span>{file} · L{start + 1}–L{finish + 1}</span>"
        f'<button type="button" class="source-link" data-file="{file}" data-line="{start + 1}">전체 코드에서 보기</button>'
        f"</figcaption><pre><code>{body}</code></pre></figure>"
    )


def shapley(game: dict) -> dict:
    """세 플레이어 A·B·C의 정확한 Shapley 값: 모든 순서에서 한계 기여의 평균."""
    players = "ABC"
    key = lambda s: "".join(sorted(s))
    out = {p: 0.0 for p in players}
    for order in permutations(players):
        seen = ""
        for p in order:
            out[p] += game[key(seen + p)] - game[key(seen)]
            seen += p
    return {p: v / factorial(len(players)) for p, v in out.items()}


def evidence(test, cl):
    tf = cl["transform"]
    rows = np.asarray(test["rows"], dtype=float)
    Z = (rows - tf["scaler_mean"]) / tf["scaler_scale"]
    pairs = [(0, 1), (5, 17), (100, 1999)]
    dist = []
    for a, b in pairs:
        raw = (rows[a] - rows[b]) ** 2
        sc = (Z[a] - Z[b]) ** 2
        dist.append({"a": a, "b": b, "raw": float(np.sqrt(raw.sum())), "scaled": float(np.sqrt(sc.sum())),
                     "raw_share": (raw / raw.sum()).tolist(), "scaled_share": (sc / sc.sum()).tolist()})
    return {
        "distance_cases": dist,
        "toy_games": [{"game": g, "shapley": shapley(g)} for g in TOY_GAMES],
        "selection": cl["selection"],
    }


def numbers(cl, sh, test):
    """본문에 들어갈 수치. 키는 템플릿의 @@NUM:키@@와 같다."""
    f3 = lambda v: f"{v:.3f}"
    f4 = lambda v: f"{v:.4f}"
    pct = lambda v, d=1: f"{v * 100:.{d}f}%"
    sel = cl["selection"]
    scan = {r["k"]: r for r in cl["scan"]}
    m = sh["model"]
    ref = m["a5_1"]
    evr = cl["pca"]["explained_variance_ratio"]
    out = {
        "rows": f"{cl['data']['rows']:,}",
        "overdue_rate": pct(cl["data"]["overdue_rate"], 2),
        "corr_max": f"{cl['data']['feature_correlation_max']:.3f}",
        "final_k": str(sel["final_k"]),
        "best_k": str(sel["best_silhouette_k"]),
        "cutoff": f4(sel["cutoff"]),
        "within": ", ".join(map(str, sel["within_one_se"])),
        "stable": ", ".join(map(str, sel["stable"])),
        "sil_full": f4(cl["silhouette_full"]),
        "pc1": pct(evr[0]), "pc2": pct(evr[1]), "pc12": pct(evr[0] + evr[1]), "pc_last": pct(evr[-1]),
        "cv_f1": f"{m['cv']['f1_mean']:.3f}±{m['cv']['f1_std']:.3f}",
        "a51_cv_f1": f"{ref['cv']['f1_mean']:.3f}±{ref['cv']['f1_std']:.3f}" if ref.get("available") else "-",
        "base_value": f3(sh["base_value"]),
        "additivity": f"{sh['additivity_error']:.1e}",
        "hold": f3(sh["bands"]["hold"]),
        "test_rows": f"{len(test['rows']):,}",
    }
    for r in cl["scan"]:
        k = r["k"]
        out[f"k{k}.sil"] = f4(r["silhouette_mean"])
        out[f"k{k}.ari"] = f3(r["ari_mean"])
    for key in ("precision", "recall", "f1", "roc_auc", "pr_auc", "accuracy"):
        out[f"test.{key}"] = f3(m["test"][key])
        if ref.get("available"):
            out[f"a51.{key}"] = f3(ref["test"][key])
    for p, n in zip(cl["profiles"], cl["personas"]):
        c = p["cluster"]
        out[f"c{c}.name"] = n["ko"]
        out[f"c{c}.size"] = f"{p['size']:,}"
        out[f"c{c}.share"] = pct(p["share"])
        out[f"c{c}.rate"] = pct(p["overdue_rate"])
        for f, v in p["mean"].items():
            out[f"c{c}.{f}"] = f"{v:,.0f}" if f == "annual_income" else (f"{v:.2f}" if f in ("debt_ratio", "overdue_count_6m") else f"{v:.1f}")
    for i, r in enumerate(sh["global"], start=1):
        out[f"g{i}.feature"] = r["feature"]
        out[f"g{i}.share"] = pct(r["share"])
        out[f"g{i}.dir"] = f"{r['direction']:+.2f}"
        out[f"g{i}.mean"] = f3(r["mean_abs_shap"])
    out["top3_share"] = pct(sum(r["share"] for r in sh["global"][:3]))
    for key in ("reject_case", "approve_case"):
        c = sh["cases"][key]
        tag = key.split("_")[0]
        out[f"{tag}.proba"] = f3(c["proba"])
        out[f"{tag}.actual"] = str(c["actual_overdue"])
        out[f"{tag}.score"] = f"{c['credit_score']:.0f}"
        out[f"{tag}.cluster"] = f"C{c['cluster']} {cl['personas'][c['cluster']]['ko']}"
        out[f"{tag}.row"] = str(c["row"])
        for r in c["contributions"]:
            out[f"{tag}.{r['feature']}.v"] = f"{r['value']:g}"
            out[f"{tag}.{r['feature']}.s"] = f"{r['shap']:+.3f}"
    rep0 = sh["cases"]["cluster_representatives"][0]
    out["rep0.proba"] = f3(rep0["proba"])
    out["rep0.actual"] = str(rep0["actual_overdue"])
    for r in sh["cluster_shap"]:
        c = r["cluster"]
        out[f"cs{c}.proba"] = f"{r['mean_proba']:.2f}"
        for f, v in r["mean_shap"].items():
            out[f"cs{c}.{f}"] = f"{v:+.3f}"
    dep = sh["dependence"]
    for o, v in dep["income_crossing"].items():
        out[f"cross{o}"] = f"{v:,.0f}" if v is not None else "-"
    for o, v in dep["theoretical_income_boundary"].items():
        out[f"bound{o}"] = f"{v:,.0f}"
    lv = {r["bin"]: r["shap_mean"] for r in dep["overdue_levels"]}
    for k_, v in lv.items():
        out[f"od{int(float(k_))}"] = f"{v:+.3f}"
    debt = dep["debt_ratio"]
    out["debt_low"] = f"{debt[0]['shap_mean']:+.3f}"
    out["debt_high"] = f"{debt[-1]['shap_mean']:+.3f}"
    inc = [r for r in dep["income_by_overdue"]]
    top_bin = inc[-1]["bin"]
    out["inc_top0"] = f"{next(r['shap_mean'] for r in inc if r['bin'] == top_bin and r['group'].endswith('=0')):+.3f}"
    out["inc_top1"] = f"{next(r['shap_mean'] for r in inc if r['bin'] == top_bin and r['group'].endswith('>=1')):+.3f}"
    for b in ("approve", "review", "reject"):
        out[f"band.{b}"] = f"{sh['test_band_counts'][b]:,}"
        out[f"band.{b}.overdue"] = f"{sh['test_overdue_by_band'][b]:,}"
    for c, row in sh["cluster_band_crosstab"].items():
        for b, v in row.items():
            out[f"ct{c}.{b}"] = f"{v:,}"
    cmp = cl["comparison"]
    for r in cmp["table"]:
        key = re.sub(r"[^a-z]+", "_", r["method"].lower()).strip("_")
        out[f"cmp.{key}.sil"] = f3(r["silhouette"]) if r["silhouette"] is not None else "-"
        out[f"cmp.{key}.ari"] = f3(r["ari_vs_kmeans"])
        out[f"cmp.{key}.sizes"] = ", ".join(f"{s:,}" for s in r["sizes"])
        out[f"cmp.{key}.k"] = str(r["clusters"])
    db = cmp["dbscan"]
    out["db.eps"] = f3(db["eps"])
    out["db.ms"] = str(db["min_samples"])
    out["db.noise"] = pct(db["noise_share"])
    return out


def main():
    cl = json.loads((RESULTS / "clustering.json").read_text(encoding="utf-8"))
    sh = json.loads((RESULTS / "shap.json").read_text(encoding="utf-8"))
    test = json.loads((RESULTS / "test_explanations.json").read_text(encoding="utf-8"))
    manifest = {"mission": "A5-2", "hash_mode": "UTF-8 text: CRLF normalized to LF; binary: exact bytes",
                "files": {}, "excerpts": {}}
    sources = {}
    for file in SOURCE_FILES:
        data = (ROOT / file).read_bytes()
        text = data.decode("utf-8").replace("\r\n", "\n")
        symbols = [{"name": n.name, "line": n.lineno} for n in ast.walk(ast.parse(text))
                   if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
        sources[file] = {"text": text, "symbols": sorted(symbols, key=lambda s: s["line"])}
        manifest["files"][file] = digest(data, text=True)

    template = (STUDY / "a5-2.template.html").read_text(encoding="utf-8")
    for name, (file, begin, end) in EXCERPTS.items():
        lines = sources[file]["text"].splitlines()
        start, finish = find_block(lines, begin, end)
        manifest["excerpts"][name] = {"file": file, "start": start + 1, "end": finish + 1,
                                      "text": "\n".join(lines[start:finish + 1])}
        template = template.replace(f"@@CODE:{name}@@", render_excerpt(name, file, lines, start, finish))

    nums = numbers(cl, sh, test)
    template = re.sub(r"@@NUM:([A-Za-z0-9_.]+)@@",
                      lambda mt: html.escape(nums[mt.group(1)]) if mt.group(1) in nums
                      else (_ for _ in ()).throw(KeyError(mt.group(1))), template)

    for image in sorted((RESULTS / "figures").glob("*.png")):
        raw = image.read_bytes()
        template = template.replace(f"@@IMAGE:{image.stem}@@", "data:image/png;base64," + base64.b64encode(raw).decode())
        manifest["files"][image.relative_to(ROOT).as_posix()] = digest(raw)
    for file in ["results/clustering.json", "results/shap.json", "results/test_explanations.json"]:
        manifest["files"][file] = digest((ROOT / file).read_bytes(), text=True)

    dataset = {
        **{k: test[k] for k in ("features", "rows", "y", "proba", "base_value", "shap", "cluster", "pca", "bands")},
        "transform": cl["transform"],
        "scan": cl["scan"],
        "selection": cl["selection"],
        "min_ari": 0.5,
        "personas": [{k: p[k] for k in ("cluster", "ko", "en", "summary", "target", "message", "action")}
                     for p in cl["personas"]],
        "profiles": [{k: p[k] for k in ("cluster", "size", "share", "mean", "z", "overdue_rate")} for p in cl["profiles"]],
        "cases": {k: sh["cases"][k]["row"] for k in ("reject_case", "approve_case")},
        "sources": sources,
    }
    embedded = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    template = template.replace("@@DATA@@", embedded)
    left = re.findall(r"@@[A-Z]+[:@][^@]*@?@?", template)
    if left:
        raise RuntimeError(f"채워지지 않은 자리표시자: {left[:5]}")

    (STUDY / "a5-2.html").write_text(template, encoding="utf-8")
    (STUDY / "calculation-evidence.json").write_text(
        json.dumps(evidence(test, cl), ensure_ascii=False, indent=1), encoding="utf-8")
    (STUDY / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    size = len(template.encode("utf-8"))
    print(f"Built study/a5-2.html: {len(EXCERPTS)} excerpts, {len(sources)} sources, "
          f"{len(list((RESULTS / 'figures').glob('*.png')))} figures, {size:,} bytes")


if __name__ == "__main__":
    main()
