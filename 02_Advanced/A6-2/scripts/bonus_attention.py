"""보너스 2: LSTM에 Attention을 붙이고, 작은 Transformer와 함께 입력 창 30일·90일에서 비교한다.

모두 변화량(v2) 설정, seed 0·1·2. 창이 길어질 때 마지막 은닉 상태 하나에만 기대는 LSTM보다
모든 시점을 다시 훑는 Attention이 나은지, 그리고 Attention이 실제로 어느 시점을 보는지 확인한다.

실행: uv run python scripts/bonus_attention.py   (약 20분)
"""
import time

import numpy as np
import torch

from perfdiag.common import REPORTS, RESULTS, Tee, configure_cpu, save_json, set_seed, utf8_console
from perfdiag.timeseries.data import SERIES, make_dataset, prepare
from perfdiag.timeseries.models import build_model
from perfdiag.timeseries.train import TrainConfig, evaluate, fit

MODELS = [("lstm", "LSTM", {"hidden": 32}),
          ("lstm_attention", "LSTM + Attention", {"hidden": 32}),
          ("transformer", "Transformer(2층, d=32)", {"d_model": 32, "heads": 4, "layers": 2, "dropout": 0.1})]
WINDOWS = (30, 90)
SEEDS = (0, 1, 2)


def main():
    utf8_console()
    configure_cpu()
    out = {}
    with Tee(REPORTS / "logs" / "bonus_attention.log"):
        for name in SERIES:
            prep = prepare(name)
            out[name] = {}
            for window in WINDOWS:
                ds = make_dataset(prep, "delta", window)
                for arch, label, kwargs in MODELS:
                    runs, start = [], time.perf_counter()
                    for seed in SEEDS:
                        set_seed(seed)
                        model = build_model(ds.n_features, arch, **kwargs)
                        history = fit(model, ds, TrainConfig(seed=seed))
                        runs.append((model, history, evaluate(model, ds)))
                    test_mae = [m["test"]["MAE"] for _, _, m in runs]
                    skill = [m["test"]["mse_scaled"] / m["test"]["naive_mse_scaled"] for _, _, m in runs]
                    entry = {"label": label, "window": window, "test_mae": test_mae, "test_skill": skill,
                             "validation_mse": [m["validation"]["mse_scaled"] for _, _, m in runs],
                             "epochs_run": [h["epochs_run"] for _, h, _ in runs],
                             "parameters": sum(p.numel() for p in runs[0][0].parameters())}
                    if arch == "lstm_attention":
                        best = min(runs, key=lambda r: r[2]["validation"]["mse_scaled"])[0]
                        best.eval()
                        with torch.no_grad():
                            best(torch.as_tensor(ds.sets["test"].X))
                        weights = best.last_attention.numpy()        # (Test 시점 수, window)
                        entry["attention_mean"] = weights.mean(0)
                        entry["attention_examples"] = weights[::max(1, len(weights) // 6)][:6]
                    out[name][f"{arch}_{window}"] = entry
                    print(f"{prep.cfg.title:<12} 창 {window:>2}  {label:<22} Test MAE {np.mean(test_mae):.4f} ± "
                          f"{np.std(test_mae):.4f}  Test skill {np.mean(skill):.3f}  ({time.perf_counter() - start:.0f}초)")
    save_json(RESULTS / "bonus_attention.json", out)


if __name__ == "__main__":
    main()
