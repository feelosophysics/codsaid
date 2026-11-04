"""거래·상품·이미지를 연결해 전처리하고 고객별 구매 특징을 계산한다.

읽는 순서: load_data → handle_missing_values → engineer_features →
detect_outliers → calculate_rfm → segment_summary.
Pandas는 행·열이 있는 표, NumPy는 이미지 같은 다차원 숫자 배열을 다룬다.
이 미션은 규칙과 통계로 분석하며 예측 AI 모델을 학습하지 않는다.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def iqr_bounds(values, threshold=1.5):
    """IQR을 이용해 이상치 후보를 판별할 하한과 상한을 계산한다.

    Args:
        values (pandas.Series): 숫자로 변환 가능한 한 컬럼. 결측값은
            분위수 계산에서 제외하며 유한한 관측값이 하나 이상 필요하다.
        threshold (float): IQR에 곱할 양수 배수. 기본값은 1.5.

    Returns:
        tuple[float, float]: (하한, 상한). 원본 값은 바꾸지 않는다.

    Raises:
        ValueError: 배수가 유한한 양수가 아니거나 데이터에 무한대가 있거나
            유효한 숫자가 없거나 숫자로 변환할 수 없는 값이 있는 경우.
    """
    # ── 입력 검사 ───────────────────────────────────────────────
    # 잘못된 값으로 틀린 경계를 내는 대신 계산 전에 오류로 멈춘다.
    # isfinite는 무한대·NaN이 아닌지 검사하고, not은 참/거짓을 뒤집는다.
    # dropna()는 결측을 뺀 임시 Series로, 원본 행을 지우지 않는다.
    # all()은 '모두 참인가', empty는 '남은 값이 없는가'를 뜻한다.
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    values = pd.to_numeric(values, errors="raise")  # "10" → 10. "가격미상"처럼 못 바꾸는 값은 오류로 알린다
    if not np.isfinite(values.dropna()).all() or values.dropna().empty:
        raise ValueError("IQR requires at least one finite observation")

    # ── 경계 계산 ───────────────────────────────────────────────
    # 예: [10,20,30,40,100] → Q1=20, Q3=40, 폭=20, 배수 1.5의 경계=(-10, 70).
    # 100은 경계 밖이지만 정상적인 고가 상품일 수 있어 후보로만 보고 여기서 삭제하지 않는다.
    q1, q3 = values.quantile([0.25, 0.75])  # 두 결과를 나눠 담는다(언패킹)
    spread = q3 - q1                        # 가운데 50%의 폭(IQR)
    return float(q1 - threshold * spread), float(q3 + threshold * spread)


class DataAnalyzer:
    """연결된 데이터를 보관하고 전처리·피처 생성·RFM 집계를 수행한다.

    클래스는 데이터와 처리 기능을 묶는 설계도이고 analyzer는 그 객체다.
    거래 표의 한 행은 주문 안의 상품 한 줄, 상품 표의 한 행은 상품 하나다.
    RFM의 금액은 기록된 거래 금액을 쓰며 상품 가격 대치로 다시 만들지 않는다.

    Attributes:
        df (pandas.DataFrame | None): 현재 처리 중인 거래 표.
        raw_df (pandas.DataFrame | None): 로드·형 변환·조인 직후의 표 사본.
        products (pandas.DataFrame | None): 상품별 속성 표.
        images (numpy.ndarray | None): 상품별 이미지 숫자 배열.
        rfm (pandas.DataFrame | None): 고객당 한 행인 구매 요약 표.
        audit (dict): 입력 규모·대치·제외·분류 기준을 기록하는 사전.
    """

    def __init__(self, data_path, products_path=None, images_path=None):
        """입력 파일 위치와 빈 분석 상태를 준비한다. 파일은 아직 읽지 않는다.

        Args:
            data_path (str | pathlib.Path): 거래 CSV 경로.
            products_path (str | pathlib.Path | None): 상품 CSV 경로.
                생략하면 거래 파일과 같은 폴더의 products.csv를 사용한다.
            images_path (str | pathlib.Path | None): 이미지 NPY 경로.
                생략하면 같은 폴더의 images.npy를 사용한다.
        """
        # ── 입력 경로 ───────────────────────────────────────────
        # self는 현재 객체 자신이고, self.이름은 여러 메서드가 함께 쓰는 상태다.
        # Path는 문자열 경로를 다루기 쉽게 바꾸며 / 연산자로 경로를 이어 붙인다.
        # A if 조건 else B는 조건에 따라 A나 B를 선택하는 표현식이다.
        self.data_path = Path(data_path)
        base = self.data_path.parent
        self.products_path = Path(products_path) if products_path else base / "products.csv"
        self.images_path = Path(images_path) if images_path else base / "images.npy"

        # ── 분석 상태 초기화 ────────────────────────────────────
        # None은 '아직 없음'이다. 빈 표와 구분해 처리 순서를 검사할 수 있다.
        self.df = None
        self.raw_df = None
        self.products = None
        self.images = None
        self.rfm = None
        self.audit = {}

    @staticmethod
    def _require_columns(frame, columns, label):
        """필수 컬럼 누락을 검사한다. 객체 상태를 쓰지 않는 보조 함수다.

        Args:
            frame (pandas.DataFrame): 검사할 표.
            columns (list[str]): 있어야 할 컬럼 이름들.
            label (str): 오류 메시지에 표시할 데이터 이름.

        Raises:
            ValueError: 필수 컬럼이 하나라도 없는 경우.
        """
        # @staticmethod는 self 없이 호출하는 기능이라는 표시다.
        # set은 중복 없는 집합이고 집합의 -는 차집합이다. sorted로 이름을 정렬한다.
        missing = sorted(set(columns) - set(frame.columns))
        if missing:  # 빈 목록 []는 거짓이라 누락이 없으면 건너뛴다
            # f"...{값}..."은 값을 끼워 넣는 문자열이다.
            raise ValueError(f"{label} missing columns: {missing}")

    def _require_loaded(self):
        """거래 표를 먼저 로드했는지 검사한다.

        Raises:
            RuntimeError: self.df가 아직 None인 경우.
        """
        if self.df is None:
            raise RuntimeError("Call load_data() first")

    def _read_inputs(self):
        """입력 파일 세 개를 읽고 날짜와 거래 금액 컬럼을 계산 가능한 자료형으로 바꾼다.

        Returns:
            tuple: (거래 표, 상품 표, 이미지 배열).

        Raises:
            ValueError: 필수 컬럼이 없거나 금액 컬럼을 숫자로 바꿀 수 없는 경우.
            OSError: 입력 파일을 읽을 수 없는 경우.
        """
        # ── CSV 읽기 ────────────────────────────────────────────
        # ID는 계산할 숫자가 아닌 식별자다. 문자열로 읽어 앞자리 0 등을 보존한다.
        transactions = pd.read_csv(self.data_path, dtype={
            "line_id": "string", "order_id": "string", "customer_id": "string", "product_id": "string"})
        products = pd.read_csv(self.products_path, dtype={"product_id": "string"})

        # ── 필수 컬럼 검사 ──────────────────────────────────────
        # 다른 데이터셋을 넣을 때 가장 먼저 만나는 실수라서 어떤 컬럼이 없는지 바로 알려 준다.
        self._require_columns(transactions, ["line_id", "order_id", "customer_id", "order_date",
                                            "product_id", "unit_price", "quantity", "amount"], "transactions")
        self._require_columns(products, ["product_id", "product_name", "category", "catalog_price",
                                        "rating", "image_index"], "products")

        # ── 날짜·숫자 변환 ──────────────────────────────────────
        # coerce는 잘못된 날짜를 NaT(날짜 결측)로 바꾼다. RFM에서 제외하고 기록한다.
        # dt는 날짜 전용 기능에 접근하며 normalize()는 시각을 자정으로 맞춘다.
        # 반복문은 컬럼 이름을 하나씩 꺼낸다. raise는 숫자로 못 바꾸는 값을 오류로 알린다.
        transactions["order_date"] = pd.to_datetime(transactions["order_date"], errors="coerce").dt.normalize()
        for col in ["unit_price", "quantity", "amount"]:
            transactions[col] = pd.to_numeric(transactions[col], errors="raise")

        # ── 이미지 읽기 ─────────────────────────────────────────
        # NPY는 NumPy 배열 저장 형식이다. 숫자 배열만 읽도록 pickle을 끈다.
        images = np.load(self.images_path, allow_pickle=False)
        return transactions, products, images

    @staticmethod
    def _validate_inputs(transactions, products, images):
        """오류 없이 결과가 틀어지거나 원인을 알기 어려운 입력을 계산 전에 막는다.

        상품·배송 숫자 컬럼의 검사는 그 값을 처음 계산하는 handle_missing_values가 맡는다.

        Args:
            transactions (pandas.DataFrame): 자료형을 정리한 거래 표.
            products (pandas.DataFrame): 상품 표.
            images (numpy.ndarray): 상품 이미지 배열.

        Raises:
            ValueError: 키·금액·주문·상품 연결·이미지 구조가 잘못된 경우.
        """
        # ── 키 검사 ─────────────────────────────────────────────
        # 주문 ID는 여러 상품 행에 반복될 수 있지만 line_id는 행마다 달라야 한다.
        # 같은 줄이 두 번 들어오면 매출이 그만큼 부푼다.
        if transactions.line_id.isna().any() or transactions.line_id.duplicated().any():
            raise ValueError("line_id must be unique and nonmissing")

        # ── 금액 검사 ───────────────────────────────────────────
        # 무한대 금액은 고객 합계를 무한대로 만든다.
        # 주문 전체 금액을 각 상품 행에 복제한 오류 등도 찾는다.
        # [[...]]는 여러 컬럼을 표로 선택하고, axis=1은 각 행의 컬럼을 가로로 검사한다.
        # 예: [단가 있음, 수량 있음, 금액 있음] → True인 행만 비교한다.
        # loc[행 조건, 컬럼]으로 값을 고르고, isclose는 소수점 계산의 작은 오차를 허용한다.
        for col in ["unit_price", "quantity", "amount"]:
            if not np.isfinite(transactions[col].dropna()).all():
                raise ValueError(f"{col} contains infinite values")
        comparable = transactions[["unit_price", "quantity", "amount"]].notna().all(axis=1)
        if not np.isclose(transactions.loc[comparable, "amount"],
                          transactions.loc[comparable, "unit_price"] * transactions.loc[comparable, "quantity"],
                          rtol=1e-6, atol=0.01).all():
            raise ValueError("amount must be the line total unit_price * quantity")

        # ── 주문 일관성 검사 ────────────────────────────────────
        # 같은 주문의 여러 상품 줄은 고객·날짜가 같아야 한다.
        # nunique는 서로 다른 값의 개수, dropna=False는 결측도 구별해 세라는 뜻이다.
        order_groups = transactions.groupby("order_id")
        for key in ["customer_id", "order_date"]:
            if (order_groups[key].nunique(dropna=False) > 1).any():
                raise ValueError(f"One order_id must have one {key}")

        # ── 상품 연결 검사 ──────────────────────────────────────
        # isin은 각 값이 목록에 있는지 답하고 ~는 참/거짓을 뒤집는다.
        # 없는 상품을 그대로 두면 이미지 계산에서 원인을 알기 어려운 오류로 멈춘다.
        if (~transactions.product_id.isin(products.product_id)).any():
            raise ValueError("Every transaction must reference a known product_id")

        # ── 이미지 배열 검사 ────────────────────────────────────
        # ndim은 축 개수, shape는 축별 크기다. any(...)는 하나라도 참인지 묻는다.
        if images.ndim not in (3, 4) or any(n == 0 for n in images.shape):
            raise ValueError("images must have shape (N,H,W) or (N,H,W,C), with nonempty axes")

        # ── 이미지 위치 검사 ────────────────────────────────────
        # 배열 위치는 0부터 시작한다. 80장이라면 유효한 위치는 0~79다.
        # 음수 위치는 오류 없이 뒤에서부터 세므로(-1 → 마지막 장) 엉뚱한 이미지를 쓰게 된다.
        # % 1로 정수인지, between으로 범위 안인지 검사한다. 빈 값은 둘 다 통과하지 못한다.
        indices = pd.to_numeric(products.image_index, errors="raise")
        if ((indices % 1) != 0).any() or not indices.between(0, len(images) - 1).all():
            raise ValueError("image_index must refer to an existing image")

    def load_data(self):
        """입력을 읽고 검사한 뒤 거래 표에 상품 속성을 연결한다.

        Returns:
            pandas.DataFrame: 상품 속성이 붙은 거래 표. self.df에도 보관한다.
                기본 샘플은 거래 2,842행에 상품 속성을 붙인 16컬럼이다.

        Raises:
            ValueError: 필수 컬럼·키·금액·주문·상품 연결·이미지 구조가 잘못된 경우.
            OSError: 입력 파일을 읽을 수 없는 경우.
        """
        transactions, products, images = self._read_inputs()
        self._validate_inputs(transactions, products, images)

        # ── 분석 표 확정 ────────────────────────────────────────
        # 거래 여러 행 → 상품 한 행으로 연결한다. 상품 키가 중복된 채 조인하면 거래 행·매출이
        # 부풀 수 있어 many_to_one을 강제한다. 어기면 merge가 오류를 낸다.
        # left는 거래 행을 모두 유지한다는 뜻이다.
        # raw_df는 날짜·금액 변환과 조인 후의 사본이다. CSV 원문 백업은 아니다.
        # isna() → 결측 여부 표, sum() → 컬럼별 결측 수, to_dict() → 사전.
        self.images = images
        self.products = products
        self.df = transactions.merge(products, on="product_id", how="left", validate="many_to_one")
        self.raw_df = self.df.copy(deep=True)
        self.rfm = None
        self.audit = {"input_rows": len(self.df), "products": len(products),
                      "missing_before": self.df.isna().sum().to_dict()}
        return self.df

    @staticmethod
    def _fill_by_group(frame, columns, group_col, strategy):
        """그룹 통계로 결측치를 채우고 그룹도 비면 전체 통계로 보완한다.

        Args:
            frame (pandas.DataFrame): 값을 직접 수정할 표.
            columns (tuple[str] | list[str]): 대치할 숫자 컬럼들.
            group_col (str): 그룹을 나눌 컬럼. 예: category.
            strategy (str): 호출할 통계 메서드 이름. 호출 측에서 median/mean으로 제한한다.

        Returns:
            dict: 컬럼 이름별로 원래 결측이었던 값의 수.

        Raises:
            ValueError: 숫자로 변환할 수 없거나 무한대가 있거나 컬럼 전체가 빈 경우.
        """
        changes = {}
        for column in columns:
            numeric = pd.to_numeric(frame[column], errors="raise")
            if not np.isfinite(numeric.dropna()).all():
                raise ValueError(f"{column} contains infinite values")
            # getattr은 이름으로 기능을 찾는다. "median"이면 numeric.median()과 같다.
            global_value = getattr(numeric, strategy)()
            if pd.isna(global_value):
                raise ValueError(f"Cannot impute all-missing column {column}")
            # agg는 그룹당 한 값으로 줄이지만 transform은 원래 행 위치에 그룹 통계를 돌려준다.
            # [10,40,NaN]인 그룹이면 [25,25,25]가 된다.
            group_values = frame.groupby(group_col, dropna=False)[column].transform(strategy)
            # fillna를 이어 호출해 그룹 값 → 전체 값 순서로 빈 곳만 채운다.
            frame[column] = numeric.fillna(group_values).fillna(global_value)
            changes[column] = int(numeric.isna().sum())
        return changes

    def handle_missing_values(self, strategy="median", group_col="category",
                              product_columns=("catalog_price", "rating"),
                              transaction_columns=("shipping_days",)):
        """상품 속성과 거래 속성의 집계 단위를 구분해 결측치를 보완한다.

        Args:
            strategy (str): median(중앙값) 또는 mean(평균). 기본값은 median.
            group_col (str): 비슷한 대상을 묶을 컬럼. 기본값은 category.
            product_columns (tuple[str]): 상품 표에서 대치할 컬럼들.
            transaction_columns (tuple[str]): 거래 표에서 대치할 컬럼들.

        Returns:
            pandas.DataFrame: 대치된 현재 거래 표. 상품 표와 audit도 갱신한다.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
            ValueError: 지원하지 않는 전략, 필수 컬럼 누락, 구매 사실 대치 시도,
                유효한 대치 통계를 구할 수 없는 경우.
        """
        self._require_loaded()

        # ── 입력 검사 ───────────────────────────────────────────
        if strategy not in ("median", "mean"):
            raise ValueError("strategy must be median or mean")
        # ID·구매 사실을 임의로 채우면 가짜 고객·매출이 생길 수 있다.
        # intersection은 두 집합에 함께 속한 컬럼이 있는지 찾는다.
        # 아래의 *목록은 목록의 원소를 펼친다.
        protected = {"amount", "quantity", "unit_price", "customer_id", "order_id", "order_date"}
        if protected.intersection(transaction_columns):
            raise ValueError("Do not impute purchase facts used for RFM")
        self._require_columns(self.df, [group_col, *transaction_columns], "transactions")
        self._require_columns(self.products, [group_col, *product_columns], "products")

        # ── 상품 속성 대치 ──────────────────────────────────────
        # 상품 10원·40원이 각각 1개인데 10원 상품이 3번 팔렸다고 해보자.
        # 상품 표의 중앙값은 25원, 거래 행 [10,10,10,40]의 중앙값은 10원이다.
        # 상품 속성은 판매 횟수에 가중되지 않도록 상품 표에서 먼저 채운다.
        product_counts = self._fill_by_group(self.products, product_columns, group_col, strategy)
        self.products["product_name"] = self.products.product_name.fillna("Unknown product")
        for column in [*product_columns, "product_name"]:
            # set_index는 ID를 조회 기준으로 삼고, map은 거래마다 그 상품의 보완된 값을 찾아 붙인다.
            # 거래 행 수는 그대로다.
            self.df[column] = self.df.product_id.map(self.products.set_index("product_id")[column])

        # ── 거래 속성 대치 ──────────────────────────────────────
        line_counts = self._fill_by_group(self.df, transaction_columns, group_col, strategy)
        self.audit["imputation"] = {"strategy": strategy, "group": group_col,
                                    "product_values": product_counts, "line_values": line_counts}
        self.audit["missing_after"] = self.df.isna().sum().to_dict()
        return self.df

    def engineer_features(self):
        """이미지와 상품명에서 숫자 피처 네 개를 만들어 거래 표에 추가한다.

        이미지에서 평균·표준편차, 이름에서 글자 수·공백 단위 단어 수를 만든다.
        피처(feature)는 분석에 사용할 특징 값이다. 이미지 의미를 학습하지 않는다.

        Returns:
            pandas.DataFrame: image_mean, image_std, name_length,
                name_word_count가 추가된 거래 표. self.df 자체도 갱신한다.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
        """
        self._require_loaded()

        # ── 이미지 → 상품별 통계 ────────────────────────────────
        # 0번(상품 축)만 남기고 나머지 축을 계산하면 상품마다 값이 하나씩 남는다.
        # (80,16,16,3) → (80,). 흑백 3차원 배열도 처리할 수 있다.
        # axis는 인자 이름, axes는 아래에서 만든 변수다. float64는 소수 자료형이다.
        # 평균은 RGB 전체 값의 단순 평균이므로 정밀한 지각 밝기나 품질 점수는 아니다.
        # 표준편차는 값의 흩어짐이다(ddof=0이 기본). 둘 다 평균 50이어도
        # [0,0,100,100]은 50, [50,50,50,50]은 0이다.
        axes = tuple(range(1, self.images.ndim))  # 4차원이면 range(1,4) → 1·2·3 → 튜플 (1,2,3)
        image_mean = self.images.mean(axis=axes, dtype=np.float64)
        image_std = self.images.std(axis=axes, dtype=np.float64)

        # ── 상품별 통계 → 거래 행 ───────────────────────────────
        # 통계는 80개, 거래는 2,842행이다. 각 거래의 이미지 위치로 배열을 조회해
        # 반복 판매에도 올바른 상품 통계를 연결한다.
        # 예: 평균 [20,80], 위치 [1,0,1] → 거래별 평균 [80,20,80].
        indices = self.df.image_index.to_numpy(dtype=int)
        self.df["image_mean"] = image_mean[indices]
        self.df["image_std"] = image_std[indices]

        # ── 상품명 → 글자 수·단어 수 ────────────────────────────
        # "Home item"은 공백 포함 9글자, split()으로 나누면 2단어다.
        # 형태소 분석이 아니며, 한국어 단어의 의미를 이해하는 과정도 아니다.
        # astype은 자료형 변환, str은 컬럼 전체의 문자열 기능이다.
        self.df["name_length"] = self.df.product_name.astype("string").str.len()
        self.df["name_word_count"] = self.df.product_name.astype("string").str.split().str.len()
        return self.df

    def detect_outliers(self, column, threshold=1.5):
        """IQR 경계 밖의 행에 표시를 붙이고 해당 행들의 사본을 반환한다.

        Args:
            column (str): 검사할 숫자 컬럼. 예: shipping_days.
            threshold (float): IQR 배수. 기본값은 1.5.

        Returns:
            pandas.DataFrame: 이상치 후보 행의 사본. self.df에는
                <컬럼명>_is_outlier라는 참/거짓 컬럼을 추가한다. 원본 값은 유지한다.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
            ValueError: 배수나 관측값이 IQR 계산 조건에 맞지 않는 경우.
        """
        self._require_loaded()
        lower, upper = iqr_bounds(self.df[column], threshold)
        values = self.df[column]
        # lt는 <, gt는 >, |는 행별 OR이다. 경계와 같은 값은 후보가 아니다.
        # 이렇게 True/False로 된 Series를 불리언 마스크라고 한다.
        flag = values.lt(lower) | values.gt(upper)
        self.df[f"{column}_is_outlier"] = flag
        # setdefault는 키가 없으면 빈 사전을 만든다. True의 합은 후보 개수다.
        self.audit.setdefault("outliers", {})[column] = {
            "threshold": threshold, "lower": lower, "upper": upper, "count": int(flag.sum())}
        return self.df.loc[flag].copy()

    def treat_outliers(self, column, threshold=1.5, method="clip"):
        """이상치 처리 전후를 비교할 별도의 한 컬럼을 반환한다.

        Args:
            column (str): 비교할 숫자 컬럼.
            threshold (float): IQR 배수. 기본값은 1.5.
            method (str): clip은 경계로 제한, remove는 경계 안의 값만 선택.

        Returns:
            pandas.Series: 처리된 비교용 값. remove는 길이가 줄 수 있다.
                self.df의 원본 컬럼과 RFM용 금액은 바꾸지 않는다.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
            ValueError: 지원하지 않는 method 또는 잘못된 IQR 입력인 경우.
        """
        self._require_loaded()
        if method not in ("clip", "remove"):
            raise ValueError("method must be clip or remove")
        lower, upper = iqr_bounds(self.df[column], threshold)
        values = self.df[column]
        # rename은 반환할 Series의 이름을 붙인다.
        if method == "clip":
            # clip은 상한이 10.5면 60을 10.5로 바꾼다. 관측 사실이 아닌 비교값이다.
            return values.clip(lower, upper).rename(f"{column}_treated")
        # between은 양쪽 경계를 포함한다.
        return values.loc[values.between(lower, upper)].rename(f"{column}_treated")

    def calculate_rfm(self, customer_col="customer_id", date_col="order_date",
                      amount_col="amount", order_col="order_id", reference_date=None,
                      recent_days=30, inactive_days=90, loyal_orders=4):
        """유효한 양수 구매를 고객별 RFM·점수·상호 배타적 그룹으로 요약한다.

        Args:
            customer_col (str): 고객 ID 컬럼.
            date_col (str): 구매 날짜 컬럼.
            amount_col (str): 행의 구매 금액 컬럼. 주문 전체 금액의 반복값은 안 된다.
            order_col (str): 주문 ID 컬럼. 구매 횟수는 고유 주문 수로 센다.
            reference_date (str | None): YYYY-MM-DD 기준일.
                생략하면 마지막 유효 구매일 다음 날. 마지막 구매일보다 빠를 수 없다.
            recent_days (int): 최근 구매로 볼 최대 경과 일수. 기본값은 30.
            inactive_days (int): 이 값을 초과하면 구매 공백으로 분류. 기본값은 90.
            loyal_orders (int): 반복 구매 기준 주문 수. 기본값은 4.

        Returns:
            pandas.DataFrame: 고객 ID를 인덱스로 한 R·F·M, 1~5점,
                합산 점수와 segment 표. self.rfm과 self.audit도 갱신한다.
                그룹은 점수 합이 아닌 R·F·M 원래 값의 규칙으로 정한다.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
            ValueError: 잘못된 기준·필수 컬럼 누락·유효 구매 없음·주문 모순인 경우.
        """
        self._require_loaded()

        # ── 입력 검사 ───────────────────────────────────────────
        if recent_days < 0 or inactive_days <= recent_days or loyal_orders < 2:
            raise ValueError("Require 0 <= recent_days < inactive_days and loyal_orders >= 2")
        self._require_columns(self.df, [customer_col, date_col, amount_col, order_col, "quantity"], "RFM")
        if self.df[amount_col].isna().any() and amount_col != "amount":
            raise ValueError("Custom amount column has missing values")

        # ── 유효 구매 선별 ──────────────────────────────────────
        # 결측 ID·잘못된 날짜·반품/0원/비양수 수량·단가는 구매 집계에서 제외한다.
        # &는 행별 AND다. 각 행마다 모든 조건을 만족하는지 검사하므로 결과는 원래 행 수만큼이다.
        # 바깥 괄호는 여러 줄로 식을 이어 적게 한다.
        valid = (self.df[customer_col].notna() & self.df[order_col].notna() & self.df[date_col].notna()
                 & self.df[amount_col].gt(0) & self.df.quantity.gt(0) & self.df.unit_price.gt(0))
        purchases = self.df.loc[valid].copy()  # 필터 후 사본에 작업해 전체 거래 표를 덮어쓰지 않는다
        if purchases.empty:
            raise ValueError("No valid positive purchases available for RFM")

        # ── 기준일 ──────────────────────────────────────────────
        # Timestamp는 날짜·시각 하나, Timedelta는 기간이다.
        # 시스템의 오늘 대신 데이터 기준일을 쓰면 재실행 시 R이 저절로 바뀌지 않는다.
        dates = pd.to_datetime(purchases[date_col], errors="raise").dt.normalize()
        reference = pd.Timestamp(reference_date).normalize() if reference_date is not None else dates.max() + pd.Timedelta(days=1)
        if pd.isna(reference) or reference < dates.max():
            raise ValueError("reference_date must not precede the latest purchase")
        purchases[date_col] = dates
        for key in [customer_col, date_col]:
            if (purchases.groupby(order_col)[key].nunique() > 1).any():
                raise ValueError(f"One order must have one {key}")

        # ── 고객별 집계 ─────────────────────────────────────────
        # 주문 안의 상품 행 여러 개 → 고객당 한 행.
        # agg(새 이름=(원래 컬럼, 집계 방식))는 이름 붙인 집계 문법이다.
        # C1의 주문 O1이 2행, O2가 1행이면 F는 3행이 아닌 2주문이다.
        # M은 양수 구매 합계로, 반품을 차감한 순매출이나 고객 평생가치가 아니다.
        # R은 기준일 - 마지막 구매일이다. 10/10 - 10/8 = 2일.
        grouped = purchases.groupby(customer_col)
        result = grouped.agg(last_purchase=(date_col, "max"), frequency=(order_col, "nunique"),
                             monetary=(amount_col, "sum"))
        result["recency"] = (reference - result.last_purchase).dt.days

        # ── R·F·M 점수 ──────────────────────────────────────────
        # rank는 상대 순위를 구하고 같은 값은 평균 순위로 같게 처리한다.
        # R은 작을수록 좋으므로 내림차순 순위로 작은 R에 큰 백분위를 준다. F·M은 클수록 좋다.
        # pct=True는 순위를 고객 수로 나눠 비율로 만든다.
        # 동점을 강제로 나누지 않으므로 점수별 인원은 같지 않을 수 있다.
        # 백분위 0.62 → ×5=3.1 → ceil(올림)=4점. clip이 1~5를 보장한다.
        for variable, ascending, score in [("recency", False, "r_score"),
                                            ("frequency", True, "f_score"),
                                            ("monetary", True, "m_score")]:
            percentile = result[variable].rank(method="average", pct=True, ascending=ascending)
            result[score] = np.ceil(percentile * 5).clip(1, 5).astype(int)
        result["rfm_score"] = result[["r_score", "f_score", "m_score"]].sum(axis=1)

        # ── 그룹 분류 ───────────────────────────────────────────
        # vip_cutoff는 고객 금액 분포의 75% 지점이다. 학습으로 찾은 정책이 아니다.
        vip_cutoff = float(result.monetary.quantile(0.75))
        inactive = result.recency > inactive_days
        new = (result.recency <= recent_days) & result.frequency.eq(1)
        vip = (result.recency <= recent_days) & (result.frequency >= loyal_orders) & (result.monetary >= vip_cutoff)
        loyal = result.frequency >= loyal_orders
        # np.select는 첫 번째로 참인 조건을 택한다. 구매 공백이 긴 반복 고객은 Loyal에도
        # 해당할 수 있으나 먼저 검사한 Inactive로만 분류된다.
        # Regular는 어느 조건에도 맞지 않을 때의 기본값이다.
        result["segment"] = np.select([inactive, new, vip, loyal],
                                       ["Inactive", "New", "VIP", "Loyal"], default="Regular")

        # ── 처리 기록 ───────────────────────────────────────────
        # ~valid는 조건의 반대다. 제외 사유는 한 행에 겹칠 수 있으므로
        # 사유별 개수를 더한 값이 전체 제외 행 수와 같다는 보장은 없다.
        self.audit["rfm"] = {"reference_date": reference.strftime("%Y-%m-%d"),
                             "eligible_rows": len(purchases), "excluded_rows": int((~valid).sum()),
                             "customers": len(result), "orders": purchases[order_col].nunique(),
                             "recent_days": recent_days, "inactive_days": inactive_days,
                             "loyal_orders": loyal_orders, "vip_monetary_cutoff": vip_cutoff,
                             "excluded_reason_counts_overlapping": {
                                 "missing_customer": int(self.df[customer_col].isna().sum()),
                                 "missing_order": int(self.df[order_col].isna().sum()),
                                 "invalid_date": int(self.df[date_col].isna().sum()),
                                 "nonpositive_or_missing_amount": int((~self.df[amount_col].gt(0)).sum()),
                                 "nonpositive_or_missing_quantity": int((~self.df.quantity.gt(0)).sum()),
                                 "nonpositive_or_missing_price": int((~self.df.unit_price.gt(0)).sum())}}
        self.rfm = result[["recency", "frequency", "monetary", "r_score", "f_score", "m_score", "rfm_score", "segment"]]
        return self.rfm

    def summarize(self, columns=("unit_price", "amount", "shipping_days", "image_mean", "image_std")):
        """선택한 숫자 컬럼의 요약 통계를 거래 행 기준으로 반환한다.

        Args:
            columns (tuple[str]): 통계를 구할 컬럼 이름들.

        Returns:
            pandas.DataFrame: 컬럼별 개수·평균·표준편차·최솟값·분위수·최댓값.

        Raises:
            RuntimeError: 데이터를 먼저 로드하지 않은 경우.
        """
        self._require_loaded()
        # describe는 결측을 뺀 통계를 구하고 .T는 행·열을 뒤집는다.
        # 여기서 Pandas의 표준편차 기본값은 ddof=1로 이미지 std(ddof=0)와 다르다.
        # 자주 팔린 상품이 여러 행에 나타나므로 상품별 동일 가중 통계는 아니다.
        return self.df[list(columns)].describe(percentiles=[0.25, 0.5, 0.75]).T

    def segment_summary(self):
        """고객별 RFM을 그룹별 고객 수·평균·매출 비중으로 집계한다.

        Returns:
            pandas.DataFrame: 그룹당 한 행인 요약 표. 비중 컬럼의 단위는 %다.

        Raises:
            RuntimeError: calculate_rfm()을 먼저 호출하지 않은 경우.
        """
        if self.rfm is None:
            raise RuntimeError("Call calculate_rfm() first")
        # 입력이 이미 고객당 한 행이므로 size는 여기서 고객 수가 된다.
        # 거래 표에서 size를 썼다면 상품 행 수를 세었을 것이다.
        summary = self.rfm.groupby("segment").agg(
            customers=("monetary", "size"), mean_recency=("recency", "mean"),
            mean_frequency=("frequency", "mean"), mean_monetary=("monetary", "mean"),
            revenue=("monetary", "sum"))
        # 고객 비중의 분모는 전체 고객 수, 매출 비중의 분모는 전체 양수 구매 금액이다.
        # 두 비중을 비교해 매출이 특정 그룹에 얼마나 집중되었는지 읽는다.
        summary["customer_share_pct"] = summary.customers / summary.customers.sum() * 100
        summary["revenue_share_pct"] = summary.revenue / summary.revenue.sum() * 100
        return summary
