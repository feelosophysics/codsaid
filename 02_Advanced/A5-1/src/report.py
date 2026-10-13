"""그래프와 Markdown 보고서 저장.

시스템 한글 폰트에 의존하지 않도록 그래프 레이블은 영어로 쓰고, 해석은 README와 학습 자료에서 한국어로 한다.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import precision_recall_curve, roc_curve

from .config import ALPHAS, FEATURES

sns.set_theme(style="whitegrid", context="notebook")

SIGNAL_COLORS = {"annual_income": "#e6550d", "debt_ratio": "#de2d26", "overdue_count_6m": "#756bb1"}
MODEL_COLORS = {
    "Rule baseline": "#7f7f7f",
    "LogReg (no handling)": "#9ecae1",
    "LogReg + class_weight": "#3182bd",
    "LogReg + SMOTE": "#08519c",
    "RF + class_weight": "#74c476",
    "RF + SMOTE": "#238b45",
    "XGB + scale_pos_weight": "#e6550d",
}


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def data_overview(df, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    counts = df["is_overdue"].value_counts().sort_index()
    axes[0].bar(["Normal (0)", "Overdue (1)"], counts.values, color=["#9ecae1", "#de2d26"])
    for i, v in enumerate(counts.values):
        axes[0].text(i, v, f"{v:,}\n({v / len(df):.1%})", ha="center", va="bottom")
    axes[0].set_title("Class balance of is_overdue")
    axes[0].set_ylabel("Customers")
    axes[0].set_ylim(0, counts.max() * 1.2)
    sns.histplot(
        df, x="credit_score", hue="is_overdue", bins=50, multiple="stack",
        palette={0: "#9ecae1", 1: "#de2d26"}, ax=axes[1],
    )
    q15 = df["credit_score"].quantile(0.15)
    axes[1].axvline(q15, color="black", ls="--", lw=1)
    axes[1].text(q15, axes[1].get_ylim()[1] * 0.92, f" 15th pct = {q15:.0f}", fontsize=9)
    axes[1].set_title("Credit score by overdue label")
    axes[1].set_xlabel("credit_score")
    _save(fig, path)


def _plot_paths(ax, alphas, rows, marker=None):
    """신호 변수 3개는 색으로, 나머지(노이즈·파생·연령대)는 회색 한 묶음으로 그린다."""
    noise_labeled = False
    for f in rows[0]["coefficients"]:
        values = [r["coefficients"][f] for r in rows]
        if f in SIGNAL_COLORS:
            ax.plot(alphas, values, marker=marker, lw=2.2, color=SIGNAL_COLORS[f], label=f)
        else:
            ax.plot(alphas, values, marker=marker, lw=1, color="#9e9e9e", alpha=0.7,
                    label=None if noise_labeled else "other 9 (noise / derived)")
            noise_labeled = True


def coefficient_paths(paths, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, (name, rows) in zip(axes, paths.items()):
        _plot_paths(ax, ALPHAS, rows, marker="o")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xscale("log")
        ax.set_xticks(ALPHAS, [str(a) for a in ALPHAS])
        ax.set_xlabel("alpha (log scale)")
        ax.set_title(f"{name}: standardized coefficients")
    axes[0].set_ylabel("Coefficient (score points per 1 SD)")
    axes[1].legend(fontsize=8, loc="lower left")
    _save(fig, path)


def ridge_extended(ext, path):
    rows = ext["rows"]
    alphas = [r["alpha"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    _plot_paths(ax, alphas, rows)
    ax.axvspan(min(ALPHAS), max(ALPHAS), color="#fdd0a2", alpha=0.4, label="required range 0.01-100")
    ax.axvline(ext["n_train"], color="black", ls=":", lw=1)
    ax.text(ext["n_train"], ax.get_ylim()[0] * 0.9, f" alpha = n_train ({ext['n_train']:,})", fontsize=9)
    ax.set_xscale("log")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("alpha (log scale)")
    ax.set_ylabel("Coefficient")
    ax.set_title("Ridge needs a much larger alpha to shrink (penalty vs. sum of squared errors)")
    ax.legend(fontsize=8)
    _save(fig, path)


def regression_fit(y_true, y_pred, label, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(y_true, y_pred, s=6, alpha=0.4)
    lo, hi = float(min(y_true.min(), y_pred.min())), float(max(y_true.max(), y_pred.max()))
    axes[0].plot([lo, hi], [lo, hi], color="black", lw=1)
    axes[0].set_xlabel("Actual credit_score")
    axes[0].set_ylabel("Predicted credit_score")
    axes[0].set_title(f"{label}: predicted vs actual (test)")
    resid = np.asarray(y_true) - np.asarray(y_pred)
    sns.histplot(resid, bins=50, ax=axes[1], color="#3182bd")
    axes[1].set_title(f"Residuals (std = {resid.std():.1f}; generator noise std = 30)")
    axes[1].set_xlabel("Actual - predicted")
    _save(fig, path)


def confusion_matrices(models, names, path):
    fig, axes = plt.subplots(1, len(names), figsize=(4.6 * len(names), 4))
    for ax, name in zip(np.atleast_1d(axes), names):
        c = models[name]["test"]["confusion"]
        mat = np.array([[c["tn"], c["fp"]], [c["fn"], c["tp"]]])
        sns.heatmap(mat, annot=True, fmt=",d", cmap="Blues", cbar=False, ax=ax,
                    xticklabels=["Pred 0", "Pred 1"], yticklabels=["True 0", "True 1"])
        m = models[name]["test"]
        ax.set_title(f"{name}\nRecall {m['recall']:.2f} / Precision {m['precision']:.2f}", fontsize=10)
    _save(fig, path)


def roc_pr_curves(models, y_test, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for name, m in models.items():
        color = MODEL_COLORS.get(name)
        fpr, tpr, _ = roc_curve(y_test, m["proba"])
        axes[0].plot(fpr, tpr, color=color, label=f"{name} (AUC {m['test']['roc_auc']:.3f})")
        prec, rec, _ = precision_recall_curve(y_test, m["proba"])
        axes[1].plot(rec, prec, color=color, label=f"{name} (AP {m['test']['pr_auc']:.3f})")
    axes[0].plot([0, 1], [0, 1], color="black", ls="--", lw=0.8)
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate (recall)", title="ROC curve (test)")
    base = float(np.mean(y_test))
    axes[1].axhline(base, color="black", ls="--", lw=0.8, label=f"Random ({base:.2f})")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-Recall curve (test)")
    for ax in axes:
        ax.legend(fontsize=7.5, loc="lower right" if ax is axes[0] else "upper right")
    _save(fig, path)


def model_comparison(models, path):
    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    names = list(models)
    x = np.arange(len(metrics))
    width = 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(12, 4.8))
    for i, name in enumerate(names):
        ax.bar(x + i * width - 0.4 + width / 2, [models[name]["test"][k] for k in metrics],
               width, label=name, color=MODEL_COLORS.get(name))
    ax.set_xticks(x, ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"])
    ax.set_ylim(0, 1.05)
    ax.set_title("Test metrics: rule baseline vs ML models (threshold 0.5)")
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    _save(fig, path)


def feature_importance(tree_imp, perm_by_model, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    names = list(tree_imp)[::-1]
    axes[0].barh(names, [tree_imp[n] for n in names], color="#238b45")
    axes[0].set_title("Random Forest impurity importance\n(after preprocessing)")
    axes[0].set_xlabel("Mean decrease in impurity")
    order = list(next(iter(perm_by_model.values())))[::-1]
    y = np.arange(len(order))
    h = 0.8 / len(perm_by_model)
    for i, (model, perm) in enumerate(perm_by_model.items()):
        axes[1].barh(y + i * h - 0.4 + h / 2, [perm[f]["mean"] for f in order], h,
                     xerr=[perm[f]["std"] for f in order], label=model, color=MODEL_COLORS.get(model))
    axes[1].set_yticks(y, order)
    axes[1].set_title("Permutation importance on test\n(drop in PR-AUC, original 6 features)")
    axes[1].set_xlabel("PR-AUC decrease")
    axes[1].legend(fontsize=8)
    _save(fig, path)


def learning_curves(curves, path):
    fig, axes = plt.subplots(1, len(curves), figsize=(5 * len(curves), 4.2))
    for ax, (name, c) in zip(np.atleast_1d(axes), curves.items()):
        s = np.array(c["train_sizes"])
        for key, label, color in [("train", "Train", "#e6550d"), ("valid", "Validation (CV)", "#3182bd")]:
            mean, std = np.array(c[f"{key}_mean"]), np.array(c[f"{key}_std"])
            ax.plot(s, mean, marker="o", color=color, label=label)
            ax.fill_between(s, mean - std, mean + std, color=color, alpha=0.15)
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("Training samples")
        ax.set_ylabel(c["metric"].upper())
        ax.legend(fontsize=8)
    _save(fig, path)


def decision_policy(proba, y_test, policy, path):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    y = np.asarray(y_test)
    bins = np.linspace(0, 1, 41)
    ax.hist(proba[y == 0], bins=bins, alpha=0.6, label="True normal", color="#9ecae1")
    ax.hist(proba[y == 1], bins=bins, alpha=0.7, label="True overdue", color="#de2d26")
    ax.set_yscale("log")
    for key, label, color in [("hold_threshold", "hold", "#fd8d3c"), ("reject_threshold", "reject", "#a50f15")]:
        t = policy[key]
        ax.axvline(t, color=color, ls="--", lw=1.5)
        ax.text(t, ax.get_ylim()[1] * 0.5, f" {label} >= {t:.2f}", color=color, fontsize=9)
    b = policy["test_bands"]
    ax.set_title(
        "Approve / hold / reject on test: "
        + ", ".join(f"{k} {v['share']:.0%} (overdue {v['overdue_rate']:.1%})" for k, v in b.items()),
        fontsize=10,
    )
    ax.set_xlabel("Predicted overdue probability")
    ax.set_ylabel("Customers (log)")
    ax.legend(fontsize=8, loc="upper center")
    _save(fig, path)


def _table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def markdown_report(summary) -> str:
    reg = summary["regression"]["comparison"]
    clf = summary["classification"]["models"]
    sel = summary["classification"]["selection"]
    pol = summary["classification"]["policy"]
    ora = summary["classification"]["oracle_ceiling"]
    lines = [
        "# A5-1 실행 결과",
        "",
        "`python -m src.run_all`이 생성한다. 모든 수치는 seed 42 합성 데이터, Test 2,000건 기준이다.",
        "",
        "## 회귀: 신용 점수",
        "",
        _table(
            ["모델", "선택 Alpha", "RMSE", "MAE", "R²"],
            [
                [k, "-" if v["alpha"] is None else v["alpha"], f"{v['test']['rmse']:.2f}",
                 f"{v['test']['mae']:.2f}", f"{v['test']['r2']:.4f}"]
                for k, v in reg.items()
            ],
        ),
        "",
        "Alpha별 Lasso 계수가 0이 된 변수:",
        "",
    ]
    for row in summary["regression"]["paths"]["Lasso"]:
        zeros = ", ".join(row["zero_coefficients"]) or "없음"
        lines.append(f"- alpha={row['alpha']}: {zeros} (Test RMSE {row['test']['rmse']:.2f})")
    lines += [
        "",
        "## 분류: 연체 위험",
        "",
        _table(
            ["모델", "CV F1 (평균±표준편차)", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC"],
            [
                [k,
                 "-" if v["cv"] is None else f"{v['cv']['f1_mean']:.3f}±{v['cv']['f1_std']:.3f}",
                 *(f"{v['test'][m]:.3f}" for m in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"])]
                for k, v in clf.items()
            ],
        ),
        "",
        f"- CV F1 최고: {sel['best_cv']}. 1-표준오차 기준 {sel['cutoff']:.3f} 이상: {', '.join(sel['within_one_std'])}.",
        f"- 최종 모델: **{sel['final']}** (기준 안에서 가장 단순한 모델).",
        f"- 참고 상한(생성 규칙을 아는 경우): Precision {ora['precision']:.3f}, Recall {ora['recall']:.3f}, F1 {ora['f1']:.3f}.",
        "",
        "튜닝 결과:",
        "",
    ]
    for k, v in clf.items():
        if v.get("best_params"):
            lines.append(f"- {k}: {v['best_params']} (조합 {v['grid_candidates']}개)")
    lines += [
        "",
        "## 승인·보류·거절 정책 (최종 모델)",
        "",
        f"Train OOF 예측으로 정한 임계값: 보류 ≥ {pol['hold_threshold']:.3f} (재현율 {pol['hold_recall_target']:.0%} 유지), "
        f"거절 ≥ {pol['reject_threshold']:.3f} (OOF F1 최대).",
        "",
        _table(
            ["구간", "고객 수", "비중", "실제 연체", "연체율"],
            [[k, v["customers"], f"{v['share']:.1%}", v["overdue"], f"{v['overdue_rate']:.1%}"]
             for k, v in pol["test_bands"].items()],
        ),
        "",
        "## 특징 중요도 (Test permutation, PR-AUC 감소)",
        "",
    ]
    for model, perm in summary["diagnostics"]["permutation"].items():
        lines.append(f"- {model}: " + ", ".join(f"{f} {v['mean']:.3f}" for f, v in perm.items()))
    lines += ["", "## 학습 곡선 (마지막 지점의 Train − Validation 차이)", ""]
    for name, c in summary["diagnostics"]["learning_curves"].items():
        lines.append(f"- {name}: {c['metric'].upper()} 차이 {c['final_gap']:.3f}")
    lines.append("")
    return "\n".join(lines)
