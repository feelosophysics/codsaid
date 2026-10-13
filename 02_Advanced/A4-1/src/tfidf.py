"""NumPy로 직접 구현한 TF-IDF.

    tfidf(t, d) = tf(t, d) × idf(t)              → 행마다 L2(또는 L1) 정규화

    idf(t) = ln((1 + n) / (1 + df(t))) + 1       (smooth_idf=True, sklearn 기본값)
    idf(t) = ln(n / df(t)) + 1                   (smooth_idf=False)

n은 문서 수, df(t)는 단어 t가 한 번 이상 나온 문서 수다. 끝의 +1 때문에 모든 문서에
나오는 단어도 가중치가 0이 되지 않는다. 이 정의는 sklearn TfidfVectorizer와 같다.

TF 변형(보너스 1)
    raw     : f(t,d)                                  원래 빈도
    log     : 1 + ln f(t,d)        (f > 0일 때)       sklearn sublinear_tf=True와 같음
    double  : K + (1-K)·f(t,d)/max_t' f(t',d)  (f > 0, K=0.5)
    binary  : 1                    (f > 0일 때)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

TF_VARIANTS = ("raw", "log", "double", "binary")


def build_vocabulary(
    docs_tokens: Sequence[Sequence[str]], min_df: int = 1, max_df: float = 1.0
) -> List[str]:
    """문서 빈도로 어휘를 거른 뒤 알파벳순으로 정렬한다(sklearn과 같은 열 순서).

    min_df: 정수. df(t) >= min_df 인 단어만 남긴다.
    max_df: 0~1 실수면 비율, 1보다 큰 정수면 문서 수. df(t) <= 상한 인 단어만 남긴다.
    """
    df: Dict[str, int] = {}
    for tokens in docs_tokens:
        for tok in set(tokens):
            df[tok] = df.get(tok, 0) + 1
    n_docs = len(docs_tokens)
    upper = max_df * n_docs if isinstance(max_df, float) else max_df
    return sorted(tok for tok, count in df.items() if min_df <= count <= upper)


def count_matrix(docs_tokens: Sequence[Sequence[str]], vocabulary: Dict[str, int]) -> np.ndarray:
    """(문서 수, 어휘 수) 단어 빈도 행렬. 어휘에 없는 토큰은 버린다.

    모든 (문서 번호, 단어 번호) 쌍을 모은 뒤 np.add.at 으로 한 번에 더한다.
    같은 쌍이 여러 번 나오면 그 횟수만큼 더해진다(일반 인덱싱 += 는 중복을 한 번만 센다).
    """
    rows, cols = [], []
    for i, tokens in enumerate(docs_tokens):
        ids = [vocabulary[tok] for tok in tokens if tok in vocabulary]
        rows.extend([i] * len(ids))
        cols.extend(ids)
    counts = np.zeros((len(docs_tokens), len(vocabulary)), dtype=np.float64)
    np.add.at(counts, (np.asarray(rows, dtype=np.intp), np.asarray(cols, dtype=np.intp)), 1.0)
    return counts


def term_frequency(counts: np.ndarray, variant: str = "raw", k: float = 0.5) -> np.ndarray:
    """빈도 행렬에 TF 변형을 적용한다. 빈도가 0인 칸은 어느 변형에서도 0이다."""
    present = counts > 0
    if variant == "raw":
        return counts.copy()
    if variant == "log":
        out = np.zeros_like(counts)
        np.log(counts, out=out, where=present)
        return np.where(present, out + 1.0, 0.0)
    if variant == "double":
        row_max = counts.max(axis=1, keepdims=True)
        ratio = np.divide(counts, row_max, out=np.zeros_like(counts), where=row_max > 0)
        return np.where(present, k + (1.0 - k) * ratio, 0.0)
    if variant == "binary":
        return present.astype(np.float64)
    raise ValueError(f"알 수 없는 TF 변형: {variant} (가능: {TF_VARIANTS})")


def document_frequency(counts: np.ndarray) -> np.ndarray:
    return (counts > 0).sum(axis=0)


def inverse_document_frequency(df: np.ndarray, n_docs: int, smooth: bool = True) -> np.ndarray:
    df = df.astype(np.float64)
    if smooth:
        return np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
    return np.log(n_docs / df) + 1.0


def normalize_rows(matrix: np.ndarray, norm: Optional[str] = "l2", inplace: bool = False) -> np.ndarray:
    """행 벡터를 단위 길이로 나눈다. 길이가 0인 행(어휘에 걸린 단어가 없는 문서)은 그대로 0."""
    if norm is None:
        return matrix
    if norm == "l2":
        lengths = np.sqrt(np.einsum("ij,ij->i", matrix, matrix))[:, None]
    elif norm == "l1":
        lengths = np.abs(matrix).sum(axis=1, keepdims=True)
    else:
        raise ValueError(f"알 수 없는 norm: {norm}")
    safe = np.where(lengths > 0, lengths, 1.0)
    if inplace:
        matrix /= safe
        return matrix
    return matrix / safe


class TfidfVectorizerNP:
    """sklearn TfidfVectorizer와 같은 인터페이스(fit / transform)의 NumPy 구현.

    입력은 이미 전처리된 토큰 리스트의 리스트다. 전처리를 바깥에 두어야
    sklearn과 정확히 같은 토큰으로 비교할 수 있다.
    """

    def __init__(
        self,
        tf: str = "raw",
        smooth_idf: bool = True,
        norm: Optional[str] = "l2",
        min_df: int = 1,
        max_df: float = 1.0,
    ):
        if tf not in TF_VARIANTS:
            raise ValueError(f"알 수 없는 TF 변형: {tf}")
        self.tf = tf
        self.smooth_idf = smooth_idf
        self.norm = norm
        self.min_df = min_df
        self.max_df = max_df

    def fit(self, docs_tokens: Sequence[Sequence[str]]) -> "TfidfVectorizerNP":
        self.fit_transform(docs_tokens)
        return self

    def fit_transform(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        self.terms_ = build_vocabulary(docs_tokens, self.min_df, self.max_df)
        self.vocabulary_ = {term: j for j, term in enumerate(self.terms_)}
        counts = count_matrix(docs_tokens, self.vocabulary_)
        self.df_ = document_frequency(counts)
        self.idf_ = inverse_document_frequency(self.df_, len(docs_tokens), self.smooth_idf)
        return self._weight(counts)

    def transform(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        """학습한 어휘와 IDF로 새 문서(또는 쿼리)를 벡터화한다. 새 단어는 무시된다."""
        return self._weight(count_matrix(docs_tokens, self.vocabulary_))

    def counts(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        return count_matrix(docs_tokens, self.vocabulary_)

    def _weight(self, counts: np.ndarray) -> np.ndarray:
        weighted = term_frequency(counts, self.tf)
        weighted *= self.idf_  # (n, V) × (V,) 브로드캐스팅: 열 j 전체에 idf[j]를 곱한다
        return normalize_rows(weighted, self.norm, inplace=True)
