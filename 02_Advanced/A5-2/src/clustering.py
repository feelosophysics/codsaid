"""고객 군집화: 스케일링, K 탐색(Elbow·Silhouette·안정성), K 선택, 군집 프로파일, PCA."""

from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from .config import (
    CLASSIFICATION_TARGET,
    FEATURES,
    K_RANGE,
    MIN_STABILITY_ARI,
    RANDOM_STATE,
    REGRESSION_TARGET,
    SILHOUETTE_SAMPLE,
    STABILITY_SEEDS,
)

# 군집 평균이 전체 평균에서 0.5 표준편차 이상 떨어진 변수를 "그 군집을 구별하는 변수"로 본다.
DISTINGUISH_Z = 0.5


def fit_scaler(X: pd.DataFrame) -> StandardScaler:
    """K-Means는 유클리드 거리를 쓰므로 단위가 큰 변수(소득, 만원)가 거리를 독차지하지 않게 표준화한다."""
    return StandardScaler().fit(X[FEATURES])


def kmeans(k: int, seed: int = RANDOM_STATE) -> KMeans:
    return KMeans(n_clusters=k, n_init=10, random_state=seed)


def scan_k(Z: np.ndarray, k_range=K_RANGE, seeds=STABILITY_SEEDS) -> list[dict]:
    """K마다 시드를 바꿔 K-Means를 여러 번 학습한다.

    - inertia: 군집 내 제곱거리 합(Elbow). 시드 평균.
    - silhouette: 시드마다 다른 무작위 표본 SILHOUETTE_SAMPLE명에서 계산한 평균·표준편차.
    - ari: 시드 쌍마다 군집 배정이 얼마나 같은지(Adjusted Rand Index) 평균. 1이면 항상 같은 군집.
    """
    rows = []
    for k in k_range:
        labels, inertias, sils = [], [], []
        for seed in seeds:
            model = kmeans(k, seed).fit(Z)
            labels.append(model.labels_)
            inertias.append(model.inertia_)
            idx = np.random.RandomState(seed).choice(len(Z), min(SILHOUETTE_SAMPLE, len(Z)), replace=False)
            sils.append(silhouette_score(Z[idx], model.labels_[idx]))
        aris = [adjusted_rand_score(a, b) for a, b in combinations(labels, 2)]
        rows.append({
            "k": k,
            "inertia": float(np.mean(inertias)),
            "silhouette_mean": float(np.mean(sils)),
            "silhouette_std": float(np.std(sils)),
            "silhouette_se": float(np.std(sils) / np.sqrt(len(sils))),
            "ari_mean": float(np.mean(aris)) if aris else 1.0,
        })
    return rows


def distinguishing_features(centers_z: np.ndarray, threshold=DISTINGUISH_Z) -> list[str]:
    """어느 한 군집에서라도 평균이 |z| ≥ threshold인 변수. 페르소나를 설명할 수 있는 축의 수다."""
    hit = (np.abs(centers_z) >= threshold).any(axis=0)
    return [f for f, h in zip(FEATURES, hit) if h]


def select_k(scan: list[dict], Z: np.ndarray) -> dict:
    """K 선택 규칙(미션 가이드: Silhouette 우선 → Elbow 보조 → 페르소나 해석 가능성).

    1. Silhouette 평균이 가장 높은 K를 찾는다.
    2. 1-표준오차 규칙(A5-1과 같은 규칙): 최고 평균 − 표준오차 이상인 K는 최고 K와 차이를 주장하기 어렵다.
    3. 그중 시드 간 ARI가 MIN_STABILITY_ARI 이상인 K만 남긴다(시드마다 바뀌는 군집은 운영할 수 없다).
    4. 남은 K 중 군집을 구별하는 변수가 가장 많은 K를 고른다. 같으면 작은 K.
       타깃은 쓰지 않는다. 같은 정도로 좋은 후보 중에서 페르소나를 더 구체적으로 설명하는 K를 고르는 단계다.
    Elbow는 그래프로 함께 보고하되, 이 데이터처럼 꺾임이 없으면 선택에 쓰지 않는다.
    """
    by_k = {r["k"]: r for r in scan}
    best = max(scan, key=lambda r: r["silhouette_mean"])
    cutoff = best["silhouette_mean"] - best["silhouette_se"]
    within = [r["k"] for r in scan if r["silhouette_mean"] >= cutoff]
    stable = [k for k in within if by_k[k]["ari_mean"] >= MIN_STABILITY_ARI]
    axes = {}
    for k in stable:
        centers = kmeans(k).fit(Z).cluster_centers_
        axes[k] = distinguishing_features(centers)
    final = max(stable, key=lambda k: (len(axes[k]), -k)) if stable else best["k"]
    return {
        "best_silhouette_k": best["k"],
        "cutoff": float(cutoff),
        "within_one_se": within,
        "stable": stable,
        "distinguishing_features": {str(k): v for k, v in axes.items()},
        "final_k": final,
    }


def fit_final(Z: np.ndarray, df: pd.DataFrame, k: int):
    """최종 K-Means를 학습하고, 연체율이 높은 군집부터 0, 1, 2…로 번호를 다시 붙인다.

    번호는 이름표일 뿐이라 바꿔도 군집 자체는 같다. 타깃은 학습에 쓰지 않고 정렬과 설명에만 쓴다.
    """
    model = kmeans(k).fit(Z)
    rate = pd.Series(df[CLASSIFICATION_TARGET].to_numpy()).groupby(model.labels_).mean()
    order = rate.sort_values(ascending=False).index.to_numpy()
    remap = np.empty(k, dtype=int)
    remap[order] = np.arange(k)
    model.cluster_centers_ = model.cluster_centers_[order]
    model.labels_ = remap[model.labels_]
    return model


def profile(df: pd.DataFrame, labels: np.ndarray, centers_z: np.ndarray) -> list[dict]:
    """군집별 크기, 원 단위 평균, 표준화 평균(z), 그리고 학습에 쓰지 않은 타깃의 평균."""
    out = []
    for c in range(len(centers_z)):
        part = df[labels == c]
        out.append({
            "cluster": c,
            "size": int(len(part)),
            "share": float(len(part) / len(df)),
            "mean": {f: float(part[f].mean()) for f in FEATURES},
            "median": {f: float(part[f].median()) for f in FEATURES},
            "z": {f: float(v) for f, v in zip(FEATURES, centers_z[c])},
            "overdue_rate": float(part[CLASSIFICATION_TARGET].mean()),
            "credit_score_mean": float(part[REGRESSION_TARGET].mean()),
            "overdue_2plus_share": float((part["overdue_count_6m"] >= 2).mean()),
        })
    return out


def pca_summary(Z: np.ndarray) -> tuple[PCA, dict]:
    """PCA는 시각화용이다. 군집은 6차원 원래 공간에서 학습했고, 2차원 그림은 그 그림자다."""
    pca = PCA(random_state=RANDOM_STATE).fit(Z)
    evr = pca.explained_variance_ratio_
    return pca, {
        "explained_variance_ratio": [float(v) for v in evr],
        "cumulative": [float(v) for v in np.cumsum(evr)],
        "loadings": {f"PC{i + 1}": {f: float(w) for f, w in zip(FEATURES, comp)} for i, comp in enumerate(pca.components_[:2])},
    }
