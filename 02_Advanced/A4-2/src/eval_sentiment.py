"""감성 분석 평가: 단계별 비교, 사전 비교, 신뢰구간, 유의성, 표적 문장, 오분류 수집."""
from __future__ import annotations

import json
from pathlib import Path

from .metrics import bootstrap_ci, classification_report, mcnemar_exact
from .sentiment import ABLATION_STEPS, FINAL_CONFIG, REQUIRED_CONFIG, Config, SentimentAnalyzer, explain

ROOT = Path(__file__).resolve().parents[1]
HANDMADE = ROOT / "data" / "handmade"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def macro_f1(t, p) -> float:
    return classification_report(t, p)["macro_f1"]


def _summary(results, y) -> dict:
    pred = [r.label for r in results]
    rep = classification_report(y, pred)
    covered = [(r.label, t) for r, t in zip(results, y) if not r.decided_by_tie]
    rep["ties"] = len(results) - len(covered)
    rep["covered_accuracy"] = sum(a == b for a, b in covered) / len(covered) if covered else None
    return rep


def ablation(analyzer: SentimentAnalyzer, rows: list[dict]) -> tuple[list[dict], dict]:
    """단계 A~I를 같은 문장에 적용한다. (요약 표, 단계별 예측)"""
    y = [r["label"] for r in rows]
    table, preds = [], {}
    for name, cfg in ABLATION_STEPS:
        res = [analyzer.analyze(r["text"], cfg) for r in rows]
        preds[name] = [x.label for x in res]
        s = _summary(res, y)
        table.append({"step": name, **{k: s[k] for k in ("accuracy", "macro_f1", "ties", "covered_accuracy")},
                      "neg_f1": s["negative"]["f1"], "pos_f1": s["positive"]["f1"]})
    return table, preds


def negation_subset(analyzer: SentimentAnalyzer, rows, preds) -> dict:
    """부정어 규칙이 실제로 작동한(감성어가 뒤집힌) 문장만 모아 A와 E를 비교한다. 전체 정확도에서는 효과가 희석된다."""
    idx = [i for i, r in enumerate(rows) if any(it.negators for it in analyzer.analyze(r["text"], REQUIRED_CONFIG).items)]
    y = [rows[i]["label"] for i in idx]
    a = [preds[ABLATION_STEPS[0][0]][i] for i in idx]
    e = [preds[ABLATION_STEPS[4][0]][i] for i in idx]
    return {"n": len(idx), "acc_A": sum(p == t for p, t in zip(a, y)) / max(1, len(y)),
            "acc_E": sum(p == t for p, t in zip(e, y)) / max(1, len(y)), "mcnemar_A_vs_E": mcnemar_exact(y, a, e),
            "examples": [rows[i]["text"] for i in idx[:8]]}


def significance(rows, preds) -> dict:
    y = [r["label"] for r in rows]
    names = [n for n, _ in ABLATION_STEPS]
    A, E, I = names[0], names[4], names[-1]
    out = {"ci95": {}, "mcnemar": {}}
    for n in (A, E, I):
        out["ci95"][n] = {"accuracy": bootstrap_ci(y, preds[n]), "macro_f1": bootstrap_ci(y, preds[n], stat=macro_f1, n_boot=1000)}
    for a, b in ((A, E), (E, I), (A, I)):
        out["mcnemar"][f"{a} vs {b}"] = mcnemar_exact(y, preds[a], preds[b])
    return out


def lexicon_comparison(rows, knu) -> list[dict]:
    y = [r["label"] for r in rows]
    out = []
    for source in ("custom", "knu", "knu+domain", "union"):
        a = SentimentAnalyzer(source, knu)
        for cname, cfg in (("필수(E)", REQUIRED_CONFIG), ("최종(I)", FINAL_CONFIG)):
            res = [a.analyze(r["text"], cfg) for r in rows]
            s = _summary(res, y)
            out.append({"lexicon": source, "config": cname, "accuracy": s["accuracy"], "macro_f1": s["macro_f1"], "ties": s["ties"]})
    return out


def targeted_rules(analyzer: SentimentAnalyzer) -> dict:
    """손으로 쓴 규칙 표적 문장 40개와 강조어 쌍 16개."""
    rows = read_jsonl(HANDMADE / "sentiment_rules.jsonl")
    tags = sorted({r["tag"] for r in rows})
    by_step = []
    for name, cfg in ABLATION_STEPS:
        res = [analyzer.analyze(r["text"], cfg) for r in rows]
        entry = {"step": name, "all": sum(x.label == r["label"] for x, r in zip(res, rows)) / len(rows)}
        for t in tags:
            sub = [(x, r) for x, r in zip(res, rows) if r["tag"] == t]
            entry[t] = sum(x.label == r["label"] for x, r in sub) / len(sub)
        by_step.append(entry)
    final = [analyzer.analyze(r["text"], FINAL_CONFIG) for r in rows]
    details = [{"id": r["id"], "tag": r["tag"], "text": r["text"], "label": r["label"], "score": x.score,
                "pred": x.label, "note": r.get("note", "")} for x, r in zip(final, rows)]

    pairs = read_jsonl(HANDMADE / "intensity_pairs.jsonl")
    pair_out = []
    for on in (False, True):
        cfg = Config(intensifier=on)
        ok = 0
        for p in pairs:
            b = analyzer.analyze(p["base"], cfg).score
            m = analyzer.analyze(p["modified"], cfg).score
            good = abs(m) > abs(b) if p["kind"] == "intensifier" else abs(m) < abs(b)
            ok += good and b != 0 and (b > 0) == (m > 0)
            if on:
                pair_out.append({**p, "base_score": b, "modified_score": m, "ok": bool(good and (b > 0) == (m > 0))})
        if not on:
            off_ok = ok
    return {"n": len(rows), "by_step": by_step, "details": details,
            "intensity": {"n": len(pairs), "ok_without_rule": off_ok, "ok_with_rule": sum(p["ok"] for p in pair_out), "pairs": pair_out}}


def collect_errors(analyzer: SentimentAnalyzer, rows, limit: int | None = None) -> list[dict]:
    out = []
    for r in rows:
        res = analyzer.analyze(r["text"], FINAL_CONFIG)
        if res.label != r["label"]:
            out.append({"id": r["id"], "label": r["label"], "pred": res.label, "score": res.score,
                        "tie": res.decided_by_tie, "text": r["text"],
                        "evidence": [(i.surface, round(i.value, 2)) for i in res.items]
                        + [(o["surface"], o["value"]) for o in res.orphans]
                        + ([(res.rating["text"], res.rating["value"])] if res.rating else []),
                        "explain": explain(res)})
    return out[:limit] if limit else out


def run(splits: dict, knu: list[dict]) -> dict:
    a = SentimentAnalyzer()
    out = {}
    for split in ("dev", "test"):
        rows = splits[split]
        table, preds = ablation(a, rows)
        out[split] = {"ablation": table, "negation_subset": negation_subset(a, rows, preds)}
        if split == "test":
            out[split]["significance"] = significance(rows, preds)
            y = [r["label"] for r in rows]
            out[split]["final_report"] = classification_report(y, preds[ABLATION_STEPS[-1][0]])
            out[split]["required_report"] = classification_report(y, preds[ABLATION_STEPS[4][0]])
    out["lexicon_comparison"] = {"dev": lexicon_comparison(splits["dev"], knu), "test": lexicon_comparison(splits["test"], knu)}
    out["targeted"] = targeted_rules(a)
    out["test_errors"] = collect_errors(a, splits["test"])
    return out
