"""보너스 그림: 하이퍼파라미터 탐색 과정·중요도, Attention 비교·가중치.

실행: uv run python scripts/bonus_figures.py
"""
import numpy as np

from perfdiag.common import RESULTS, load_json, utf8_console
from perfdiag.plots import plt, save
from perfdiag.timeseries.data import SERIES

STAGE_COLOR = {"coarse": "#90b4e0", "fine": "#d62728"}
LOG_PARAMS = {"lr", "hidden", "weight_decay"}


def hparam(data):
    trials = data["trials"]
    names = list(data["space"])
    fig = plt.figure(figsize=(16, 8.4))
    grid = fig.add_gridspec(2, 4)
    y = np.array([t["validation_skill"] for t in trials])
    for k, name in enumerate(names):
        ax = fig.add_subplot(grid[k // 3, k % 3])
        x = np.array([t["params"][name] for t in trials], dtype=float)
        for stage in ("coarse", "fine"):
            mask = np.array([t["stage"] == stage for t in trials])
            ax.scatter(x[mask], y[mask], c=STAGE_COLOR[stage], s=36, edgecolor="white", lw=0.5,
                       label="1단계 Coarse" if stage == "coarse" else "2단계 Fine")
        best = data["best"]["params"][name]
        ax.axvline(best, color="#333", ls=":", lw=1)
        if name in LOG_PARAMS:
            ax.set_xscale("log")
        if name == "hidden":   # 로그 축의 보조 눈금 글자가 겹치지 않게 정수 눈금만 쓴다
            ax.set_xticks([8, 16, 32, 64, 96], ["8", "16", "32", "64", "96"])
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
        imp = data["importance"][name]
        ax.set_title(f"{name}  (η²={imp['eta_squared']:.2f}, ρ={imp['spearman']:+.2f})", fontsize=10)
        ax.set_ylabel("Validation skill (MSE/Naive)")
    fig.axes[0].legend(fontsize=8)
    ax = fig.add_subplot(grid[0, 3])
    order = sorted(names, key=lambda n: data["importance"][n]["eta_squared"])
    ax.barh(order, [data["importance"][n]["eta_squared"] for n in order], color="#2b6cb0")
    ax.set_title("하이퍼파라미터 중요도 (η²)")
    ax = fig.add_subplot(grid[1, 3])
    best_so_far = np.minimum.accumulate(y)
    ax.scatter(range(1, len(y) + 1), y, c=[STAGE_COLOR[t["stage"]] for t in trials], s=20)
    ax.plot(range(1, len(y) + 1), best_so_far, color="#333", label="지금까지 최저")
    n_coarse = sum(t["stage"] == "coarse" for t in trials)
    ax.axvline(n_coarse + 0.5, color="#999", ls="--")
    ax.set_xlabel("trial")
    ax.set_title("탐색 진행: Coarse → Fine")
    ax.legend(fontsize=8)
    fig.suptitle("보너스 1 — 서울 기온 LSTM(변화량) Random Search → Coarse-to-Fine (점선: 최적 trial)", fontsize=12)
    fig.tight_layout()
    return save(fig, "bonus_hparam_search.png")


def attention(data):
    fig, axes = plt.subplots(2, 2, figsize=(15, 8.4))
    for row, name in enumerate(SERIES):
        res = data[name]
        ax = axes[row, 0]
        keys = [k for k in res]
        short = {"lstm": "LSTM", "lstm_attention": "LSTM\n+Attention", "transformer": "Transformer"}
        labels = [f"{short[k.rsplit('_', 1)[0]]}\n창 {res[k]['window']}" for k in keys]
        means = [np.mean(res[k]["test_skill"]) for k in keys]
        stds = [np.std(res[k]["test_skill"]) for k in keys]
        colors = ["#90b4e0" if k.startswith("lstm_") and "attention" not in k else
                  "#2b6cb0" if "attention" in k else "#d69e2e" for k in keys]
        ax.bar(range(len(keys)), means, yerr=stds, color=colors, capsize=3)
        ax.axhline(1.0, color="#333", ls="--", lw=1, label="Naive = 1")
        ax.set_xticks(range(len(keys)), labels, fontsize=8)
        lo = min(m - s for m, s in zip(means, stds))
        ax.set_ylim(max(0, lo - 0.05), max(1.02, max(means) + 0.05))
        ax.set_ylabel("Test skill (MSE/Naive, 낮을수록 좋음)")
        title = "AAPL" if name == "aapl" else "서울 기온"
        ax.set_title(f"{title} — Test skill, seed 3개 평균±표준편차")
        ax.legend(fontsize=8)
        ax = axes[row, 1]
        for window, color in ((30, "#90b4e0"), (90, "#2b6cb0")):
            weights = np.asarray(res[f"lstm_attention_{window}"]["attention_mean"])
            lags = np.arange(window, 0, -1)
            ax.plot(lags, weights, color=color, label=f"창 {window}일")
            ax.axhline(1 / window, color=color, ls=":", lw=0.8)
        ax.invert_xaxis()
        ax.set_xlabel("몇 일 전 (lag) — 오른쪽 끝이 예측 직전 날")
        ax.set_ylabel("평균 Attention 가중치")
        ax.set_title(f"{title} — LSTM+Attention의 평균 가중치 (점선: 균등 1/창)")
        ax.legend(fontsize=8)
    fig.tight_layout()
    return save(fig, "bonus_attention.png")


def main():
    utf8_console()
    if (RESULTS / "bonus_hparam_search.json").exists():
        print(f"저장: {hparam(load_json(RESULTS / 'bonus_hparam_search.json')).name}")
    if (RESULTS / "bonus_attention.json").exists():
        print(f"저장: {attention(load_json(RESULTS / 'bonus_attention.json')).name}")


if __name__ == "__main__":
    main()
