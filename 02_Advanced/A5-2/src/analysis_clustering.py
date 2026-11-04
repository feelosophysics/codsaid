"""1단계: 고객 군집화. 타깃 없이 6개 입력 변수만으로 페르소나를 만든다.

    python -m src.analysis_clustering
"""

import json
import time

import numpy as np
from sklearn.metrics import silhouette_score

from . import clustering, compare, personas, report
from .config import FEATURES, FIGURES_DIR, RESULTS_DIR, limit_threads
from .data import describe, features_only, load_data

CLUSTERING_JSON = RESULTS_DIR / "clustering.json"


def run(df=None, with_bonus=True, verbose=True):
    limit_threads()
    started = time.time()

    def step(msg):
        if verbose:
            print(f"[{time.time() - started:6.1f}s] {msg}", flush=True)

    df = load_data() if df is None else df
    X = features_only(df)
    scaler = clustering.fit_scaler(X)
    Z = scaler.transform(X)
    step(f"데이터 {len(df):,}행, 입력 변수 {len(FEATURES)}개 표준화")

    scan = clustering.scan_k(Z)
    selection = clustering.select_k(scan, Z)
    k = selection["final_k"]
    step(f"K 탐색 완료: Silhouette 최고 K={selection['best_silhouette_k']}, 최종 K={k}")

    model = clustering.fit_final(Z, df, k)
    labels = model.labels_
    profiles = clustering.profile(df, labels, model.cluster_centers_)
    names = personas.assign(profiles)
    pca, pca_info = clustering.pca_summary(Z)
    coords = pca.transform(Z)[:, :2]
    step("군집 프로파일·PCA 완료")

    labels_en = [personas.short_label(p) for p in names]
    report.k_selection(scan, selection, FIGURES_DIR / "01_k_selection.png")
    report.pca_clusters(coords, labels, pca_info, labels_en, FIGURES_DIR / "02_pca_clusters.png")
    report.cluster_profiles(profiles, labels_en, FIGURES_DIR / "03_cluster_profiles.png")

    bonus = None
    if with_bonus:
        result = compare.compare(Z, df, labels, k)
        report.clustering_comparison(result, coords, labels, FIGURES_DIR / "13_clustering_comparison.png")
        db = result["dbscan"]
        bonus = {
            "sample_size": len(result["sample_index"]),
            "table": result["table"],
            "dbscan": {key: db[key] for key in ("eps", "min_samples", "n_clusters", "noise_share", "sizes",
                                                "overdue_count_crosstab", "overdue_rate")},
        }
        step("보너스: 알고리즘 비교 완료")

    summary = {
        "data": describe(df),
        "scan": scan,
        "selection": selection,
        "profiles": profiles,
        "personas": names,
        "pca": pca_info,
        "silhouette_full": float(silhouette_score(Z, labels)),
        "comparison": bonus,
        # 학습 자료·대시보드가 같은 군집 배정을 다시 계산할 수 있도록 변환 정보를 함께 저장한다.
        "transform": {
            "features": FEATURES,
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
            "centers": model.cluster_centers_.tolist(),
            "pca_mean": pca.mean_.tolist(),
            "pca_components": pca.components_[:2].tolist(),
        },
        "labels": labels.tolist(),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CLUSTERING_JSON.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    step(f"저장 완료: {CLUSTERING_JSON.relative_to(RESULTS_DIR.parent)}")
    return summary


def load_result() -> dict:
    if not CLUSTERING_JSON.exists():
        raise FileNotFoundError("results/clustering.json이 없습니다. 먼저 `python -m src.analysis_clustering`를 실행하세요.")
    return json.loads(CLUSTERING_JSON.read_text(encoding="utf-8"))


def assign_clusters(X, transform: dict) -> np.ndarray:
    """저장된 평균·표준편차·중심으로 새 고객의 군집을 정한다(가장 가까운 중심)."""
    Z = (np.asarray(X[transform["features"]], dtype=float) - transform["scaler_mean"]) / transform["scaler_scale"]
    centers = np.asarray(transform["centers"])
    return np.argmin(((Z[:, None, :] - centers[None]) ** 2).sum(axis=2), axis=1)


if __name__ == "__main__":
    run()
