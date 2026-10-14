"""보너스 1: Grid Search 대신 Random Search → Coarse-to-Fine으로 LSTM 하이퍼파라미터를 찾는다.

대상: 서울 기온, 변화량(v2) LSTM. 목적 함수는 Validation MSE이고 Test는 마지막 재학습 뒤 한 번만 본다.
  1단계 Coarse  넓은 범위에서 무작위 16회
  2단계 Fine    1단계 상위 4개가 차지한 범위로 좁혀 무작위 8회
  중요도        각 하이퍼파라미터를 3구간으로 나눴을 때 log(Validation MSE) 분산 중 구간 차이로 설명되는 비율(η²)
  마무리        최적 설정을 seed 3개로 다시 학습해 기본 설정(LSTM·변화량, 은닉 32, 창 30)과 Test에서 비교

실행: uv run python scripts/bonus_hparam_search.py   (CPU 6스레드 약 25분)
"""
import math
import time

import numpy as np
from scipy import stats

from perfdiag.common import REPORTS, RESULTS, Tee, configure_cpu, load_json, save_json, utf8_console
from perfdiag.timeseries.data import make_dataset, prepare
from perfdiag.timeseries.train import TrainConfig, run

SERIES = "seoul"
COARSE_TRIALS, FINE_TRIALS, TOP_K = 16, 8, 4
SPACE = {
    # 이름: (종류, 범위)
    "lr": ("log", (1e-4, 1e-2)),
    "hidden": ("logint", (8, 96)),
    "layers": ("choice", (1, 2)),
    "dropout": ("uniform", (0.0, 0.5)),
    "window": ("choice", (7, 14, 30, 60)),
    "weight_decay": ("log", (1e-6, 1e-2)),
}
SEARCH_TRAIN = {"epochs": 40, "patience": 8}   # 노트북 CPU 예산: trial 하나 1분 안팎


def sample(space, rng):
    out = {}
    for name, (kind, values) in space.items():
        if kind == "log":
            out[name] = float(math.exp(rng.uniform(math.log(values[0]), math.log(values[1]))))
        elif kind == "logint":
            out[name] = int(round(math.exp(rng.uniform(math.log(values[0]), math.log(values[1])))))
        elif kind == "uniform":
            out[name] = float(rng.uniform(*values))
        else:
            out[name] = values[rng.integers(len(values))]
    return out


def narrow(space, top):
    """상위 설정들이 차지한 범위로 좁힌다 (로그 척도 변수는 로그 공간에서 10% 여유)."""
    fine = {}
    for name, (kind, values) in space.items():
        seen = [t["params"][name] for t in top]
        if kind == "choice":
            fine[name] = (kind, tuple(sorted(set(seen))))
        elif kind in ("log", "logint"):
            lo, hi = math.log(min(seen)), math.log(max(seen))
            pad = 0.1 * (hi - lo) + 1e-9
            low, high = math.exp(lo - pad), math.exp(hi + pad)
            fine[name] = (kind, (max(values[0], low), min(values[1], high)))
        else:
            pad = 0.1 * (max(seen) - min(seen)) + 1e-9
            fine[name] = (kind, (max(values[0], min(seen) - pad), min(values[1], max(seen) + pad)))
    return fine


def evaluate(prep, datasets, params, seeds=(0,), train_kwargs=None):
    window = params["window"]
    if window not in datasets:
        datasets[window] = make_dataset(prep, "delta", window)
    model_kwargs = {"hidden": params["hidden"], "layers": params["layers"], "dropout": params["dropout"]}
    cfg = TrainConfig(lr=params["lr"], weight_decay=params["weight_decay"], **(train_kwargs or SEARCH_TRAIN))
    return run(datasets[window], "lstm", model_kwargs, cfg, seeds)


def importance(trials):
    """η²: 3구간(분위수)으로 나눈 그룹 간 분산 / 전체 분산. 선택형 변수는 값별로 묶는다. Spearman ρ도 함께."""
    y = np.log([t["validation_mse"] for t in trials])
    out = {}
    for name, (kind, _) in SPACE.items():
        x = np.array([t["params"][name] for t in trials], dtype=float)
        if kind == "choice":
            groups = [y[x == v] for v in np.unique(x)]
        else:
            edges = np.quantile(x, [1 / 3, 2 / 3])
            bins = np.digitize(x, edges)
            groups = [y[bins == b] for b in range(3)]
        between = sum(len(g) * (g.mean() - y.mean()) ** 2 for g in groups if len(g))
        eta2 = float(between / ((y - y.mean()) ** 2).sum())
        rho = float(stats.spearmanr(np.log(x) if kind in ("log", "logint") else x, y).statistic)
        out[name] = {"eta_squared": eta2, "spearman": rho}
    return out


def main():
    utf8_console()
    configure_cpu()
    prep = prepare(SERIES)
    datasets = {}
    rng = np.random.default_rng(2026)
    trials = []
    with Tee(REPORTS / "logs" / "bonus_hparam_search.log"):
        for stage, n, space in (("coarse", COARSE_TRIALS, SPACE), ("fine", FINE_TRIALS, None)):
            if stage == "fine":
                top = sorted(trials, key=lambda t: t["validation_mse"])[:TOP_K]
                space = narrow(SPACE, top)
                print("\n좁힌 범위: " + ", ".join(f"{k}={v[1]}" for k, v in space.items()))
                fine_space = space
            for i in range(n):
                params = sample(space, rng)
                start = time.perf_counter()
                result = evaluate(prep, datasets, params)
                m = result["seeds"][0]["metrics"]["validation"]
                trial = {"trial": len(trials) + 1, "stage": stage, "params": params,
                         "validation_mse": m["mse_scaled"], "validation_skill": m["mse_scaled"] / m["naive_mse_scaled"],
                         "validation_mae": m["MAE"], "epochs_run": result["seeds"][0]["history"]["epochs_run"],
                         "seconds": time.perf_counter() - start}
                trials.append(trial)
                print(f"[{stage:<6} {trial['trial']:>2}] Validation MSE {trial['validation_mse']:.4f} "
                      f"(skill {trial['validation_skill']:.3f}) " + ", ".join(
                          f"{k}={v:.2g}" if isinstance(v, float) else f"{k}={v}" for k, v in params.items())
                      + f"  {trial['seconds']:.0f}초")
        best = min(trials, key=lambda t: t["validation_mse"])
        imp = importance(trials)
        print("\n중요도 (η², Spearman ρ):")
        for name, v in sorted(imp.items(), key=lambda kv: -kv[1]["eta_squared"]):
            print(f"  {name:<13} η²={v['eta_squared']:.3f}  ρ={v['spearman']:+.3f}")

        print(f"\n최적 설정(trial {best['trial']})을 seed 3개로 다시 학습 (epoch 150, patience 20)")
        final = evaluate(prep, datasets, best["params"], seeds=(0, 1, 2), train_kwargs={})
        default = load_json(RESULTS / f"ts_deep_{SERIES}.json")["experiments"]["lstm_delta"]
        for label, r in (("기본 설정", default), ("탐색 최적", final)):
            print(f"  {label}: Test MAE {r['test_summary']['MAE']['mean']:.4f} ± {r['test_summary']['MAE']['std']:.4f}, "
                  f"RMSE {r['test_summary']['RMSE']['mean']:.4f}")
    final.pop("model")
    final.pop("test_prediction")
    save_json(RESULTS / "bonus_hparam_search.json", {
        "series": SERIES, "space": {k: [v[0], list(v[1])] for k, v in SPACE.items()},
        "fine_space": {k: [v[0], list(v[1])] for k, v in fine_space.items()},
        "search_train": SEARCH_TRAIN, "trials": trials, "best": best, "importance": imp,
        "final": {"params": best["params"], "test_summary": final["test_summary"], "diagnosis": final["diagnosis"]},
        "default": {"test_summary": default["test_summary"], "model_kwargs": default["model_kwargs"],
                    "window": default["window"]},
    })


if __name__ == "__main__":
    main()
