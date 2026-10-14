"""정보 추출·마스킹 평가.

일치 기준: (유형, 원문 문자열)이 정답과 정확히 같으면 TP다. 범위가 한 글자라도 다르면 FP 하나와 FN 하나가 된다.
정규화 정확도: TP 중 정규화 값까지 정답과 같은 비율.
마스킹: 같은 기준의 P/R에 더해, 마스킹 결과에 정답 개인정보 원문이 그대로 남았는지(유출) 센다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .extract import extract, mask
from .metrics import prf
from .patterns import CORE_TYPES, PII_TYPES

ROOT = Path(__file__).resolve().parents[1]
HANDMADE = ROOT / "data" / "handmade"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _match(pred: list[tuple], gold: list[tuple]):
    """중복을 허용하는 다중집합 비교. (일치, 남은 예측, 남은 정답)"""
    g = Counter(gold)
    hit, extra = [], []
    for p in pred:
        if g[p] > 0:
            g[p] -= 1
            hit.append(p)
        else:
            extra.append(p)
    missed = list(g.elements())
    return hit, extra, missed


def evaluate_extraction(cases: list[dict] | None = None) -> dict:
    cases = cases or read_jsonl(HANDMADE / "extraction_cases.jsonl")
    counts = {t: Counter() for t in CORE_TYPES}
    norm = {t: [0, 0] for t in CORE_TYPES}
    errors = []
    for c in cases:
        ents = extract(c["text"], CORE_TYPES)
        pred = [(e.type, e.text) for e in ents]
        gold = [(g["type"], g["text"]) for g in c["gold"]]
        hit, extra, missed = _match(pred, gold)
        for t, _ in hit:
            counts[t]["tp"] += 1
        for t, _ in extra:
            counts[t]["fp"] += 1
        for t, _ in missed:
            counts[t]["fn"] += 1
        values = {(e.type, e.text): e.value for e in ents}
        gold_values = {(g["type"], g["text"]): g["value"] for g in c["gold"]}
        wrong_value = []
        for key in hit:
            norm[key[0]][1] += 1
            if values[key] == gold_values[key]:
                norm[key[0]][0] += 1
            else:
                wrong_value.append({"type": key[0], "text": key[1], "pred": values[key], "gold": gold_values[key]})
        if extra or missed or wrong_value:
            errors.append({"id": c["id"], "text": c["text"], "fail": c.get("fail", "예상 밖"), "note": c.get("note", ""),
                           "false_positive": extra, "missed": missed, "wrong_value": wrong_value})
    per_type = {}
    for t in CORE_TYPES:
        r = prf(counts[t]["tp"], counts[t]["fp"], counts[t]["fn"])
        r["normalization_accuracy"] = norm[t][0] / norm[t][1] if norm[t][1] else None
        r["sentences"] = sum(1 for c in cases if c["focus"] == t)
        per_type[t] = r
    tot = sum((counts[t] for t in CORE_TYPES), Counter())
    micro = prf(tot["tp"], tot["fp"], tot["fn"])
    focus = Counter(c["focus"] for c in cases)
    return {"n_sentences": len(cases), "sentences_by_focus": dict(focus), "per_type": per_type, "micro": micro,
            "errors": errors, "failure_types": dict(Counter(e["fail"] for e in errors))}


def evaluate_masking(cases: list[dict] | None = None) -> dict:
    cases = cases or read_jsonl(HANDMADE / "masking_cases.jsonl")
    counts = {t: Counter() for t in PII_TYPES}
    leaks, rows = [], []
    for c in cases:
        masked, ents = mask(c["text"])
        pred = [(e.type, e.text) for e in ents]
        gold = [(g["type"], g["text"]) for g in c["gold"]]
        hit, extra, missed = _match(pred, gold)
        for t, _ in hit:
            counts[t]["tp"] += 1
        for t, _ in extra:
            counts[t]["fp"] += 1
        for t, _ in missed:
            counts[t]["fn"] += 1
        leaked = [g for g in c["gold"] if g["text"] in masked]
        leaks += [{"id": c["id"], **g} for g in leaked]
        rows.append({"id": c["id"], "text": c["text"], "masked": masked, "fail": c.get("fail", ""), "note": c.get("note", ""),
                     "false_positive": extra, "missed": missed})
    per_type = {t: prf(counts[t]["tp"], counts[t]["fp"], counts[t]["fn"]) for t in PII_TYPES}
    n_gold = sum(len(c["gold"]) for c in cases)
    return {"n_sentences": len(cases), "n_gold": n_gold, "per_type": per_type, "leaks": leaks,
            "leak_rate": len(leaks) / n_gold if n_gold else 0.0, "rows": rows}
