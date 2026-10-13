"""그래프와 Markdown 보고서 저장.

시스템 한글 폰트에 의존하지 않도록 그래프 레이블은 영어로 쓰고, 해석은 README와 학습 자료에서 한국어로 한다.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import shap

from .config import FEATURES, MIN_STABILITY_ARI

sns.set_theme(style="whitegrid", context="notebook")
CLUSTER_COLORS = ["#c0392b", "#e67e22", "#f1c40f", "#27ae60", "#2980b9", "#8e44ad", "#7f8c8d", "#34495e"]


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _save_current(path):
    """shap 그래프는 현재 Figure에 그린다."""
    _save(plt.gcf(), path)


def k_selection(scan, selection, path):
    ks = [r["k"] for r in scan]
    final = selection["final_k"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    axes[0].plot(ks, [r["inertia"] for r in scan], "o-", color="#34495e")
    axes[0].set_title("Elbow: inertia (no clear bend)")
    axes[0].set_ylabel("Within-cluster sum of squares")
    sil = [r["silhouette_mean"] for r in scan]
    axes[1].errorbar(ks, sil, yerr=[r["silhouette_std"] for r in scan], fmt="o-", capsize=4, color="#2980b9")
    axes[1].axhline(selection["cutoff"], ls="--", color="#c0392b", lw=1,
                    label=f"best - 1 SE = {selection['cutoff']:.4f}")
    axes[1].set_title("Silhouette (mean +/- SD over 5 seeds)")
    axes[1].legend(loc="lower right", fontsize=9)
    axes[2].bar(ks, [r["ari_mean"] for r in scan], color=["#27ae60" if k in selection["stable"] else "#bdc3c7" for k in ks])
    axes[2].axhline(MIN_STABILITY_ARI, ls="--", color="#c0392b", lw=1, label=f"stability floor {MIN_STABILITY_ARI}")
    axes[2].set_title("Stability: mean pairwise ARI across seeds")
    axes[2].set_ylim(0, 1)
    axes[2].legend(loc="upper right", fontsize=9)
    for ax in axes:
        ax.set_xlabel("K")
        ax.set_xticks(ks)
        ax.axvline(final, color="#e67e22", lw=6, alpha=0.18)
    _save(fig, path)


def pca_clusters(coords, labels, pca_info, names, path):
    evr = pca_info["explained_variance_ratio"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.6, 1]})
    # 큰 군집부터 그리고 위험 군집(C0)을 마지막에 그려서 가려지지 않게 한다.
    for c in reversed(range(len(names))):
        m = labels == c
        axes[0].scatter(coords[m, 0], coords[m, 1], s=5, alpha=0.45, color=CLUSTER_COLORS[c], label=names[c])
    handles, legend_labels = axes[0].get_legend_handles_labels()
    axes[0].set_xlabel(f"PC1 ({evr[0]:.1%} of variance)")
    axes[0].set_ylabel(f"PC2 ({evr[1]:.1%} of variance)")
    axes[0].set_title(f"K-Means clusters on PCA 2D (PC1+PC2 = {evr[0] + evr[1]:.1%})")
    axes[0].legend(handles[::-1], legend_labels[::-1], markerscale=4, fontsize=8, loc="upper right", framealpha=0.9)
    pcs = [f"PC{i + 1}" for i in range(len(evr))]
    axes[1].bar(pcs, evr, color="#2980b9", label="each PC")
    axes[1].plot(pcs, np.cumsum(evr), "o-", color="#c0392b", label="cumulative")
    axes[1].axhline(1 / len(evr), ls=":", color="black", lw=1, label="1/6 (no structure)")
    for i, v in enumerate(evr):
        axes[1].text(i, v + 0.01, f"{v:.1%}", ha="center", fontsize=8)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("Explained variance ratio")
    axes[1].legend(fontsize=8, loc="center right")
    _save(fig, path)


def cluster_profiles(profiles, names, path):
    z = np.array([[p["z"][f] for f in FEATURES] for p in profiles])
    raw = [[p["mean"][f] for f in FEATURES] for p in profiles]
    fmt = {"age": "{:.0f}", "annual_income": "{:,.0f}", "spending_score": "{:.0f}", "debt_ratio": "{:.2f}",
           "credit_card_count": "{:.1f}", "overdue_count_6m": "{:.2f}"}
    annot = [[f"{fmt[f].format(v)}\n(z {zz:+.2f})" for f, v, zz in zip(FEATURES, row, zrow)] for row, zrow in zip(raw, z)]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [4, 1]})
    sns.heatmap(z, annot=annot, fmt="", cmap="RdBu_r", center=0, vmin=-2.5, vmax=2.5, ax=axes[0],
                xticklabels=FEATURES, yticklabels=names, cbar_kws={"label": "z-score of cluster mean"},
                annot_kws={"fontsize": 8})
    axes[0].set_title("Cluster profiles: raw mean (z-score vs all customers)")
    axes[0].tick_params(axis="x", rotation=20)
    rates = [p["overdue_rate"] for p in profiles]
    axes[1].barh(range(len(profiles)), rates, color=CLUSTER_COLORS[:len(profiles)])
    axes[1].set_yticks(range(len(profiles)), [f"C{p['cluster']} (n={p['size']:,})" for p in profiles])
    axes[1].invert_yaxis()
    for i, r in enumerate(rates):
        axes[1].text(r, i, f" {r:.1%}", va="center", fontsize=9)
    axes[1].set_xlim(0, max(rates) * 1.35)
    axes[1].set_title("Overdue rate (not used for clustering)")
    _save(fig, path)


def shap_summary(explanation, path):
    plt.figure(figsize=(9, 4.8))
    shap.plots.beeswarm(explanation, max_display=len(FEATURES), show=False)
    plt.title("SHAP summary: impact on predicted overdue probability (Test 2,000)")
    _save_current(path)


def shap_bar(explanation, path):
    plt.figure(figsize=(8, 4))
    shap.plots.bar(explanation, max_display=len(FEATURES), show=False)
    plt.title("Global importance: mean |SHAP value|")
    _save_current(path)


def waterfall(explanation_row, title, path):
    plt.figure(figsize=(9, 5))
    shap.plots.waterfall(explanation_row, max_display=len(FEATURES), show=False)
    plt.title(title)
    _save_current(path)


def force_html(explanation_row, path):
    plot = shap.plots.force(explanation_row.base_values, explanation_row.values,
                            features=explanation_row.data, feature_names=FEATURES, matplotlib=False)
    shap.save_html(str(path), plot)


DEPENDENCE_COLOR = {"annual_income": "overdue_count_6m", "overdue_count_6m": "annual_income",
                    "debt_ratio": "annual_income"}


def dependence(explanation, feature, path, boundary=None):
    fig, ax = plt.subplots(figsize=(8.5, 5))
    color = DEPENDENCE_COLOR.get(feature)
    shap.plots.scatter(explanation[:, feature], color=explanation[:, color] if color else None,
                       ax=ax, show=False, alpha=0.6, dot_size=10)
    ax.axhline(0, color="black", lw=0.8)
    if boundary:
        top, bottom = ax.get_ylim()[1], ax.get_ylim()[0]
        for n, (x, label) in enumerate(boundary):
            ax.axvline(x, ls="--", lw=1, color="#555")
            ax.text(x, top - (top - bottom) * (0.06 + 0.07 * n), f" {label}", fontsize=8, color="#333",
                    bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none", "pad": 1})
    ax.set_title(f"SHAP dependence: {feature}" + (f" (color = {color})" if color else ""))
    _save(fig, path)


def cluster_shap(cluster_rows, names, path):
    m = np.array([[r["mean_shap"][f] for f in FEATURES] for r in cluster_rows])
    fig, ax = plt.subplots(figsize=(12, 4.6))
    lim = np.abs(m).max()
    sns.heatmap(m, annot=True, fmt="+.3f", cmap="RdBu_r", center=0, vmin=-lim, vmax=lim, ax=ax,
                xticklabels=FEATURES, yticklabels=[f"{n}  (mean p={r['mean_proba']:.2f})" for n, r in zip(names, cluster_rows)],
                cbar_kws={"label": "mean SHAP (probability points)"})
    ax.set_title("Why each persona is risky: mean SHAP per cluster (Test customers)")
    ax.tick_params(axis="x", rotation=20)
    _save(fig, path)


def persona_cases(cases, names, path):
    fig, axes = plt.subplots(2, 3, figsize=(16, 7.5))
    lim = max(abs(c["shap"]) for case in cases for c in case["contributions"]) * 1.15
    for ax, case, name in zip(axes.ravel(), cases, names):
        rows = case["contributions"][::-1]
        vals = [r["shap"] for r in rows]
        ax.barh([f"{r['feature']} = {r['value']:g}" for r in rows], vals,
                color=["#c0392b" if v > 0 else "#2980b9" for v in vals])
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlim(-lim, lim)
        ax.set_title(f"{name}\nbase {case['base_value']:.2f} -> p = {case['proba']:.2f} (actual {case['actual_overdue']})",
                     fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Local SHAP for the representative (closest-to-center) Test customer of each persona", y=1.01)
    _save(fig, path)


def clustering_comparison(result, coords, kmeans_labels, path):
    idx = result["sample_index"]
    db = result["dbscan"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    ax = axes[0, 0]
    ax.plot(db["k_distance"], color="#34495e")
    ax.axhline(db["eps"], ls="--", color="#c0392b", label=f"knee eps = {db['eps']:.3f}")
    ax.set_title(f"DBSCAN: sorted {db['min_samples']}-NN distance")
    ax.set_xlabel("customers (sorted)")
    ax.set_ylabel("distance")
    ax.legend()
    panels = [
        (axes[0, 1], kmeans_labels[idx], "K-Means (K=6)"),
        (axes[1, 0], result["hierarchical_labels"]["ward"], "Hierarchical ward (K=6)"),
    ]
    for ax, lab, title in panels:
        for c in sorted(set(lab), reverse=True):
            m = lab == c
            ax.scatter(coords[idx][m, 0], coords[idx][m, 1], s=7, alpha=0.6,
                       color="#bdc3c7" if c < 0 else CLUSTER_COLORS[c % len(CLUSTER_COLORS)],
                       label="noise" if c < 0 else f"{c}")
        ax.set_title(title + " on the same 2,000 sample")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.legend(markerscale=3, fontsize=7, loc="upper right")
    # DBSCAN 군집은 PC1·PC2 평면에서는 보이지 않는다. 대신 연체 횟수별로 어느 군집에 들어갔는지 센다.
    ax = axes[1, 1]
    cross = db["overdue_count_crosstab"]
    levels = sorted({int(lv) for row in cross.values() for lv in row})
    bottom = np.zeros(len(levels))
    for c in sorted(cross, key=int):
        counts = np.array([cross[c].get(str(lv), 0) for lv in levels])
        ax.bar([str(lv) for lv in levels], counts, bottom=bottom,
               color="#bdc3c7" if int(c) < 0 else CLUSTER_COLORS[int(c) % len(CLUSTER_COLORS)],
               label="noise" if int(c) < 0 else f"DBSCAN cluster {c}")
        bottom += counts
    ax.set_yscale("log")
    ax.set_xlabel("overdue_count_6m")
    ax.set_ylabel("customers (log scale)")
    ax.set_title(f"DBSCAN (eps={db['eps']:.2f}): clusters = overdue count levels, noise {db['noise_share']:.1%}")
    ax.legend(fontsize=8)
    _save(fig, path)


def markdown_report(summary) -> str:
    """results/report.md: 실행할 때마다 다시 만드는 수치 요약. 해석은 README에 쓴다."""
    cl, sh = summary["clustering"], summary["shap"]
    lines = ["# A5-2 실행 결과 요약", "", "`python -m src.run_all`이 생성한다. 해석은 README.md에 있다.", "",
             "## 군집 수 탐색", "", "| K | Inertia | Silhouette (평균±SD) | ARI |", "| ---: | ---: | ---: | ---: |"]
    for r in cl["scan"]:
        lines.append(f"| {r['k']} | {r['inertia']:,.0f} | {r['silhouette_mean']:.4f}±{r['silhouette_std']:.4f} | {r['ari_mean']:.3f} |")
    s = cl["selection"]
    lines += ["", f"- Silhouette 최고 K={s['best_silhouette_k']}, 1-표준오차 기준선 {s['cutoff']:.4f}, "
                  f"기준선 이상 {s['within_one_se']}, 안정 {s['stable']} → 최종 K={s['final_k']}",
              f"- PCA 설명 분산: " + ", ".join(f"PC{i + 1} {v:.1%}" for i, v in enumerate(cl["pca"]["explained_variance_ratio"])),
              "", "## 군집 프로파일", "",
              "| 군집 | 페르소나 | 고객 | 비중 | " + " | ".join(FEATURES) + " | 연체율 |",
              "| --- | --- | ---: | ---: | " + " | ".join("---:" for _ in FEATURES) + " | ---: |"]
    for p, n in zip(cl["profiles"], cl["personas"]):
        lines.append(f"| C{p['cluster']} | {n['ko']} | {p['size']:,} | {p['share']:.1%} | "
                     + " | ".join(f"{p['mean'][f]:,.2f}" for f in FEATURES) + f" | {p['overdue_rate']:.1%} |")
    m = sh["model"]
    lines += ["", "## 분류 모델 (RF + class_weight, 원본 6개 변수)", "",
              f"- CV F1 {m['cv']['f1_mean']:.3f}±{m['cv']['f1_std']:.3f}, CV ROC-AUC {m['cv']['roc_auc_mean']:.3f}",
              "- Test (임계값 0.5): " + ", ".join(f"{k} {m['test'][k]:.3f}" for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc")),
              f"- 보류 임계값 {sh['bands']['hold']:.3f}, 거절 임계값 {sh['bands']['reject']:.1f}",
              "", "## Global SHAP", "", "| 변수 | 평균 abs SHAP | 비중 | 방향(순위 상관) |", "| --- | ---: | ---: | ---: |"]
    for r in sh["global"]:
        lines.append(f"| {r['feature']} | {r['mean_abs_shap']:.4f} | {r['share']:.1%} | {r['direction']:+.2f} |")
    lines += ["", f"- 기준값 E[f(X)] = {sh['base_value']:.4f}, 가법성 최대 오차 {sh['additivity_error']:.1e}", "",
              "## Local 사례", ""]
    for key in ("reject_case", "approve_case"):
        c = sh["cases"][key]
        lines.append(f"- {key}: Test 행 {c['row']}, 확률 {c['proba']:.3f}, 실제 {c['actual_overdue']}, "
                     + ", ".join(f"{r['feature']}={r['value']:g} ({r['shap']:+.3f})" for r in c["contributions"]))
    return "\n".join(lines) + "\n"
