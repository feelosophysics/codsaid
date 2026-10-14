"""정보 추출과 개인정보 마스킹.

extract(text) 흐름
1. 패턴마다 finditer로 후보를 모은다.
2. URL은 끝 문장부호를 떼고, normalize로 검증한다. 검증에 실패한 후보는 버린다.
3. 후보끼리 겹치면 더 긴 쪽, 길이가 같으면 PRIORITY가 앞인 쪽을 남긴다.
   예: "900101-1234567"은 주민번호 패턴과 다른 패턴이 동시에 노릴 수 있다. 주민번호가 이긴다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .normalize import normalize, trim_url
from .patterns import COMPILED, CORE_TYPES, LABELS, PII_TYPES, PRIORITY


@dataclass
class Entity:
    type: str
    text: str
    start: int
    end: int
    value: object
    info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def candidates(text: str, types=CORE_TYPES) -> list[Entity]:
    found = []
    for kind in types:
        for m in COMPILED[kind].finditer(text):
            raw, start, end = m.group(0), m.start(), m.end()
            groups = m.groupdict()
            if kind == "url":
                trimmed = trim_url(raw)
                end -= len(raw) - len(trimmed)
                if groups.get("rest"):
                    groups["rest"] = groups["rest"][: len(groups["rest"]) - (len(raw) - len(trimmed))]
                raw = trimmed
            result = normalize(kind, groups, raw)
            if result is None:
                continue
            value, info = result
            found.append(Entity(kind, raw, start, end, value, info))
    return found


def resolve_overlaps(found: list[Entity]) -> list[Entity]:
    order = sorted(found, key=lambda e: (-(e.end - e.start), PRIORITY.index(e.type), e.start))
    kept: list[Entity] = []
    for e in order:
        if all(e.end <= k.start or e.start >= k.end for k in kept):
            kept.append(e)
    return sorted(kept, key=lambda e: e.start)


def extract(text: str, types=CORE_TYPES) -> list[Entity]:
    return resolve_overlaps(candidates(text, types))


def extract_grouped(text: str, types=CORE_TYPES) -> dict[str, list]:
    out: dict[str, list] = {t: [] for t in types}
    for e in extract(text, types):
        out[e.type].append(e.value)
    return out


# ─────────────────────────────── 보너스 1: 마스킹 ───────────────────────────────

def mask_value(e: Entity) -> str:
    """유형별 마스킹 형식.

    - 전화: 가운데 자리만 가린다 (010-****-5678, 미션 예시와 같은 형식)
    - 이메일: 로컬 파트 앞 2글자만 남긴다 (us***@domain.com)
    - 주민번호: 생년월일과 성별 자리만 남긴다 (900101-1******)
    - 카드: 앞 6자리와 끝 4자리만 남긴다. PCI DSS가 화면 표시에 허용하는 최대 범위다
    - 주소: 시·도와 시·군·구까지만 남긴다
    """
    v = str(e.value)
    if e.type == "phone":
        parts = v.split("-")
        if len(parts) == 3:
            return f"{parts[0]}-{'*' * len(parts[1])}-{parts[2]}"
        return f"{parts[0]}-****"
    if e.type == "email":
        local, domain = v.split("@", 1)
        return f"{local[:2]}{'*' * max(3, len(local) - 2)}@{domain}"
    if e.type == "rrn":
        return v[:8] + "*" * 6
    if e.type == "card":
        digits = v.replace("-", "")
        masked = digits[:6] + "*" * (len(digits) - 10) + digits[-4:]
        sizes = [len(p) for p in v.split("-")]
        out, i = [], 0
        for s in sizes:
            out.append(masked[i:i + s])
            i += s
        return "-".join(out)
    if e.type == "address":
        return f"{e.info['sido']} {e.info['sigungu']} ****"
    return "*" * len(e.text)


def mask(text: str, types=PII_TYPES) -> tuple[str, list[Entity]]:
    """개인정보를 찾아 가린 문장과 찾은 개체 목록."""
    ents = extract(text, types)
    out, last = [], 0
    for e in ents:
        out.append(text[last:e.start])
        out.append(mask_value(e))
        last = e.end
    out.append(text[last:])
    return "".join(out), ents


def format_report(text: str) -> str:
    """CLI 출력용. 미션 결과 예시의 형식을 따른다."""
    lines = ["=== 정보 추출 결과 ===", f'입력: "{text}"', "", "추출 결과:"]
    ents = extract(text)
    if not ents:
        lines.append("- (없음)")
    for e in ents:
        label = LABELS[e.type]
        if e.type == "money":
            unit = "원" if e.info["currency"] == "KRW" else "센트(USD)"
            shown = f"{e.value} ({unit}, 정규화)"
        elif str(e.value) != e.text:
            shown = f"{e.value} (정규화, 원문 '{e.text}')"
        else:
            shown = str(e.value)
        lines.append(f"- {label}: {shown}")
    return "\n".join(lines)
