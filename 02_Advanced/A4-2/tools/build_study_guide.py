"""study/a4-2.template.html + study/engine.js + 사전·정규식·평가 결과 → study/a4-2.html (오프라인 단일 파일).

    uv run python tools/build_study_guide.py      (먼저 uv run python -m src.run_all 로 outputs/ 를 만든다)

HTML에 넣는 것
- 엔진 데이터: 수식어·직접 구축 사전(활용 변이 표면형 포함), 속성 사전, 정규식의 JS 변환본
- NSMC dev·test 2,000건(CC0). 브라우저에서 규칙을 끄고 켜며 정확도를 다시 계산한다
- 직접 쓴 평가 문장(추출·마스킹·속성·규칙 표적)과 outputs/*.json 의 결과
- src/ 핵심 함수 원문과 줄 번호
KNU 감성사전은 라이선스가 명시돼 있지 않아 넣지 않는다(비교 결과 수치만 넣는다).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aspect import load_aspects  # noqa: E402
from src.data import load_splits  # noqa: E402
from src.lexicon import build_entries, predicate_variants  # noqa: E402
from src.patterns import CORE_TYPES, LABELS, PATTERNS, PII_TYPES, PRIORITY, to_js_source  # noqa: E402
from src.sentiment import ABLATION_STEPS, FINAL_CONFIG, JOSA  # noqa: E402

STUDY = ROOT / "study"
OUT = ROOT / "outputs"
HANDMADE = ROOT / "data" / "handmade"

EXCERPTS = [
    ("src/patterns.py", "EMAIL"),
    ("src/patterns.py", "DATE"),
    ("src/patterns.py", "MONEY"),
    ("src/normalize.py", "parse_korean_amount"),
    ("src/normalize.py", "normalize"),
    ("src/extract.py", "resolve_overlaps"),
    ("src/extract.py", "mask_value"),
    ("src/lexicon.py", "predicate_variants"),
    ("src/lexicon.py", "Matcher._match_at"),
    ("src/lexicon.py", "knu_entries"),
    ("src/sentiment.py", "clause_map"),
    ("src/sentiment.py", "SentimentAnalyzer.analyze"),
    ("src/aspect.py", "AspectAnalyzer.analyze"),
    ("src/bonus_tfidf.py", "fit_predict"),
    ("src/metrics.py", "mcnemar_exact"),
]


def config_dict(cfg) -> dict:
    return {k: getattr(cfg, k) for k in cfg.__dataclass_fields__}


def entry_dict(e) -> dict:
    term = e.term.lower()
    forms = predicate_variants(term) if e.pos == "P" else [term]
    return {"term": e.term if e.kind == "EMO" else term, "kind": e.kind, "score": e.score, "pos": e.pos,
            "domain": e.domain, "flags": sorted(e.flags), "note": e.note, "forms": forms}


def engine_data() -> dict:
    entries = [entry_dict(e) for e in build_entries("custom")]
    aspects, context = load_aspects()
    mentions, term_to_aspect = [], {}
    for name, (_d, terms) in aspects.items():
        for t in terms:
            term_to_aspect[t.lower()] = name
            mentions.append({"term": t.lower(), "kind": "SENTI", "score": 1.0, "pos": "N", "domain": "aspect",
                             "flags": ["start"], "note": "", "forms": [t.lower()]})
    ctx: dict[str, list] = {}
    for aspect, term, score in context:
        ctx.setdefault(aspect, []).append({"term": term.lower(), "kind": "SENTI", "score": score, "pos": "P",
                                           "domain": f"context:{aspect}", "flags": [], "note": "",
                                           "forms": predicate_variants(term.lower())})
    return {
        "entries": entries, "josa": JOSA,
        "patterns": {k: to_js_source(v) for k, v in PATTERNS.items()},
        "pattern_sources": PATTERNS,
        "priority": list(PRIORITY), "core_types": list(CORE_TYPES), "pii_types": list(PII_TYPES), "labels": LABELS,
        "aspects": {"mentions": mentions, "term_to_aspect": term_to_aspect, "context": ctx,
                    "table": {k: {"domain": d, "terms": t} for k, (d, t) in aspects.items()}},
        "steps": [{"name": n, "config": config_dict(c)} for n, c in ABLATION_STEPS],
        "final_config": config_dict(FINAL_CONFIG),
    }


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def results() -> dict:
    L = lambda n: json.loads((OUT / n).read_text(encoding="utf-8"))  # noqa: E731
    sent = L("sentiment_eval.json")
    notes = json.loads((HANDMADE / "test_error_annotations.json").read_text(encoding="utf-8"))
    errors = {e["id"]: e for e in sent["test_errors"]}
    annotated = [{**n, "text": errors[n["id"]]["text"], "label": errors[n["id"]]["label"]} for n in notes if n["id"] in errors]
    ext = L("extraction_eval.json")
    asp = L("aspect_eval.json")
    return {
        "sentiment": {s: {"ablation": sent[s]["ablation"], "negation_subset": {k: v for k, v in sent[s]["negation_subset"].items() if k != "examples"}}
                      for s in ("dev", "test")},
        "significance": sent["test"]["significance"],
        "final_report": sent["test"]["final_report"],
        "lexicon_comparison": sent["lexicon_comparison"],
        "targeted": {"by_step": sent["targeted"]["by_step"], "intensity": sent["targeted"]["intensity"]},
        "error_annotations": annotated,
        "n_test_errors": len(sent["test_errors"]),
        "n_tie_errors": sum(e["tie"] for e in sent["test_errors"]),
        "extraction": {"per_type": ext["per_type"], "micro": ext["micro"], "errors": ext["errors"]},
        "masking": {k: v for k, v in L("masking_eval.json").items()},
        "aspect": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in asp.items()},
        "aspect_rows": asp["preceding"]["rows"],
        "tfidf": L("rule_vs_tfidf.json"),
        "lexicon_stats": L("lexicon_stats.json"),
    }


def code_excerpts() -> list[dict]:
    out = []
    for rel, name in EXCERPTS:
        source = (ROOT / rel).read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        parts = name.split(".")
        node = None
        for top in tree.body:
            if isinstance(top, ast.Assign) and any(getattr(t, "id", None) == parts[0] for t in top.targets):
                node = top
            elif getattr(top, "name", None) == parts[0]:
                node = top
                if len(parts) == 2:
                    node = next(n for n in top.body if getattr(n, "name", None) == parts[1])
        if node is None:
            raise KeyError(name)
        start = node.lineno - 1
        if getattr(node, "decorator_list", None):
            start = node.decorator_list[0].lineno - 1
        out.append({"file": rel, "name": name, "start": start + 1, "code": "\n".join(lines[start:node.end_lineno])})
    return out


def build() -> Path:
    splits = load_splits()
    data = {
        "engine": engine_data(),
        "reviews": {s: [[r["id"], r["text"], r["label"]] for r in splits[s]] for s in ("dev", "test")},
        "cases": {
            "extraction": read_jsonl(HANDMADE / "extraction_cases.jsonl"),
            "masking": read_jsonl(HANDMADE / "masking_cases.jsonl"),
            "aspect": read_jsonl(HANDMADE / "aspect_cases.jsonl"),
            "rules": read_jsonl(HANDMADE / "sentiment_rules.jsonl"),
            "pairs": read_jsonl(HANDMADE / "intensity_pairs.jsonl"),
        },
        "results": results(),
        "code": code_excerpts(),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    engine = (STUDY / "engine.js").read_text(encoding="utf-8")
    html = (STUDY / "a4-2.template.html").read_text(encoding="utf-8")
    app = (STUDY / "app.js").read_text(encoding="utf-8")
    html = html.replace("/*__ENGINE__*/", engine).replace("/*__APP__*/", app).replace("__DATA__", payload)
    path = STUDY / "a4-2.html"
    path.write_text(html, encoding="utf-8")
    print(f"{path} ({path.stat().st_size / 1024:.0f} KB, 데이터 {len(payload) / 1024:.0f} KB)")
    return path


if __name__ == "__main__":
    build()
