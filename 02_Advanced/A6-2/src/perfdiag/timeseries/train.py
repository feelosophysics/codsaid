"""시계열 모델 학습·평가.

- Train 윈도우는 미니배치마다 섞는다. 분할은 이미 시간순으로 끝났고, 각 윈도우는 '과거 → 다음 값' 한 쌍이라
  Train 안에서 순서를 섞어도 미래가 들어오지 않는다. Validation·Test는 섞지 않는다.
- 조기 종료와 모델 선택은 Validation 손실만 본다. Test는 마지막에 한 번 평가한다.
- 매 epoch마다 Train 전체를 eval 모드(Dropout 끔)로 다시 평가해 Validation과 같은 조건의 곡선을 그린다.
"""
import copy
import time
from dataclasses import asdict, dataclass

import numpy as np
import torch
from torch import nn

from ..common import set_seed
from ..diagnosis import diagnose_forecast
from ..metrics import regression_metrics
from .baselines import naive
from .models import build_model, count_parameters


@dataclass
class TrainConfig:
    epochs: int = 150
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 0.0
    patience: int = 20          # Validation 손실이 이만큼 epoch 동안 나아지지 않으면 멈춘다
    early_stopping: bool = True
    seed: int = 0


@torch.no_grad()
def predict(model, X, batch_size=512):
    model.eval()
    X = torch.as_tensor(X)
    return torch.cat([model(X[i:i + batch_size]) for i in range(0, len(X), batch_size)]).numpy()


def mse(model, ws):
    return float(np.mean((predict(model, ws.X) - ws.target) ** 2))


def fit(model, dataset, cfg):
    set_seed(cfg.seed)
    train = dataset.sets["train"]
    X, y = torch.as_tensor(train.X), torch.as_tensor(train.target)
    generator = torch.Generator().manual_seed(cfg.seed)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    loss_fn = nn.MSELoss()
    history = {"train_loss": [], "validation_loss": []}
    best = (float("inf"), 0, copy.deepcopy(model.state_dict()))
    start = time.perf_counter()
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        order = torch.randperm(len(X), generator=generator)
        for i in range(0, len(X), cfg.batch_size):
            batch = order[i:i + cfg.batch_size]
            loss = loss_fn(model(X[batch]), y[batch])
            opt.zero_grad()
            loss.backward()
            opt.step()
        history["train_loss"].append(mse(model, train))
        history["validation_loss"].append(mse(model, dataset.sets["validation"]))
        if history["validation_loss"][-1] < best[0]:
            best = (history["validation_loss"][-1], epoch, copy.deepcopy(model.state_dict()))
        elif cfg.early_stopping and epoch - best[1] >= cfg.patience:
            break
    if cfg.early_stopping:
        model.load_state_dict(best[2])
    history.update(best_epoch=best[1] if cfg.early_stopping else len(history["train_loss"]),
                   epochs_run=len(history["train_loss"]), seconds=time.perf_counter() - start)
    return history


def naive_scaled_mse(dataset, split):
    """같은 구간의 Naive(ŷ(t)=y(t−1))를 모델과 같은 정규화 단위로 잰 MSE. 진단의 기준선이다."""
    ws = dataset.sets[split]
    prev = dataset.prep.from_level(ws.prev_level)
    if dataset.mode == "level":
        pred = dataset.target_scaler.transform(dataset.prep.to_level(prev).reshape(-1, 1)).ravel()
    else:
        pred = dataset.target_scaler.transform(np.zeros((len(ws.t), 1))).ravel()  # 변화량 0 = Naive
    return float(np.mean((pred - ws.target) ** 2))


def evaluate(model, dataset):
    out = {}
    for split in ("train", "validation", "test"):
        pred = dataset.reconstruct(split, predict(model, dataset.sets[split].X))
        out[split] = regression_metrics(dataset.actual(split), pred, dataset.prep.cfg.with_mape)
        out[split]["mse_scaled"] = mse(model, dataset.sets[split])
        out[split]["naive_mse_scaled"] = naive_scaled_mse(dataset, split)
    return out


def run(dataset, arch="lstm", model_kwargs=None, cfg=None, seeds=(0, 1, 2)):
    """같은 설정을 seed 여러 개로 학습한다. 대표 seed는 Validation MSE가 가장 낮은 것이다."""
    model_kwargs = model_kwargs or {}
    cfg = cfg or TrainConfig()
    runs = []
    for seed in seeds:
        set_seed(seed)
        model = build_model(dataset.n_features, arch, **model_kwargs)
        history = fit(model, dataset, TrainConfig(**{**asdict(cfg), "seed": seed}))
        metrics = evaluate(model, dataset)
        runs.append({"seed": seed, "history": history, "metrics": metrics, "model": model})
    best = min(runs, key=lambda r: r["metrics"]["validation"]["mse_scaled"])
    model = best["model"]
    m = best["metrics"]
    diagnosis = diagnose_forecast(m["train"]["mse_scaled"], m["validation"]["mse_scaled"],
                                  m["train"]["naive_mse_scaled"], m["validation"]["naive_mse_scaled"])
    test_pred = dataset.reconstruct("test", predict(model, dataset.sets["test"].X))
    summary = {}
    for key in ("MAE", "RMSE", "MAPE"):
        values = [r["metrics"]["test"][key] for r in runs]
        summary[key] = None if values[0] is None else {"mean": float(np.mean(values)), "std": float(np.std(values))}
    return {
        "arch": arch, "mode": dataset.mode, "window": dataset.window, "model_kwargs": model_kwargs,
        "train_config": asdict(cfg), "parameters": count_parameters(model), "best_seed": best["seed"],
        "seeds": [{"seed": r["seed"], "metrics": r["metrics"], "history": r["history"]} for r in runs],
        "test_summary": summary, "diagnosis": diagnosis.to_dict(),
        "test_prediction": test_pred, "model": model,
    }


def naive_test_errors(dataset):
    ws = dataset.sets["test"]
    return dataset.actual("test") - naive(dataset.prep.y, ws.t)
