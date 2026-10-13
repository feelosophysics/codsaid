"""텍스트 정제 → 토큰화 → 철자 변형 통합 → 불용어 제거.

설계 기준(근거는 README '전처리 설계' 참고)
- 이메일·URL은 정제 단계에서 지운다. 개인 식별 정보이면서 주제 신호가 거의 없다.
- 아포스트로피는 공백이 아니라 빈 문자열로 지운다. don't → dont 로 한 토큰을 유지해야
  불용어 목록에서 함께 걸러진다.
- 토큰은 영문자로 시작하는 [a-z0-9] 연속 2자 이상이다. x11, 3d(→ 숫자 시작이라 제외),
  mpeg2 같은 기술 용어는 살리고, 연도·점수·전화번호 같은 순수 숫자는 버린다.
- 철자 변형(colour/color 등)만 통합하고 의미 동의어(car/automobile)는 통합하지 않는다.
- 어간 추출은 하지 않는다. graphics → graphic, windows → window 처럼 범주 신호가 섞인다.
"""
from __future__ import annotations

import re
from typing import Iterable, List

from .stopwords import STOPWORDS

EMAIL_RE = re.compile(r"\S+@\S+")
URL_RE = re.compile(r"(?:https?://|ftp://|www\.)\S+")
APOSTROPHE_RE = re.compile(r"['’`]")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
TOKEN_RE = re.compile(r"^[a-z][a-z0-9]+$")

# 의미가 같은 철자 변형만 통합한다(영국식/미국식, 표기 변형).
SPELLING_VARIANTS = {
    "colour": "color", "colours": "colors", "centre": "center", "centres": "centers",
    "favourite": "favorite", "programme": "program", "programmes": "programs",
    "behaviour": "behavior", "grey": "gray", "analyse": "analyze",
    "email": "mail", "emails": "mail", "jpg": "jpeg", "tiff": "tif",
}


def clean(text: str) -> str:
    """소문자화 후 이메일·URL·아포스트로피를 지우고 영숫자 외 문자를 공백으로 바꾼다."""
    text = text.lower()
    text = EMAIL_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = APOSTROPHE_RE.sub("", text)
    return NON_ALNUM_RE.sub(" ", text).strip()


def tokenize(text: str) -> List[str]:
    """정제된 문자열을 공백으로 나눈 뒤 토큰 규칙에 맞는 것만 남긴다."""
    return [tok for tok in clean(text).split() if TOKEN_RE.match(tok)]


def normalize(tokens: Iterable[str]) -> List[str]:
    return [SPELLING_VARIANTS.get(tok, tok) for tok in tokens]


def remove_stopwords(tokens: Iterable[str]) -> List[str]:
    return [tok for tok in tokens if tok not in STOPWORDS]


def preprocess(text: str) -> List[str]:
    """전체 파이프라인. TF-IDF·BM25·분류가 모두 이 함수 하나를 analyzer로 쓴다."""
    return remove_stopwords(normalize(tokenize(text)))
