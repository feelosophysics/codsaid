"""정규식이 찾은 후보를 검증하고 정규화된 값으로 바꾼다.

정규화 형식
- 이메일: 도메인만 소문자. 로컬 파트는 RFC 5321상 대소문자를 구분할 수 있어 그대로 둔다.
- 전화번호: 하이픈 구분. +82는 0으로 바꾼다 (+82 10-1234-5678 → 010-1234-5678).
- 날짜: ISO 8601 (YYYY-MM-DD). 연도가 없으면 ISO 8601:2000의 --MM-DD 형식.
- 금액: 정수. 원화는 원 단위, 달러는 센트 단위 정수와 통화 코드.
  소수 금액을 float로 다루면 0.1+0.2 같은 오차가 생겨서, 금융 시스템은 최소 화폐 단위 정수로 저장한다.
- URL: 스킴·호스트 소문자, www.만 있으면 http:// 보충, 기본 포트(:80, :443) 제거, 끝 문장부호 제거.

검증에 실패하면 None을 돌려준다. 호출한 쪽은 그 후보를 버린다.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

HANGUL_DIGITS = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
SMALL_UNITS = {"십": 10, "백": 100, "천": 1000}
BIG_UNITS = {"만": 10**4, "억": 10**8, "조": 10**12}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

_AMOUNT_TOKEN = re.compile(r"[0-9][0-9,]*(?:\.[0-9]+)?|[일이삼사오육칠팔구]|[십백천]|[만억조]")


def two_digit_year(yy: int) -> int:
    """POSIX strptime %y 규칙: 69~99 → 1969~1999, 00~68 → 2000~2068."""
    return 1900 + yy if yy >= 69 else 2000 + yy


def iso_date(y: int | None, m: int, d: int) -> str | None:
    """실제로 있는 날짜만 받는다. 연도가 없으면 윤년(2000)으로 2월 29일까지 허용한다."""
    try:
        dt.date(y if y is not None else 2000, m, d)
    except ValueError:
        return None
    return f"{y:04d}-{m:02d}-{d:02d}" if y is not None else f"--{m:02d}-{d:02d}"


def parse_korean_amount(text: str) -> int | None:
    """'1억 2천만' → 120000000, '2.5억' → 250000000, '오천' → 5000, '1,500만' → 15000000.

    만 아래 자리(section)를 모으다가 큰 단위(만·억·조)를 만나면 곱해서 total에 더한다.
    숫자도 단위도 없는 후보('사원'의 '사')는 금액이 아니므로 None.
    """
    s = text.replace(" ", "")
    if not re.search(r"[0-9십백천만억조]", s):
        return None
    tokens = _AMOUNT_TOKEN.findall(s)
    if "".join(tokens) != s:
        return None
    total, section, num = Decimal(0), Decimal(0), None
    for tok in tokens:
        if tok[0].isdigit():
            if num is not None:
                return None  # 숫자가 연달아 오는 형식은 해석하지 않는다
            num = Decimal(tok.replace(",", ""))
        elif tok in HANGUL_DIGITS:
            if num is not None:
                return None
            num = Decimal(HANGUL_DIGITS[tok])
        elif tok in SMALL_UNITS:
            section += (num if num is not None else 1) * SMALL_UNITS[tok]
            num = None
        else:  # 큰 단위
            section += num if num is not None else 0
            total += (section if section else 1) * BIG_UNITS[tok]
            section, num = Decimal(0), None
    total += section + (num if num is not None else 0)
    return int(total.to_integral_value())


def luhn_ok(digits: str) -> bool:
    """카드번호 체크섬. 뒤에서 두 번째 자리부터 하나 걸러 2배 하고 9를 넘으면 9를 뺀다. 합이 10의 배수면 유효."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def rrn_checksum_ok(digits13: str) -> bool:
    """2020년 10월 이전 발급 주민등록번호의 검증식. 이후 번호는 뒷자리가 임의라 맞지 않을 수 있다."""
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    s = sum(int(a) * w for a, w in zip(digits13[:12], weights))
    return (11 - s % 11) % 10 == int(digits13[12])


TRAILING_PUNCT = ".,;:!?'\""
CLOSERS = {")": "(", "]": "[", "}": "{"}


def trim_url(raw: str) -> str:
    """문장 끝에 붙은 문장부호를 뗀다. 괄호는 짝이 안 맞을 때만 뗀다 (위키 문서명의 '(동음이의)' 보호)."""
    while raw:
        last = raw[-1]
        if last in TRAILING_PUNCT:
            raw = raw[:-1]
        elif last in CLOSERS and raw.count(last) > raw.count(CLOSERS[last]):
            raw = raw[:-1]
        else:
            break
    return raw


def normalize(kind: str, g: dict, raw: str):
    """(정규화 값, 부가 정보) 또는 None."""
    if kind == "email":
        return f"{g['local']}@{g['domain'].lower()}", {}

    if kind == "phone":
        if g.get("rep"):
            return f"{g['rep']}-{g['rep_last']}", {"kind": "대표번호"}
        area = "0" + g["area_i"] if g.get("area_i") else g["area"]
        return f"{area}-{g['mid']}-{g['last']}", {"kind": "휴대전화" if area.startswith("01") else "일반"}

    if kind == "date":
        if g.get("m"):
            y = g.get("y")
            year = None if y is None else (int(y) if len(y) == 4 else two_digit_year(int(y)))
            iso = iso_date(year, int(g["m"]), int(g["d"]))
        elif g.get("m2"):
            y = g["y2"]
            year = int(y) if len(y) == 4 else two_digit_year(int(y))
            iso = iso_date(year, int(g["m2"]), int(g["d2"]))
        else:
            iso = iso_date(int(g["y3"]), MONTHS[g["mon"][:3].lower()], int(g["d3"]))
        return (iso, {}) if iso else None

    if kind == "money":
        if g.get("krw") is not None:
            v = parse_korean_amount(g["krw"])
            return (v, {"currency": "KRW"}) if v is not None else None
        if g.get("won_sym"):
            return int(Decimal(g["won_sym"].replace(",", ""))), {"currency": "KRW"}
        usd = g.get("usd") or g.get("usd2")
        cents = int((Decimal(usd.replace(",", "")) * 100).to_integral_value())
        return cents, {"currency": "USD", "unit": "cent"}

    if kind == "url":
        scheme = (g.get("scheme") or "http").lower()
        host = g["host"].lower()
        port = g.get("port")
        if port and (scheme, port) in {("http", "80"), ("https", "443")}:
            port = None
        rest = g.get("rest") or ""
        return f"{scheme}://{host}{':' + port if port else ''}{rest}", {}

    if kind == "rrn":
        digits = g["birth"] + g["back"]
        yy, mm, dd = int(digits[:2]), int(digits[2:4]), int(digits[4:6])
        century = {"1": 1900, "2": 1900, "3": 2000, "4": 2000, "5": 1900, "6": 1900, "7": 2000, "8": 2000}[digits[6]]
        if iso_date(century + yy, mm, dd) is None:
            return None
        return f"{g['birth']}-{g['back']}", {"checksum": rrn_checksum_ok(digits)}

    if kind == "card":
        digits = re.sub(r"[ -]", "", raw)
        groups = [digits[i:i + 4] for i in range(0, 16, 4)] if len(digits) == 16 else [digits[:4], digits[4:10], digits[10:]]
        return "-".join(groups), {"luhn": luhn_ok(digits)}

    if kind == "address":
        return re.sub(r"\s+", " ", raw.strip()), {"sido": g["sido"], "sigungu": g["sigungu"].strip()}

    raise ValueError(kind)
