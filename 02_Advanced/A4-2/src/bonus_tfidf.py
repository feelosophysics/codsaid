"""보너스 2: 규칙 기반과 TF-IDF 분류의 비교, 학습 데이터 양에 따른 변화.

- 같은 test 1,000건으로 평가한다.
- 학습 데이터는 pool(train에서 dev를 뺀 148,995건)에서 긍정·부정을 같은 수로 뽑는다.
  n=10이면 5+5건이다. 표본에 따라 결과가 크게 흔들리므로 seed를 바꿔 반복하고 평균·표준편차를 본다.
- 특성: 글자 1~3-gram TF-IDF(char_wb). 띄어쓰기가 불규칙하고 활용이 많은 한국어에서 어절 단위보다 안정적이다.
  벡터라이저는 학습 표본으로만 적합한다(어휘·IDF에 test가 섞이면 누수다).
- 혼합형: TF-IDF 옆에 규칙 점수(최종 설정)와 '점수 0(단서 없음 또는 상쇄)' 표시를 특성 2개로 붙인다.
- 규칙은 학습하지 않으므로 n에 상관없이 같은 값이다. 대신 사전을 만들 때 dev 1,000건을 사람이 읽었다.
"""
from __future__ import annotations

import os
import random
import time

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .metrics import classification_report
from .sentiment import FINAL_CONFIG, REQUIRED_CONFIG, SentimentAnalyzer

SIZES = [10, 30, 100, 300, 1000, 3000, 10000]
MISSION_SIZES = (10, 100, 1000)


def seeds_for(n: int) -> int:
    return 10 if n <= 1000 else 3


def balanced_sample(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    by = {0: [r for r in pool if r["label"] == 0], 1: [r for r in pool if r["label"] == 1]}
    out = rng.sample(by[0], n // 2) + rng.sample(by[1], n - n // 2)
    rng.shuffle(out)
    return out


def rule_features(analyzer: SentimentAnalyzer, texts) -> csr_matrix:
    feats = []
    for t in texts:
        r = analyzer.analyze(t, FINAL_CONFIG)
        feats.append([np.tanh(r.score / 3.0), 1.0 if r.decided_by_tie else 0.0])
    return csr_matrix(np.array(feats))


def fit_predict(train: list[dict], test_texts, test_rule=None, train_rule=None):
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), sublinear_tf=True)
    Xtr = vec.fit_transform([r["text"] for r in train])
    Xte = vec.transform(test_texts)
    if train_rule is not None:
        Xtr, Xte = hstack([Xtr, train_rule]).tocsr(), hstack([Xte, test_rule]).tocsr()
    clf = LogisticRegression(C=1.0, solver="liblinear", max_iter=1000)
    clf.fit(Xtr, [r["label"] for r in train])
    return clf.predict(Xte).tolist(), Xtr.shape[1]


def run(splits: dict, sizes=SIZES, log=print) -> dict:
    analyzer = SentimentAnalyzer()
    test = splits["test"]
    texts = [r["text"] for r in test]
    y = [r["label"] for r in test]
    test_rule = rule_features(analyzer, texts)

    rules = {}
    for name, cfg in (("규칙(필수 E)", REQUIRED_CONFIG), ("규칙(최종 I)", FINAL_CONFIG)):
        rep = classification_report(y, analyzer.predict(texts, cfg))
        rules[name] = {"accuracy": rep["accuracy"], "macro_f1": rep["macro_f1"]}

    curve = []
    for n in sizes:
        for model in ("TF-IDF", "TF-IDF+규칙 점수"):
            accs, f1s, dims = [], [], []
            t0 = time.time()
            for seed in range(seeds_for(n)):
                train = balanced_sample(splits["pool"], n, random.Random(1000 * n + seed))
                if model == "TF-IDF":
                    pred, dim = fit_predict(train, texts)
                else:
                    tr_rule = rule_features(analyzer, [r["text"] for r in train])
                    pred, dim = fit_predict(train, texts, test_rule, tr_rule)
                rep = classification_report(y, pred)
                accs.append(rep["accuracy"])
                f1s.append(rep["macro_f1"])
                dims.append(dim)
            row = {"model": model, "n": n, "seeds": len(accs),
                   "acc_mean": float(np.mean(accs)), "acc_std": float(np.std(accs)),
                   "acc_min": float(np.min(accs)), "acc_max": float(np.max(accs)),
                   "f1_mean": float(np.mean(f1s)), "f1_std": float(np.std(f1s)),
                   "features_mean": float(np.mean(dims)), "seconds": round(time.time() - t0, 2)}
            curve.append(row)
            log(f"  {model:14s} n={n:>6} acc={row['acc_mean']:.3f}±{row['acc_std']:.3f} ({row['seconds']}s)")

    # 규칙을 넘어서는 가장 작은 n (평균 기준)
    final_acc = rules["규칙(최종 I)"]["accuracy"]
    crossover = next((r["n"] for r in curve if r["model"] == "TF-IDF" and r["acc_mean"] > final_acc), None)
    return {"rules": rules, "curve": curve, "crossover_n": crossover, "sizes": sizes,
            "threads": os.environ.get("OMP_NUM_THREADS")}


def plot(result: dict, path) -> None:
    """학습 곡선. 범례 + 직접 표기. 색은 dataviz 기준 팔레트의 1~3번 슬롯과 중립 회색."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    for name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False

    colors = {"TF-IDF": "#2a78d6", "TF-IDF+규칙 점수": "#eb6834"}
    rule_colors = {"규칙(최종 I)": "#1baf7a", "규칙(필수 E)": "#8a8984"}
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for model, color in colors.items():
        rows = [r for r in result["curve"] if r["model"] == model]
        xs = [r["n"] for r in rows]
        m = np.array([r["acc_mean"] for r in rows])
        s = np.array([r["acc_std"] for r in rows])
        ax.fill_between(xs, m - s, m + s, color=color, alpha=0.12, linewidth=0)
        ax.plot(xs, m, color=color, linewidth=2, marker="o", markersize=5, label=f"{model} (평균 ± 표준편차)")
        ax.annotate(f"{m[-1]:.3f}", (xs[-1], m[-1]), textcoords="offset points", xytext=(6, 0), va="center",
                    fontsize=8, color="#52514e")
    for name, color in rule_colors.items():
        v = result["rules"][name]["accuracy"]
        ax.axhline(v, color=color, linewidth=2, linestyle="--" if "필수" in name else "-", label=f"{name} {v:.3f}")
    ax.axhline(0.5, color="#c3c2b7", linewidth=1, linestyle=":")
    ax.set_xscale("log")
    ax.set_xticks(result["sizes"])
    ax.set_xticklabels([f"{n:,}" for n in result["sizes"]])
    ax.set_xlabel("학습 리뷰 수 (긍정·부정 반반, 로그 눈금)", color="#52514e")
    ax.set_ylabel("test 1,000건 정확도", color="#52514e")
    ax.set_title("규칙 기반 vs TF-IDF 분류: 학습 데이터 양에 따른 정확도", fontsize=11, color="#0b0b0b", loc="left")
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e", labelsize=8)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
