"""누수 재현 실험: 체크포인트를 하나씩 일부러 어기면 Test 점수가 얼마나 '좋아 보이는지' 잰다.

모두 AAPL, LSTM 은닉 32, seed 0. 정상 설정과 한 가지씩만 다르다.
  정상 v1        수준값, Scaler는 Train 행으로 fit, 시간순 분할
  ① 섞어서 분할   수준값, 예측 시점을 무작위로 7:1:2 배정 (체크 1 위반)
  ② 전체로 fit    수준값, MinMax Scaler를 전체 기간으로 fit (체크 2 위반)
  정상 v2        변화량(다변량)
  ③ 윈도우에 t 포함  변화량, 입력 창이 t-29 … t (체크 3 위반: 그날 수익률이 입력에 들어감)
  ④ 중심 이동평균   변화량, 피처에 rolling(5, center=True) 추가 (체크 4 위반: 후행이 아닌 창)

실행: uv run python scripts/ts_leakage.py
"""
import numpy as np
import pandas as pd

from perfdiag.common import REPORTS, RESULTS, Tee, configure_cpu, save_json, utf8_console
from perfdiag.timeseries.data import make_dataset, prepare
from perfdiag.timeseries.train import TrainConfig, run

CASES = [
    ("correct_level", "정상 v1 (수준값)", "level", {}, None),
    ("shuffled_split", "① 섞어서 분할", "level", {"shuffle": True}, 1),
    ("scaler_all", "② Scaler를 전체 기간으로 fit", "level", {"scaler_all": True}, 2),
    ("correct_delta", "정상 v2 (변화량)", "delta", {}, None),
    ("lookahead_window", "③ 입력 창에 t 포함", "delta", {"lookahead": True}, 3),
    ("centered_feature", "④ 중심 이동평균 피처", "delta", {"centered": True}, 4),
]


def build(prep, mode, leak):
    kwargs = {}
    if leak.get("shuffle"):
        targets = np.concatenate(list(prep.splits.values()))
        rng = np.random.default_rng(0)
        shuffled = targets[rng.permutation(len(targets))]
        n_train, n_validation = len(prep.splits["train"]), len(prep.splits["validation"])
        kwargs["splits"] = {"train": np.sort(shuffled[:n_train]),
                            "validation": np.sort(shuffled[n_train:n_train + n_validation]),
                            "test": np.sort(shuffled[n_train + n_validation:])}
        kwargs["scaler_rows"] = kwargs["splits"]["train"]   # 'Train으로만 fit'은 지킨다 (Train이 전 기간에 흩어져 있을 뿐)
    if leak.get("scaler_all"):
        kwargs["scaler_rows"] = np.arange(prep.first_target - 90, len(prep.y))
    if leak.get("lookahead"):
        kwargs["lookahead"] = True
    if leak.get("centered"):
        returns = pd.Series(np.concatenate([[0.0], np.diff(np.log(prep.y))]))
        kwargs["extra"] = returns.rolling(5, center=True).mean().fillna(0.0).to_numpy()
    return make_dataset(prep, mode, 30, **kwargs)


def main():
    utf8_console()
    configure_cpu()
    prep = prepare("aapl")
    out = {}
    with Tee(REPORTS / "logs" / "ts_leakage.log"):
        print(f"{'설정':<26}{'Test MAE':>10}{'Test MAPE':>11}{'Validation MAE':>16}")
        for key, label, mode, leak, check in CASES:
            ds = build(prep, mode, leak)
            result = run(ds, "lstm", {"hidden": 32}, TrainConfig(), seeds=(0,))
            m = result["seeds"][0]["metrics"]
            out[key] = {"label": label, "mode": mode, "violates_check": check,
                        "test": m["test"], "validation": m["validation"], "train": m["train"],
                        "note": "Test 구간이 정상 설정과 다르다 (무작위 시점)" if leak.get("shuffle") else ""}
            print(f"{label:<26}{m['test']['MAE']:>10.4f}{m['test']['MAPE']:>10.3f}%{m['validation']['MAE']:>16.4f}")
    save_json(RESULTS / "ts_leakage.json", out)


if __name__ == "__main__":
    main()
