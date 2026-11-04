"""시계열 결과 그림: Train/Validation 손실 곡선, 예측 vs 실제, 베이스라인 비교 막대, 누수 재현.

학습 없이 results/*.json만 읽는다. 실행: uv run python scripts/ts_figures.py
"""
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from perfdiag.common import RESULTS, load_json, utf8_console
from perfdiag.plots import (ACTUAL_COLOR, BASELINE_COLOR, DEEP_COLOR, PREDICTION_COLOR, TRAIN_COLOR,
                            VALIDATION_COLOR, plt, save)
from perfdiag.timeseries.data import SERIES

CURVES = ["lstm_level", "gru_level", "lstm_delta", "gru_delta", "probe_small", "probe_large", "probe_regularized"]


def loss_curves(name, deep):
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.2))
    for ax, key in zip(axes.flat, CURVES):
        e = deep["experiments"][key]
        run = next(r for r in e["seeds"] if r["seed"] == e["best_seed"])
        h, m = run["history"], run["metrics"]
        epochs = np.arange(1, len(h["train_loss"]) + 1)
        ax.plot(epochs, h["train_loss"], color=TRAIN_COLOR, label="Train loss")
        ax.plot(epochs, h["validation_loss"], color=VALIDATION_COLOR, label="Validation loss")
        ax.axhline(m["train"]["naive_mse_scaled"], color=TRAIN_COLOR, ls=":", lw=1, label="Naive (Train)")
        ax.axhline(m["validation"]["naive_mse_scaled"], color=VALIDATION_COLOR, ls=":", lw=1, label="Naive (Validation)")
        if e["train_config"]["early_stopping"]:
            ax.axvline(h["best_epoch"], color="#555", ls="--", lw=0.8)
        ax.set_yscale("log")
        d = e["diagnosis"]
        ax.set_title(f"{e['label']}\n{d['label']}  (skill {d['train']:.2f} → {d['validation']:.2f})", fontsize=10)
        ax.set_xlabel("Epoch")
    axes.flat[0].set_ylabel("MSE (정규화 단위, log)")
    axes.flat[4].set_ylabel("MSE (정규화 단위, log)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].axis("off")
    axes.flat[-1].legend(handles, labels, loc="center", fontsize=10, title="점선 = 같은 구간 Naive 손실\n세로 점선 = 복원한 epoch")
    fig.suptitle(f"{deep['title']} — Train/Validation 손실 곡선 (대표 seed)", fontsize=13)
    fig.tight_layout()
    return save(fig, f"ts_{name}_loss_curves.png")


def prediction(name, deep):
    dates = pd.to_datetime(deep["test_dates"])
    actual = np.asarray(deep["test_actual"])
    final = deep["experiments"][deep["final"]]
    level = deep["experiments"]["lstm_level"]
    fig, axes = plt.subplots(3, 1, figsize=(13, 10.5), gridspec_kw={"height_ratios": [3, 2, 2]})
    ax = axes[0]
    ax.plot(dates, actual, color=ACTUAL_COLOR, lw=1.2, label="실제값")
    ax.plot(dates, final["test_prediction"], color=PREDICTION_COLOR, lw=1.0, alpha=0.85,
            label=f"예측값: {final['label']}")
    ax.set_title(f"{deep['title']} — Test 구간 예측 vs 실제 (최종 모델)")
    ax.legend(loc="upper left")
    ax.set_ylabel(deep["unit"])
    zoom = slice(-60, None)
    ax = axes[1]
    ax.plot(dates[zoom], actual[zoom], color=ACTUAL_COLOR, marker="o", ms=3, lw=1.2, label="실제값")
    ax.plot(dates[zoom], np.asarray(final["test_prediction"])[zoom], color=PREDICTION_COLOR, marker="o", ms=3,
            lw=1.0, label="예측값(최종)")
    ax.plot(dates[zoom], np.r_[np.nan, actual[zoom][:-1]], color="#888", ls="--", lw=0.9, label="Naive(전날 값)")
    ax.set_title("마지막 60일 확대")
    ax.legend(loc="upper left", fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax = axes[2]
    ax.plot(dates, actual, color=ACTUAL_COLOR, lw=1.2, label="실제값")
    ax.plot(dates, level["test_prediction"], color=PREDICTION_COLOR, lw=1.0, alpha=0.85, label=f"예측값: {level['label']}")
    ax.set_title("비교: v1 수준값 모델")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_ylabel(deep["unit"])
    fig.tight_layout()
    return save(fig, f"ts_{name}_prediction.png")


def baseline_bars(name, base, deep):
    rows = [(m, v["test"]["MAE"], v["test"]["RMSE"], "baseline") for m, v in base["metrics"].items()]
    for key in ("lstm_level", "gru_level", "lstm_delta", "gru_delta", "probe_regularized"):
        e = deep["experiments"][key]
        s = e["test_summary"]
        rows.append((e["label"], s["MAE"]["mean"], s["RMSE"]["mean"], "final" if key == deep["final"] else "deep"))
    df = pd.DataFrame(rows, columns=["model", "MAE", "RMSE", "kind"])
    colors = df["kind"].map({"baseline": BASELINE_COLOR, "deep": "#90b4e0", "final": DEEP_COLOR})
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))
    naive = base["metrics"]["Naive"]["test"]
    for ax, metric in zip(axes, ("MAE", "RMSE")):
        bars = ax.bar(df["model"], df[metric], color=colors)
        ax.axhline(naive[metric], color="#333", ls="--", lw=1, label=f"Naive {naive[metric]:.3f}")
        ax.set_title(f"Test {metric} ({deep['unit']}) — 낮을수록 좋다")
        ax.tick_params(axis="x", rotation=60)
        for label in ax.get_xticklabels():
            label.set_ha("right")
        top = np.sort(df[metric])[-2] * 1.15    # 가장 큰 막대(선형 추세)는 잘라서 나머지 차이를 보이게 한다
        ax.set_ylim(0, top)
        for bar, value in zip(bars, df[metric]):
            text = f"{value:.2f}" if value < top else f"{value:.1f}↑"
            ax.text(bar.get_x() + bar.get_width() / 2, min(value, top * 0.97), text, ha="center", va="bottom",
                    fontsize=7.5)
        ax.legend(loc="upper left")
    fig.suptitle(f"{deep['title']} — 베이스라인 vs 딥러닝 (회색: 베이스라인, 파랑: 딥러닝, 진한 파랑: 최종 모델)",
                 fontsize=12)
    fig.tight_layout()
    return save(fig, f"ts_{name}_baseline_bars.png")


def leakage(results):
    labels = [v["label"] for v in results.values()]
    mae = [v["test"]["MAE"] for v in results.values()]
    leak = [v["violates_check"] is not None for v in results.values()]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    bars = ax.barh(labels[::-1], mae[::-1], color=["#e07b7b" if x else DEEP_COLOR for x in leak[::-1]])
    for bar, value in zip(bars, mae[::-1]):
        ax.text(value, bar.get_y() + bar.get_height() / 2, f" {value:.3f}", va="center", fontsize=9)
    ax.set_xlabel("Test MAE (USD) — 낮아 보일수록 의심")
    ax.set_title("AAPL: 누수 체크포인트를 하나씩 어기면 점수가 '좋아 보인다' (빨강 = 누수)")
    fig.tight_layout()
    return save(fig, "ts_leakage_demo.png")


def main():
    utf8_console()
    for name in SERIES:
        base = load_json(RESULTS / f"ts_baselines_{name}.json")
        deep = load_json(RESULTS / f"ts_deep_{name}.json")
        for path in (loss_curves(name, deep), prediction(name, deep), baseline_bars(name, base, deep)):
            print(f"저장: {path.name}")
    if (RESULTS / "ts_leakage.json").exists():
        print(f"저장: {leakage(load_json(RESULTS / 'ts_leakage.json')).name}")


if __name__ == "__main__":
    main()
