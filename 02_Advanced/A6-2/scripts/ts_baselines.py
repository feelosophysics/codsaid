"""1단계: 딥러닝 학습 전에 베이스라인을 먼저 구현하고 성능을 측정한다.

결과 results/ts_baselines_<series>.json에 측정 시각을 남긴다. ts_deep.py는 이 파일이 없으면 실행을 거부한다.

실행: uv run python scripts/ts_baselines.py
"""
import hashlib

import numpy as np

from perfdiag.common import REPORTS, RESULTS, Tee, now_iso, save_json, utf8_console
from perfdiag.metrics import regression_metrics
from perfdiag.timeseries.baselines import all_baselines
from perfdiag.timeseries.data import SERIES, prepare


def split_fingerprint(prep):
    """Test 구간이 모든 모델에서 같은지 확인하는 지문 (시점 번호와 실제값의 해시)."""
    t = prep.splits["test"]
    return hashlib.sha256(t.tobytes() + prep.y[t].tobytes()).hexdigest()[:16]


def run_series(name):
    prep = prepare(name)
    preds, params = all_baselines(prep.y, prep.splits)
    rows = {}
    for model, by_split in preds.items():
        rows[model] = {split: regression_metrics(prep.y[prep.splits[split]], p, prep.cfg.with_mape)
                       for split, p in by_split.items()}
    # 베이스라인 중 '최선'도 Validation MAE로 고른다 (Test로 고르면 Test를 본 것이 된다)
    best = min(rows, key=lambda m: rows[m]["validation"]["MAE"])
    print(f"\n=== {prep.cfg.title} ({name}) ===")
    for split, info in prep.info.items():
        print(f"  {split:<10} {info['n']:>5}개 시점  {info['start']} ~ {info['end']}")
    print(f"  {'모델':<14}{'Validation MAE':>15}{'Test MAE':>11}{'Test RMSE':>11}{'Test MAPE':>11}")
    for model, m in rows.items():
        mape = "-" if m["test"]["MAPE"] is None else f"{m['test']['MAPE']:.3f}%"
        flag = "  ← Validation 최선" if model == best else ""
        print(f"  {model:<14}{m['validation']['MAE']:>15.4f}{m['test']['MAE']:>11.4f}"
              f"{m['test']['RMSE']:>11.4f}{mape:>11}{flag}")
    return {
        "series": name, "title": prep.cfg.title, "unit": prep.cfg.unit, "measured_at": now_iso(),
        "split_info": prep.info, "test_fingerprint": split_fingerprint(prep),
        "metrics": rows, "params": params, "best_by_validation": best,
        "test_predictions": {m: np.round(p["test"], 6) for m, p in preds.items()},
    }


def main():
    utf8_console()
    with Tee(REPORTS / "logs" / "ts_baselines.log"):
        for name in SERIES:
            save_json(RESULTS / f"ts_baselines_{name}.json", run_series(name))


if __name__ == "__main__":
    main()
