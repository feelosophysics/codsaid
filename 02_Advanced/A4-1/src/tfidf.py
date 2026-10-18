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
    """각 문서의 출현 여부로 단어를 걸러 공통 열 이름을 정한다.

    이어 쓰는 작은 예: docs_tokens=[[space, space, orbit], [goalie, orbit]].
    set(tokens)는 첫 문서의 space 중복을 지워 df={space:1, orbit:2, goalie:1}를 만든다.
    정렬 결과 terms=[goalie, orbit, space]. min_df=2면 orbit만 남는다.
    이 열 순서를 모든 문서·질의에서 지키지 않으면 서로 다른 단어를 곱하게 된다.

    Args:
        docs_tokens: 바깥 목록은 문서, 안쪽 목록은 토큰. N개 문서.
        min_df: 출현 문서 수의 정수 하한. 단어 총빈도 하한과 다르다.
        max_df: float이면 문서 수에 곱하는 비율, int이면 절대 문서 수.
            1.0은 전체 문서, 정수 1은 한 문서라는 차이가 있다.

    Returns:
        List[str]: 알파벳순 어휘 목록. 조건에 맞는 단어가 없으면 빈 목록.
        잘못된 범위에 대한 별도 유효성 검사는 없으므로 호출자가 유효한 값을 준다.
    """
    # {}는 빈 dict. 토큰을 키, 문서 수를 값으로 보관한다. set은 중복을 없앤다.
    df: Dict[str, int] = {}
    for tokens in docs_tokens:
        for tok in set(tokens):
            df[tok] = df.get(tok, 0) + 1
    n_docs = len(docs_tokens)
    upper = max_df * n_docs if isinstance(max_df, float) else max_df
    return sorted(tok for tok, count in df.items() if min_df <= count <= upper)


def count_matrix(docs_tokens: Sequence[Sequence[str]], vocabulary: Dict[str, int]) -> np.ndarray:
    """토큰 중복을 세어 (문서 수 N, 어휘 수 V) 실수 행렬로 만든다.

    위 예의 열 [goalie, orbit, space]이면 [[0,1,2],[1,1,0]]이다.
    첫 행은 첫 문서, 세 번째 열은 space 빈도 2다. 어휘에 없는 토큰은 무시한다.
    rows=[0,0,0,1,1], cols=[2,2,1,0,1]처럼 토큰 하나당 좌표 한 쌍을 만든다.

    Args:
        docs_tokens: N개 문서의 토큰 목록.
        vocabulary: {단어: 열 번호}. 번호는 0부터 V-1까지 중복 없이 연속해야 한다.

    Returns:
        np.ndarray: shape (N,V), float64. float로 만들어 이후 가중치·나눗셈을 저장한다.
    """
    rows, cols = [], []
    for i, tokens in enumerate(docs_tokens):
        # enumerate는 (문서 위치 i, 토큰 목록)을 준다. 사전의 [] 조회는 단어의 열 번호를 꺼낸다.
        ids = [vocabulary[tok] for tok in tokens if tok in vocabulary]
        # [i] * 3은 [i,i,i]. extend는 목록 전체를 이어 붙여 토큰 좌표 수를 맞춘다.
        rows.extend([i] * len(ids))
        cols.extend(ids)
    counts = np.zeros((len(docs_tokens), len(vocabulary)), dtype=np.float64)
    # 중복 좌표 (0,2)가 두 번 있어야 space=2다. add.at은 반복 좌표를 모두 누적한다.
    # 정수 좌표 배열 dtype=intp와 빈도용 float64는 용도가 다르다.
    np.add.at(counts, (np.asarray(rows, dtype=np.intp), np.asarray(cols, dtype=np.intp)), 1.0)
    return counts


def term_frequency(counts: np.ndarray, variant: str = "raw", k: float = 0.5) -> np.ndarray:
    """반복 횟수에 줄 가중치(TF)를 선택한다.

    [4,1,0] 한 행을 넣으면 raw=[4,1,0], log=[2.3863,1,0],
    double(k=.5)=[1,.625,0], binary=[1,1,0]이다.
    log는 4회 반복을 4배보다 작게 보상하고 binary는 존재 여부만 남긴다.
    double의 max는 문서마다 따로 계산한다. 어느 방식도 단어 의미를 배우지는 않는다.

    Args:
        counts: shape (N,V) 비음수 빈도. double은 V가 1 이상이어야 한다.
        variant: raw, log, double, binary 중 하나.
        k: double의 최저 양수 가중치 기준. 보통 0~1, 기본 0.5.

    Returns:
        np.ndarray: counts와 같은 shape의 새 TF 배열. 없는 단어의 칸은 항상 0.

    Raises:
        ValueError: 지원하지 않는 variant, 또는 double에 빈 어휘를 준 경우.
    """
    # > 0은 원소마다 True/False인 마스크를 만든다. where=present로 log(0)을 피한다.
    # np.where(조건,A,B)는 칸마다 A 또는 B를 고른다. out=은 결과를 담을 배열이다.
    present = counts > 0
    if variant == "raw":
        return counts.copy()
    if variant == "log":
        out = np.zeros_like(counts)
        np.log(counts, out=out, where=present)
        return np.where(present, out + 1.0, 0.0)
    if variant == "double":
        # axis=1은 단어 열을 따라 줄여 문서별 최댓값을 만든다. keepdims=True로
        # (N,) 대신 (N,1)을 남겨 (N,V)의 각 행에 그 행의 최댓값을 나눈다.
        row_max = counts.max(axis=1, keepdims=True)
        ratio = np.divide(counts, row_max, out=np.zeros_like(counts), where=row_max > 0)
        return np.where(present, k + (1.0 - k) * ratio, 0.0)
    if variant == "binary":
        return present.astype(np.float64)
    raise ValueError(f"알 수 없는 TF 변형: {variant} (가능: {TF_VARIANTS})")


def document_frequency(counts: np.ndarray) -> np.ndarray:
    """열마다 그 단어가 나온 문서 수 df를 센다.

    [[0,1,2],[1,1,0]] > 0 → [[False,True,True],[True,True,False]].
    axis=0은 문서 방향을 합쳐 없애므로 [1,2,1], shape (V,)가 남는다.
    counts.sum(axis=0)=[1,2,2]는 총빈도라 df와 다르다.

    Args:
        counts: shape (N,V) 빈도 행렬.

    Returns:
        np.ndarray: shape (V,) 출현 문서 수.
    """
    return (counts > 0).sum(axis=0)


def inverse_document_frequency(df: np.ndarray, n_docs: int, smooth: bool = True) -> np.ndarray:
    """여러 문서에 흔한 단어의 상대 가중치를 줄이는 IDF를 계산한다.

    N=2, df=[1,2,1]이면 smooth=True에서 ln(3/[2,3,2])+1
    = [1.405465,1,1.405465]. np.log는 밑 e의 자연로그 ln이다.
    분자·분모의 +1은 평활화, 마지막 +1은 모든 문서에 나오는 단어도 1로 남긴다.
    희귀하다고 중요한 의미라는 보장은 없으며 오타도 커질 수 있다.

    Args:
        df: shape (V,) 출현 문서 수. 비평활화 시 모든 값이 양수여야 한다.
        n_docs: IDF 학습에 사용한 문서 수 N.
        smooth: True면 ln((N+1)/(df+1))+1, False면 ln(N/df)+1.

    Returns:
        np.ndarray: shape (V,) 열별 가중치. 입력 유효성 검사는 따로 하지 않는다.
    """
    df = df.astype(np.float64)
    if smooth:
        return np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
    return np.log(n_docs / df) + 1.0


def normalize_rows(matrix: np.ndarray, norm: Optional[str] = "l2", inplace: bool = False) -> np.ndarray:
    """문서마다 벡터 크기를 맞추어 반복량보다 단어 비율을 비교한다.

    L2 길이는 sqrt(제곱합). [3,4]의 길이 5로 나누면 [.6,.8]이다.
    L1은 절댓값 합 7로 나누어 [3/7,4/7]로 만든다. L1은 L2 단위 길이가 아니다.
    0벡터는 나눌 길이가 없어 그대로 0으로 둔다(코사인도 이 구현에서는 0 처리).

    예상 질문: [6,8]과 [3,4]를 L2 정규화하면? 답: 둘 다 [.6,.8].

    Args:
        matrix: shape (N,V) 실수 행렬.
        norm: l2, l1 또는 None. None은 계산 없이 원래 객체를 반환한다.
        inplace: True면 원래 배열을 제자리 수정한다. False면 나눈 새 배열을 반환한다.

    Returns:
        np.ndarray: 같은 shape. norm=None 또는 inplace=True면 입력과 동일 객체.

    Raises:
        ValueError: 알 수 없는 norm.
    """
    if norm is None:
        return matrix
    if norm == "l2":
        # einsum("ij,ij->i")는 행 i·열 j의 같은 칸을 곱하고 j를 합친다: 행별 제곱합.
        # (N,V) 두 배열 → (N,), [:,None]은 새 축을 넣어 (N,1). sqrt는 제곱근이다.
        lengths = np.sqrt(np.einsum("ij,ij->i", matrix, matrix))[:, None]
    elif norm == "l1":
        lengths = np.abs(matrix).sum(axis=1, keepdims=True)
    else:
        raise ValueError(f"알 수 없는 norm: {norm}")
    # 길이가 0인 행은 분모만 1로 바꾼다. 0/1=0이므로 존재하지 않는 단어를 만들어내지 않는다.
    safe = np.where(lengths > 0, lengths, 1.0)
    if inplace:
        matrix /= safe
        return matrix
    return matrix / safe


class TfidfVectorizerNP:
    """문서에서 어휘·IDF를 배우고 같은 좌표계로 새 문서를 바꾸는 객체.

    class는 데이터와 기능을 묶는 설계도, vec=TfidfVectorizerNP()는 객체 생성이다.
    self는 그 객체 자신이다. fit 후 self.vocabulary_를 보관해 transform에서 재사용한다.
    이름 끝 _는 학습으로 얻은 속성이라는 관례다. fit 없이 transform하면 속성이 없다.
    sklearn 전체 기능을 복제하지 않고 이 미션에 필요한 부분만 구현한다.

    Attributes:
        terms_: 열 순서의 단어 목록.
        vocabulary_: {단어: 열 번호}.
        df_: shape (V,) 학습 문서에서 센 출현 문서 수.
        idf_: shape (V,) 학습 문서에서 계산한 가중치.
    """

    def __init__(
        self,
        tf: str = "raw",
        smooth_idf: bool = True,
        norm: Optional[str] = "l2",
        min_df: int = 1,
        max_df: float = 1.0,
    ):
        """변환 설정을 저장한다. 이때 어휘를 학습하지 않는다.

        Args:
            tf: TF 변형 이름.
            smooth_idf: IDF 평활화 여부.
            norm: 행 정규화 방식 l2, l1, None.
            min_df: 어휘에 포함할 최소 문서 수.
            max_df: float 비율 또는 int 문서 수 상한.

        Raises:
            ValueError: 지원하지 않는 tf.
        """
        if tf not in TF_VARIANTS:
            raise ValueError(f"알 수 없는 TF 변형: {tf}")
        self.tf = tf
        self.smooth_idf = smooth_idf
        self.norm = norm
        self.min_df = min_df
        self.max_df = max_df

    def fit(self, docs_tokens: Sequence[Sequence[str]]) -> "TfidfVectorizerNP":
        """어휘·IDF를 저장하고 객체 자체를 반환한다.

        내부에서는 fit_transform으로 행렬까지 계산한 뒤 행렬은 버린다.
        따라서 빠른 학습 전용 경로가 아니라 편의용 인터페이스다.

        Args:
            docs_tokens: 어휘·IDF 학습에 쓸 문서 토큰 목록.

        Returns:
            TfidfVectorizerNP: self. vec.fit(docs).transform(queries)처럼 이어 호출할 수 있다.
        """
        self.fit_transform(docs_tokens)
        return self

    def fit_transform(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        """어휘·IDF를 새로 학습하고 그 문서의 TF-IDF 행렬을 반환한다.

        예의 counts=[[0,1,2],[1,1,0]], idf=[1.405465,1,1.405465].
        raw 가중치는 [[0,1,2.810930],[1.405465,1,0]], L2 결과는 대략
        [[0,.335176,.942156],[.814802,.579739,0]]이다. shape은 계속 (2,3)이다.
        다시 호출하면 이전 어휘와 IDF를 덮어쓴다. 질의에는 transform을 써야 한다.

        Args:
            docs_tokens: 같은 어휘를 만들 학습 문서 N개의 토큰 목록.

        Returns:
            np.ndarray: shape (N,V). 객체에 terms_, vocabulary_, df_, idf_도 저장한다.
        """
        self.terms_ = build_vocabulary(docs_tokens, self.min_df, self.max_df)
        # 사전 컴프리헨션: 정렬된 terms_를 enumerate로 번호 매겨 {goalie:0, orbit:1, space:2}.
        self.vocabulary_ = {term: j for j, term in enumerate(self.terms_)}
        counts = count_matrix(docs_tokens, self.vocabulary_)
        self.df_ = document_frequency(counts)
        self.idf_ = inverse_document_frequency(self.df_, len(docs_tokens), self.smooth_idf)
        return self._weight(counts)

    def transform(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        """기존 어휘·IDF를 고정해 질의 또는 평가 문서를 변환한다.

        위 학습 뒤 [[space, unknown]]은 counts=[[0,0,1]], 정규화 결과 [[0,0,1]].
        unknown은 새 열을 만들지 않는다. 전부 미등록이면 한 행 전체가 0이다.

        Args:
            docs_tokens: 새 문서 M개의 토큰 목록. 한 질의도 [[토큰들]]로 감싼다.

        Returns:
            np.ndarray: shape (M,V). fit의 V·열 순서·idf_를 그대로 사용한다.

        Raises:
            AttributeError: 먼저 fit 또는 fit_transform을 호출하지 않은 경우.
        """
        return self._weight(count_matrix(docs_tokens, self.vocabulary_))

    def counts(self, docs_tokens: Sequence[Sequence[str]]) -> np.ndarray:
        """학습한 열 순서로 가중치 없는 원래 빈도 행렬을 만든다.

        BM25는 L2 결과가 아니라 빈도가 필요하므로 이 경로를 쓴다.

        Args:
            docs_tokens: M개 문서의 토큰 목록. 먼저 어휘를 학습해야 한다.

        Returns:
            np.ndarray: shape (M,V) 빈도.
        """
        return count_matrix(docs_tokens, self.vocabulary_)

    def _weight(self, counts: np.ndarray) -> np.ndarray:
        """빈도 → TF → 열별 IDF 곱 → 행 정규화를 차례로 수행한다.

        *는 같은 칸끼리 곱이다. (N,V)에 (V,)를 곱하면 각 행에 같은 IDF가 적용된다.
        이를 브로드캐스팅이라 한다. @ 행렬 곱과 구분한다.

        Args:
            counts: shape (N,V) 빈도 행렬.

        Returns:
            np.ndarray: shape (N,V) TF-IDF. TF가 새 배열이라 원래 counts는 보존된다.
        """
        weighted = term_frequency(counts, self.tf)
        weighted *= self.idf_  # (n, V) × (V,) 브로드캐스팅: 열 j 전체에 idf[j]를 곱한다
        return normalize_rows(weighted, self.norm, inplace=True)
