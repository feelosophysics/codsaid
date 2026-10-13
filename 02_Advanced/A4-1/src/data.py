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
    texts: List[str]          # 원문(스니펫 표시용)
    tokens: List[List[str]]   # 전처리 결과
    labels: np.ndarray        # 범주 번호
    doc_ids: np.ndarray       # 원래 위치 번호
    target_names: List[str]
    n_raw: int                # 제거 전 문서 수

    def __len__(self) -> int:
        return len(self.texts)


def load_corpus(min_tokens: int = MIN_TOKENS) -> Corpus:
    from sklearn.datasets import fetch_20newsgroups  # 데이터 다운로드에만 사용

    raw = fetch_20newsgroups(
        subset="all",
        categories=CATEGORIES,
        remove=("headers", "footers", "quotes"),
        data_home=str(DATA_HOME),
        shuffle=False,
    )
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
    """범주 비율을 유지한 8:2 분할(위치 번호 반환)."""
    from sklearn.model_selection import train_test_split

    positions = np.arange(len(labels))
    return train_test_split(
        positions, test_size=test_size, random_state=random_state, stratify=labels
    )
