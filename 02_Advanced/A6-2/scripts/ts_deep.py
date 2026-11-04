"""2~4단계: LSTM·GRU 학습 → 편향/분산 진단 → 개선 적용 → 베이스라인 대비 정량화.

실험 (시계열마다, seed 0·1·2. 진단용 probe 두 개는 seed 0만)
  v1 수준값   LSTM·GRU   입력: 수준값 1개(MinMax), 출력: 다음 수준값           ← 흔한 튜토리얼 방식
  v2 변화량   LSTM·GRU   입력: 다변량 피처(Standard), 출력: 변화량(로그 수익률·기온 차)
  진단용      LSTM 은닉 2            일부러 작은 모델 (편향 확인)
              LSTM 은닉 128×2층      정규화·조기 종료 없음 (분산 확인)
              LSTM 은닉 128×2층 + Dropout 0.3 + Weight decay + 조기 종료 (분산 처방)

최종 딥러닝 모델은 진단용 앞의 두 개를 뺀 후보 중 원래 단위의 Validation MAE로 고른다. Test는 비교에만 쓴다.

실행: uv run python scripts/ts_deep.py   (먼저 scripts/ts_baselines.py)
"""
import argparse
import time

import numpy as np

from perfdiag.common import REPORTS, RESULTS, Tee, configure_cpu, load_json, now_iso, save_json, utf8_console
from perfdiag.metrics import diebold_mariano, improvement
from perfdiag.timeseries.baselines import naive
from perfdiag.timeseries.data import SERIES, make_dataset, prepare
from perfdiag.timeseries.train import TrainConfig, run

from ts_baselines import split_fingerprint

EXPERIMENTS = [
    # key, 표시 이름, mode, arch, 모델 인자, 학습 설정, 역할
    ("lstm_level", "LSTM·수준값(v1)", "level", "lstm", {"hidden": 32}, {}, "candidate"),
    ("gru_level", "GRU·수준값(v1)", "level", "gru", {"hidden": 32}, {}, "candidate"),
    ("lstm_delta", "LSTM·변화량(v2)", "delta", "lstm", {"hidden": 32}, {}, "candidate"),
    ("gru_delta", "GRU·변화량(v2)", "delta", "gru", {"hidden": 32}, {}, "candidate"),
    ("probe_small", "LSTM 은닉 2", "delta", "lstm", {"hidden": 2}, {}, "probe"),
    ("probe_large", "LSTM 128×2 (규제 없음)", "delta", "lstm", {"hidden": 128, "layers": 2},
     {"epochs": 100, "early_stopping": False}, "probe"),
    ("probe_regularized", "LSTM 128×2 + 규제", "delta", "lstm", {"hidden": 128, "layers": 2, "dropout": 0.3},
     {"epochs": 100, "weight_decay": 1e-4}, "candidate"),
]
WINDOW = 30
SEEDS = (0, 1, 2)


def require_baselines(name, prep):
    path = RESULTS / f"ts_baselines_{name}.json"
    if not path.exists():
        raise SystemExit(f"{path.name}이 없다. 미션 제약: 베이스라인을 먼저 측정한다 → scripts/ts_baselines.py")
    baselines = load_json(path)
    if baselines["test_fingerprint"] != split_fingerprint(prep):
        raise SystemExit("베이스라인과 Test 구간이 다르다. ts_baselines.py를 다시 실행한다")
    return baselines


def compare(prep, baselines, deep_metrics, deep_errors):
    """딥러닝 모델이 각 베이스라인보다 몇 % 나은지 (양수 = 오차 감소)."""
    table = {}
    for model, m in baselines["metrics"].items():
        row = {}
        for key in ("MAE", "RMSE", "MAPE"):
            if m["test"][key] is not None:
                row[key] = improvement(m["test"][key], deep_metrics[key])
        table[model] = row
    t = prep.splits["test"]
    naive_errors = prep.y[t] - naive(prep.y, t)
    best = baselines["best_by_validation"]
    best_errors = prep.y[t] - np.asarray(baselines["test_predictions"][best])
    dm_naive = diebold_mariano(deep_errors, naive_errors)
    dm_best = diebold_mariano(deep_errors, best_errors)
    return table, {"vs_naive": {"statistic": dm_naive[0], "p_value": dm_naive[1]},
                   "vs_best_baseline": {"model": best, "statistic": dm_best[0], "p_value": dm_best[1]}}


def run_series(name, seeds):
    prep = prepare(name)
    baselines = require_baselines(name, prep)
    started = now_iso()
    print(f"\n=== {prep.cfg.title} — 베이스라인 측정 {baselines['measured_at']} → 딥러닝 시작 {started} ===")
    datasets = {mode: make_dataset(prep, mode, WINDOW) for mode in ("level", "delta")}
    experiments = {}
    for key, label, mode, arch, kwargs, train_kwargs, role in EXPERIMENTS:
        start = time.perf_counter()
        # 진단용 probe는 곡선 모양을 보여 주는 것이 목적이라 seed 1개로 충분하다 (가장 오래 걸리는 실험)
        result = run(datasets[mode], arch, kwargs, TrainConfig(**train_kwargs), seeds[:1] if role == "probe" else seeds)
        result.pop("model")
        result.update(label=label, role=role)
        experiments[key] = result
        d = result["diagnosis"]
        s = result["test_summary"]
        print(f"  {label:<24} 파라미터 {result['parameters']:>7,}  Test MAE {s['MAE']['mean']:.4f}±{s['MAE']['std']:.4f}"
              f"  {d['label']:<28} ({time.perf_counter() - start:.0f}초)")
        print(f"    {d['rule']}")
    candidates = [k for k, e in experiments.items() if e["role"] == "candidate"]
    # 수준값·변화량 모델은 정규화 단위가 달라 mse_scaled끼리 비교할 수 없다 → 원래 단위의 Validation MAE로 고른다
    final = min(candidates, key=lambda k: next(r["metrics"]["validation"]["MAE"] for r in experiments[k]["seeds"]
                                               if r["seed"] == experiments[k]["best_seed"]))
    e = experiments[final]
    best_seed = next(r for r in e["seeds"] if r["seed"] == e["best_seed"])
    deep_test = best_seed["metrics"]["test"]
    t = prep.splits["test"]
    deep_errors = prep.y[t] - np.asarray(e["test_prediction"])
    table, dm = compare(prep, baselines, deep_test, deep_errors)
    print(f"  → Validation으로 고른 최종 모델: {e['label']} (seed {e['best_seed']})")
    for model, row in table.items():
        print(f"    vs {model:<13} " + "  ".join(f"{k} {v:+.2f}%" for k, v in row.items()))
    print(f"    Diebold-Mariano vs Naive: 통계량 {dm['vs_naive']['statistic']:+.3f}, p={dm['vs_naive']['p_value']:.4f}")
    print(f"    Diebold-Mariano vs {dm['vs_best_baseline']['model']}: 통계량 "
          f"{dm['vs_best_baseline']['statistic']:+.3f}, p={dm['vs_best_baseline']['p_value']:.4f}")
    return {
        "series": name, "title": prep.cfg.title, "unit": prep.cfg.unit, "window": WINDOW, "seeds": list(seeds),
        "baselines_measured_at": baselines["measured_at"], "deep_started_at": started,
        "test_fingerprint": split_fingerprint(prep), "feature_names": prep.feature_names,
        "test_dates": [str(d) for d in prep.dates[t]], "test_actual": prep.y[t],
        "experiments": experiments, "final": final, "final_test": deep_test,
        "improvement_vs_baselines": table, "diebold_mariano": dm,
    }


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", nargs="*", default=list(SERIES))
    parser.add_argument("--seeds", type=int, default=len(SEEDS))
    args = parser.parse_args()
    threads = configure_cpu()
    with Tee(REPORTS / "logs" / "ts_deep.log"):
        print(f"CPU 스레드 {threads}개")
        for name in args.series:
            save_json(RESULTS / f"ts_deep_{name}.json", run_series(name, tuple(range(args.seeds))))


if __name__ == "__main__":
    main()
