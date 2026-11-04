"""가중치 초기화 실험 (Zero vs Random vs He, 선택으로 Xavier).

1. XOR 학습 곡선: 같은 조건에서 seed 20개를 돌려 중앙값·사분위 범위·성공률을 비교한다.
   seed 하나만 보면 운에 따라 결론이 뒤집히기 때문이다.
2. 대칭성: Zero·상수 초기화에서 은닉 뉴런들이 끝까지 같은 값으로 남는지 확인한다.
3. 깊은 망(ReLU·Tanh 10층): 층마다 활성값 표준편차와 가중치 기울기 크기를 재서
   기울기 소실·폭주를 직접 본다.
4. MNIST 1 epoch: 입력이 784차원일 때 초기화 차이가 얼마나 커지는지 본다.
5. 민감도: 망 크기·옵티마이저·학습률을 바꿔도 결론이 유지되는지 확인한다.

실행: uv run python scripts/init_experiment.py [--seeds 20] [--skip-mnist]
결과: figures/init_*.png, reports/init_experiment.json, reports/init_experiment.log
"""
import argparse

import numpy as np

from _common import INIT_COLORS, INIT_LABELS, MNIST_DIR, REPORTS, Tee, plt, save_figure, save_json
from minigrad import Tensor, nn, no_grad, optim
from minigrad.data import DataLoader, load_mnist, xor_dataset
from train_xor import HIDDEN, LR, build_model, first_epoch_below, train_xor

REQUIRED = ("zero", "random", "he")
ALL = REQUIRED + ("xavier",)
EPOCHS = 100


# ---------------------------------------------------------------------------- 1. XOR 곡선
def xor_curves(n_seeds):
    curves, stats = {}, {}
    for init in ALL:
        runs = [train_xor(init, seed, EPOCHS) for seed in range(n_seeds)]
        losses = np.array([r[0] for r in runs])
        accs = np.array([r[1] for r in runs])
        hits = [first_epoch_below(l) for l in losses]
        reached = [h for h in hits if h is not None]
        curves[init] = losses
        stats[init] = {
            "loss_epoch0_median": float(np.median(losses[:, 0])),
            "loss_epoch5_median": float(np.median(losses[:, 5])),
            "loss_epoch50_median": float(np.median(losses[:, 50])),
            "loss_epoch100_median": float(np.median(losses[:, 100])),
            "loss_epoch0_max": float(losses[:, 0].max()),
            "success_rate": len(reached) / n_seeds,         # 100 epoch 안에 loss < 0.1
            "final_acc_100_rate": float((accs[:, -1] == 1.0).mean()),
            "epochs_to_0.1_median": float(np.median(reached)) if reached else None,
            "failed_seeds": [s for s, h in enumerate(hits) if h is None],
            "seed0_loss_epoch5": float(losses[0, 5]),
            "seed0_loss_epoch50": float(losses[0, 50]),
            "seed0_loss_epoch100": float(losses[0, 100]),
        }
    zero = curves["zero"]
    stats["zero"]["max_change_until_50"] = float(np.abs(zero[:, :51] - zero[:, :1]).max())
    return curves, stats


def plot_xor(curves, stats, n_seeds):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.6, 1]})
    epochs = np.arange(EPOCHS + 1)
    ax = axes[0]
    for init in ALL:
        losses = curves[init]
        median = np.median(losses, axis=0)
        low, high = np.percentile(losses, [25, 75], axis=0)
        style = "--" if init == "xavier" else "-"
        ax.plot(epochs, median, style, color=INIT_COLORS[init], lw=2,
                label=f"{INIT_LABELS[init]} (성공 {stats[init]['success_rate']:.0%})")
        ax.fill_between(epochs, low, high, color=INIT_COLORS[init], alpha=0.15)
    ax.axhline(0.1, color="black", lw=0.8, ls=":")
    ax.text(EPOCHS, 0.11, "Loss 0.1", ha="right", va="bottom", fontsize=8)
    ax.set(xlim=(0, EPOCHS), ylim=(0, 1.0), xlabel="Epoch", ylabel="BCE Loss",
           title=f"XOR 2-{HIDDEN[0]}-{HIDDEN[1]}-1, Adam lr={LR}: seed {n_seeds}개 중앙값과 25–75% 범위")
    ax.legend(loc="upper right", fontsize=9)

    ax = axes[1]
    for seed_curve in curves["random"]:
        ax.plot(epochs, seed_curve, color=INIT_COLORS["random"], alpha=0.35, lw=1)
    for seed_curve in curves["he"]:
        ax.plot(epochs, seed_curve, color=INIT_COLORS["he"], alpha=0.35, lw=1)
    ax.plot([], [], color=INIT_COLORS["random"], label="Random N(0,1)")
    ax.plot([], [], color=INIT_COLORS["he"], label="He")
    ax.set(yscale="log", xlim=(0, EPOCHS), xlabel="Epoch", ylabel="BCE Loss (log)",
           title="seed별 곡선: Random은 출발점과 결과가 들쭉날쭉")
    ax.legend(fontsize=9)
    fig.tight_layout()
    save_figure(fig, "init_comparison.png")


def loss_control(n_seeds):
    """대조 실험: 출력 Sigmoid+BCE 대신 안정형 BCE(로짓 입력)로 같은 seed를 다시 학습한다.

    분리형에서는 σ(z)가 0·1로 포화되면 clip 때문에 기울기가 0이 된다. 실패 원인이 초기화 자체인지,
    포화된 출력을 손실이 처리하는 방식인지 가르기 위한 실험이다.
    """
    stats = {}
    for init in ALL:
        losses = np.array([train_xor(init, seed, EPOCHS, loss="logits")[0] for seed in range(n_seeds)])
        hits = [first_epoch_below(l) for l in losses]
        reached = [h for h in hits if h is not None]
        stats[init] = {"loss_epoch0_median": float(np.median(losses[:, 0])),
                       "loss_epoch5_median": float(np.median(losses[:, 5])),
                       "loss_epoch50_median": float(np.median(losses[:, 50])),
                       "success_rate": len(reached) / n_seeds,
                       "epochs_to_0.1_median": float(np.median(reached)) if reached else None,
                       "failed_seeds": [s for s, h in enumerate(hits) if h is None]}
    return stats


def saturation_diagnosis(seeds):
    """Random 초기화 seed의 초기 출력 로짓 크기와 최종 결과."""
    X, y = xor_dataset()
    rows = {}
    for seed in seeds:
        with no_grad():
            logits = build_model("random", seed, sigmoid_output=False)(Tensor(X)).data.ravel()
        losses, accs, _ = train_xor("random", seed, EPOCHS)
        rows[seed] = {"initial_logits": logits, "final_loss": float(losses[-1]), "final_acc": float(accs[-1])}
    return rows


# ---------------------------------------------------------------------------- 2. 대칭성
def symmetry_check():
    """은닉층 1의 뉴런(가중치 열)들이 서로 다른 값을 갖게 되는지 본다.

    distinct = W1 열들 사이의 최대 차이. 0이면 모든 뉴런이 같은 일을 하고 있다는 뜻이다.
    """
    X, y = xor_dataset()
    X = Tensor(X)
    result = {}
    for label, fill in (("zero", 0.0), ("constant_0.5", 0.5), ("he", None)):
        model = build_model("he", seed=0)
        if fill is not None:
            for p in model.parameters():
                p.data[...] = fill if p.ndim == 2 else 0.0
        opt = optim.Adam(model.parameters(), lr=LR)
        losses = []
        for _ in range(50):
            loss = nn.binary_cross_entropy(model(X), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        W1 = model[0].W.data
        distinct = float(np.abs(W1 - W1[:, :1]).max())
        result[label] = {"loss_first": losses[0], "loss_after_50": losses[-1], "W1_column_spread": distinct}
    return result


# ---------------------------------------------------------------------------- 3. 깊은 망
def deep_statistics(depth=10, width=256, batch=512, seed=0):
    """depth개 은닉층의 활성값 표준편차(순전파)와 가중치 기울기 노름(역전파)."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((batch, width))
    labels = rng.integers(0, 10, batch)
    stats = {}
    for act_name, act in (("relu", nn.ReLU), ("tanh", nn.Tanh)):
        for init in ALL:
            weight_rng = np.random.default_rng(seed + 1)  # 초기화 방법끼리 같은 난수열을 쓴다
            layers = [nn.Linear(width, width, init=init, rng=weight_rng, name=f"L{i}") for i in range(depth)]
            head = nn.Linear(width, 10, init=init, rng=weight_rng, name="head")
            h, acts = Tensor(X), []
            for layer in layers:
                h = act()(layer(h))
                acts.append(float(h.data.std()))
            loss = nn.cross_entropy(head(h), labels)
            loss.backward()
            grads = [float(np.linalg.norm(layer.W.grad)) for layer in layers]
            stats[f"{act_name}/{init}"] = {"activation_std": acts, "weight_grad_norm": grads,
                                           "loss": float(loss.item())}
    return stats


def plot_deep(stats, depth=10):
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    layers = np.arange(1, depth + 1)
    for row, act in enumerate(("relu", "tanh")):
        for col, key in enumerate(("activation_std", "weight_grad_norm")):
            ax = axes[row, col]
            for init in ALL:
                if init == "zero":  # 모든 값이 정확히 0이라 로그 축에 그릴 수 없다
                    continue
                ax.plot(layers, stats[f"{act}/{init}"][key], marker="o", color=INIT_COLORS[init],
                        label=INIT_LABELS[init], ls="--" if init == "xavier" else "-")
            ax.plot([], [], color=INIT_COLORS["zero"], label="Zero: 모든 층 정확히 0 (로그 축에 없음)")
            ax.set(yscale="log", xlabel="은닉층 번호 (1 = 입력 쪽)", xticks=layers,
                   ylabel="활성값 표준편차" if col == 0 else "‖∂L/∂W‖",
                   title=f"{act.upper()} 10층: " + ("순전파 활성값" if col == 0 else "역전파 기울기 크기"))
            ax.legend(fontsize=8)
    fig.tight_layout()
    save_figure(fig, "init_deep_stats.png")


# ---------------------------------------------------------------------------- 4. MNIST
def mnist_curves(seed=0, batch_size=64, lr=0.1):
    X_train, y_train, X_test, y_test = load_mnist(MNIST_DIR)
    result = {}
    for init in ALL:
        rng = np.random.default_rng(seed)
        model = nn.mlp([784, 128, 10], init=init, rng=rng)
        opt = optim.SGD(model.parameters(), lr=lr)
        losses = []
        for xb, yb in DataLoader(X_train, y_train, batch_size, rng=rng):
            loss = nn.cross_entropy(model(Tensor(xb)), yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        with no_grad():
            acc = float((model(Tensor(X_test)).data.argmax(axis=1) == y_test).mean())
        result[init] = {"step_losses": losses, "first_loss": losses[0], "test_accuracy": acc}
    return result


def plot_mnist(result):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    window = 20
    for init in ALL:
        losses = np.array(result[init]["step_losses"])
        smooth = np.convolve(losses, np.ones(window) / window, mode="valid")
        ax.plot(np.arange(window, len(losses) + 1), smooth, color=INIT_COLORS[init],
                ls="--" if init == "xavier" else "-",
                label=f"{INIT_LABELS[init]}: 시작 {losses[0]:.1f}, 테스트 {result[init]['test_accuracy']:.1%}")
    ax.set(yscale="log", xlabel="미니배치 스텝 (1 epoch = 938)", ylabel="Cross-Entropy (20스텝 이동평균, log)",
           title="MNIST 784-128-10, SGD lr=0.1, 1 epoch")
    ax.legend(fontsize=9)
    fig.tight_layout()
    save_figure(fig, "init_mnist.png")


# ---------------------------------------------------------------------------- 5. 민감도
def sensitivity(n_seeds):
    settings = [((8,), "sgd", 0.5), ((16, 16), "sgd", 0.5), ((32, 32), "sgd", 0.1), ((32, 32), "sgd", 0.5),
                ((16, 16), "adam", 0.01), ((32, 32), "adam", 0.01), ((32, 32), "adam", 0.05)]
    rows = []
    for hidden, opt_name, lr in settings:
        row = {"hidden": list(hidden), "optimizer": opt_name, "lr": lr}
        for init in ALL:
            losses = np.array([train_xor(init, s, EPOCHS, hidden=hidden, optimizer=opt_name, lr=lr)[0]
                               for s in range(n_seeds)])
            row[init] = {"success_rate": float((losses.min(axis=1) < 0.1).mean()),
                         "loss_epoch5_median": float(np.median(losses[:, 5])),
                         "loss_epoch100_median": float(np.median(losses[:, 100]))}
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description="가중치 초기화 실험")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--skip-mnist", action="store_true")
    args = parser.parse_args()

    with Tee(REPORTS / "init_experiment.log"):
        print(f"## 1. XOR, seed {args.seeds}개, 2-{HIDDEN[0]}-{HIDDEN[1]}-1 ReLU, Adam lr={LR}, {EPOCHS} epoch")
        curves, xor_stats = xor_curves(args.seeds)
        print(f"{'Init':<14}{'E0':>8}{'E5':>8}{'E50':>8}{'E100':>8}{'성공률':>8}{'0.1 도달':>9}  실패 seed")
        for init in ALL:
            s = xor_stats[init]
            reach = "-" if s["epochs_to_0.1_median"] is None else f"{s['epochs_to_0.1_median']:.0f}"
            print(f"{INIT_LABELS[init]:<14}{s['loss_epoch0_median']:>8.4f}{s['loss_epoch5_median']:>8.4f}"
                  f"{s['loss_epoch50_median']:>8.4f}{s['loss_epoch100_median']:>8.4f}"
                  f"{s['success_rate']:>8.0%}{reach:>9}  {s['failed_seeds']}")
        print(f"Zero: epoch 0–50 사이 loss 최대 변화량 {xor_stats['zero']['max_change_until_50']:.2e}")
        plot_xor(curves, xor_stats, args.seeds)

        failed = xor_stats["random"]["failed_seeds"]
        diagnosis = saturation_diagnosis([0] + failed)
        print("\n## 1-1. Random 실패 seed 진단: 초기 출력 로짓과 최종 결과 (seed 0은 성공 예)")
        for seed, d in diagnosis.items():
            print(f"seed {seed:<3} 초기 로짓 {np.array2string(d['initial_logits'], precision=1):<28} "
                  f"최종 loss {d['final_loss']:.3f}  정확도 {d['final_acc']:.0%}")
        print("최종 loss 6.908 = −log(1e-12)/4: 샘플 하나가 clip 경계에 붙어 기울기 0으로 멈춘 상태")

        control = loss_control(args.seeds)
        print("\n## 1-2. 대조: 안정형 BCE(로짓 입력)로 같은 seed 재학습")
        for init in ALL:
            c = control[init]
            reach = "-" if c["epochs_to_0.1_median"] is None else f"{c['epochs_to_0.1_median']:.0f}"
            print(f"{INIT_LABELS[init]:<14} E0 {c['loss_epoch0_median']:.4f}  E5 {c['loss_epoch5_median']:.4f}  "
                  f"E50 {c['loss_epoch50_median']:.4f}  성공률 {c['success_rate']:.0%}  0.1 도달 {reach}  "
                  f"실패 seed {c['failed_seeds']}")

        print("\n## 2. 대칭성 (W1 열 사이 최대 차이, 0이면 모든 은닉 뉴런이 같다)")
        symmetry = symmetry_check()
        for label, s in symmetry.items():
            print(f"{label:<14} loss {s['loss_first']:.4f} → {s['loss_after_50']:.4f}   "
                  f"W1 열 차이 {s['W1_column_spread']:.2e}")

        print("\n## 3. 깊은 망 10층 x 256, 입력 N(0,1) 512개")
        deep = deep_statistics()
        for key, s in deep.items():
            acts, grads = s["activation_std"], s["weight_grad_norm"]
            print(f"{key:<14} 활성 std L1 {acts[0]:.2e} → L10 {acts[-1]:.2e}   "
                  f"‖∂L/∂W‖ L1 {grads[0]:.2e} / L10 {grads[-1]:.2e}   loss {s['loss']:.3g}")
        plot_deep(deep)

        mnist = None
        if not args.skip_mnist:
            print("\n## 4. MNIST 784-128-10 ReLU, SGD lr=0.1, batch 64, 1 epoch")
            mnist = mnist_curves()
            for init in ALL:
                m = mnist[init]
                print(f"{INIT_LABELS[init]:<14} 첫 스텝 loss {m['first_loss']:8.3f}   "
                      f"마지막 loss {m['step_losses'][-1]:.3f}   테스트 정확도 {m['test_accuracy']:.2%}")
            plot_mnist(mnist)

        print(f"\n## 5. 민감도 (seed {args.seeds}개, 100 epoch 안 loss < 0.1 성공률)")
        sens = sensitivity(args.seeds)
        print(f"{'hidden':<10}{'opt':<6}{'lr':<6}" + "".join(f"{INIT_LABELS[i]:>16}" for i in ALL))
        for row in sens:
            cells = "".join(f"{row[i]['success_rate']:>10.0%} ({row[i]['loss_epoch5_median']:.2f})" for i in ALL)
            print(f"{str(row['hidden']):<10}{row['optimizer']:<6}{row['lr']:<6}{cells}")
        print("괄호 안은 epoch 5 loss 중앙값")

    if mnist is not None:
        for init in ALL:
            mnist[init]["step_losses"] = mnist[init]["step_losses"][::10]  # JSON 크기를 줄인다
    save_json({
        "xor": {"hidden": list(HIDDEN), "optimizer": "adam", "lr": LR, "epochs": EPOCHS, "seeds": args.seeds,
                "stats": xor_stats, "median_curves": {k: np.median(v, axis=0) for k, v in curves.items()}},
        "random_failure_diagnosis": diagnosis, "logits_bce_control": control,
        "symmetry": symmetry, "deep": deep, "mnist": mnist, "sensitivity": sens,
    }, "init_experiment.json")


if __name__ == "__main__":
    main()
