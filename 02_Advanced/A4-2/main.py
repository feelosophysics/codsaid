"""고객 문의·리뷰 텍스트에서 정보를 뽑고 감성을 판단하는 규칙 기반 파이프라인 CLI.

    python main.py --text "문의: support@company.co.kr, 전화 02-1234-5678 일시: 2024년 3월 15일, 참가비: 50,000원"
    python main.py --text "이 식당은 정말 맛있지 않았어요"
    python main.py --text "음식은 맛있는데 가격이 비싸요" --aspect
    python main.py --text "연락처 010-1234-5678, 주민번호 900101-1234567" --mask
    python main.py --file inquiries.txt --json        # 한 줄에 한 문장
"""
from __future__ import annotations

import argparse
import json
import sys

from src.aspect import AspectAnalyzer, format_report as aspect_report
from src.extract import extract, format_report as extraction_report, mask
from src.patterns import CORE_TYPES, LABELS
from src.sentiment import FINAL_CONFIG, REQUIRED_CONFIG, SentimentAnalyzer, explain


PLACEHOLDER = "□"


def hide_entities(text: str, ents) -> str:
    """추출한 개체 자리를 □로 바꾼다. 이메일·날짜 속 마침표가 절 경계로, 숫자가 평점으로 읽히지 않게 한다."""
    out, last = [], 0
    for e in ents:
        out += [text[last:e.start], PLACEHOLDER]
        last = e.end
    return "".join(out + [text[last:]])


def analyze_one(text: str, args, analyzer: SentimentAnalyzer, aspect: AspectAnalyzer | None) -> dict:
    cfg = REQUIRED_CONFIG if args.rules == "required" else FINAL_CONFIG
    ents = extract(text, CORE_TYPES)
    plain = hide_entities(text, ents)
    res = analyzer.analyze(plain, cfg)
    out = {
        "text": text,
        "entities": [e.to_dict() for e in ents],
        "sentiment": {"score": res.score, "label": "긍정" if res.label == 1 else "부정",
                      "decided_by_default": res.decided_by_tie, "tokens": [p for p, _ in res.pieces]},
    }
    if args.mask:
        masked, ents = mask(text)
        out["masked"] = masked
        out["pii"] = [{"type": LABELS[e.type], "text": e.text} for e in ents]
    if aspect:
        r = aspect.analyze(plain)
        out["aspects"] = {a: v["polarity"] for a, v in r.aspects.items()}
    out["_reports"] = [extraction_report(text), explain(res)] + ([aspect_report(r)] if aspect else [])
    return out


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="정규식 정보 추출 + 감성 사전 감성 분석")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="분석할 문장")
    src.add_argument("--file", help="한 줄에 한 문장씩 담긴 UTF-8 텍스트 파일")
    p.add_argument("--rules", choices=["final", "required"], default="final",
                   help="final: 확장 규칙 포함(기본), required: 미션 필수 범위(사전·부정어·강조어·이중부정)")
    p.add_argument("--lexicon", choices=["custom", "knu", "knu+domain", "union"], default="custom",
                   help="감성 사전. knu 계열은 처음 실행할 때 KNU 감성사전을 내려받는다")
    p.add_argument("--mask", action="store_true", help="개인정보(주민번호·카드·주소·전화·이메일)를 가린 문장도 출력")
    p.add_argument("--aspect", action="store_true", help="속성별 감성(보너스 3)도 출력")
    p.add_argument("--json", action="store_true", help="사람이 읽는 보고서 대신 JSON 출력")
    args = p.parse_args(argv)

    knu = None
    if args.lexicon != "custom":
        from src.data import load_knu
        knu = load_knu()
    analyzer = SentimentAnalyzer(args.lexicon, knu)
    aspect = AspectAnalyzer() if args.aspect else None
    if args.text is not None:
        texts = [args.text]
    else:
        with open(args.file, encoding="utf-8") as f:
            texts = [line.strip() for line in f if line.strip()]

    results = [analyze_one(t, args, analyzer, aspect) for t in texts]
    if args.json:
        for r in results:
            r.pop("_reports")
        print(json.dumps(results[0] if len(results) == 1 else results, ensure_ascii=False, indent=2, default=str))
        return 0
    for i, r in enumerate(results):
        if i:
            print("\n" + "─" * 60 + "\n")
        print("\n\n".join(r["_reports"]))
        if args.mask:
            print(f"\n=== 개인정보 마스킹 ===\n{r['masked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
