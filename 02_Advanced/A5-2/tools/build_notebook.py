"""학습용 군집화·SHAP 노트북 생성. 실행: python tools/build_notebook.py"""
import argparse
from pathlib import Path

import nbformat


SETUP = '''from pathlib import Path
import hashlib
import json
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

project_root = None
for candidate in [Path.cwd()] + list(Path.cwd().parents):
    if (candidate / "src" / "analysis_clustering.py").is_file():
        project_root = candidate
        break
if project_root is None:
    raise FileNotFoundError("A5-2 또는 notebooks 폴더에서 실행하세요.")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import limit_threads
limit_threads(2)
pd.set_option("display.precision", 4)
RANDOM_STATE = 42
feature_columns = ["age", "annual_income", "spending_score", "debt_ratio",
                   "credit_card_count", "overdue_count_6m"]
learning_dir = project_root / "results" / "learning"
figure_dir = learning_dir / "figures"
figure_dir.mkdir(parents=True, exist_ok=True)
data_path = project_root / "finance_data.csv"
if not data_path.exists():
    raise FileNotFoundError("finance_data.csv가 없습니다. A5-1과 동일한 제공 데이터를 준비하세요.")
customers = pd.read_csv(data_path)
X = customers[feature_columns].copy()
data_fingerprint = hashlib.sha256(data_path.read_bytes()).hexdigest()
assert customers.shape == (10000, 8)
assert set(["credit_score", "is_overdue"]).isdisjoint(X.columns)
print("고객 수:", len(customers), "/ 입력 변수 수:", X.shape[1])
print("결측치 수:", X.isna().sum().sum())
display(X.head())'''


def make_notebook(parts):
    cells = []
    for kind, source in parts:
        if kind == "md":
            cells.append(nbformat.v4.new_markdown_cell(source.strip()))
        else:
            cells.append(nbformat.v4.new_code_cell(source.strip()))
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata.language_info = {"name": "python", "version": "3.12"}
    nbformat.validate(notebook)
    return notebook


CLUSTERING = [
("md", '''# 1단계 — 고객을 묶고 특징 설명하기

**질문:** 정답 없이 고객을 묶으면 어떤 차이를 발견할 수 있을까?

같은 입력 6개로 거리 → 표준화 → K-Means → K 선택 → PCA → 군집 요약을 직접 실행한다. 다음 노트북에서 분류와 SHAP을 연결한다. 군집 번호는 정답이나 신용 등급이 아니다.

이 데이터는 가상 고객 10,000명의 합성 데이터다. 원본 열을 추가·수정하지 않는다. 5개 시드의 K 탐색에는 시간이 걸린다. 새 커널에서 위에서부터 실행한다. 그래프 축은 폰트 호환성을 위해 영어로 표시한다.'''),
("code", SETUP),
("md", '''## 1. 고객 한 쌍의 거리부터 보기

두 고객의 차이를 제곱해 더하면 제곱 유클리드 거리가 된다. 먼저 변수별 기여를 본다. 연 소득은 만원 단위의 수천, 부채 비율은 0~1이므로 원래 숫자를 그대로 쓰면 소득이 거리를 지배한다.'''),
("code", '''first_customer = X.iloc[0]
second_customer = X.iloc[1]
raw_squared_difference = (first_customer - second_customer) ** 2
raw_distance_share = raw_squared_difference / raw_squared_difference.sum()
display(pd.DataFrame({"customer_0": first_customer, "customer_1": second_customer,
                      "share_of_squared_distance": raw_distance_share}))'''),
("md", '''## 2. 단위를 맞추기 — StandardScaler

평균을 빼고 표준편차로 나눠 각 변수의 단위를 맞춘다. `fit`은 기준을 배우고, `transform`은 기준을 적용한다. 여기서는 **현재 고객 집단 전체를 기술하는 군집화**라 전체 입력에 fit한다. 미래 고객에 대한 평가 성능을 측정하는 실험은 아니다. 뒤의 분류는 Train에서만 학습한다.'''),
("code", '''from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaler.fit(X)
Z = scaler.transform(X)
print("표준화 전후 크기:", X.shape, Z.shape)
display(pd.DataFrame({"mean": scaler.mean_, "scale": scaler.scale_}, index=feature_columns))

scaled_squared_difference = (Z[0] - Z[1]) ** 2
scaled_distance_share = scaled_squared_difference / scaled_squared_difference.sum()
display(pd.DataFrame({"raw_share": raw_distance_share,
                      "scaled_share": scaled_distance_share}, index=feature_columns))'''),
("md", '''**확인 질문:** 표준화하면 모든 변수의 의미나 중요도가 같아질까?
<details><summary>답 확인</summary>아니다. 단위를 맞출 뿐이다. 거리 계산에 무엇을 포함할지는 별도의 설계 판단이다. 변수별 역할과 생성 구조를 확인해야 한다.</details>

## 3. K-Means 하나 직접 실행

K는 군집 개수다. 먼저 K=2로 학습하고 고객별 번호와 중심을 본다. 중심은 각 군집 입력의 평균 위치다. 거리와 중심의 반복 계산은 라이브러리가 수행하지만, 학습 입력과 출력은 직접 확인한다.'''),
("code", '''from sklearn.cluster import KMeans

two_cluster_model = KMeans(n_clusters=2, n_init=10, random_state=RANDOM_STATE)
two_cluster_model.fit(Z)
print("처음 10명의 군집:", two_cluster_model.labels_[:10])
print("중심의 크기:", two_cluster_model.cluster_centers_.shape)
print("군집 내 제곱거리 합:", two_cluster_model.inertia_)

distance_from_first = np.linalg.norm(two_cluster_model.cluster_centers_ - Z[0], axis=1)
print("첫 고객에서 각 중심까지 거리:", distance_from_first)
assert np.argmin(distance_from_first) == two_cluster_model.labels_[0]'''),
("md", '''## 4. K를 바꿔 비교하기

Inertia는 군집 안의 제곱거리 합이며 K가 커지면 보통 작아진다. Elbow는 그 감소가 완만해지는 지점을 보는 방법이다. Silhouette은 같은 군집과의 응집도와 다른 군집과의 분리도를 함께 본다. 높을수록 분리가 뚜렷하지만 진짜 고객 유형을 증명하는 수치는 아니다.

먼저 K 하나를 평가하는 함수를 만든다. 데이터·출력 구조는 앞에서 확인했다. 계산량을 줄이기 위해 Silhouette은 4,000명 표본에서 잰다. 같은 시드의 표본은 K 사이에 동일하다.'''),
("code", '''from sklearn.metrics import silhouette_score, adjusted_rand_score

def evaluate_one_k(Z_input, cluster_count, seed):
    estimator = KMeans(n_clusters=cluster_count, n_init=10, random_state=seed)
    cluster_labels = estimator.fit_predict(Z_input)
    random_generator = np.random.RandomState(seed)
    sample_indices = random_generator.choice(len(Z_input), min(4000, len(Z_input)), replace=False)
    silhouette = silhouette_score(Z_input[sample_indices], cluster_labels[sample_indices])
    return estimator.inertia_, silhouette, cluster_labels

example_inertia, example_silhouette, example_labels = evaluate_one_k(Z, 2, 0)
print("K=2, seed=0:", example_inertia, example_silhouette)'''),
("md", '''같은 K라도 시작 중심이 다르면 결과가 달라질 수 있다. 시드 5개로 반복하고, 군집 배정의 일관성을 ARI로 측정한다. ARI는 두 배정의 번호가 달라도 같은 묶음이면 1이다. 아래 리스트에는 K 하나당 요약 딕셔너리 하나를 저장한다.'''),
("code", '''from itertools import combinations

k_values = range(2, 9)
seeds = range(5)
scan_rows = []
for cluster_count in k_values:
    inertias = []
    silhouettes = []
    label_sets = []
    for seed in seeds:
        inertia, silhouette, cluster_labels = evaluate_one_k(Z, cluster_count, seed)
        inertias.append(inertia)
        silhouettes.append(silhouette)
        label_sets.append(cluster_labels)
    stability_scores = []
    for first_labels, second_labels in combinations(label_sets, 2):
        stability_scores.append(adjusted_rand_score(first_labels, second_labels))
    scan_rows.append({
        "k": cluster_count,
        "inertia": float(np.mean(inertias)),
        "silhouette_mean": float(np.mean(silhouettes)),
        "silhouette_std": float(np.std(silhouettes)),
        "silhouette_se": float(np.std(silhouettes) / np.sqrt(len(silhouettes))),
        "ari_mean": float(np.mean(stability_scores)),
    })
scan_table = pd.DataFrame(scan_rows).set_index("k")
display(scan_table)'''),
("code", '''fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
axes[0].plot(scan_table.index, scan_table["inertia"], marker="o")
axes[0].set_title("Elbow: inertia")
axes[1].errorbar(scan_table.index, scan_table["silhouette_mean"],
                 yerr=scan_table["silhouette_std"], marker="o", capsize=3)
axes[1].set_title("Silhouette: mean and SD")
axes[2].plot(scan_table.index, scan_table["ari_mean"], marker="o")
axes[2].set_title("Seed stability: ARI")
for axis in axes:
    axis.set_xlabel("K")
plt.tight_layout()
plt.savefig(figure_dir / "01_k_selection.png", dpi=140)
plt.show()'''),
("md", '''## 5. 지표와 해석을 연결해 K 선택

이 실험은 Silhouette 최고 평균에서 표준오차 하나를 뺀 기준 이상을 후보로 두고, ARI 0.5 이상인 후보 중 구별 가능한 입력 축이 많은 K를 선택한다. 구별 축은 어느 중심이라도 전체 평균에서 0.5표준편차 이상 벗어난 변수다. 이 기준은 **업무상 해석을 위한 휴리스틱**이며 통계적 동등성 검정이 아니다. Elbow에 뚜렷한 꺾임이 없다면 있다고 꾸미지 않는다. 타깃은 이 선택에 사용하지 않는다.'''),
("code", '''best_row = scan_table.loc[scan_table["silhouette_mean"].idxmax()]
silhouette_cutoff = best_row["silhouette_mean"] - best_row["silhouette_se"]
within_one_se = scan_table.index[scan_table["silhouette_mean"] >= silhouette_cutoff].tolist()
stable_candidates = []
for cluster_count in within_one_se:
    if scan_table.loc[cluster_count, "ari_mean"] >= 0.5:
        stable_candidates.append(cluster_count)

candidate_rows = []
for cluster_count in stable_candidates:
    candidate_model = KMeans(n_clusters=cluster_count, n_init=10, random_state=RANDOM_STATE)
    candidate_model.fit(Z)
    distinguishes = (np.abs(candidate_model.cluster_centers_) >= 0.5).any(axis=0)
    names = []
    for feature_name, is_distinguishing in zip(feature_columns, distinguishes):
        if is_distinguishing:
            names.append(feature_name)
    candidate_rows.append({"k": cluster_count, "axis_count": len(names), "features": names})

if candidate_rows:
    candidate_table = pd.DataFrame(candidate_rows).sort_values(["axis_count", "k"], ascending=[False, True])
    selected_k = int(candidate_table.iloc[0]["k"])
    display(candidate_table)
else:
    selected_k = int(best_row.name)
print("선택한 K:", selected_k)'''),
("md", '''**출력 읽기:** K별 점수 차이와 절대 수준을 함께 본다. 이 합성 데이터의 입력은 독립 난수로 생성됐으므로 명확한 자연 군집을 기대하기 어렵다. 고객을 몇 묶음으로 설명할지는 탐색적 결정이다. K를 바꾸면 번호와 페르소나도 달라질 수 있다.

## 6. 최종 군집과 원래 단위의 특징

선택한 K로 학습한 뒤 원래 변수의 평균을 본다. 군집 번호는 이름표다. 학습 후 연체율을 비교할 수 있지만, 그것이 군집 정답이나 모델 성능 평가는 아니다. 결과표는 원본 CSV가 아닌 별도 복사본으로 만든다.'''),
("code", '''cluster_model = KMeans(n_clusters=selected_k, n_init=10, random_state=RANDOM_STATE)
cluster_labels = cluster_model.fit_predict(Z)
cluster_centers = cluster_model.cluster_centers_
centers_in_original_units = scaler.inverse_transform(cluster_centers)

profile_table = pd.DataFrame(centers_in_original_units, columns=feature_columns)
profile_table.index.name = "cluster"
profile_table["customers"] = np.bincount(cluster_labels, minlength=selected_k)
profile_table["overdue_rate"] = 0.0
for cluster_id in range(selected_k):
    member_mask = cluster_labels == cluster_id
    profile_table.loc[cluster_id, "overdue_rate"] = customers.loc[member_mask, "is_overdue"].mean()
display(profile_table)
assert profile_table["customers"].sum() == len(customers)'''),
("md", '''### 6-1. 페르소나는 평균과 근거에서 붙이기

첫 군집을 먼저 설명한다. 중심의 z값이 +0.5 이상이면 해당 입력이 평균보다 높은 편, -0.5 이하면 낮은 편이라고 요약한다. 예를 들어 연체 횟수 높은 묶음에는 상환 관리 상담 가설을 세울 수 있다. 나이·카드 수가 다르다는 사실만으로 위험 원인이나 거절 사유라고 단정하지 않는다.'''),
("code", '''center_z_table = pd.DataFrame(cluster_centers, columns=feature_columns)
display(center_z_table)
persona_rows = []
for cluster_id in range(selected_k):
    descriptions = []
    for feature_name in feature_columns:
        z_value = center_z_table.loc[cluster_id, feature_name]
        if z_value >= 0.5:
            descriptions.append(feature_name + " 높은 편")
        elif z_value <= -0.5:
            descriptions.append(feature_name + " 낮은 편")
    if center_z_table.loc[cluster_id, "overdue_count_6m"] >= 0.5:
        action_hypothesis = "상환 일정 점검·상담 대상 가설; 개별 모델 설명 확인"
    elif center_z_table.loc[cluster_id, "debt_ratio"] >= 0.5:
        action_hypothesis = "부채 부담 상담 대상 가설; 개별 모델 설명 확인"
    else:
        action_hypothesis = "고객 수요·선호 조사 후 상품 안내 가설 검토"
    persona_rows.append({"cluster": cluster_id, "description": ", ".join(descriptions),
                         "action_hypothesis": action_hypothesis})
persona_table = pd.DataFrame(persona_rows)
display(persona_table)'''),
("md", '''## 7. PCA — 6차원 군집을 2차원에서 보기

PCA의 축은 원래 변수의 가중 합이다. 군집은 원래 6개 표준화 입력에서 만들고, PCA는 그림을 그리는 데만 사용한다. 2차원 설명 분산이 낮으면 그림에 드러나지 않는 차이가 많다는 뜻이다. 그림의 겹침만으로 군집이 틀렸다고 단정하지 않는다.'''),
("code", '''from sklearn.decomposition import PCA

pca = PCA(n_components=2, random_state=RANDOM_STATE)
coordinates = pca.fit_transform(Z)
print("좌표 크기:", coordinates.shape)
print("각 축 설명 분산:", pca.explained_variance_ratio_)
print("두 축 합:", pca.explained_variance_ratio_.sum())
display(pd.DataFrame(pca.components_, columns=feature_columns, index=["PC1", "PC2"]))

fig, axis = plt.subplots(figsize=(7, 5))
for cluster_id in range(selected_k):
    member_mask = cluster_labels == cluster_id
    axis.scatter(coordinates[member_mask, 0], coordinates[member_mask, 1],
                 s=5, alpha=0.35, label=f"C{cluster_id}")
axis.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%})")
axis.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
axis.set_title(f"PCA view; total explained variance {pca.explained_variance_ratio_.sum():.1%}")
axis.legend(markerscale=3)
plt.tight_layout()
plt.savefig(figure_dir / "02_pca_clusters.png", dpi=140)
plt.show()'''),
("md", '''**확인 질문:** PC1은 소득이고 PC2는 부채 비율일까?
<details><summary>답 확인</summary>아니다. 위 표의 가중치로 여러 변수를 섞은 축이다. 고객 특성은 PCA 좌표 자체보다 원래 변수의 평균과 분포로 설명한다.</details>

## 8. 같은 계산의 모듈 연결과 다음 단계 저장

앞에서 펼친 표준화·K 선택이 기존 함수와 같은 결과인지 확인한다. 최종 군집 번호는 기존 보고서가 연체율 순으로 다시 붙인 번호와 다를 수 있다. ARI는 번호가 달라도 같은 배정인지 확인할 수 있다.'''),
("code", '''from src import clustering

module_scaler = clustering.fit_scaler(X)
np.testing.assert_allclose(module_scaler.transform(X), Z)
module_selection = clustering.select_k(scan_rows, Z)
assert module_selection["final_k"] == selected_k
module_cluster = clustering.fit_final(Z, customers, selected_k)
assert adjusted_rand_score(module_cluster.labels_, cluster_labels) == 1.0
print("기존 모듈과 표준화·K 선택·군집 배정 일치")'''),
("code", '''np.savez_compressed(
    learning_dir / "clustering.npz",
    labels=cluster_labels, centers=cluster_centers,
    scaler_mean=scaler.mean_, scaler_scale=scaler.scale_,
)
metadata = {"data_sha256": data_fingerprint, "features": feature_columns,
            "selected_k": selected_k, "rows": len(customers), "random_state": RANDOM_STATE}
(learning_dir / "clustering_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
profile_table.to_csv(learning_dir / "cluster_profiles.csv")
persona_table.to_csv(learning_dir / "personas.csv", index=False)
print("다음: analysis_shap.ipynb")'''),
("md", '''다음 노트북은 이 군집 결과를 읽어 같은 고객의 모델 판단과 연결한다. 고객 입력 6개는 그대로 유지한다. 전체 집단의 군집화와 Train/Test로 나눈 지도학습은 목적과 평가 방식이 다르다.

알고리즘 비교와 대시보드는 확장 주제다. 기존 CLI의 `src.compare`와 `app.py`에서 이어갈 수 있다. 기존 `results/clustering.json`과 최종 보고서 그림은 이 실습으로 덮어쓰지 않는다.'''),
]


SHAP = [
("md", '''# 2단계 — 이 고객을 왜 위험하다고 예측했을까?

**진행:** 동일 입력 확인 → Train/Test → 분류 모델 학습 → 예측 → 한 고객 SHAP → 전체 요약 → 승인·거절 사례 → Dependence → 군집별 설명.

`analysis_clustering.ipynb`를 먼저 실행한다. 데이터와 입력 순서가 같은 군집 결과만 사용한다. 분류와 SHAP은 원본 6개 변수에 적용하며, 군집 번호를 분류 입력에 추가하지 않는다. SHAP은 모델의 예측을 분해하는 설명이고 실제 원인이나 대출 정책의 정당성을 입증하지 않는다.'''),
("code", SETUP),
("md", '''## 1. 앞서 만든 군집 결과 확인

저장된 데이터 해시와 변수 순서를 확인한다. 이전 데이터의 군집 결과를 새 고객에 잘못 연결하지 않기 위한 조건이다. `.npz`에는 숫자 배열만 저장했으며 pickle 객체를 읽지 않는다.'''),
("code", '''metadata_path = learning_dir / "clustering_metadata.json"
arrays_path = learning_dir / "clustering.npz"
if not metadata_path.exists() or not arrays_path.exists():
    raise FileNotFoundError("먼저 analysis_clustering.ipynb를 처음부터 실행하세요.")
cluster_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
if cluster_metadata["data_sha256"] != data_fingerprint or cluster_metadata["features"] != feature_columns:
    raise ValueError("데이터 또는 변수 순서가 다릅니다. 군집화 노트북을 다시 실행하세요.")
with np.load(arrays_path, allow_pickle=False) as saved_arrays:
    cluster_labels_all = saved_arrays["labels"].copy()
    cluster_centers = saved_arrays["centers"].copy()
    cluster_scaler_mean = saved_arrays["scaler_mean"].copy()
    cluster_scaler_scale = saved_arrays["scaler_scale"].copy()
selected_k = cluster_metadata["selected_k"]
assert len(cluster_labels_all) == len(customers)
assert cluster_centers.shape == (selected_k, len(feature_columns))
print("군집 수:", selected_k)'''),
("md", '''## 2. 분류는 Train에서 학습하고 Test에서 평가

현재 고객 집단 전체를 기술한 군집화와 달리, 분류는 입력으로 연체 여부를 예측하는 지도학습이다. A5-1과 같은 8:2 층화 분할, seed 42를 사용한다. 원본 데이터의 결측치가 없고, RF는 거리를 기준으로 학습하지 않으므로 표준화하지 않는다. SHAP도 원래 단위로 읽을 수 있다.'''),
("code", '''from sklearn.model_selection import train_test_split

y = customers["is_overdue"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE,
)
print("Train/Test:", X_train.shape, X_test.shape)
print("Train/Test 연체 비율:", y_train.mean(), y_test.mean())
assert set(X_train.index).isdisjoint(X_test.index)'''),
("md", '''## 3. Random Forest를 직접 만들고 학습

설정은 A5-1에서 이어온 RF의 400개 나무, 깊이 12, 리프 최소 1, class_weight=balanced다. 입력은 원본 6개로 맞춘다. 앞 미션의 파생 입력을 포함한 모델과는 동일한 객체가 아니라, 같은 설정으로 다시 학습하는 모델이다.'''),
("code", '''from sklearn.ensemble import RandomForestClassifier

risk_model = RandomForestClassifier(
    n_estimators=400, max_depth=12, min_samples_leaf=1,
    class_weight="balanced", random_state=RANDOM_STATE, n_jobs=2,
)
risk_model.fit(X_train, y_train)
print("클래스 순서:", risk_model.classes_)
print("학습한 입력 수:", risk_model.n_features_in_)'''),
("md", '''## 4. 연체 점수와 0/1 예측 구분

`predict_proba`는 고객×클래스 배열이다. 클래스 순서를 확인하고 클래스 1의 열을 선택한다. 0.5 이상을 위험 판정으로 본다. 가중치 학습 모델의 출력은 보정 검증 없이 실제 연체율과 같다고 간주하지 않는다.'''),
("code", '''from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

probabilities_by_class = risk_model.predict_proba(X_test)
overdue_class_index = int(np.flatnonzero(risk_model.classes_ == 1)[0])
overdue_probabilities = probabilities_by_class[:, overdue_class_index]
predicted_labels = (overdue_probabilities >= 0.5).astype(int)
metrics = {
    "accuracy": accuracy_score(y_test, predicted_labels),
    "precision": precision_score(y_test, predicted_labels),
    "recall": recall_score(y_test, predicted_labels),
    "f1": f1_score(y_test, predicted_labels),
    "roc_auc": roc_auc_score(y_test, overdue_probabilities),
}
display(pd.Series(metrics))
display(pd.DataFrame({"actual": y_test.iloc[:5], "score": overdue_probabilities[:5],
                      "prediction": predicted_labels[:5]}))'''),
("md", '''## 5. 한 고객의 점수를 SHAP으로 분해

SHAP이 설명하는 대상은 이 RF의 **연체 클래스 점수**다. TreeExplainer에 배경 표본을 따로 넘기지 않아 트리에 기록된 학습 경로를 기준으로 설명한다. 기준값은 그 설명 방식의 기대 출력이며 실제 연체율 12%나 지금 Test 평균과 같다고 가정하지 않는다. 라이브러리의 첫 계산 결과는 고객×변수×클래스 구조다.'''),
("code", '''warnings.filterwarnings("ignore", message="IProgress not found.*")
import shap

tree_explainer = shap.TreeExplainer(risk_model)
all_class_explanations = tree_explainer(X_test)
print("SHAP 전체 shape:", all_class_explanations.values.shape)
assert all_class_explanations.values.shape == (len(X_test), len(feature_columns), len(risk_model.classes_))
overdue_explanation = all_class_explanations[:, :, overdue_class_index]
print("연체 클래스만 선택:", overdue_explanation.values.shape)'''),
("code", '''first_position = 0
first_contributions = overdue_explanation.values[first_position]
first_base_value = float(overdue_explanation.base_values[first_position])
first_model_score = float(overdue_probabilities[first_position])
display(pd.DataFrame({"feature": feature_columns, "input_value": X_test.iloc[first_position].to_numpy(),
                      "contribution": first_contributions}))
print("기준값:", first_base_value)
print("기여 합:", first_contributions.sum())
print("기준값 + 기여 합:", first_base_value + first_contributions.sum())
print("모델 점수:", first_model_score)
reconstructed_scores = overdue_explanation.base_values + overdue_explanation.values.sum(axis=1)
np.testing.assert_allclose(reconstructed_scores, overdue_probabilities, atol=1e-6, rtol=0)
print("Test 전체 SHAP 재구성 최대 오차:", np.abs(reconstructed_scores - overdue_probabilities).max())'''),
("md", '''**출력 읽기:** 양수는 기준값보다 점수를 올리는 방향, 음수는 낮추는 방향이다. 점수 0.10의 변화는 10퍼센트포인트다. 값이 높으면 항상 양수가 되는 것은 아니며 모델의 관계에 달려 있다.

**확인 질문:** 한 고객의 가장 큰 기여 변수가 전체 고객에서도 반드시 1위일까?
<details><summary>답 확인</summary>아니다. Local은 그 고객의 기여다. Global은 여러 고객의 영향 크기를 요약한다. 서로 다른 질문이다.</details>

## 6. 여러 고객을 요약 — Global SHAP

고객별 절댓값 기여를 평균내면 방향이 상쇄되지 않는 영향 크기를 얻는다. Summary Plot에서는 점 하나가 고객 하나이며 색은 해당 입력값의 높고 낮음을 나타낸다.'''),
("code", '''importance_rows = []
for feature_index, feature_name in enumerate(feature_columns):
    contributions = overdue_explanation.values[:, feature_index]
    importance_rows.append({"feature": feature_name,
                            "mean_absolute_shap": np.abs(contributions).mean()})
importance_table = pd.DataFrame(importance_rows).sort_values("mean_absolute_shap", ascending=False)
display(importance_table)
shap.plots.beeswarm(overdue_explanation, max_display=6, show=False)
plt.tight_layout()
plt.savefig(figure_dir / "03_shap_summary.png", dpi=140, bbox_inches="tight")
plt.show()'''),
("md", '''전체 중요도는 **Test 2,000명의 설명**을 요약한 것이며 모든 미래 고객에 대한 불변 순위가 아니다. 소득·연체 이력·부채 비율의 방향을 그림에서 확인하고 생성 구조와 비교한다. 원인 효과나 개인의 책임으로 해석하지 않는다.

## 7. 승인·보류·거절 기준과 대표 고객

거절은 점수 0.5 이상, 승인 기준은 Train OOF에서 연체자의 95%를 보류 이상으로 보내도록 정한다. Test로 기준을 고르지 않는다. 이 절차는 비용 최적화나 확률 보정을 대신하지 않는다.'''),
("code", '''from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import precision_recall_curve
from sklearn.base import clone

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
oof_probabilities = cross_val_predict(clone(risk_model), X_train, y_train,
                                      cv=cv, method="predict_proba", n_jobs=1)[:, overdue_class_index]
_, oof_recall, oof_thresholds = precision_recall_curve(y_train, oof_probabilities)
meets_target = oof_recall[:-1] >= 0.95
hold_threshold = min(float(oof_thresholds[meets_target].max()), 0.5)
print("승인: 점수 <", hold_threshold, "/ 거절: 점수 >= 0.5")'''),
("md", '''같은 고객의 군집 번호와 예측 점수를 연결한다. 먼저 군집별 중심에 가장 가까운 Test 고객을 대표로 고른다. 가까움은 앞의 6차원 표준화 공간에서 측정한다. PCA 그림에서의 가까움으로 바꾸지 않는다.'''),
("code", '''test_cluster_ids = cluster_labels_all[X_test.index.to_numpy()]
Z_test = (X_test.to_numpy() - cluster_scaler_mean) / cluster_scaler_scale
distance_to_own_center = np.linalg.norm(Z_test - cluster_centers[test_cluster_ids], axis=1)
representative_rows = []
for cluster_id in range(selected_k):
    positions = np.flatnonzero(test_cluster_ids == cluster_id)
    if len(positions):
        closest_position = int(positions[np.argmin(distance_to_own_center[positions])])
        representative_rows.append({"cluster": cluster_id, "test_position": closest_position,
                                     "customer_index": int(X_test.index[closest_position]),
                                     "score": overdue_probabilities[closest_position]})
display(pd.DataFrame(representative_rows))
nearest_clusters = []
for customer_point in Z_test:
    distances = np.linalg.norm(cluster_centers - customer_point, axis=1)
    nearest_clusters.append(int(np.argmin(distances)))
np.testing.assert_array_equal(nearest_clusters, test_cluster_ids)'''),
("md", '''### 7-1. 승인과 거절을 각각 한 건 설명

거절 조건을 만족하는 Test 고객, 승인 조건을 만족하는 Test 고객 중 자기 군집 중심에 가장 가까운 고객을 고른다. 정답 라벨로 맞힌 사례만 골라내지 않는다. 승인·거절은 모델 점수 기준이며 실제 정상·연체 정답과 다를 수 있다.'''),
("code", '''reject_positions = np.flatnonzero(overdue_probabilities >= 0.5)
approve_positions = np.flatnonzero(overdue_probabilities < hold_threshold)
if not len(reject_positions) or not len(approve_positions):
    raise ValueError("승인 또는 거절 조건에 맞는 고객이 없습니다. 점수 분포를 확인하세요.")
reject_position = int(reject_positions[np.argmin(distance_to_own_center[reject_positions])])
approve_position = int(approve_positions[np.argmin(distance_to_own_center[approve_positions])])
case_positions = [("reject", reject_position), ("approve", approve_position)]
for case_name, test_position in case_positions:
    print(case_name, "/ 고객:", X_test.index[test_position],
          "/ 군집:", test_cluster_ids[test_position],
          "/ 점수:", round(overdue_probabilities[test_position], 4),
          "/ 실제 연체:", y_test.iloc[test_position])
    shap.plots.waterfall(overdue_explanation[test_position], max_display=7, show=False)
    plt.tight_layout()
    plt.savefig(figure_dir / f"04_waterfall_{case_name}.png", dpi=140, bbox_inches="tight")
    plt.show()'''),
("code", '''for case_name, test_position in case_positions:
    contributions = overdue_explanation.values[test_position]
    sorted_indices = np.argsort(np.abs(contributions))[::-1]
    print(case_name, "— 기준 점수", round(float(overdue_explanation.base_values[test_position]), 3),
          "→ 이 고객 점수", round(float(overdue_probabilities[test_position]), 3))
    for feature_index in sorted_indices[:3]:
        feature_name = feature_columns[feature_index]
        input_value = X_test.iloc[test_position, feature_index]
        change = contributions[feature_index] * 100
        direction = "올리는" if change >= 0 else "낮추는"
        print(f"  {feature_name}={input_value:g}: 점수를 {abs(change):.1f}%p {direction} 방향의 기여")'''),
("md", '''## 8. Dependence — 입력값과 설명값의 관계

전체 중요도 상위 두 변수와 부채 비율을 본다. 중복이면 다음 순위로 보충한다. 가로축은 입력, 세로축은 그 변수의 기여이며 예측 점수 자체가 아니다. 다른 입력이 다르면 같은 가로축 값에서도 기여가 다를 수 있다.'''),
("code", '''dependence_features = importance_table["feature"].head(2).tolist()
if "debt_ratio" not in dependence_features:
    dependence_features.append("debt_ratio")
for feature_name in importance_table["feature"]:
    if len(dependence_features) == 3:
        break
    if feature_name not in dependence_features:
        dependence_features.append(feature_name)

for feature_name in dependence_features:
    shap.plots.scatter(overdue_explanation[:, feature_name], show=False)
    plt.tight_layout()
    plt.savefig(figure_dir / f"05_dependence_{feature_name}.png", dpi=140, bbox_inches="tight")
    plt.show()
print("확인한 변수:", dependence_features)'''),
("md", '''**해석 연습:** 소득이 높을 때 소득 기여가 위험 점수를 낮추는 방향인지 확인한다. 같은 소득의 점들이 퍼져 있으면 다른 입력과 모델의 조건부 관계도 작용할 수 있다. 연체 이력과 부채 비율도 입력값이 커질 때의 방향을 그림에서 확인한다. 고객의 소득만 바꾸면 실제 연체가 줄어든다는 인과 결론은 여기서 얻을 수 없다.

## 9. 군집 특징과 모델 근거를 함께 보기

군집별 Test 고객의 평균 예측 점수와 평균 SHAP을 비교한다. 군집의 평균 특징이 개인에게 모두 해당하지는 않는다. 같은 군집 안에서도 개별 점수와 기여가 다르므로 일괄 거절이나 마케팅 기준으로 바로 쓰지 않는다.'''),
("code", '''cluster_explanation_rows = []
for cluster_id in range(selected_k):
    member_mask = test_cluster_ids == cluster_id
    if not member_mask.any():
        continue
    row = {"cluster": cluster_id, "test_customers": int(member_mask.sum()),
           "mean_score": float(overdue_probabilities[member_mask].mean())}
    for feature_index, feature_name in enumerate(feature_columns):
        row[feature_name] = float(overdue_explanation.values[member_mask, feature_index].mean())
    cluster_explanation_rows.append(row)
cluster_explanation_table = pd.DataFrame(cluster_explanation_rows).set_index("cluster")
display(cluster_explanation_table)
cluster_explanation_table[feature_columns].plot.barh(stacked=True, figsize=(10, 5))
plt.axvline(0, color="gray", linewidth=0.7)
plt.xlabel("Mean SHAP contribution to model score")
plt.tight_layout()
plt.savefig(figure_dir / "06_cluster_shap.png", dpi=140, bbox_inches="tight")
plt.show()
cluster_explanation_table.to_csv(learning_dir / "cluster_shap.csv")'''),
("md", '''## 10. 공통 함수와 연결해서 검증

앞에서 펼친 계산을 기존 모듈에서 어떻게 재사용하는지 확인한다. SHAP의 가법성, 모델 설정, Train/Test 분할을 대조한다. 기존 보고서는 군집 번호를 연체율 순으로 다시 붙이고 다른 대표 사례 선정 규칙을 사용하므로 사례 번호와 군집 번호를 그대로 섞지 않는다.'''),
("code", '''from src import explain
from src import model as model_module
from src.data import split_data

module_split = split_data(customers)
np.testing.assert_array_equal(module_split.X_test.index, X_test.index)
assert risk_model.get_params() == model_module.build_model().get_params()
assert explain.additivity_error(overdue_explanation, overdue_probabilities) < 1e-6
module_importance = explain.global_importance(overdue_explanation)
module_features = []
for row in module_importance:
    module_features.append(row["feature"])
assert module_features == importance_table["feature"].tolist()
print("기존 모듈과 분할·모델 설정·SHAP 요약 일치")'''),
("md", '''## 11. 정리

군집화는 고객의 입력 차이를 묶고, 분류는 연체 여부를 예측하며, SHAP은 특정 모델 점수의 기여를 설명한다. PCA는 그림의 축이고 원래 입력 변수가 아니다. Global과 Local은 서로 다른 범위의 질문이다.

다음 질문에 결과를 가리키며 답해 본다: 군집 특징과 개별 판단 근거는 언제 다른가? 높은 SHAP 중요도가 고객 위험의 원인임을 뜻하는가? 낮은 Silhouette에서도 페르소나를 사용한다면 어떤 검증과 한계 설명이 필요한가?

그림과 표는 `results/learning/`에 저장된다. 기존 최종 보고서와 대시보드 자료는 그대로 유지된다. 알고리즘 비교와 Streamlit은 기본 흐름을 이해한 뒤 기존 CLI·앱에서 이어갈 수 있다.'''),
]


def build_all(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, parts in [("analysis_clustering", CLUSTERING), ("analysis_shap", SHAP)]:
        notebook = make_notebook(parts)
        path = output_dir / f"{name}.ipynb"
        nbformat.write(notebook, path)
        print(f"Created {len(notebook.cells)} cells: {name}.ipynb")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "notebooks")
    args = parser.parse_args()
    build_all(args.output_dir)
