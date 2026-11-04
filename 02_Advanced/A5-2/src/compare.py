"""보너스 2: K-Means를 DBSCAN, 계층적 군집(Agglomerative)과 비교한다."""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors

from .config import RANDOM_STATE

# 계층적 군집은 모든 쌍의 거리를 다루므로 메모리가 고객 수의 제곱으로 는다.
# 1만 명이면 거리 행렬만 약 400MB라서, 노트북 부담을 줄이려고 무작위 표본에서 비교한다.
HIERARCHICAL_SAMPLE = 2000
LINKAGES = ["ward", "complete", "average"]


def dbscan_min_samples(n_features: int) -> int:
    """흔히 쓰는 경험 규칙: 차원 수의 2배."""
    return 2 * n_features


def k_distance(Z: np.ndarray, min_samples: int) -> np.ndarray:
    """각 고객에서 min_samples번째 이웃까지의 거리(자기 자신 포함)를 오름차순으로 정렬한 곡선."""
    dist, _ = NearestNeighbors(n_neighbors=min_samples).fit(Z).kneighbors(Z)
    return np.sort(dist[:, -1])


def knee(curve: np.ndarray) -> float:
    """Kneedle 방식: 양 끝을 잇는 직선에서 가장 멀리 떨어진 지점을 꺾이는 점으로 본다."""
    x = np.linspace(0, 1, len(curve))
    y = (curve - curve[0]) / (curve[-1] - curve[0])
    return float(curve[int(np.argmax(x - y))])


def run_dbscan(Z: np.ndarray, df: pd.DataFrame) -> dict:
    ms = dbscan_min_samples(Z.shape[1])
    curve = k_distance(Z, ms)
    eps = knee(curve)
    labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(Z)
    cross = pd.crosstab(labels, df["overdue_count_6m"])
    clustered = labels >= 0
    return {
        "eps": eps,
        "min_samples": ms,
        "labels": labels,
        "k_distance": curve,
        "n_clusters": int(len(set(labels)) - (-1 in labels)),
        "noise_share": float((~clustered).mean()),
        "sizes": {str(k): int(v) for k, v in pd.Series(labels).value_counts().sort_index().items()},
        "overdue_count_crosstab": {str(k): {str(c): int(v) for c, v in row.items()} for k, row in cross.iterrows()},
        "overdue_rate": {str(k): float(v) for k, v in df["is_overdue"].groupby(labels).mean().items()},
    }


def compare(Z: np.ndarray, df: pd.DataFrame, kmeans_labels: np.ndarray, k: int) -> dict:
    """같은 표본에서 Silhouette과 K-Means와의 일치도(ARI)를 비교한다."""
    idx = np.random.RandomState(RANDOM_STATE).choice(len(Z), HIERARCHICAL_SAMPLE, replace=False)
    Zs, km = Z[idx], kmeans_labels[idx]
    rows = [{"method": "K-Means", "clusters": k, "silhouette": float(silhouette_score(Zs, km)),
             "ari_vs_kmeans": 1.0, "sizes": np.bincount(km).tolist(), "noise_share": 0.0}]
    hier = {}
    for link in LINKAGES:
        lab = AgglomerativeClustering(n_clusters=k, linkage=link).fit_predict(Zs)
        hier[link] = lab
        rows.append({"method": f"Hierarchical ({link})", "clusters": k,
                     "silhouette": float(silhouette_score(Zs, lab)),
                     "ari_vs_kmeans": float(adjusted_rand_score(km, lab)),
                     "sizes": sorted(np.bincount(lab).tolist(), reverse=True), "noise_share": 0.0})
    db = run_dbscan(Z, df)
    lab = db["labels"][idx]
    core = lab >= 0
    rows.append({"method": "DBSCAN", "clusters": db["n_clusters"],
                 "silhouette": float(silhouette_score(Zs[core], lab[core])) if len(set(lab[core])) > 1 else None,
                 "ari_vs_kmeans": float(adjusted_rand_score(km, lab)),
                 "sizes": [int(v) for k_, v in sorted(db["sizes"].items(), key=lambda t: int(t[0])) if int(k_) >= 0],
                 "noise_share": db["noise_share"]})
    return {"sample_index": idx, "table": rows, "hierarchical_labels": hier, "dbscan": db}
