"""회귀 지표(MAE·RMSE·MAPE), 개선율, 예측 정확도 차이 검정(Diebold-Mariano)."""
import numpy as np
from scipy import stats


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(p))))


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def mape(y, p):
    """평균 절대 백분율 오차(%). 실제값이 0에 가까우면 커지므로 기온처럼 0을 지나는 값에는 쓰지 않는다."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    return float(np.mean(np.abs((y - p) / y)) * 100)


def regression_metrics(y, p, with_mape=True):
    out = {"MAE": mae(y, p), "RMSE": rmse(y, p)}
    out["MAPE"] = mape(y, p) if with_mape else None
    return out


def improvement(baseline, model):
    """베이스라인 대비 오차 감소율(%). 양수면 모델이 더 좋고, 음수면 더 나쁘다."""
    return float((baseline - model) / baseline * 100)


def diebold_mariano(errors_a, errors_b, horizon=1, power=2):
    """두 예측의 손실 차이가 0인지 검정한다 (Harvey 등 1997의 소표본 보정 포함).

    d_t = |e_a|^power - |e_b|^power. 통계량이 음수면 A의 손실이 더 작다.
    반환: (통계량, 양측 p값). p값이 크면 '두 모델의 정확도가 같다'를 기각하지 못한다.
    """
    d = np.abs(np.asarray(errors_a)) ** power - np.abs(np.asarray(errors_b)) ** power
    n = len(d)
    d_mean = d.mean()
    # 장기 분산: 시차 horizon-1까지의 자기공분산을 더한다 (1-step이면 표본 분산만)
    gamma = [np.mean((d[k:] - d_mean) * (d[:n - k] - d_mean)) for k in range(horizon)]
    long_run_var = gamma[0] + 2 * sum(gamma[1:])
    if long_run_var <= 0:   # 두 예측의 손실이 모든 시점에서 같다
        return 0.0, 1.0
    dm =d_mean / np.sqrt(long_run_var / n)
    correction = np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    statistic = float(dm * correction)
    p_value = float(2 * stats.t.sf(abs(statistic), df=n - 1))
    return statistic, p_value
