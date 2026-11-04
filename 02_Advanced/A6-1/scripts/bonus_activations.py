"""보너스 2: Tanh, LeakyReLU, ELU (그리고 기존 ReLU, Sigmoid) 비교.

1. autograd로 구한 도함수를 손으로 유도한 공식과 비교한다.
2. 깊은 망(8층)에서 입력 쪽 층까지 전달되는 기울기 크기를 비교한다.
3. Two Moons 분류를 같은 조건에서 학습해 손실 곡선과 결정 경계를 비교한다.

실행: uv run python scripts/bonus_activations.py
"""
import numpy as np

from _common import REPORTS, Tee, plt, save_figure, save_json
from minigrad import Tensor, nn, no_grad, optim
from minigrad.data import make_moons

ALPHA_LEAKY, ALPHA_ELU = 0.1, 1.0

# 이름: (레이어, 손으로 유도한 도함수, 권장 초기화)
ACTIVATIONS = {
    "ReLU": (nn.ReLU, lambda x: (x > 0).astype(float), "he"),
    "LeakyReLU": (lambda: nn.LeakyReLU(ALPHA_LEAKY), lambda x: np.where(x > 0, 1.0, ALPHA_LEAKY), "he"),
    "ELU": (lambda: nn.ELU(ALPHA_ELU), lambda x: np.where(x > 0, 1.0, ALPHA_ELU * np.exp(x)), "he"),
    "Tanh": (nn.Tanh, lambda x: 1 - np.tanh(x) ** 2, "xavier"),
    "Sigmoid": (nn.Sigmoid, lambda x: (1 / (1 + np.exp(-x))) * (1 - 1 / (1 + np.exp(-x))), "xavier"),
}
COLORS = {"ReLU": "#1f77b4", "LeakyReLU": "#17becf", "ELU": "#2ca02c", "Tanh": "#ff7f0e", "Sigmoid": "#d62728"}


def derivative_check():
    xs = np.linspace(-4, 4, 801)
    xs = xs[np.abs(xs) > 1e-9]          # x=0(꺾이는 점)은 제외
    out = {}
    for name, (make, formula, _) in ACTIVATIONS.items():
        x = Tensor(xs.copy(), requires_grad=True)
        y = make()(x)
        y.sum().backward()               # Σf(xᵢ)를 xᵢ로 미분하면 f'(xᵢ)
        out[name] = {"x": xs, "f": y.data, "autograd": x.grad, "formula": formula(xs),
                     "max_abs_diff": float(np.abs(x.grad - formula(xs)).max())}
    return out


def depth_gradients(depth=8, width=64, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((256, width))
    labels = rng.integers(0, 2, 256)
    out = {}
    for name, (make, _, init) in ACTIVATIONS.items():
        weight_rng = np.random.default_rng(seed + 1)
        layers = []
        for i in range(depth):
            layers += [nn.Linear(width, width, init=init, rng=weight_rng, name=f"L{i}"), make()]
        model = nn.Sequential(*layers, nn.Linear(width, 2, init=init, rng=weight_rng, name="head"))
        nn.cross_entropy(model(Tensor(X)), labels).backward()
        out[name] = [float(np.linalg.norm(model[2 * i].W.grad)) for i in range(depth)]
    return out


def train_moons(seeds=10, epochs=300):
    X, y = make_moons(400, noise=0.2, rng=np.random.default_rng(0))
    X_test, y_test = make_moons(1000, noise=0.2, rng=np.random.default_rng(1))
    out = {}
    for name, (make, _, init) in ACTIVATIONS.items():
        curves, accs, models = [], [], []
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            sizes = [2, 32, 32, 32, 32, 2]
            layers = []
            for i, (a, b) in enumerate(zip(sizes[:-1], sizes[1:])):
                layers.append(nn.Linear(a, b, init=init, rng=rng, name=f"Linear_{i + 1}"))
                if i < len(sizes) - 2:
                    layers.append(make())
            model = nn.Sequential(*layers)
            opt = optim.Adam(model.parameters(), lr=0.01)
            losses = []
            for _ in range(epochs):
                loss = nn.cross_entropy(model(Tensor(X)), y)
                opt.zero_grad()
                loss.backward()
                opt.step()
                losses.append(loss.item())
            with no_grad():
                accs.append(float((model(Tensor(X_test)).data.argmax(1) == y_test).mean()))
            curves.append(losses)
            models.append(model)
        out[name] = {"curves": np.array(curves), "test_acc": np.array(accs), "model": models[0]}
    return X, y, out


def main():
    with Tee(REPORTS / "bonus_activations.log"):
        deriv = derivative_check()
        print("## 1. autograd 도함수 vs 손 유도 공식 (x ∈ [−4, 4], 800점)")
        for name, d in deriv.items():
            print(f"{name:<10} 최대 절대 차이 {d['max_abs_diff']:.1e}")

        grads = depth_gradients()
        print("\n## 2. 8층 x 64 망: 층별 ‖∂L/∂W‖ (ReLU 계열은 He, Tanh·Sigmoid는 Xavier)")
        for name, g in grads.items():
            print(f"{name:<10} L1(입력 쪽) {g[0]:.2e}   L8(출력 쪽) {g[-1]:.2e}   비율 L1/L8 {g[0] / g[-1]:.2e}")

        X, y, moons = train_moons()
        print("\n## 3. Two Moons (학습 400, 테스트 1000, noise 0.2), 2-32x4-2, Adam lr=0.01, 300 epoch, seed 10개")
        for name, r in moons.items():
            c = r["curves"]
            print(f"{name:<10} loss@50 {np.median(c[:, 49]):.4f}  loss@300 {np.median(c[:, -1]):.4f}  "
                  f"테스트 정확도 {r['test_acc'].mean():.2%} ± {r['test_acc'].std():.2%}")

        fig, axes = plt.subplots(2, 5, figsize=(17, 6.5))
        for col, (name, d) in enumerate(deriv.items()):
            ax = axes[0, col]
            ax.plot(d["x"], d["f"], color=COLORS[name], lw=2, label="f(x)")
            ax.plot(d["x"], d["autograd"], color="black", lw=1.2, label="f′ autograd")
            ax.plot(d["x"][::40], d["formula"][::40], "o", ms=3.5, mfc="none", color="#555", label="f′ 공식")
            ax.set(title=f"{name}  (차이 {d['max_abs_diff']:.0e})", ylim=(-1.6, 2.2), xlabel="x")
            ax.axhline(0, color="#999", lw=0.6)
            ax.legend(fontsize=7, loc="upper left")
        ax = axes[1, 0]
        for name, g in grads.items():
            ax.plot(range(1, len(g) + 1), g, "o-", color=COLORS[name], label=name)
        ax.set(yscale="log", xlabel="층 (1=입력 쪽)", ylabel="‖∂L/∂W‖", title="8층 망의 층별 기울기")
        ax.legend(fontsize=7)
        ax = axes[1, 1]
        for name, r in moons.items():
            ax.plot(np.median(r["curves"], axis=0), color=COLORS[name], label=name)
        ax.set(yscale="log", xlabel="Epoch", ylabel="CE (seed 10개 중앙값)", title="Two Moons 학습 곡선")
        ax.legend(fontsize=7)
        gx, gy = np.meshgrid(np.linspace(-1.6, 2.6, 160), np.linspace(-1.2, 1.7, 120))
        grid = Tensor(np.column_stack([gx.ravel(), gy.ravel()]))
        for col, name in enumerate(("ReLU", "ELU", "Sigmoid"), start=2):
            ax = axes[1, col]
            with no_grad():
                prob = moons[name]["model"](grid).softmax().data[:, 1].reshape(gx.shape)
            ax.contourf(gx, gy, prob, levels=20, cmap="RdBu_r", alpha=0.6)
            ax.contour(gx, gy, prob, levels=[0.5], colors="black", linewidths=1)
            ax.scatter(X[:, 0], X[:, 1], c=y, cmap="RdBu_r", s=6, edgecolors="none")
            ax.set(title=f"{name} 결정 경계 (seed 0)", xticks=[], yticks=[])
        fig.tight_layout()
        save_figure(fig, "bonus_activations.png")

    save_json({
        "derivative_max_abs_diff": {k: v["max_abs_diff"] for k, v in deriv.items()},
        "depth_weight_grad_norm": grads,
        "moons": {k: {"loss_epoch50_median": float(np.median(v["curves"][:, 49])),
                      "loss_epoch300_median": float(np.median(v["curves"][:, -1])),
                      "test_acc_mean": float(v["test_acc"].mean()), "test_acc_std": float(v["test_acc"].std())}
                  for k, v in moons.items()},
    }, "bonus_activations.json")


if __name__ == "__main__":
    main()
