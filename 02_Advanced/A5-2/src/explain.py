"""SHAP으로 모델의 판단 근거를 설명한다: Global(전체), Local(개별 고객), Dependence(변수 변화에 따른 추이)."""

import numpy as np
import pandas as pd
import shap

from .config import FEATURES, REJECT_THRESHOLD

# Dependence Plot 변수 선택 기준(미션): Summary Plot 상위 1~2개 + 비즈니스 의미가 큰 변수 1개.
# 부채 비율은 대출 규제(DSR)와 고객 상담에서 직접 조정할 수 있는 변수라서 비즈니스 변수로 둔다.
BUSINESS_FEATURE = "debt_ratio"


def explain(model, X: pd.DataFrame) -> shap.Explanation:
    """TreeExplainer로 연체(클래스 1) 확률에 대한 SHAP 값을 계산한다.

    배경 데이터를 넘기지 않으면 트리에 기록된 학습 표본 수로 기댓값을 계산한다(tree_path_dependent).
    KernelExplainer와 달리 근사 없이 정확한 값을 트리 구조에서 바로 구한다.
    """
    explanation = shap.TreeExplainer(model)(X)
    # (고객, 변수, 클래스) → 연체 클래스만
    return explanation[:, :, 1]


def additivity_error(explanation: shap.Explanation, proba: np.ndarray) -> float:
    """SHAP의 핵심 성질: 기준값 + 변수별 기여 합 = 그 고객의 예측 확률."""
    return float(np.abs(explanation.base_values + explanation.values.sum(axis=1) - proba).max())


def global_importance(explanation: shap.Explanation) -> list[dict]:
    """평균 |SHAP|(영향 크기)과 방향(변수 값과 SHAP 값의 순위 상관)을 함께 계산한다."""
    values, data = explanation.values, explanation.data
    total = np.abs(values).mean(axis=0).sum()
    rows = []
    for j, f in enumerate(FEATURES):
        direction = pd.Series(data[:, j]).corr(pd.Series(values[:, j]), method="spearman")
        rows.append({
            "feature": f,
            "mean_abs_shap": float(np.abs(values[:, j]).mean()),
            "share": float(np.abs(values[:, j]).mean() / total),
            "direction": float(direction),
        })
    return sorted(rows, key=lambda r: r["mean_abs_shap"], reverse=True)


def dependence_features(importance: list[dict]) -> list[str]:
    top = [r["feature"] for r in importance[:2]]
    return top + ([BUSINESS_FEATURE] if BUSINESS_FEATURE not in top else [importance[2]["feature"]])


def binned_dependence(explanation: shap.Explanation, feature: str, by: str | None = None, bins=8) -> list[dict]:
    """Dependence Plot을 숫자로 요약한다. 값이 적은 변수는 값마다, 연속 변수는 분위수 구간마다 평균 SHAP."""
    j = FEATURES.index(feature)
    x, v = explanation.data[:, j], explanation.values[:, j]
    if len(np.unique(x)) <= 10:
        groups = pd.Series(x)
        labels = groups
    else:
        labels = pd.qcut(x, bins, duplicates="drop")
    frame = pd.DataFrame({"x": x, "shap": v, "bin": labels})
    if by:
        frame["by"] = np.where(explanation.data[:, FEATURES.index(by)] >= 1, f"{by}>=1", f"{by}=0")
        group_cols = ["bin", "by"]
    else:
        group_cols = ["bin"]
    out = []
    for keys, part in frame.groupby(group_cols, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        out.append({
            "bin": str(keys[0]),
            **({"group": keys[1]} if by else {}),
            "x_mean": float(part["x"].mean()),
            "shap_mean": float(part["shap"].mean()),
            "n": int(len(part)),
        })
    return out


def income_crossing(explanation: shap.Explanation, overdue_level: int) -> float | None:
    """연체 횟수가 같은 고객 안에서 소득 SHAP이 양수(위험 증가)에서 음수로 바뀌는 소득.

    소득을 오름차순으로 놓고 SHAP 이동 평균이 처음 0 아래로 내려가는 지점이다.
    """
    j, o = FEATURES.index("annual_income"), FEATURES.index("overdue_count_6m")
    mask = explanation.data[:, o] == overdue_level
    if mask.sum() < 50:
        return None
    order = np.argsort(explanation.data[mask, j])
    x = explanation.data[mask, j][order]
    v = pd.Series(explanation.values[mask, j][order]).rolling(50, center=True, min_periods=25).mean().to_numpy()
    below = np.where(v < 0)[0]
    return float(x[below[0]]) if len(below) else None


def cluster_shap(explanation: shap.Explanation, clusters: np.ndarray, k: int) -> list[dict]:
    """군집별 평균 SHAP: 그 페르소나의 예측 확률이 전체 기준값에서 어떤 변수 때문에 멀어지는가."""
    out = []
    for c in range(k):
        m = clusters == c
        out.append({
            "cluster": c,
            "n_test": int(m.sum()),
            "mean_shap": {f: float(explanation.values[m, j].mean()) for j, f in enumerate(FEATURES)},
            "mean_proba": float(explanation.base_values[m].mean() + explanation.values[m].sum(axis=1).mean()),
        })
    return out


def representatives(Z_test: np.ndarray, centers: np.ndarray, clusters: np.ndarray, proba: np.ndarray,
                    bands: dict) -> dict:
    """군집별 대표 고객과, 미션이 요구하는 승인·거절 사례를 고른다(모두 Test 고객).

    - 군집 대표: 그 군집 Test 고객 중 6차원 표준화 공간에서 중심에 가장 가까운 고객
    - 거절 사례: 연체율이 가장 높은 군집(C0)에서 확률 ≥ 0.5인 고객 중 중심에 가장 가까운 고객
    - 승인 사례: 연체율이 가장 낮은 군집에서 확률 < 보류 임계값(자동 승인)인 고객 중 중심에 가장 가까운 고객
    """
    dist = np.linalg.norm(Z_test - centers[clusters], axis=1)

    def nearest(mask):
        idx = np.where(mask)[0]
        return int(idx[np.argmin(dist[idx])]) if len(idx) else None

    k = len(centers)
    reps = {c: nearest(clusters == c) for c in range(k)}
    reject = nearest((clusters == 0) & (proba >= REJECT_THRESHOLD))
    approve = nearest((clusters == k - 1) & (proba < bands["hold"]))
    return {
        "cluster_representatives": {str(c): i for c, i in reps.items()},
        "reject_case": reject,
        "approve_case": approve,
        "distance_to_center": {str(c): float(dist[i]) for c, i in reps.items() if i is not None},
    }


def case_detail(explanation: shap.Explanation, i: int, proba: np.ndarray, y: np.ndarray) -> dict:
    contrib = sorted(
        ({"feature": f, "value": float(explanation.data[i, j]), "shap": float(explanation.values[i, j])}
         for j, f in enumerate(FEATURES)),
        key=lambda r: abs(r["shap"]), reverse=True,
    )
    return {
        "row": int(i),
        "base_value": float(explanation.base_values[i]),
        "proba": float(proba[i]),
        "actual_overdue": int(y[i]),
        "contributions": contrib,
    }


FEATURE_KO = {
    "age": "나이",
    "annual_income": "연 소득",
    "spending_score": "소비 점수",
    "debt_ratio": "부채 비율",
    "credit_card_count": "신용카드 수",
    "overdue_count_6m": "최근 6개월 연체 횟수",
}
UNIT = {"age": "세", "annual_income": "만원", "spending_score": "점", "debt_ratio": "", "credit_card_count": "장",
        "overdue_count_6m": "회"}


def narrate(case: dict, top=3) -> list[str]:
    """비기술자에게 전할 문장. 확률은 %p(퍼센트포인트)로 말한다."""
    lines = [f"평균적인 고객의 모델 점수는 {case['base_value']:.0%}이고, 이 고객은 {case['proba']:.0%}입니다."]
    for r in case["contributions"][:top]:
        value = f"{r['value']:,.0f}{UNIT[r['feature']]}" if r["feature"] != "debt_ratio" else f"{r['value']:.2f}"
        verb = "올라갔습니다" if r["shap"] > 0 else "내려갔습니다"
        lines.append(f"{FEATURE_KO[r['feature']]}({value}) 때문에 점수가 {abs(r['shap']) * 100:.1f}%p {verb}.")
    return lines
