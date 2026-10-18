"""20 Newsgroups 5개 범주 로딩과 정리.

- 헤더·서명(footer)·인용문(quotes)을 제거한다. 헤더의 Newsgroups:/From: 줄은 정답 범주와
  작성자 이메일을 그대로 담고 있어서, 남겨두면 분류가 본문이 아니라 헤더로 풀린다(정보 누수).
- 전처리 후 토큰이 MIN_TOKENS 개 미만인 문서는 결측으로 보고 뺀다(빈 글, 인용만 있던 답글).
- 문서 ID는 sklearn이 주는 원래 순서(shuffle=False)의 위치 번호다. 제거 후에도 바뀌지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

from .preprocess import preprocess

# __file__은 현재 파일, resolve()는 절대 경로, parents[1]은 src의 부모 A4-1이다.
# Path끼리 /로 이으면 하위 경로를 만든다. 실행 터미널 위치 대신 파일 위치를 기준으로 한다.
ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = ROOT / "data"
CATEGORIES = [
    "comp.graphics",
    "comp.windows.x",
    "rec.sport.baseball",
    "rec.sport.hockey",
    "sci.space",
]
MIN_TOKENS = 5
RANDOM_STATE = 42


@dataclass
class Corpus:
    """동일한 문서를 같은 위치로 연결하는 데이터 묶음.

    @dataclass는 아래 필드들을 받는 초기화 메서드를 자동으로 만든다.
    texts[p], tokens[p], labels[p], doc_ids[p]는 반드시 같은 문서다.
    위치 p는 제거 후 0부터 다시 매기지만 doc_ids[p]는 제거 전 ID다.
    예: 원래 0,1,2번 중 1번을 제거하면 위치 [0,1], ID [0,2]가 된다.

    Attributes:
        texts: N개 원문. 화면 발췌용으로 보존한다.
        tokens: N개 토큰 리스트. 한 문서의 길이는 서로 달라도 된다.
        labels: shape (N,) 정답 범주 번호. target_names의 위치와 대응한다.
        doc_ids: shape (N,) 오름차순 원래 ID. 검색 결과에 표시한다.
        target_names: 번호를 범주 이름으로 바꾸는 목록.
        n_raw: 짧은 글을 제거하기 전 문서 수.
    """
    texts: List[str]          # 원문(스니펫 표시용)
    tokens: List[List[str]]   # 전처리 결과
    labels: np.ndarray        # 범주 번호
    doc_ids: np.ndarray       # 원래 위치 번호
    target_names: List[str]
    n_raw: int                # 제거 전 문서 수

    def __len__(self) -> int:
        """len(corpus)를 원문 목록의 길이 N으로 해석한다.

        Returns:
            int: 필터링 후 문서 수. n_raw와 다를 수 있다.
        """
        return len(self.texts)


def load_corpus(min_tokens: int = MIN_TOKENS) -> Corpus:
    """캐시에서 게시글을 읽고 전처리·길이 필터를 함께 적용한다.

    fetch_20newsgroups는 캐시가 없으면 다운로드한다. 헤더·서명·인용문을 빼도
    모든 메타정보가 완전히 제거된다는 보장은 없다. 남은 본문으로만 학습한다.

    Args:
        min_tokens: 전처리 후 남은 토큰 수의 하한. 서로 다른 단어 수가 아닌 중복 포함 수.

    Returns:
        Corpus: 필터를 통과한 원문·토큰·정답·원래 ID의 묶음.

    Raises:
        OSError: 캐시 읽기나 최초 다운로드 등 외부 자료 접근에 실패한 경우.
    """
    from sklearn.datasets import fetch_20newsgroups  # 데이터 다운로드에만 사용

    raw = fetch_20newsgroups(
        subset="all",
        categories=CATEGORIES,
        remove=("headers", "footers", "quotes"),
        data_home=str(DATA_HOME),
        shuffle=False,
    )
    # 원문 N개 → 길이가 서로 다른 토큰 목록 N개. enumerate는 (0부터의 위치, 값)을 준다.
    # keep에 남긴 동일 위치로 모든 필드를 골라야 원문·정답이 뒤섞이지 않는다.
    all_tokens = [preprocess(text) for text in raw.data]
    keep = [i for i, toks in enumerate(all_tokens) if len(toks) >= min_tokens]
    return Corpus(
        texts=[raw.data[i] for i in keep],
        tokens=[all_tokens[i] for i in keep],
        labels=np.asarray(raw.target)[keep],
        doc_ids=np.asarray(keep),
        target_names=list(raw.target_names),
        n_raw=len(raw.data),
    )


def train_test_indices(labels: np.ndarray, test_size: float = 0.2, random_state: int = RANDOM_STATE):
    """정답 비율을 대략 유지하며 학습·최종 평가 위치를 나눈다.

    stratify는 각 범주 비율을 유지하도록 분할한다. random_state는 같은 입력의
    분할을 재현하게 한다. 원래 자료의 공식 train/test가 아닌 전체 자료의 새 8:2 분할이다.

    Args:
        labels: shape (N,) 범주 번호.
        test_size: Test로 남길 비율. 기본 0.2.
        random_state: 분할 난수의 고정 기준.

    Returns:
        tuple: (train_idx, test_idx). 각 값은 Corpus의 위치 번호 배열이다.

    Raises:
        ValueError: 표본 수가 층화 분할을 수행하기에 부족한 경우.
    """
    from sklearn.model_selection import train_test_split

    # arange(N)은 [0,1,...,N-1] 배열. 문서 내용 대신 위치를 나누면 여러 필드를 같은 분할로 꺼낸다.
    positions = np.arange(len(labels))
    return train_test_split(
        positions, test_size=test_size, random_state=random_state, stratify=labels
    )
