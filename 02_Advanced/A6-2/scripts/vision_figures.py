"""전이 학습 그림: shots × 전략 Train/Validation 손실 곡선, 데이터 크기별 정확도, 혼동 행렬.

학습 없이 results/vision_transfer.json만 읽는다. 실행: uv run python scripts/vision_figures.py
"""
import numpy as np

from perfdiag.common import RESULTS, load_json, utf8_console
from perfdiag.plots import TRAIN_COLOR, VALIDATION_COLOR, plt, save
from perfdiag.vision.data import CLASS_KO

ORDER = ["linear_probe", "partial", "full", "scratch"]
STYLE = {"linear_probe": ("#3182ce", "o"), "partial": ("#38a169", "s"), "full": ("#d69e2e", "^"),
         "scratch": ("#e53e3e", "x")}


def loss_curves(data):
    runs = data["runs"]
    shots = sorted({r["shots"] for r in runs})
    fig, axes = plt.subplots(len(shots), 4, figsize=(17, 3.6 * len(shots)), squeeze=False)
    for i, s in enumerate(shots):
        for j, strategy in enumerate(ORDER):
            ax = axes[i, j]
            run = next((r for r in runs if r["shots"] == s and r["strategy"] == strategy), None)
            if run is None:
                ax.axis("off")
                continue
            h = run["history"]
            epochs = np.arange(1, len(h["train_loss"]) + 1)
            ax.plot(epochs, h["train_loss"], color=TRAIN_COLOR, label="Train loss")
            ax.plot(epochs, h["validation_loss"], color=VALIDATION_COLOR, label="Validation loss")
            ax.axvline(h["best_epoch"], color="#555", ls="--", lw=0.8)
            ax.set_yscale("log")
            d = run["diagnosis"]
            ax.set_title(f"{s}장/클래스 · {run['label']}\nTrain 정확도 {run['train']['accuracy']:.2f} / Validation "
                         f"{run['validation']['accuracy']:.2f} → {d['label']}", fontsize=9.5)
            ax.set_xlabel("Epoch")
            if j == 0:
                ax.set_ylabel("Cross-entropy (log)")
    axes[0, 0].legend(fontsize=9)
    fig.suptitle("Few-shot 전이 학습 — Train/Validation 손실 곡선 (세로 점선: 복원한 epoch = Validation 손실 최저)",
                 fontsize=12)
    fig.tight_layout()
    return save(fig, "vision_loss_curves.png")


def shots_chart(data):
    runs = data["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    for strategy in ORDER:
        rs = sorted([r for r in runs if r["strategy"] == strategy], key=lambda r: r["shots"])
        if not rs:
            continue
        color, marker = STYLE[strategy]
        x = [r["shots"] for r in rs]
        axes[0].plot(x, [r["test"]["accuracy"] for r in rs], color=color, marker=marker, ms=8, label=rs[0]["label"])
        axes[1].plot(x, [r["validation"]["error"] - r["train"]["error"] for r in rs], color=color, marker=marker, ms=8,
                     label=rs[0]["label"])
    axes[0].set_title("Test 정확도 — 클래스당 Train 사진 수별")
    axes[0].set_ylabel("Test 정확도")
    axes[1].set_title("Validation 오류율 − Train 오류율 (분산의 크기)")
    axes[1].axhline(0.05, color="#999", ls=":", lw=1)
    for ax in axes:
        ax.set_xlabel("클래스당 Train 사진 수")
        ax.set_xticks(sorted({r["shots"] for r in runs}))
        ax.legend(fontsize=9)
    fig.tight_layout()
    return save(fig, "vision_shots_strategy.png")


def confusion(data):
    matrix = np.asarray(data["main"]["confusion"])
    names = [CLASS_KO[c] for c in data["classes"]]
    fig, ax = plt.subplots(figsize=(7.5, 6.4))
    rates = matrix / matrix.sum(1, keepdims=True)
    ax.imshow(rates, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(names)):
        for j in range(len(names)):
            if matrix[i, j]:
                ax.text(j, i, matrix[i, j], ha="center", va="center", color="white" if rates[i, j] > 0.5 else "#222")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), names)
    ax.set_xlabel("예측")
    ax.set_ylabel("실제")
    ax.grid(False)
    main = data["main"]
    ax.set_title(f"주 모델 Test 혼동 행렬 ({main['shots']}장/클래스, {main['strategy']})")
    fig.tight_layout()
    return save(fig, "vision_confusion.png")


def main():
    utf8_console()
    data = load_json(RESULTS / "vision_transfer.json")
    for path in (loss_curves(data), shots_chart(data), confusion(data)):
        print(f"저장: {path.name}")


if __name__ == "__main__":
    main()
