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
# 이 선언은 아래 타입 힌트의 평가를 늦춘다. text: str, -> List[str]는 입력·반환 안내이며
# 실제로 값을 검사하거나 문자열로 바꿔 주지는 않는다.
from __future__ import annotations

import re
from typing import Iterable, List

from .stopwords import STOPWORDS

# import는 다른 모듈의 기능을 가져온다. from .stopwords의 점은 같은 src 패키지를 뜻한다.
# r"..."는 역슬래시를 그대로 보존하는 문자열, re.compile은 반복 사용할 정규식 규칙을 만든다.
# \S+는 공백 아닌 문자 1개 이상, (?:...)는 묶음, |는 또는, \.은 실제 점이다.
EMAIL_RE = re.compile(r"\S+@\S+")
URL_RE = re.compile(r"(?:https?://|ftp://|www\.)\S+")
APOSTROPHE_RE = re.compile(r"['’`]")
# [^a-z0-9]+는 영문 소문자·숫자가 아닌 연속 부분.
# TOKEN_RE의 ^와 $는 문자열 시작·끝, [a-z]는 첫 글자, 뒤의 +는 최소 한 글자 더 필요하다는 뜻이다.
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
    """원문을 검색 계산에 쓸 소문자 문자열로 정제한다.

    원문 자체를 수정하지 않고 새 문자열을 반환한다. 이메일·URL을 먼저 지워야
    기호를 공백으로 바꾼 뒤 nasa, gov 같은 조각이 주제 단어로 남는 일을 줄인다.
    단, 프로토콜 없는 export.lcs.mit.edu 같은 호스트명은 이 규칙에 걸리지 않는다.

    Args:
        text: 영어 게시글 또는 검색어 문자열.

    Returns:
        str: 정제한 문자열. "Don't COLOUR!" → "dont colour".
        이 단계는 불용어를 지우거나 color로 철자를 통합하지 않는다.
    """
    # 점(.) 뒤 메서드를 호출한다. 문자열은 불변이므로 lower()의 새 결과를 text에 다시 저장한다.
    # sub(대체문자, 원문)는 규칙에 맞는 부분을 교체한다. dont 형태를 유지해야 축약 불용어에 걸린다.
    text = text.lower()
    text = EMAIL_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = APOSTROPHE_RE.sub("", text)
    return NON_ALNUM_RE.sub(" ", text).strip()


def tokenize(text: str) -> List[str]:
    """문자열을 정제한 뒤 규칙에 맞는 토큰 목록으로 나눈다.

    토큰은 이 구현이 단어 하나로 취급하는 문자열이다. 사전으로 의미를 판별하지 않는다.
    "X11 3d 1993 a mpeg2" → ["x11", "mpeg2"]. 3d도 숫자로 시작하므로 버린다.

    Args:
        text: 아직 정제하지 않아도 되는 문자열. 내부에서 clean을 호출한다.

    Returns:
        List[str]: 순서와 중복을 유지한 토큰. "space space"는 두 개를 남긴다.
    """
    # [식 for 변수 in 묶음 if 조건]은 리스트 컴프리헨션이다. 공백으로 나눈 항목을 tok로
    # 하나씩 읽고 match가 성공한 것만 목록에 담는다. return은 그 결과를 반환하고 함수를 끝낸다.
    return [tok for tok in clean(text).split() if TOKEN_RE.match(tok)]


def normalize(tokens: Iterable[str]) -> List[str]:
    """등록한 철자·표기 변형을 대표 표기로 바꾼다.

    여기의 normalize는 문자열 표기 통합이다. tfidf.normalize_rows의 벡터 길이
    정규화와 다르다. colour→color, jpg→jpeg처럼 표에 있는 경우만 바꾼다.

    Args:
        tokens: 차례로 읽을 수 있는 토큰 묶음(Iterable). 보통 tokenize의 리스트.

    Returns:
        List[str]: 같은 개수의 새 토큰 목록. 없는 키는 원래 토큰을 유지한다.
    """
    # dict.get(키, 기본값): colour 키는 color, 미등록 space 키는 기본값 space를 돌려준다.
    return [SPELLING_VARIANTS.get(tok, tok) for tok in tokens]


def remove_stopwords(tokens: Iterable[str]) -> List[str]:
    """주제 구분에 덜 쓸 것으로 정한 토큰을 제거한다.

    불용어는 모든 과제에서 쓸모없는 단어라는 뜻이 아니다. 여기서는 not도 제거하므로
    부정 의미를 잃는다. 이 선택의 한계는 experiments.bow_limits에서 확인한다.

    Args:
        tokens: 철자 통합이 끝난 토큰 묶음.

    Returns:
        List[str]: STOPWORDS에 없는 것만 남긴 목록. 순서·남은 중복은 유지한다.
    """
    return [tok for tok in tokens if tok not in STOPWORDS]


def preprocess(text: str) -> List[str]:
    """문서와 질의에 같은 전처리 네 단계를 적용한다.

    "I don't like the colour of this window"를 따라가 보자.
    tokenize → [i, dont, like, the, colour, of, this, window],
    normalize → colour만 color로 교체, remove_stopwords → [color, window].
    검색어에도 같은 함수를 써야 문서의 color와 질의의 colour가 같은 열에 들어간다.

    예상 질문: "space space and unknown"의 space는 한 번만 남을까?
    답: [space, space, unknown]이다. 중복은 TF 빈도 계산에 필요해 유지한다.

    Args:
        text: 원문 문서 또는 검색어.

    Returns:
        List[str]: TF-IDF·BM25·분류의 공통 입력. 모두 제거되면 빈 리스트.
    """
    # 중첩 호출은 안쪽부터 평가한다: tokenize → normalize → remove_stopwords.
    return remove_stopwords(normalize(tokenize(text)))
