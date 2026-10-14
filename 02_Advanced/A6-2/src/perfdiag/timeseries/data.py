"""시계열 데이터: 내려받기 → 피처 생성(분할 전, 과거 값만) → 시간순 분할 → Train 전용 정규화 → 윈도우.

누수 방지 규칙 (리포트 'reports/LEAKAGE.md'에 근거를 적는다)
1. 시간순 분할: 예측 대상 시점 t를 시간순으로 7:1:2로 나눈다. 섞지 않는다.
2. 전처리 Fit 구간: Scaler 통계는 Train 구간 날짜의 행으로만 계산한다.
3. 윈도우: 시점 t를 예측하는 입력은 t-L … t-1 행뿐이다. t 자신과 그 이후는 들어가지 않는다.
4. 피처 생성 시점: 지연값·이동평균은 분할 전에 전체 시계열에서 한 번에 만든다.
   모든 피처가 '그날과 그 이전' 값만 쓰는 후행(trailing) 창이므로, 분할 전에 만들어도 미래가 섞이지 않는다.
   분할 뒤에 만들면 Validation·Test 첫 n일의 이동평균이 비거나 Train 끝 값을 다시 계산해야 해서 오히려 번거롭다.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..common import TIMESERIES


MAX_WINDOW = 90   # 실험에서 쓰는 가장 긴 입력 창 (보너스 Attention 실험)


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    title: str
    csv_name: str
    target: str
    unit: str
    log_target: bool        # 주가는 로그 가격의 차이(로그 수익률)로 다룬다
    with_mape: bool         # 0을 지나는 값(기온)은 MAPE가 의미 없다

    @property
    def csv(self):
        return TIMESERIES / self.csv_name


SERIES = {
    "aapl": SeriesConfig("aapl", "AAPL 종가", "AAPL_2015_2025.csv", "Close", "USD", True, True),
    "seoul": SeriesConfig("seoul", "서울 일평균 기온", "seoul_weather_2015_2025.csv", "temperature_2m_mean", "°C",
                          False, False),
}

WEATHER_VARIABLES = ["temperature_2m_mean", "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                     "wind_speed_10m_max", "shortwave_radiation_sum", "relative_humidity_2m_mean",
                     "pressure_msl_mean"]


# ----------------------------------------------------------------------------- 내려받기
def fetch_aapl(start="2015-01-01", end="2026-01-01"):
    """yfinance 일봉. auto_adjust=False의 Close는 '분할만 반영한' 가격이다.

    Adj Close는 이후 지급된 배당까지 과거 가격에 소급 반영하므로, 과거 시점에서는 알 수 없던 정보를 담는다.
    그래서 예측 대상은 Close로 하고 Adj Close는 참고용으로만 저장한다.
    """
    import yfinance as yf

    raw = yf.download("AAPL", start=start, end=end, auto_adjust=False, progress=False)
    raw.columns = raw.columns.get_level_values(0)
    df = raw[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index).date
    df.index.name = "date"
    return df


def fetch_seoul_weather(start="2015-01-01", end="2025-12-31"):
    """Open-Meteo 과거 기상 API(ERA5 재분석)의 서울 시청 좌표 일별 값."""
    import requests

    response = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=60, params={
        "latitude": 37.5665, "longitude": 126.978, "start_date": start, "end_date": end,
        "daily": ",".join(WEATHER_VARIABLES), "timezone": "Asia/Seoul"})
    response.raise_for_status()
    daily = response.json()["daily"]
    df = pd.DataFrame(daily).rename(columns={"time": "date"}).set_index("date")
    df.index = pd.to_datetime(df.index).date
    df.index.name = "date"
    return df.dropna()


def load_frame(cfg):
    df = pd.read_csv(cfg.csv, index_col="date", parse_dates=True)
    if df.isna().any().any():
        raise ValueError(f"{cfg.csv.name}에 결측치가 있다")
    return df


# ----------------------------------------------------------------------------- 피처 (분할 전, 과거만)
def build_features(df, cfg):
    """날짜 d의 피처는 d와 그 이전 행만으로 계산한다 (rolling·ewm·diff 모두 후행 창)."""
    f = pd.DataFrame(index=df.index)
    if cfg.name == "aapl":
        close = df["Close"]
        log_close = np.log(close)
        f["log_return"] = log_close.diff()                          # 오늘 수익률 r_d
        f["range"] = np.log(df["High"] / df["Low"])                 # 장중 변동폭
        f["body"] = np.log(close / df["Open"])                      # 시가 대비 종가
        f["volume_change"] = np.log(df["Volume"]).diff()
        f["gap_sma5"] = close / close.rolling(5).mean() - 1         # 최근 5일 평균과의 괴리
        f["gap_sma20"] = close / close.rolling(20).mean() - 1
        f["gap_ema"] = close / close.ewm(alpha=0.3, adjust=False).mean() - 1
        f["volatility20"] = f["log_return"].rolling(20).std()
    else:
        for column in WEATHER_VARIABLES:
            f[column] = df[column]
        f["precipitation_sum"] = np.log1p(df["precipitation_sum"])
        f["temp_change"] = df["temperature_2m_mean"].diff()
        f["temp_sma7"] = df["temperature_2m_mean"].rolling(7).mean()
        day = pd.to_datetime(pd.Series(df.index, index=df.index)).dt.dayofyear
        f["season_sin"] = np.sin(2 * np.pi * day / 365.25)
        f["season_cos"] = np.cos(2 * np.pi * day / 365.25)
    return f


# ----------------------------------------------------------------------------- 분할
def chronological_split(targets, ratios=(0.7, 0.1, 0.2)):
    """예측 대상 시점 배열을 앞에서부터 순서대로 자른다 (shuffle 없음)."""
    n = len(targets)
    n_train = int(round(n * ratios[0]))
    n_validation = int(round(n * ratios[1]))
    return {"train": targets[:n_train],
            "validation": targets[n_train:n_train + n_validation],
            "test": targets[n_train + n_validation:]}


class StandardScaler:
    """평균 0, 표준편차 1로 바꾼다. fit은 Train 행에만 호출한다."""

    def fit(self, values):
        values = np.asarray(values, dtype=float)
        self.mean_ = values.mean(axis=0)
        self.scale_ = values.std(axis=0)
        self.scale_ = np.where(self.scale_ == 0, 1.0, self.scale_)
        return self

    def transform(self, values):
        return (np.asarray(values, dtype=float) - self.mean_) / self.scale_

    def inverse_transform(self, values):
        return np.asarray(values, dtype=float) * self.scale_ + self.mean_


class MinMaxScaler:
    """[0, 1]로 바꾼다. Train 범위를 벗어난 값은 0 미만·1 초과가 된다 (외삽)."""

    def fit(self, values):
        values = np.asarray(values, dtype=float)
        self.min_ = values.min(axis=0)
        self.range_ = values.max(axis=0) - self.min_
        return self

    def transform(self, values):
        return (np.asarray(values, dtype=float) - self.min_) / self.range_

    def inverse_transform(self, values):
        return np.asarray(values, dtype=float) * self.range_ + self.min_


@dataclass
class Prepared:
    cfg: SeriesConfig
    dates: np.ndarray            # (n,) 날짜
    y: np.ndarray                # (n,) 원래 단위의 값
    level: np.ndarray            # (n,) 모델이 다루는 수준값: 주가는 log(Close), 기온은 그대로
    features: np.ndarray         # (n, f) 분할 전에 만든 후행 피처
    feature_names: list
    splits: dict                 # {"train": 시점 배열, ...}
    first_target: int
    info: dict = field(default_factory=dict)

    def train_rows(self):
        """Train 구간에 속한 날짜 행. Scaler는 이 행으로만 fit한다.

        첫 Train 윈도우의 시작(first_target − MAX_WINDOW)부터 마지막 Train 예측 대상 시점까지다.
        그보다 앞 행은 이동평균 준비 기간이라 피처가 비어 있고, 어떤 윈도우에도 들어가지 않는다.
        """
        return np.arange(self.first_target - MAX_WINDOW, self.splits["train"][-1] + 1)

    def to_level(self, y):
        return np.log(y) if self.cfg.log_target else np.asarray(y, dtype=float)

    def from_level(self, level):
        return np.exp(level) if self.cfg.log_target else np.asarray(level, dtype=float)


def prepare(name, first_target=120, ratios=(0.7, 0.1, 0.2)):
    """first_target 이전 행은 입력(최대 윈도우 90일 + 이동평균 준비 20일)으로만 쓴다.

    모든 모델·베이스라인이 같은 시점 배열을 평가하므로 Test 구간이 완전히 같다 (공정 비교 규칙).
    """
    cfg = SERIES[name]
    df = load_frame(cfg)
    features = build_features(df, cfg)
    if features.iloc[first_target - MAX_WINDOW:].isna().any().any():
        raise ValueError("first_target이 너무 작아 입력 창에 결측 피처가 들어간다")
    y = df[cfg.target].to_numpy(dtype=float)
    targets = np.arange(first_target, len(df))
    prep = Prepared(cfg, np.array(df.index.date), y, np.log(y) if cfg.log_target else y.copy(),
                    features.to_numpy(dtype=float), list(features.columns),
                    chronological_split(targets, ratios), first_target)
    for split, idx in prep.splits.items():
        prep.info[split] = {"n": len(idx), "start": str(prep.dates[idx[0]]), "end": str(prep.dates[idx[-1]])}
    return prep


# ----------------------------------------------------------------------------- 윈도우
def window_indices(targets, window, lookahead=False):
    """시점 t의 입력 행 번호 (m, window). 정상: t-window … t-1. lookahead=True는 누수 재현용(t 포함)."""
    offsets = np.arange(-window, 0) + (1 if lookahead else 0)
    return np.asarray(targets)[:, None] + offsets[None, :]


@dataclass
class WindowSet:
    X: np.ndarray                # (m, window, f) float32
    target: np.ndarray           # (m,) 정규화된 목표
    t: np.ndarray                # (m,) 예측 대상 시점
    prev_level: np.ndarray       # (m,) 수준값 level[t-1] (delta 복원용)


@dataclass
class Dataset:
    prep: Prepared
    mode: str
    window: int
    sets: dict
    input_scaler: object
    target_scaler: object

    @property
    def n_features(self):
        return self.sets["train"].X.shape[-1]

    def reconstruct(self, split, pred_scaled):
        """정규화된 예측 → 원래 단위(달러·°C)."""
        ws = self.sets[split]
        pred = self.target_scaler.inverse_transform(np.asarray(pred_scaled).reshape(-1, 1)).ravel()
        level = pred if self.mode == "level" else ws.prev_level + pred
        return self.prep.from_level(level)

    def actual(self, split):
        return self.prep.y[self.sets[split].t]


def make_dataset(prep, mode="delta", window=30, scaler_rows=None, splits=None, lookahead=False, extra=None):
    """mode
    - "level": 수준값 하나만 입력해 다음 수준값을 예측한다 (MinMax). 흔한 튜토리얼 방식이다.
    - "delta": 다변량 피처를 입력해 변화량 level[t] − level[t−1]을 예측한다 (Standard).

    scaler_rows·splits·lookahead·extra는 누수 재현 실험에서만 바꾼다. 기본값이 올바른 설정이다.
    """
    rows = prep.train_rows() if scaler_rows is None else scaler_rows
    splits = prep.splits if splits is None else splits
    if mode == "level":
        values = prep.level.reshape(-1, 1)
        input_scaler = MinMaxScaler().fit(values[rows])
        inputs = input_scaler.transform(values)
        target_values = prep.level
        target_scaler = input_scaler
    elif mode == "delta":
        values = prep.features if extra is None else np.column_stack([prep.features, extra])
        input_scaler = StandardScaler().fit(values[rows])
        inputs = input_scaler.transform(values)
        target_values = np.concatenate([[np.nan], np.diff(prep.level)])
        target_scaler = StandardScaler().fit(target_values[rows].reshape(-1, 1))
    else:
        raise ValueError(mode)
    scaled_target = target_scaler.transform(target_values.reshape(-1, 1)).ravel()

    sets = {}
    for split, targets in splits.items():
        idx = window_indices(targets, window, lookahead)
        if idx.min() < 0:
            raise ValueError("윈도우가 시계열 시작보다 앞을 가리킨다")
        sets[split] = WindowSet(inputs[idx].astype(np.float32), scaled_target[targets].astype(np.float32),
                                np.asarray(targets), prep.level[np.asarray(targets) - 1])
    return Dataset(prep, mode, window, sets, input_scaler, target_scaler)
