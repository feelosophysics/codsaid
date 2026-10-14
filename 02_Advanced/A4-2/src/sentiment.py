"""감성 사전 기반 감성 분석.

필수 범위: 토큰화 → 사전 점수 합산 → 부정어 반전 → 강조어 가중치 → 이중부정
확장 규칙(설정으로 끄고 켠다. dev 집합에서 효과를 보고 최종 설정을 정한다)
- contrast: 대조 접속(지만·하지만·근데·그래도) 앞 절 × 0.5, 뒤 절 × 1.5 (VADER의 'but' 규칙)
- orphan  : 꾸밀 감성어가 없는 부정어("이건 아니다", "보지 마세요")를 약한 부정(-1)으로 센다
- rating  : "1점", "10점" 같은 평점 언급을 ±2로 센다
- emoticon: ㅋㅋ, ㅡㅡ, ^^, ♥ 같은 이모티콘과 영어 감성어

범위(scope) 규칙
- 강조어·약화어: 감성어 앞, 같은 절, 2어절 이내, 사이에 다른 감성어가 없을 때
- 앞 부정어(안·못): 감성어 바로 앞(같은 어절에 붙었거나 바로 앞 어절)
- 뒤 부정어(않·없·아니·못하·지 마): 감성어 뒤, 같은 절, 3어절 이내, 다음 감성어 전까지.
  여러 개면 개수만큼 뒤집는다. 두 개면 원래 극성으로 돌아온다(이중부정: "재미있지 않을 수 없다").
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field, replace

from .lexicon import Hit, Matcher, base, build_entries, is_syllable, split_syllable

# ─────────────────────────────── 설정 ───────────────────────────────


@dataclass(frozen=True)
class Config:
    negation: bool = True
    intensifier: bool = True
    double_negation: bool = True
    contrast: bool = False
    orphan: bool = False
    rating: bool = False
    emoticon: bool = False
    tie_label: int = 0          # 점수가 0일 때(감성 단서 없음 또는 상쇄) 내릴 판정. dev에서 정한다
    neg_window: int = 3         # 뒤 부정어를 찾는 어절 수
    int_window: int = 2         # 강조어를 찾는 어절 수
    orphan_score: float = -1.0
    rating_score: float = 2.0


# 미션의 '부정어/강조어 규칙 적용 전후 비교'를 위한 단계
ABLATION_STEPS: list[tuple[str, Config]] = [
    ("A 사전 합산만", Config(negation=False, intensifier=False, double_negation=False)),
    ("B A + 강조어", Config(negation=False, intensifier=True, double_negation=False)),
    ("C A + 부정어(한 번만 반전)", Config(negation=True, intensifier=False, double_negation=False)),
    ("D A + 부정어 + 강조어", Config(negation=True, intensifier=True, double_negation=False)),
    ("E D + 이중부정 (필수 범위)", Config()),
    ("F E + 이모티콘", Config(emoticon=True)),
    ("G F + 대조 접속", Config(emoticon=True, contrast=True)),
    ("H G + 고립 부정어", Config(emoticon=True, contrast=True, orphan=True)),
    ("I H + 평점 언급", Config(emoticon=True, contrast=True, orphan=True, rating=True)),
]

# ─────────────────────────────── 전처리·토큰화 ───────────────────────────────

JOSA = sorted(["은", "는", "이", "가", "을", "를", "에", "에서", "에게", "의", "도", "만", "으로", "로", "와", "과",
               "하고", "이랑", "랑", "까지", "부터", "보다", "처럼", "같이", "이나", "나", "께서", "한테", "이다", "입니다", "이에요", "예요"],
              key=len, reverse=True)

TOKEN_RE = re.compile(
    r"(?P<hangul>[가-힣]+)"
    r"|(?P<emo>\^[_\-.ㅡ~o]?\^|[-ㅡ][_.][-ㅡ]|;{2,}|[♥♡❤]+)"
    r"|(?P<jamo>[ㄱ-ㅎㅏ-ㅣ]+)"
    r"|(?P<latin>[a-z]+)"
    r"|(?P<num>[0-9]+(?:[.,][0-9]+)*)"
    r"|(?P<punct>[.!?…~,]+)"
    r"|(?P<other>\S)"
)
CLAUSE_PUNCT = set(".!?…~,")
STRONG_CONJ = {"하지만", "그러나", "그런데", "근데", "그래도", "반면", "반면에", "그치만", "그렇지만", "허나", "다만"}
RATING_RE = re.compile(r"(?<![0-9.])(-?[0-9]{1,2}(?:\.[0-9])?)[ ]?점(?![ ]?만점)(?!수)")
STAR_RE = re.compile(r"별[ ]?(?:0|1|한|하나|반)[ ]?개")  # 별 한 개, 별반개, 별1개


def normalize_text(text: str) -> str:
    """NFC 정규화, 영문 소문자, 공백 하나로."""
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def canonical_emo(kind: str, s: str) -> str:
    """같은 글자 반복은 2개로 줄인다(ㅋㅋㅋㅋ → ㅋㅋ). 웃는 얼굴 변형은 ^^, 못마땅한 얼굴은 -_-로 모은다."""
    if kind == "emo":
        if s.startswith("^"):
            return "^^"
        if s[0] in "-ㅡ":
            return "-_-"
        if s.startswith(";"):
            return ";;"
        return s[0]
    s = s.replace("ㅜ", "ㅠ")  # 우는 얼굴 두 표기(ㅜㅜ, ㅠㅠ)를 하나로
    return re.sub(r"(.)\1+", r"\1\1", s)


@dataclass
class Token:
    text: str
    kind: str
    start: int
    end: int
    eojeol: int


def tokenize(text: str) -> list[Token]:
    """normalize_text를 거친 문장을 글자 종류별 토큰으로 나눈다. 어절 번호를 함께 단다."""
    tokens, eojeol = [], 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > 0 and text[m.start() - 1] == " ":
            eojeol += 1
        tokens.append(Token(m.group(0), m.lastgroup, m.start(), m.end(), eojeol))
    return tokens


def ends_with_contrast(word: str) -> str | None:
    """어절 끝의 연결 어미로 절 경계를 판단한다. 'strong'(지만·으나) / 'weak'(는데·은데·ㄴ데·던데) / None"""
    if word.endswith("지만") or word.endswith("으나"):
        return "strong"
    if word.endswith("데") and len(word) >= 2:
        prev = word[-2]
        if prev in "는던" or (is_syllable(prev) and split_syllable(prev)[2] == 4):  # 4 = 받침 ㄴ
            return "weak"
    return None


def clause_map(text: str, tokens: list[Token]) -> tuple[list[int], int | None]:
    """글자마다 절 번호, 마지막 강한 대조 경계의 글자 위치."""
    clause = [0] * (len(text) + 1)
    cid, last_strong = 0, None
    boundary_after: set[int] = set()
    boundary_before: set[int] = set()
    words = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    for w, s, e in words:
        core = re.sub(r"[^가-힣]+$", "", w)
        if core in STRONG_CONJ:
            boundary_before.add(s)
            last_strong = s
        elif core:
            c = ends_with_contrast(core)
            if c:
                boundary_after.add(s + len(core))
                if c == "strong":
                    last_strong = s + len(core)
    punct_at = {t.start for t in tokens if t.kind == "punct" and set(t.text) & CLAUSE_PUNCT}
    for i in range(len(text) + 1):
        if i in boundary_before or i in boundary_after:
            cid += 1
        clause[i] = cid
        if i in punct_at:
            cid += 1
    return clause, last_strong


# ─────────────────────────────── 분석기 ───────────────────────────────


@dataclass
class Scored:
    surface: str
    term: str
    base: float
    start: int
    modifiers: list = field(default_factory=list)   # [(표면형, 배율)]
    negators: list = field(default_factory=list)    # [표면형]
    contrast: float = 1.0
    value: float = 0.0
    kind: str = "SENTI"


@dataclass
class Result:
    text: str
    score: float
    label: int
    decided_by_tie: bool
    items: list
    tokens: list
    pieces: list
    rating: dict | None = None
    orphans: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class SentimentAnalyzer:
    def __init__(self, source: str = "custom", knu: list[dict] | None = None, config: Config = Config()):
        self.source = source
        self.matcher = Matcher(build_entries(source, knu))
        self.config = config

    def with_config(self, **kw) -> "SentimentAnalyzer":
        clone = object.__new__(SentimentAnalyzer)
        clone.source, clone.matcher = self.source, self.matcher
        clone.config = replace(self.config, **kw)
        return clone

    # 문장 하나 분석
    def analyze(self, raw: str, config: Config | None = None) -> Result:
        cfg = config or self.config
        text = normalize_text(raw)
        tokens = tokenize(text)
        hits = self.matcher.find(text)
        if cfg.emoticon:
            for t in tokens:
                if t.kind in ("emo", "jamo", "latin"):
                    e = self.matcher.emoticons.get(canonical_emo(t.kind, t.text))
                    if e:
                        hits.append(Hit("EMO", e, t.start, t.end, t.text))
            hits.sort(key=lambda h: h.start)

        eo = _eojeol_index(text)
        clause, last_strong = clause_map(text, tokens)
        # 범위를 끊는 것은 감성어(SENTI)뿐이다. 이모티콘은 부정·강조를 받지 않고 범위도 끊지 않는다
        used: set[int] = set()
        items: list[Scored] = []

        for k, h in enumerate(hits):
            if h.kind == "EMO":
                item = Scored(h.surface, h.entry.term, h.entry.score, h.start, kind="EMO")
                item.contrast = _contrast(cfg, last_strong, h.start)
                item.value = item.base * item.contrast
                items.append(item)
                continue
            if h.kind != "SENTI":
                continue
            item = Scored(h.surface, h.entry.term, h.entry.score, h.start)
            factor, flips = 1.0, 0
            fixed = "keep" in h.entry.flags  # '별로'처럼 부정어와 함께 써도 극성이 그대로인 말
            # 앞쪽: 강조어·약화어, 앞 부정어
            for j in range(k - 1, -1, -1):
                m = hits[j]
                if clause[m.start] != clause[h.start] or m.kind == "SENTI":
                    break
                dist = eo[h.start] - eo[m.start]
                if m.kind in ("INT", "DIM") and cfg.intensifier and dist <= cfg.int_window:
                    factor *= m.entry.score
                    item.modifiers.append((m.surface, m.entry.score))
                elif m.kind == "NEG_PRE" and cfg.negation and not fixed and dist <= 1 and j not in used:
                    used.add(j)
                    flips += 1
                    item.negators.append(m.surface)
            # 뒤쪽: 뒤 부정어(다음 감성어 전까지). 짝이 없는 '안·못'도 뒤에서 꾸미는 것으로 본다("몰입이 안 된다")
            if cfg.negation and not fixed:
                for j in range(k + 1, len(hits)):
                    m = hits[j]
                    if clause[m.start] != clause[h.start] or m.kind == "SENTI":
                        break
                    if eo[m.start] - eo[h.end - 1] > cfg.neg_window:
                        break
                    if j in used:
                        continue
                    if m.kind == "NEG_POST":
                        is_post = "afterji" not in m.entry.flags or _after_ji(text, m.start)
                    else:
                        is_post = m.kind == "NEG_PRE" and not _modifies_next(hits, j, eo)
                    if is_post:
                        used.add(j)
                        flips += 1
                        item.negators.append(m.surface)
                if not cfg.double_negation:
                    flips = min(flips, 1)
            sign = -1 if flips % 2 else 1
            item.contrast = _contrast(cfg, last_strong, h.start)
            item.value = item.base * factor * sign * item.contrast
            items.append(item)

        orphans = []
        if cfg.orphan:
            for j, m in enumerate(hits):
                if m.kind in ("NEG_PRE", "NEG_POST") and j not in used:
                    orphans.append({"surface": m.surface, "start": m.start, "value": cfg.orphan_score})

        rating = None
        if cfg.rating:
            found = []
            for rm in RATING_RE.finditer(text):
                v = float(rm.group(1))
                if v <= 4:
                    found.append((rm.start(), {"text": rm.group(0), "points": v, "value": -cfg.rating_score}))
                elif 8 <= v <= 10:
                    found.append((rm.start(), {"text": rm.group(0), "points": v, "value": cfg.rating_score}))
            for rm in STAR_RE.finditer(text):
                found.append((rm.start(), {"text": rm.group(0), "points": None, "value": -cfg.rating_score}))
            if found:
                rating = max(found, key=lambda x: x[0])[1]  # 여러 번 나오면 마지막 언급

        score = sum(i.value for i in items) + sum(o["value"] for o in orphans) + (rating["value"] if rating else 0)
        score = round(score, 6)
        tie = score == 0
        label = cfg.tie_label if tie else int(score > 0)
        return Result(raw, score, label, tie, items, [t.text for t in tokens], _pieces(text, tokens, hits), rating, orphans)

    def predict(self, texts, config: Config | None = None) -> list[int]:
        return [self.analyze(t, config).label for t in texts]

    def scores(self, texts, config: Config | None = None) -> list[float]:
        return [self.analyze(t, config).score for t in texts]


def _contrast(cfg: Config, last_strong: int | None, pos: int) -> float:
    if not cfg.contrast or last_strong is None:
        return 1.0
    return 0.5 if pos < last_strong else 1.5


# 연결 어미 '-지'. 조사 '까지'의 '지'는 제외한다("연기까지 못함"). 규칙 고정 뒤 단위 테스트에서 찾은 구현 버그다
AFTER_JI = re.compile(r"(?<!까)지(?:는|도|를|가|들)?[ ]?$")


def _after_ji(text: str, pos: int) -> bool:
    """'못하·마세요'가 '~지' 바로 뒤에 왔는가(재미있지 못하다, 보지 마세요)."""
    return bool(AFTER_JI.search(text[max(0, pos - 4):pos]))


def _eojeol_index(text: str) -> list[int]:
    out, k = [], 0
    for ch in text:
        out.append(k)
        if ch == " ":
            k += 1
    out.append(k)
    return out


def _modifies_next(hits: list[Hit], j: int, eo: list[int]) -> bool:
    """앞 부정어(안·못) 바로 뒤 1어절 안에 감성어가 있으면 그 감성어를 꾸민다."""
    m = hits[j]
    for n in hits[j + 1:]:
        if n.kind == "SENTI":
            return eo[n.start] - eo[m.start] <= 1
        if eo[n.start] - eo[m.start] > 1:
            break
    return False


def _pieces(text: str, tokens: list[Token], hits: list[Hit]) -> list[tuple[str, str]]:
    """설명용 토큰 조각: 사전에 걸린 부분과 나머지(어미·조사)를 나눈다. 미션 예시의 [이, 식당, 은, 정말, 맛있, 지, 않았어요] 형태."""
    role = {"SENTI": "senti", "EMO": "emo", "INT": "int", "DIM": "int", "NEG_PRE": "neg", "NEG_POST": "neg"}
    by_start = {h.start: h for h in hits}
    cover = {i: h for h in hits for i in range(h.start, h.end)}
    out = []
    for t in tokens:
        if t.kind != "hangul":
            h = by_start.get(t.start)
            out.append((t.text, role[h.kind] if h else t.kind))
            continue
        # 글자마다 어느 사전 항목에 걸렸는지 표시하고 같은 항목끼리 묶는다.
        # "잘 봤"처럼 띄어 쓴 구는 두 어절에 걸쳐 있으므로 시작 위치만으로는 나눌 수 없다.
        segs = []
        for i in range(t.start, t.end):
            h = cover.get(i)
            key = (id(h), role[h.kind]) if h else (None, "rest")
            if segs and segs[-1][2] == key[0] and segs[-1][1] == key[1]:
                segs[-1][0] += text[i]
            else:
                segs.append([text[i], key[1], key[0]])
        segs = [(s, r) for s, r, _ in segs]
        if segs and segs[-1][1] == "rest" and not segs[-1][0].endswith("지만"):
            gap = segs[-1][0]
            for josa in JOSA:
                if gap.endswith(josa) and len(gap) - len(josa) >= 2:  # '문의'를 '문+의'로 자르지 않게 2음절 이상 남긴다
                    segs[-1:] = [(gap[: -len(josa)], "rest"), (josa, "josa")]
                    break
        # 부정어 뒤 어미는 부정어와 붙여 보여 준다(않 + 았어요 → 않았어요)
        merged = []
        for s in segs:
            if merged and merged[-1][1] == "neg" and s[1] == "rest":
                merged[-1] = (merged[-1][0] + s[0], "neg")
            else:
                merged.append(s)
        out += merged
    return out


def explain(result: Result) -> str:
    """미션 결과 예시와 같은 형식의 계산 과정."""
    lines = ["=== 감성 분석 과정 ===", f'문장: "{result.text}"', ""]
    lines.append("1. 토큰화: [" + ", ".join(p for p, _ in result.pieces) + "]")
    senti = [f"{i.surface}({i.base:+g})" for i in result.items]
    lines.append("2. 감성 단어 탐지: " + (", ".join(senti) if senti else "(없음)"))
    negs = [f"'{n}'" for i in result.items for n in i.negators]
    lines.append("3. 부정어 탐지: " + (", ".join(negs) + " → 감성 반전" if negs else "(없음)"))
    mods = [f"'{s}' → 강도 ×{f:g}" for i in result.items for s, f in i.modifiers]
    lines.append("4. 강조어 탐지: " + (", ".join(mods) if mods else "(없음)"))
    extra = []
    if any(i.contrast != 1.0 for i in result.items):
        extra.append("대조 접속: 앞 절 ×0.5, 뒤 절 ×1.5")
    for o in result.orphans:
        extra.append(f"고립 부정어 '{o['surface']}' → {o['value']:+g}")
    if result.rating:
        extra.append(f"평점 언급 '{result.rating['text']}' → {result.rating['value']:+g}")
    if extra:
        lines.append("5. 확장 규칙: " + "; ".join(extra))
    lines.append("")
    terms = []
    for i in result.items:
        parts = [f"({i.base:+g})"]
        if i.negators:
            parts.append("(-1)" * len(i.negators))
        parts += [f"{f:g}" for _, f in i.modifiers]
        if i.contrast != 1.0:
            parts.append(f"{i.contrast:g}")
        terms.append(" × ".join(parts) if len(parts) > 1 else parts[0])
    terms += [f"({o['value']:+g})" for o in result.orphans]
    if result.rating:
        terms.append(f"({result.rating['value']:+g})")
    calc = " + ".join(terms) if terms else "0"
    lines.append(f"계산: {calc} = {result.score:g}")
    verdict = "긍정" if result.label == 1 else "부정"
    if result.decided_by_tie:
        verdict += " (점수 0: 단서 없음 → 기본값)"
    lines.append(f"최종 판정: {verdict}")
    return "\n".join(lines)


# dev에서 고른 최종 설정. 확장 규칙을 모두 켠 I 단계. test를 보기 전에 고정했다
FINAL_CONFIG = Config(emoticon=True, contrast=True, orphan=True, rating=True)
REQUIRED_CONFIG = Config()
