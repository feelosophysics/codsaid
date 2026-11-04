"""보너스 3: 속성(Aspect) 기반 감성 분석.

"음식은 맛있는데 가격이 비싸요" → 맛(긍정), 가격(부정)

1. 절 나누기: 문장부호, 대조 어미(지만·는데·은데·으나), 접속사(하지만·근데 …)로 자른다.
   감성 분석기의 clause_map을 그대로 쓴다.
2. 속성어 찾기: aspects.tsv의 속성어가 어절 처음에 나오면 그 속성으로 본다.
   '맛있다'처럼 감성어 안에 속성어가 들어 있으면 그것도 속성 언급으로 본다(암시적 속성).
3. 절마다 감성 분석: 그 절에 나온 속성의 문맥 의존어(@context)를 더한 사전으로 분석한다.
   예: 가격이 있는 절에서만 '싸다'가 +2, 배송이 있는 절에서만 '빠르다'가 +2.
   부정어·강조어 규칙은 그대로 적용된다("배송이 빠르지 않았다" → 배송 부정).
4. 연결: 감성어(와 꾸밀 대상이 없는 부정어)를 같은 절에서 앞에 나온 속성 중 가장 가까운 것에 붙인다.
   한국어는 "속성은 + 평가" 순서이기 때문이다. 앞에 속성이 없으면 뒤의 가장 가까운 속성에 붙인다.
   거리만 보는 방식(nearest)과 비교했다: "직원분들이 정말 친절하고 분위기도 좋았어요"에서
   nearest는 '친절'을 뒤의 '분위기'에 붙인다.
   문맥 의존어는 자기 속성에 붙인다. 속성이 없는 절의 감성은 '전체'로 모은다.
5. 속성별로 점수를 더해 부호로 극성을 정한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .lexicon import Entry, Matcher, build_entries, load_aspects
from .sentiment import Config, SentimentAnalyzer, clause_map, normalize_text, tokenize

ASPECT_CONFIG = Config(emoticon=True, orphan=True)  # 대조 가중치·평점 규칙은 속성 판단에 쓰지 않는다
GENERAL = "전체"


@dataclass
class AspectResult:
    text: str
    aspects: dict = field(default_factory=dict)      # 속성 → {"score", "polarity", "evidence": [(표면형, 값)]}
    mentions: list = field(default_factory=list)     # (속성, 표면형, 위치)
    clauses: list = field(default_factory=list)


class AspectAnalyzer:
    def __init__(self, link: str = "preceding"):
        """link: preceding(앞 속성 우선, 기본) / nearest(거리만 보고 가장 가까운 속성)"""
        self.link = link
        aspects, context = load_aspects()
        self.aspects = aspects
        self.term_to_aspect = {}
        entries = []
        for name, (_domain, terms) in aspects.items():
            for t in terms:
                self.term_to_aspect[t.lower()] = name
                entries.append(Entry(t.lower(), "SENTI", 1.0, "N", "aspect", frozenset({"start"})))
        self.mention_matcher = Matcher(entries)
        self.context = {}
        for aspect, term, score in context:
            self.context.setdefault(aspect, []).append((term, score))
        self.base_entries = build_entries("custom")
        self._cache: dict[frozenset, SentimentAnalyzer] = {}

    def _analyzer(self, present: frozenset) -> SentimentAnalyzer:
        """이 절에 나온 속성들의 문맥 의존어를 앞에 둔 사전. 같은 표면형이면 문맥 의존어가 먼저 잡힌다."""
        if present not in self._cache:
            extra = [Entry(term, "SENTI", score, "P", f"context:{a}") for a in sorted(present) for term, score in self.context.get(a, [])]
            a = object.__new__(SentimentAnalyzer)
            a.source, a.config = "custom+context", ASPECT_CONFIG
            mods = [e for e in self.base_entries if e.kind not in ("SENTI", "EMO", "BLOCK")]
            rest = [e for e in self.base_entries if e.kind in ("SENTI", "EMO", "BLOCK")]
            a.matcher = Matcher(mods + extra + rest)
            self._cache[present] = a
        return self._cache[present]

    def analyze(self, raw: str) -> AspectResult:
        text = normalize_text(raw)
        clause, _ = clause_map(text, tokenize(text))
        # 절 경계(글자 위치)
        spans, start = [], 0
        for i in range(1, len(text) + 1):
            if i == len(text) or clause[i] != clause[start]:
                spans.append((start, i))
                start = i
        result = AspectResult(raw)
        for a, b in spans:
            seg = text[a:b]
            if not seg.strip():
                continue
            mentions = [(self.term_to_aspect[h.entry.term], h.surface, h.start) for h in self.mention_matcher.find(seg)]
            result.mentions += [(m[0], m[1], m[2] + a) for m in mentions]
            present = frozenset(m[0] for m in mentions)
            res = self._analyzer(present).analyze(seg)
            evid = [(it.surface, it.value, it.start, it.term) for it in res.items] + \
                   [(o["surface"], o["value"], o["start"], None) for o in res.orphans]
            assigned = []
            for surface, value, pos, term in evid:
                if value == 0:
                    continue
                target = None
                for asp in sorted(present):  # frozenset 순회 순서는 해시에 따라 바뀌므로 정렬한다
                    if term and any(term == t for t, _ in self.context.get(asp, [])):
                        target = asp
                if target is None and mentions:
                    target = self._link(mentions, pos)
                target = target or GENERAL
                slot = result.aspects.setdefault(target, {"score": 0.0, "evidence": []})
                slot["score"] += value
                slot["evidence"].append((surface, round(value, 2)))
                assigned.append((surface, target))
            result.clauses.append({"text": seg.strip(), "aspects": sorted(present), "assigned": assigned})
        for v in result.aspects.values():
            v["polarity"] = "pos" if v["score"] > 0 else ("neg" if v["score"] < 0 else "neutral")
        return result

    def _link(self, mentions, pos: int) -> str:
        """감성어를 붙일 속성. 한국어는 "속성은 + 평가" 순서라 기본은 앞에 나온 속성 중 가장 가까운 것이다.
        앞에 속성이 없으면 뒤 속성 중 가장 가까운 것을 쓴다."""
        if self.link == "preceding":
            before = [m for m in mentions if m[2] <= pos]
            if before:
                return max(before, key=lambda m: m[2])[0]
        return min(mentions, key=lambda m: (abs(m[2] - pos), m[2] > pos))[0]

    def pairs(self, raw: str, include_general: bool = False) -> set[tuple[str, str]]:
        r = self.analyze(raw)
        return {(a, v["polarity"]) for a, v in r.aspects.items()
                if v["polarity"] != "neutral" and (include_general or a != GENERAL)}


def sentence_level_pairs(aa: AspectAnalyzer, analyzer: SentimentAnalyzer, raw: str) -> set[tuple[str, str]]:
    """비교 기준: 문장 전체 감성 하나를 문장에 나온 모든 속성에 똑같이 붙인다(속성 분석을 하지 않은 경우)."""
    r = aa.analyze(raw)
    named = {m[0] for m in r.mentions}
    s = analyzer.analyze(raw, ASPECT_CONFIG).score
    if s == 0:
        return set()
    pol = "pos" if s > 0 else "neg"
    return {(a, pol) for a in named}


def format_report(r: AspectResult) -> str:
    lines = ["=== 속성 기반 감성 분석 ===", f'문장: "{r.text}"', ""]
    for c in r.clauses:
        lines.append(f"- 절 \"{c['text']}\" 속성 {c['aspects'] or '없음'} ← " +
                     (", ".join(f"{s}→{t}" for s, t in c["assigned"]) or "감성어 없음"))
    lines.append("")
    if not r.aspects:
        lines.append("결과: (감성 단서 없음)")
    for a, v in r.aspects.items():
        label = {"pos": "긍정", "neg": "부정", "neutral": "중립"}[v["polarity"]]
        lines.append(f"결과: {a}({label}, {v['score']:+g}) ← " + ", ".join(f"{s}({x:+g})" for s, x in v["evidence"]))
    return "\n".join(lines)


def evaluate(cases: list[dict] | None = None, link: str = "preceding") -> dict:
    """(속성, 극성) 쌍의 P/R/F1. '전체'는 평가에서 뺀다. 속성 탐지만 본 P/R/F1과 문장 단위 기준선도 함께 낸다."""
    import json
    from pathlib import Path

    from .metrics import prf

    if cases is None:
        path = Path(__file__).resolve().parents[1] / "data" / "handmade" / "aspect_cases.jsonl"
        cases = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    aa = AspectAnalyzer(link)
    base = SentimentAnalyzer()
    tot = {"pair": [0, 0, 0], "aspect": [0, 0, 0], "baseline": [0, 0, 0]}
    rows = []
    for c in cases:
        gold = {tuple(g) for g in c["gold"]}
        pred = aa.pairs(c["text"])
        sent = sentence_level_pairs(aa, base, c["text"])
        for key, p, g in (("pair", pred, gold), ("aspect", {a for a, _ in pred}, {a for a, _ in gold}), ("baseline", sent, gold)):
            tot[key][0] += len(p & g)
            tot[key][1] += len(p - g)
            tot[key][2] += len(g - p)
        rows.append({"id": c["id"], "domain": c["domain"], "text": c["text"], "gold": sorted(gold), "pred": sorted(pred),
                     "baseline": sorted(sent), "correct": pred == gold, "fail": c.get("fail", ""), "note": c.get("note", "")})
    return {"link": link, "n": len(cases), "pair": prf(*tot["pair"]), "aspect_detection": prf(*tot["aspect"]),
            "sentence_baseline": prf(*tot["baseline"]), "exact_sentences": sum(r["correct"] for r in rows), "rows": rows}
