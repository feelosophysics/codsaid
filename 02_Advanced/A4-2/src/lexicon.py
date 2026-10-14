"""감성 사전 읽기, 활용형 변이 생성, 문장 안에서 표제어 찾기.

형태소 분석기 없이 한국어 활용을 다루는 방법
1. 받침 확장: 표제어 마지막 음절에 받침이 없으면 받침이 더해진 음절도 일치로 본다.
   지루하 → 지루한(ㄴ)·지루할(ㄹ)·지루함(ㅁ)·지루합(ㅂ)·지루했? (했은 '해'+ㅆ이라 2번 규칙이 필요)
2. 모음 축약·불규칙 변이(P 용언만): 사전에 어간만 적어 두면 아래 형태를 자동으로 만든다.
   하→해(지루해·지루했), ㅣ→ㅕ(멋지→멋져), ㅡ→ㅓ/ㅏ(슬프→슬퍼, 나쁘→나빠), ㅜ→ㅝ, ㅗ→ㅘ, ㅚ→ㅙ,
   ㅂ 불규칙(아깝→아까우·아까워), 르 불규칙(다르→달라), ㅅ 불규칙(낫→나아·나으)
3. 최장 일치: 문장의 각 위치에서 가장 긴 표제어 하나만 쓴다(재미 < 재밌 < 재미없).
   길이가 같으면 받침 확장 없이 정확히 일치한 쪽이 이긴다(재밌 > 재미+ㅆ).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON_DIR = ROOT / "data" / "lexicon"

SBASE, SEND = 0xAC00, 0xD7A3
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]


def is_syllable(ch: str) -> bool:
    return len(ch) == 1 and SBASE <= ord(ch) <= SEND


def split_syllable(ch: str) -> tuple[int, int, int]:
    code = ord(ch) - SBASE
    return code // 588, (code % 588) // 28, code % 28


def join_syllable(cho: int, jung: int, jong: int = 0) -> str:
    return chr(SBASE + cho * 588 + jung * 28 + jong)


def base(ch: str) -> str:
    """받침을 뗀 음절. 한글 음절이 아니면 그대로."""
    if not is_syllable(ch):
        return ch
    c, j, _ = split_syllable(ch)
    return join_syllable(c, j)


def is_open(ch: str) -> bool:
    return is_syllable(ch) and split_syllable(ch)[2] == 0


# ─────────────────────────────── 변이 생성 ───────────────────────────────

BRIGHT = {JUNG.index(v) for v in "ㅏㅑㅗ"}  # 양성 모음: 뒤 ㅡ가 ㅏ로 바뀐다 (나쁘 → 나빠)
CONTRACT = {"ㅣ": "ㅕ", "ㅜ": "ㅝ", "ㅗ": "ㅘ", "ㅚ": "ㅙ"}


def predicate_variants(stem: str) -> list[str]:
    """용언 어간의 활용 표면형(받침 확장 전). 원형이 첫 번째."""
    out = [stem]
    last = stem[-1]
    if not is_syllable(last):
        return out
    c, j, t = split_syllable(last)
    head = stem[:-1]
    vowel = JUNG[j]
    if t == 0:
        if last == "하":
            out.append(head + "해")
        elif last == "르" and head and is_open(head[-1]):
            pc, pj, _ = split_syllable(head[-1])
            new_vowel = "ㅏ" if pj in BRIGHT else "ㅓ"
            out.append(head[:-1] + join_syllable(pc, pj, JONG.index("ㄹ")) + join_syllable(CHO.index("ㄹ"), JUNG.index(new_vowel)))
        elif vowel == "ㅡ":
            bright = bool(head) and is_syllable(head[-1]) and split_syllable(head[-1])[1] in BRIGHT
            out.append(head + join_syllable(c, JUNG.index("ㅏ" if bright else "ㅓ")))
        elif vowel in CONTRACT:
            out.append(head + join_syllable(c, JUNG.index(CONTRACT[vowel])))
    elif JONG[t] == "ㅂ" and len(stem) >= 2:
        # ㅂ 불규칙: 아깝 → 아까우(운·울·움) / 아까워(웠). 규칙 활용(좁은)은 형태가 달라 걸리지 않는다
        out.append(head + join_syllable(c, j) + "우")
        out.append(head + join_syllable(c, j) + "워")
    elif JONG[t] == "ㅅ" and stem == "낫":
        out += ["나으", "나아"]
    return out


# ─────────────────────────────── 사전 ───────────────────────────────

@dataclass
class Entry:
    term: str
    kind: str          # SENTI, INT, DIM, NEG_PRE, NEG_POST, BLOCK, EMO
    score: float       # SENTI·EMO는 점수, INT·DIM은 배율, 부정어는 -1
    pos: str = "N"
    domain: str = "general"
    flags: frozenset = frozenset()
    note: str = ""
    forms: list = field(default_factory=list)


def _read_tsv(path: Path) -> list[list[str]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            rows.append(line.split("\t"))
    return rows


def _flags(s: str) -> frozenset:
    return frozenset(x for x in s.split("+") if x)


def load_sentiment_tsv(path: Path = LEXICON_DIR / "sentiment.tsv") -> list[Entry]:
    out = []
    for term, score, pos, domain, match, note in (r + [""] * (6 - len(r)) for r in _read_tsv(path)):
        kind = "EMO" if pos == "E" else ("BLOCK" if float(score) == 0 else "SENTI")
        out.append(Entry(term, kind, float(score), pos, domain, _flags(match), note))
    return out


def load_modifiers(path: Path = LEXICON_DIR / "modifiers.tsv") -> list[Entry]:
    out = []
    for term, kind, factor, match, note in (r + [""] * (5 - len(r)) for r in _read_tsv(path)):
        out.append(Entry(term, kind, float(factor), "N", "general", _flags(match), note))
    return out


def load_aspects(path: Path = LEXICON_DIR / "aspects.tsv"):
    """(속성 → (domain, 속성어 목록), [(속성, 어간, 점수)])"""
    aspects, context = {}, []
    for row in _read_tsv(path):
        if row[0] == "@context":
            context.append((row[1], row[2], float(row[3])))
        else:
            aspects[row[0]] = (row[1], [t.strip() for t in row[2].split(",") if t.strip()])
    return aspects, context


def knu_entries(knu: list[dict]) -> tuple[list[Entry], dict]:
    """KNU 감성사전(14,854개)을 같은 형식으로 바꾼다.

    - '...다'로 끝나는 표제어는 용언으로 보고 '다'를 떼서 변이를 만든다(가난하다 → 가난하).
    - 띄어 쓴 구(가슴이 뭉클하다)도 그대로 쓴다. 매칭기는 공백도 한 글자로 비교한다.
    - 극성 0은 차단어로 둔다.
    - 이모티콘처럼 한글이 없는 표제어는 EMO로 둔다.
    - 직접 구축 사전과 같은 안전 규칙을 적용한다.
      1음절 체언(지·해·화·정·운 …)은 조사·어미와 구별되지 않아 뺀다.
      1음절 용언 어간(좋·싫·밉 …)은 어절 처음에서만 일치시킨다.
      부정어·강조어와 같은 표제어(없·아니·못하·더럽게)는 modifiers.tsv가 처리하므로 뺀다.
    """
    out = []
    stats = {"total": len(knu), "predicate": 0, "phrase": 0, "emoticon": 0, "neutral": 0,
             "dropped_one_syllable_noun": 0, "dropped_modifier": 0, "start_only": 0}
    modifier_terms = {m.term for m in load_modifiers()}
    seen = set()
    for e in knu:
        word = e["word"].strip()
        score = float(e["polarity"])
        if not word or word in seen:
            continue
        seen.add(word)
        stem = word[:-1] if word.endswith("다") and len(word) >= 2 and " " not in word[-3:] else word
        if stem in modifier_terms:
            stats["dropped_modifier"] += 1
            continue
        if len(stem) == 1 and is_syllable(stem) and stem == word:
            stats["dropped_one_syllable_noun"] += 1
            continue
        has_hangul = any(is_syllable(ch) for ch in word)
        if not has_hangul:
            out.append(Entry(word.lower(), "EMO", score, "E", "knu"))
            stats["emoticon"] += 1
            continue
        if " " in word:
            stats["phrase"] += 1
        kind = "BLOCK" if score == 0 else "SENTI"
        stats["neutral"] += score == 0
        if stem != word:
            flags = frozenset({"start"}) if len(stem) == 1 else frozenset()
            stats["start_only"] += len(stem) == 1
            out.append(Entry(stem, kind, score, "P", "knu", flags))
            stats["predicate"] += 1
        else:
            out.append(Entry(word, kind, score, "N", "knu"))
    return out, stats


# ─────────────────────────────── 매칭 ───────────────────────────────

@dataclass
class Form:
    surface: str
    entry: Entry
    ext: bool  # 마지막 음절 받침 확장 허용


@dataclass
class Hit:
    kind: str
    entry: Entry
    start: int
    end: int
    surface: str  # 문장에서 실제로 일치한 부분
    exact: bool = True


def _is_word_char(ch: str) -> bool:
    return is_syllable(ch)


class Matcher:
    """문장 전체를 왼쪽부터 훑으며 위치마다 가장 긴 표제어를 찾는다.

    이모티콘·영어(EMO)는 토큰 단위로 따로 비교하므로 여기 넣지 않는다.
    같은 표면형이 여러 번 정의되면 먼저 나온 것을 쓴다.
    """

    def __init__(self, entries: list[Entry]):
        self.index: dict[str, list[Form]] = {}
        self.emoticons: dict[str, Entry] = {}
        seen = set()
        for e in entries:
            if e.kind == "EMO":
                self.emoticons.setdefault(e.term, e)
                continue
            term = e.term.lower()  # 문장도 소문자로 바꿔 비교한다(B급, 3D)
            surfaces = predicate_variants(term) if e.pos == "P" else [term]
            e.forms = surfaces
            for s in surfaces:
                if s in seen:
                    continue
                seen.add(s)
                f = Form(s, e, ext="noext" not in e.flags and is_open(s[-1]))
                self.index.setdefault(base(s[0]), []).append(f)
        for forms in self.index.values():
            forms.sort(key=lambda f: -len(f.surface))

    def _match_at(self, text: str, i: int):
        best = None
        for f in self.index.get(base(text[i]), ()):
            s, n = f.surface, len(f.surface)
            if i + n > len(text) or (best and n < len(best[0].surface)):
                continue
            if text[i:i + n - 1] != s[:-1]:
                continue
            last = text[i + n - 1]
            if last == s[-1]:
                exact = True
            elif f.ext and is_syllable(last) and base(last) == s[-1]:
                exact = False
            else:
                continue
            flags = f.entry.flags
            at_start = i == 0 or not _is_word_char(text[i - 1])
            at_end = i + n == len(text) or not _is_word_char(text[i + n])
            if ("start" in flags or "glue" in flags) and not at_start:
                continue
            if "exact" in flags and not (at_start and at_end):
                continue
            if "end" in flags and not at_end:
                continue
            cand = (f, exact)
            if best is None or n > len(best[0].surface) or (exact and not best[1]):
                best = cand
        return best

    def find(self, text: str) -> list[Hit]:
        hits: list[Hit] = []
        i = 0
        while i < len(text):
            m = self._match_at(text, i) if is_syllable(text[i]) or text[i].isdigit() or text[i].isalpha() else None
            if m:
                f, exact = m
                n = len(f.surface)
                hits.append(Hit(f.entry.kind, f.entry, i, i + n, text[i:i + n], exact))
                i += n
            else:
                i += 1
        # glue: 어절 전체이거나, 바로 뒤에 감성어가 붙어 있을 때만 인정
        kept = []
        for k, h in enumerate(hits):
            if "glue" in h.entry.flags:
                whole = h.end == len(text) or not _is_word_char(text[h.end])
                nxt = hits[k + 1] if k + 1 < len(hits) else None
                glued = nxt is not None and nxt.start == h.end and nxt.kind == "SENTI"
                if not (whole or glued):
                    continue
            if h.kind == "BLOCK":
                continue
            kept.append(h)
        return kept


def build_entries(source: str = "custom", knu: list[dict] | None = None) -> list[Entry]:
    """source: custom(직접 구축) / knu(KNU만) / knu+domain(KNU+도메인 특화어) / union(직접 구축 우선 + KNU)"""
    custom = load_sentiment_tsv()
    mods = load_modifiers()
    if source == "custom":
        senti = custom
    else:
        k, _ = knu_entries(knu)
        if source == "knu":
            senti = k
        elif source == "knu+domain":
            senti = [e for e in custom if e.domain in ("movie", "service")] + k
        elif source == "union":
            senti = custom + k
        else:
            raise ValueError(source)
    # 수식어(강조·부정)를 먼저 두어 같은 표면형이면 수식어로 읽게 한다(KNU의 '않다' 같은 표제어 무시)
    return mods + senti
