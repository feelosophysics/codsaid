"""보너스 1: Inverted Dropout과 L2 정규화(Weight Decay)의 과적합 억제 효과.

과적합이 잘 보이도록 MNIST 학습 데이터에서 1,000장만 뽑아 큰 망(784-256-256-10)을 오래 학습한다.
하이퍼파라미터(p, λ)는 학습에 쓰지 않은 검증 5,000장으로 고르고, 테스트 10,000장은
최종 보고에만 쓴다 (테스트로 고르면 테스트 성능을 낙관적으로 보게 된다).

실행: uv run python scripts/bonus_regularization.py [--epochs 100]
"""
import argparse

import numpy as np

from _common import MNIST_DIR, REPORTS, Tee, plt, save_figure, save_json
from minigrad import Tensor, nn, no_grad, optim
from minigrad.data import DataLoader, load_mnist

N_TRAIN, N_VAL = 1000, 5000
EVAL_EVERY = 5


def build(dropout, rng):
    layers = [nn.Linear(784, 256, init="he", rng=rng, name="Linear_1"), nn.ReLU()]
    if dropout:
        layers.append(nn.Dropout(dropout, rng=rng))
    layers += [nn.Linear(256, 256, init="he", rng=rng, name="Linear_2"), nn.ReLU()]
    if dropout:
        layers.append(nn.Dropout(dropout, rng=rng))
    layers.append(nn.Linear(256, 10, init="he", rng=rng, name="Linear_3"))
    return nn.Sequential(*layers)


def evaluate(model, X, y):
    model.eval()
    with no_grad():
        logits = model(Tensor(X))
        loss = nn.cross_entropy(logits, y).item()
    model.train()
    return loss, float((logits.data.argmax(axis=1) == y).mean())


def run(data, dropout=0.0, weight_decay=0.0, epochs=100, seed=0):
    X_tr, y_tr, X_val, y_val, X_te, y_te = data
    rng = np.random.default_rng(seed)
    model = build(dropout, rng)
    opt = optim.SGD(model.parameters(), lr=0.05, momentum=0.9, weight_decay=weight_decay)
    history = []
    for epoch in range(1, epochs + 1):
        for xb, yb in DataLoader(X_tr, y_tr, 64, rng=rng):
            loss = nn.cross_entropy(model(Tensor(xb)), yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
        if epoch % EVAL_EVERY == 0 or epoch == 1:
            history.append({"epoch": epoch, "train": evaluate(model, X_tr, y_tr),
                            "val": evaluate(model, X_val, y_val), "test": evaluate(model, X_te, y_te)})
    weights = np.concatenate([p.data.ravel() for p in model.parameters() if p.ndim == 2])
    last = history[-1]
    return {"dropout": dropout, "weight_decay": weight_decay, "history": history,
            "train_acc": last["train"][1], "val_acc": last["val"][1], "test_acc": last["test"][1],
            "test_loss": last["test"][0], "gap": last["train"][1] - last["test"][1],
            "weight_l2": float(np.linalg.norm(weights)), "weights_sample": weights[::97]}


def dropout_behaviour():
    """학습 모드에서는 매번 다른 마스크, 평가 모드에서는 항등 함수, 기댓값은 보존."""
    layer = nn.Dropout(0.5, rng=np.random.default_rng(0))
    x = Tensor(np.ones((1000, 100)))
    a, b = layer(x).data, layer(x).data
    layer.eval()
    c = layer(x).data
    return {"train_zero_fraction": float((a == 0).mean()), "train_kept_value": float(a[a > 0][0]),
            "train_mean": float(a.mean()), "two_train_calls_equal": bool(np.array_equal(a, b)),
            "eval_is_identity": bool(np.array_equal(c, x.data))}


def main():
    parser = argparse.ArgumentParser(description="Dropout·L2 정규화 실험")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    with Tee(REPORTS / "bonus_regularization.log"):
        behaviour = dropout_behaviour()
        print("## Inverted Dropout 동작 (p=0.5, 입력 전부 1)")
        print(f"학습 모드: 0이 된 비율 {behaviour['train_zero_fraction']:.3f}, 남은 값 {behaviour['train_kept_value']}"
              f" (=1/(1−p)), 평균 {behaviour['train_mean']:.3f} (기댓값 1 유지)")
        print(f"학습 모드 두 번 호출 결과가 같은가: {behaviour['two_train_calls_equal']} / "
              f"평가 모드가 항등 함수인가: {behaviour['eval_is_identity']}\n")

        X_train, y_train, X_test, y_test = load_mnist(MNIST_DIR)
        order = np.random.default_rng(123).permutation(len(X_train))
        tr, val = order[:N_TRAIN], order[N_TRAIN:N_TRAIN + N_VAL]
        data = (X_train[tr], y_train[tr], X_train[val], y_train[val], X_test, y_test)
        print(f"## 과적합 실험: 학습 {N_TRAIN}장, 검증 {N_VAL}장, 테스트 {len(X_test)}장, "
              f"784-256-256-10, SGD(lr=0.05, momentum=0.9), {args.epochs} epoch")

        def report(tag, r):
            print(f"{tag:<26} train {r['train_acc']:.2%}  val {r['val_acc']:.2%}  test {r['test_acc']:.2%}  "
                  f"gap {r['gap']:+.2%}  test loss {r['test_loss']:.3f}  ‖W‖ {r['weight_l2']:.1f}")

        runs = {"baseline": run(data, epochs=args.epochs)}
        report("baseline", runs["baseline"])
        print("\n검증 정확도로 하이퍼파라미터 선택")
        l2_candidates = {lam: run(data, weight_decay=lam, epochs=args.epochs) for lam in (1e-4, 1e-3, 1e-2)}
        for lam, r in l2_candidates.items():
            report(f"  L2 λ={lam:g}", r)
        drop_candidates = {p: run(data, dropout=p, epochs=args.epochs) for p in (0.2, 0.5)}
        for p, r in drop_candidates.items():
            report(f"  Dropout p={p}", r)
        best_lam = max(l2_candidates, key=lambda k: l2_candidates[k]["val_acc"])
        best_p = max(drop_candidates, key=lambda k: drop_candidates[k]["val_acc"])
        runs["l2"] = l2_candidates[best_lam]
        runs["dropout"] = drop_candidates[best_p]
        runs["both"] = run(data, dropout=best_p, weight_decay=best_lam, epochs=args.epochs)
        print(f"\n선택: λ={best_lam:g}, p={best_p}  (테스트는 아래 최종 비교에서만 사용)")
        for tag in ("baseline", "l2", "dropout", "both"):
            report({"baseline": "기준 (정규화 없음)", "l2": f"L2 λ={best_lam:g}", "dropout": f"Dropout p={best_p}",
                    "both": "Dropout + L2"}[tag], runs[tag])

        labels = {"baseline": "정규화 없음", "l2": f"L2 λ={best_lam:g}", "dropout": f"Dropout p={best_p}",
                  "both": "Dropout+L2"}
        colors = {"baseline": "#d62728", "l2": "#1f77b4", "dropout": "#2ca02c", "both": "#9467bd"}
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
        for tag, r in runs.items():
            epochs = [h["epoch"] for h in r["history"]]
            axes[0].plot(epochs, [h["train"][1] for h in r["history"]], "--", color=colors[tag], alpha=0.7)
            axes[0].plot(epochs, [h["test"][1] for h in r["history"]], "-", color=colors[tag], label=labels[tag])
            axes[1].plot(epochs, [h["test"][0] for h in r["history"]], color=colors[tag], label=labels[tag])
            axes[2].hist(r["weights_sample"], bins=80, range=(-0.4, 0.4), histtype="step", color=colors[tag],
                         label=f"{labels[tag]} (‖W‖={r['weight_l2']:.1f})", density=True)
        axes[0].set(xlabel="Epoch", ylabel="정확도", ylim=(0.8, 1.005), title="정확도: 점선=학습, 실선=테스트")
        axes[1].set(xlabel="Epoch", ylabel="Cross-Entropy", title="테스트 손실 (과적합하면 다시 오른다)")
        axes[2].set(xlabel="가중치 값", ylabel="밀도", title="학습 후 가중치 분포")
        for ax in axes:
            ax.legend(fontsize=8)
        fig.tight_layout()
        save_figure(fig, "bonus_regularization.png")

    for r in [*runs.values(), *l2_candidates.values(), *drop_candidates.values()]:
        r.pop("weights_sample", None)
    save_json({"dropout_behaviour": behaviour, "selected": {"weight_decay": best_lam, "dropout": best_p},
               "runs": runs, "l2_candidates": {str(k): v for k, v in l2_candidates.items()},
               "dropout_candidates": {str(k): v for k, v in drop_candidates.items()}}, "bonus_regularization.json")


if __name__ == "__main__":
    main()
