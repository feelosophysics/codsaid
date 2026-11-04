"""MNIST 분류: 784-128-10 ReLU MLP, He 초기화, SGD(lr=0.1), batch 64.

데이터는 IDX(UBYTE) 바이너리를 직접 파싱해 NumPy 배열로 쓴다 (minigrad.data.mnist).
기준: 1 epoch 후 테스트 정확도 80% 이상.

실행: uv run python scripts/train_mnist.py [--epochs 1] [--optimizer sgd|adam]
"""
import argparse
import sys
import time

import numpy as np

from _common import MNIST_DIR, REPORTS, Tee, plt, save_figure, save_json
from minigrad import Tensor, nn, no_grad, optim
from minigrad.data import DataLoader, load_mnist


def accuracy(model, X, y, batch_size=2000):
    model.eval()
    correct = 0
    with no_grad():
        for start in range(0, len(X), batch_size):
            logits = model(Tensor(X[start:start + batch_size])).data
            correct += int((logits.argmax(axis=1) == y[start:start + batch_size]).sum())
    model.train()
    return correct / len(X)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--optimizer", choices=("sgd", "adam"), default="sgd")
    parser.add_argument("--lr", type=float, default=None, help="기본값: sgd 0.1, adam 0.001")
    parser.add_argument("--init", choices=nn.init.METHODS, default="he")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    lr = args.lr or (0.1 if args.optimizer == "sgd" else 0.001)

    with Tee(REPORTS / "train_mnist.log"):
        X_train, y_train, X_test, y_test = load_mnist(MNIST_DIR)
        print(f"MNIST train {X_train.shape}, test {X_test.shape}, 픽셀 범위 [{X_train.min()}, {X_train.max()}]")
        rng = np.random.default_rng(args.seed)
        model = nn.mlp([784, args.hidden, 10], activation=nn.ReLU, init=args.init, rng=rng)
        opt = optim.SGD(model.parameters(), lr=lr) if args.optimizer == "sgd" else optim.Adam(model.parameters(), lr=lr)
        loader = DataLoader(X_train, y_train, args.batch_size, shuffle=True, rng=rng)
        print(f"모델 784-{args.hidden}-10, init={args.init}, {args.optimizer}(lr={lr}), batch {args.batch_size}, "
              f"{len(loader)} 스텝/epoch, seed {args.seed}\n")

        step_losses, history = [], []
        start = time.perf_counter()
        for epoch in range(1, args.epochs + 1):
            for step, (xb, yb) in enumerate(loader, start=1):
                loss = nn.cross_entropy(model(Tensor(xb)), yb)
                opt.zero_grad()
                loss.backward()
                opt.step()
                step_losses.append(loss.item())
                if step % 200 == 0:
                    print(f"epoch {epoch} step {step:4d}/{len(loader)}  loss(최근 200) "
                          f"{np.mean(step_losses[-200:]):.4f}")
            train_acc, test_acc = accuracy(model, X_train, y_train), accuracy(model, X_test, y_test)
            history.append({"epoch": epoch, "train_accuracy": train_acc, "test_accuracy": test_acc,
                            "seconds": time.perf_counter() - start})
            print(f"== epoch {epoch}: train {train_acc:.2%}, test {test_acc:.2%} "
                  f"({time.perf_counter() - start:.1f}초 경과)\n")

        passed = history[0]["test_accuracy"] >= 0.8
        print(f"판정 (1 epoch 테스트 정확도 ≥ 80%): {'PASS' if passed else 'FAIL'} "
              f"({history[0]['test_accuracy']:.2%})")

        with no_grad():
            pred = model(Tensor(X_test)).data.argmax(axis=1)
        confusion = np.zeros((10, 10), dtype=int)
        np.add.at(confusion, (y_test, pred), 1)
        per_class = confusion.diagonal() / confusion.sum(axis=1)
        print("클래스별 테스트 정확도: " + ", ".join(f"{d}:{a:.1%}" for d, a in enumerate(per_class)))

        fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw={"width_ratios": [1.3, 1, 1.1]})
        window = 50
        smooth = np.convolve(step_losses, np.ones(window) / window, mode="valid")
        axes[0].plot(step_losses, color="#9ecae1", lw=0.6, label="스텝별")
        axes[0].plot(np.arange(window - 1, len(step_losses)), smooth, color="#1f77b4", lw=2, label="50스텝 평균")
        axes[0].set(yscale="log", xlabel="스텝", ylabel="Cross-Entropy",
                    title=f"학습 손실 ({args.epochs} epoch, 테스트 {history[-1]['test_accuracy']:.2%})")
        axes[0].legend()
        im = axes[1].imshow(confusion, cmap="Blues")
        axes[1].set(xticks=range(10), yticks=range(10), xlabel="예측", ylabel="정답", title="혼동 행렬 (테스트)")
        for (i, j), v in np.ndenumerate(confusion):
            if v:
                axes[1].text(j, i, v, ha="center", va="center", fontsize=6,
                             color="white" if v > confusion.max() / 2 else "black")
        fig.colorbar(im, ax=axes[1], fraction=0.046)
        wrong = np.flatnonzero(pred != y_test)[:12]
        grid = np.ones((3 * 30, 4 * 30))
        axes[2].set_title("틀린 예시 (정답→예측)")
        for k, idx in enumerate(wrong):
            r, c = divmod(k, 4)
            grid[r * 30 + 1:r * 30 + 29, c * 30 + 1:c * 30 + 29] = 1 - X_test[idx].reshape(28, 28)
            axes[2].text(c * 30 + 2, r * 30 + 6, f"{y_test[idx]}→{pred[idx]}", color="#d62728", fontsize=9)
        axes[2].imshow(grid, cmap="gray", vmin=0, vmax=1)
        axes[2].axis("off")
        fig.tight_layout()
        save_figure(fig, "mnist_training.png")

    save_json({"config": {**vars(args), "lr": lr}, "history": history, "passed": passed,
               "per_class_accuracy": per_class, "confusion": confusion}, "train_mnist.json")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
