"""오프라인 HTML 학습 자료를 만든다.

템플릿(study/a5-1.template.html)에 다음을 채운다.
- @@CODE:이름@@  원본 소스의 정확한 발췌(줄 번호 포함)
- @@NUM:이름@@   results/metrics.json에서 읽은 수치
- @@IMAGE:이름@@ results/figures의 PNG(base64)
- @@DATA@@       화면 조작용 Test 데이터·예측 확률·계수 경로·소스 사본

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
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from src.baseline import RULES, rule_hits  # noqa: E402
from src.classification import classification_metrics  # noqa: E402

STUDY = ROOT / "study"
RESULTS = ROOT / "results"
SOURCE_FILES = [
    "data_gen.py",
    "src/config.py",
    "src/data.py",
    "src/baseline.py",
    "src/features.py",
    "src/regression.py",
    "src/classification.py",
    "src/diagnostics.py",
    "src/report.py",
    "src/run_all.py",
    "tests/test_pipeline.py",
]
# 이름: (파일, 시작 줄 접두어, 끝 줄 접두어). 끝 줄은 시작 이후 처음 나오는 줄이다.
EXCERPTS = {
    "datagen_score": ("data_gen.py", "df['credit_score'] = (", "df['credit_score'] = df['credit_score'].clip"),
    "datagen_label": ("data_gen.py", "threshold = df['credit_score']", ")"),
    "features_const": ("src/config.py", "# 원본 6개 입력 변수", "CLASSIFICATION_TARGET ="),
    "split": ("src/data.py", "def split_data(", "    return Split("),
    "rules": ("src/baseline.py", "RULES = [", "]"),
    "rule_if": ("src/baseline.py", "def rule_based_predict(", "    return 0"),
    "rule_score": ("src/baseline.py", "    def risk_score(", "        return np.column_stack("),
    "derived": ("src/features.py", "class DerivedFeatures(", "        return X"),
    "preprocessor": ("src/features.py", "def build_preprocessor(", '            ("columns", columns),'),
    "ridge_lasso": ("src/regression.py", "MODELS = {", "}"),
    "tune_reg": ("src/regression.py", "    for name, factory in MODELS.items():\n        search", "        predictions[name] = pred"),
    "grids": ("src/classification.py", "RF_GRID = {", "}  # 16개"),
    "imb_pipeline": ("src/classification.py", "def make_pipeline(", "    return Pipeline(steps)"),
    "gridsearch": ("src/classification.py", "        if grid:", "            n_candidates = len("),
    "select": ("src/classification.py", "def select_final(", '    return {"best_cv"'),
    "policy": ("src/classification.py", "def decision_policy(", "    hold_t = min("),
    "permutation": ("src/diagnostics.py", "def permutation_on_test(", "    result = permutation_importance("),
    "learning_curve": ("src/diagnostics.py", "def classification_learning_curve(", "    return _curve("),
    "test_leak": ("tests/test_pipeline.py", "    def test_fit_uses_train_only(", "        ))"),
    "test_smote": ("tests/test_pipeline.py", "    def test_smote_lives_inside_imblearn_pipeline(", "        self.assertEqual(len("),
}
RULE_SUBSETS = [
    ["R1", "R2", "R3", "R4", "R5", "R6"],
    ["R1", "R2", "R3", "R4", "R5"],
    ["R1"],
    ["R2", "R3"],
    ["R6"],
    ["R1", "R4"],
]
THRESHOLDS = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8]


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


def metric_case(y, pred, score):
    m = classification_metrics(y, pred, score)
    return {k: m[k] for k in ["accuracy", "precision", "recall", "f1", "roc_auc", "confusion"]}


def evidence(pred_data):
    X = pd.DataFrame(pred_data["rows"], columns=pred_data["features"])
    y = np.asarray(pred_data["is_overdue"])
    hits = rule_hits(X)
    rule_cases = []
    for subset in RULE_SUBSETS:
        score = hits[subset].sum(axis=1).to_numpy()
        rule_cases.append({"rules": subset, **metric_case(y, (score > 0).astype(int), score)})
    threshold_cases = []
    for model, proba in pred_data["proba"].items():
        p = np.asarray(proba)
        for t in THRESHOLDS:
            case = metric_case(y, (p >= t).astype(int), p)
            threshold_cases.append({"model": model, "threshold": t, **case})
    band_cases = []
    p = np.asarray(pred_data["proba"][pred_data["final"]])
    for hold, reject in [(pred_data["policy"]["hold"], pred_data["policy"]["reject"]), (0.1, 0.5), (0.3, 0.3), (0.05, 0.9)]:
        masks = {"approve": p < hold, "hold": (p >= hold) & (p < reject), "reject": p >= reject}
        band_cases.append({
            "hold": hold, "reject": reject,
            "bands": {k: {"customers": int(m.sum()), "overdue": int(y[m].sum())} for k, m in masks.items()},
        })
    # 규칙 정의는 JavaScript가 그대로 읽으므로, 정의를 바꾸면 위 사례도 자동으로 다시 계산된다.
    return {"rule_cases": rule_cases, "threshold_cases": threshold_cases, "band_cases": band_cases,
            "rule_hit_counts": {k: int(v) for k, v in hits.sum().items()}}


def numbers(m, pred):
    """본문에 들어갈 수치. 키는 템플릿의 @@NUM:키@@와 같다."""
    f3 = lambda v: f"{v:.3f}"
    pct = lambda v, d=1: f"{v * 100:.{d}f}%"
    clf = m["classification"]["models"]
    sel = m["classification"]["selection"]
    final = sel["final"]
    pol = m["classification"]["policy"]
    ora = m["classification"]["oracle_ceiling"]
    reg = m["regression"]["comparison"]
    data = m["data"]
    lasso_alpha = reg["Lasso"]["alpha"]
    lasso_rows = {r["alpha"]: r for r in m["regression"]["paths"]["Lasso"]}
    perm_final = m["diagnostics"]["permutation"][final]
    perm_top = list(perm_final)
    out = {
        "rows": f"{data['rows']:,}",
        "overdue_rate": pct(data["overdue_rate"], 2),
        "income_floor_rows": f"{data['income_floor_rows']:,}",
        "train_rows": f"{m['split']['train']:,}",
        "test_rows": f"{m['split']['test']:,}",
        "test_overdue": f"{pol['test_total_overdue']:,}",
        "final_model": final,
        "best_cv_model": sel["best_cv"],
        "contrast_model": m["classification"]["comparison"]["contrast"],
        "tree_model": m["diagnostics"]["tree_model"],
        "cutoff": f3(sel["cutoff"]),
        "within": ", ".join(sel["within_one_std"]),
        "oracle_precision": f3(ora["precision"]),
        "oracle_recall": f3(ora["recall"]),
        "oracle_f1": f3(ora["f1"]),
        "hold_t": f3(pol["hold_threshold"]),
        "reject_t": f3(pol["reject_threshold"]),
        "lasso_alpha": str(lasso_alpha),
        "ridge_alpha": str(reg["Ridge"]["alpha"]),
        "lasso_rmse": f"{reg['Lasso']['test']['rmse']:.2f}",
        "lasso_mae": f"{reg['Lasso']['test']['mae']:.2f}",
        "lasso_r2": f"{reg['Lasso']['test']['r2']:.4f}",
        "ridge_rmse": f"{reg['Ridge']['test']['rmse']:.2f}",
        "mean_rmse": f"{reg['Mean baseline']['test']['rmse']:.2f}",
        "lasso1_zero": ", ".join(lasso_rows[1]["zero_coefficients"]),
        "lasso10_rmse": f"{lasso_rows[10]['test']['rmse']:.2f}",
        "perm_first": perm_top[0],
        "perm_second": perm_top[1],
        "perm_third": perm_top[2],
    }
    for name, v in clf.items():
        key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            out[f"{key}.{metric}"] = f3(v["test"][metric])
        if v["cv"]:
            out[f"{key}.cv_f1"] = f"{v['cv']['f1_mean']:.3f}±{v['cv']['f1_std']:.3f}"
        if v.get("best_params"):
            out[f"{key}.params"] = ", ".join(f"{k}={p}" for k, p in v["best_params"].items())
            out[f"{key}.grid"] = str(v["grid_candidates"])
        c = v["test"]["confusion"]
        for k in "tn fp fn tp".split():
            out[f"{key}.{k}"] = f"{c[k]:,}"
    # 규칙 R6(카드 수)을 끄기 전후
    X = pd.DataFrame(pred["rows"], columns=pred["features"])
    yv = np.asarray(pred["is_overdue"])
    hits = rule_hits(X)
    for tag, ids in [("all", [r["id"] for r in RULES]), ("off", [r["id"] for r in RULES if r["id"] != "R6"])]:
        flagged = hits[ids].any(axis=1).to_numpy()
        out[f"r6.tp_{tag}"] = f"{int((flagged & (yv == 1)).sum()):,}"
        out[f"r6.fp_{tag}"] = f"{int((flagged & (yv == 0)).sum()):,}"
    # 사후 확인: Test에서 임계값만 바꿨을 때 F1이 어디까지 오르는가(모델 선택에는 쓰지 않는다).
    y = np.asarray(pred["is_overdue"])
    for role, name in [("final", final), ("contrast", m["classification"]["comparison"]["contrast"])]:
        p = np.asarray(pred["proba"][name])
        grid = np.round(np.arange(0.01, 1.0, 0.01), 2)
        f1s = [classification_metrics(y, (p >= t).astype(int), p)["f1"] for t in grid]
        best = int(np.argmax(f1s))
        out[f"tuned.{role}.f1"] = f3(f1s[best])
        out[f"tuned.{role}.t"] = f"{grid[best]:.2f}"
    final_key = re.sub(r"[^a-z0-9]+", "_", final.lower()).strip("_")
    for metric in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        out[f"final.{metric}"] = out[f"{final_key}.{metric}"]
    for band, v in pol["test_bands"].items():
        out[f"band.{band}.share"] = pct(v["share"])
        out[f"band.{band}.rate"] = pct(v["overdue_rate"])
        out[f"band.{band}.customers"] = f"{v['customers']:,}"
        out[f"band.{band}.overdue"] = f"{v['overdue']:,}"
    for role, name in m["diagnostics"]["learning_curve_roles"].items():
        c = m["diagnostics"]["learning_curves"][name]
        key = f"lc_{role}"
        out[f"{key}.gap"] = f"{c['final_gap']:.3f}"
        out[f"{key}.valid"] = f"{c['valid_mean'][-1]:.3f}"
        out[f"{key}.train"] = f"{c['train_mean'][-1]:.3f}"
    return out


def main():
    metrics = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))
    pred_data = json.loads((RESULTS / "test_predictions.json").read_text(encoding="utf-8"))
    manifest = {"mission": "A5-1", "hash_mode": "UTF-8 text: CRLF normalized to LF; binary: exact bytes",
                "files": {}, "excerpts": {}}
    sources = {}
    for file in SOURCE_FILES:
        data = (ROOT / file).read_bytes()
        text = data.decode("utf-8").replace("\r\n", "\n")
        symbols = [{"name": n.name, "line": n.lineno} for n in ast.walk(ast.parse(text))
                   if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
        sources[file] = {"text": text, "symbols": sorted(symbols, key=lambda s: s["line"])}
        manifest["files"][file] = digest(data, text=True)

    template = (STUDY / "a5-1.template.html").read_text(encoding="utf-8")
    for name, (file, begin, end) in EXCERPTS.items():
        lines = sources[file]["text"].splitlines()
        start, finish = find_block(lines, begin, end)
        manifest["excerpts"][name] = {"file": file, "start": start + 1, "end": finish + 1,
                                      "text": "\n".join(lines[start:finish + 1])}
        template = template.replace(f"@@CODE:{name}@@", render_excerpt(name, file, lines, start, finish))

    nums = numbers(metrics, pred_data)
    template = re.sub(r"@@NUM:([a-z0-9_.]+)@@",
                      lambda mt: html.escape(nums[mt.group(1)]) if mt.group(1) in nums
                      else (_ for _ in ()).throw(KeyError(mt.group(1))), template)

    for image in sorted((RESULTS / "figures").glob("*.png")):
        raw = image.read_bytes()
        template = template.replace(f"@@IMAGE:{image.stem}@@", "data:image/png;base64," + base64.b64encode(raw).decode())
        manifest["files"][image.relative_to(ROOT).as_posix()] = digest(raw)
    for file in ["results/metrics.json", "results/test_predictions.json"]:
        manifest["files"][file] = digest((ROOT / file).read_bytes(), text=True)

    clf = metrics["classification"]
    dataset = {
        "features": pred_data["features"],
        "rows": pred_data["rows"],
        "y": pred_data["is_overdue"],
        "proba": pred_data["proba"],
        "final": pred_data["final"],
        "policy": pred_data["policy"],
        "rules": [{"id": r["id"], "label": r["label"], "conditions": [list(c) for c in r["conditions"]]} for r in RULES],
        "paths": metrics["regression"]["paths"],
        "models": {k: {"test": v["test"], "cv": v["cv"]} for k, v in clf["models"].items()},
        "sources": sources,
    }
    embedded = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    template = template.replace("@@DATA@@", embedded)
    left = re.findall(r"@@[A-Z]+[:@][^@]*@?@?", template)
    if left:
        raise RuntimeError(f"채워지지 않은 자리표시자: {left[:5]}")

    (STUDY / "a5-1.html").write_text(template, encoding="utf-8")
    ev = evidence(pred_data)
    (STUDY / "calculation-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")
    (STUDY / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    size = len(template.encode("utf-8"))
    print(f"Built study/a5-1.html: {len(EXCERPTS)} excerpts, {len(sources)} sources, "
          f"{len(list((RESULTS / 'figures').glob('*.png')))} figures, {size:,} bytes")


if __name__ == "__main__":
    main()
