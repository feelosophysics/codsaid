"""미션 실행 순서(analysis_clustering → analysis_shap)대로 보고서 노트북 두 개의 셀을 만든다.

계산 로직은 src/에 있고, 노트북은 단계를 실행해 결과를 보여 주는 보고서다. 실행은 execute_notebook.py가 한다.
"""
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]

SETUP = """import json
import warnings
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

warnings.filterwarnings("ignore", category=UserWarning)
# shap이 불러오는 tqdm의 위젯 안내 경고. 출력에 로컬 경로가 남지 않게 숨긴다.
warnings.filterwarnings("ignore", message="IProgress not found")
pd.set_option("display.precision", 4)
pd.set_option("display.width", 160)"""

CLUSTERING = [
    ("md", """# 1단계 — 고객 군집화 (analysis_clustering)

목표: 타깃(신용 점수·연체 여부) 없이 6개 입력 변수만으로 고객을 묶어 페르소나를 정의한다.
계산은 `src/analysis_clustering.py`가 하고, 이 노트북은 단계별 결과를 보여 주는 보고서다.

데이터는 A5-1과 같은 `data_gen.py`로 만든 **합성 데이터**이며 실제 금융 고객에 대한 결론이 아니다."""),
    ("code", SETUP + """

from src import analysis_clustering, clustering
from src.config import FEATURES, FIGURES_DIR, TARGETS
from src.data import features_only, load_data

df = load_data()
X = features_only(df)
print(f"{len(df):,}행, 군집화 입력 {list(X.columns)}")
print("타깃이 입력에 없는가:", set(TARGETS).isdisjoint(X.columns))
X.describe().T[["mean", "std", "min", "max"]]"""),
    ("md", """## 1. 왜 스케일링하는가

K-Means는 유클리드 거리로 가까운 고객을 묶는다. 소득(만원, 표준편차 약 2,000)과 부채 비율(0~1)을 그대로 쓰면 거리가 거의 소득만으로 정해진다.
아래는 두 고객 사이 거리에서 각 변수가 차지하는 비중이다."""),
    ("code", """a, b = X.iloc[0], X.iloc[1]
scaler = clustering.fit_scaler(X)
za, zb = scaler.transform(X.iloc[[0, 1]])
raw_share = (a - b) ** 2 / ((a - b) ** 2).sum()
scaled_share = pd.Series((za - zb) ** 2 / ((za - zb) ** 2).sum(), index=FEATURES)
pd.DataFrame({"customer_0": a, "customer_1": b, "share_raw": raw_share, "share_scaled": scaled_share})"""),
    ("md", """## 2. 전체 실행

K 탐색(K=2~8, 시드 5개), K 선택, 최종 군집, 페르소나, PCA, 보너스 알고리즘 비교까지 한 번에 실행하고 `results/clustering.json`에 저장한다."""),
    ("code", """result = analysis_clustering.run(df)
pd.DataFrame(result["scan"]).set_index("k")"""),
    ("md", """## 3. K 선택

규칙: **Silhouette 우선 → Elbow 보조 → 페르소나 해석 가능성** (미션 가이드).

1. Silhouette 평균이 가장 높은 K를 찾고, A5-1과 같은 1-표준오차 규칙으로 차이를 주장하기 어려운 후보를 남긴다.
2. 시드를 바꿔도 군집이 유지되는지(ARI ≥ 0.5) 확인한다.
3. 남은 후보 중 군집을 구별하는 변수가 가장 많은 K를 고른다."""),
    ("code", """sel = result["selection"]
print(json.dumps(sel, ensure_ascii=False, indent=1))
display(Image(FIGURES_DIR / "01_k_selection.png"))"""),
    ("md", """Silhouette이 모든 K에서 0.12~0.14로 낮고 평평하며, Elbow도 꺾이지 않는다. `data_gen.py`가 6개 변수를 **서로 독립인 난수**로 만들었기 때문이다.
이 데이터에는 자연스러운 군집이 없고, K-Means는 연속적인 공간을 나눌 뿐이다. 그래서 K는 "진짜 군집 수"가 아니라 **운영할 페르소나 수**를 고르는 결정이다.

K=2는 Silhouette이 가장 높지만 "6개월 연체 0회 / 1회 이상" 규칙 하나와 같다. K=6은 통계적으로 K=2와 구별되지 않으면서 5개 변수로 고객을 구별한다."""),
    ("code", """k2 = clustering.kmeans(2).fit(scaler.transform(X))
pd.crosstab(k2.labels_, df["overdue_count_6m"])"""),
    ("md", """## 4. PCA 2차원 시각화

PCA는 그림을 그리기 위한 투영이다. 군집은 6차원 원래 공간에서 학습했다. 주성분(PC)은 원래 변수가 아니라 변수들의 가중 합이므로, "PC1이 높은 고객" 대신 아래 적재값(loading)으로 해석한다."""),
    ("code", """pca = result["pca"]
print("설명된 분산:", [f"{v:.1%}" for v in pca["explained_variance_ratio"]])
display(pd.DataFrame(pca["loadings"]).round(3))
display(Image(FIGURES_DIR / "02_pca_clusters.png"))"""),
    ("md", """변수가 서로 독립이라 주성분마다 설명 분산이 약 1/6(16.7%)이다. PC1+PC2는 34.6%뿐이라 2차원 그림에서 군집이 많이 겹쳐 보인다. 나머지 65%의 차이가 그림에 보이지 않을 뿐, 6차원에서는 군집이 나뉘어 있다.

## 5. 군집 프로파일과 페르소나

연체율과 신용 점수는 군집화에 쓰지 않았다. 군집을 만든 뒤 설명에만 쓴다."""),
    ("code", """rows = []
for p, n in zip(result["profiles"], result["personas"]):
    rows.append({"cluster": f"C{p['cluster']}", "persona": n["ko"], "size": p["size"], "share": p["share"],
                 **{f: p["mean"][f] for f in FEATURES}, "overdue_rate": p["overdue_rate"],
                 "credit_score": p["credit_score_mean"]})
display(pd.DataFrame(rows).set_index("cluster"))
display(Image(FIGURES_DIR / "03_cluster_profiles.png"))"""),
    ("code", """for n in result["personas"]:
    display(Markdown(f"**C{n['cluster']} {n['ko']}** — {n['summary']}  \\n대상: {n['target']} · 메시지: {n['message']} · 액션: {n['action']}"))"""),
    ("md", """## 6. 보너스 2 — 군집화 알고리즘 비교

같은 2,000명 표본에서 K-Means, 계층적 군집(ward·complete·average), DBSCAN을 비교한다. 계층적 군집은 거리 행렬이 고객 수의 제곱으로 커지므로 표본에서만 돌린다."""),
    ("code", """cmp = result["comparison"]
display(pd.DataFrame(cmp["table"]).set_index("method"))
db = cmp["dbscan"]
print(f"DBSCAN eps={db['eps']:.3f}(k-거리 곡선의 꺾이는 점), min_samples={db['min_samples']}")
display(pd.DataFrame(db["overdue_count_crosstab"]).T.rename_axis("DBSCAN label"))
display(Image(FIGURES_DIR / "13_clustering_comparison.png"))"""),
    ("md", """- 알고리즘끼리 일치도(ARI)가 0.04~0.19로 낮다. 진짜 군집이 있다면 방법이 달라도 비슷한 답이 나온다. 결과가 이렇게 엇갈리는 것 자체가 "자연스러운 군집이 없다"는 증거다.
- DBSCAN은 연체 횟수 0·1·2회를 각각 하나의 군집으로 나누고, 3회 이상은 노이즈로 분류한다. 이산 변수의 값 사이 빈틈이 이 데이터에서 유일하게 밀도가 끊기는 곳이기 때문이다. 밀도 기반 방법은 데이터에 실제로 있는 빈틈만 찾는다.
- average 연결은 한 군집에 1,807명이 몰린다. 평균 거리 기준은 경계가 흐린 데이터에서 큰 덩어리 하나와 소수의 외톨이로 나뉘기 쉽다."""),
]

SHAP = [
    ("md", """# 2단계 — 모델 해석 (analysis_shap)

목표: A5-1 최종 모델을 다시 학습해 SHAP으로 "왜 그런 판정인가"를 설명하고, 1단계 페르소나와 연결한다.
먼저 `analysis_clustering` 노트북(또는 `python -m src.analysis_clustering`)을 실행해야 한다."""),
    ("code", SETUP + """

from src import analysis_shap, explain
from src.analysis_clustering import load_result
from src.config import FEATURES, FIGURES_DIR, RF_PARAMS
from src.data import load_data

df = load_data()
clustering = load_result()
print("A5-1에서 가져온 설정:", RF_PARAMS)"""),
    ("md", """## 1. 모델: A5-1 설정 재사용

A5-1 최종 모델(RF + class_weight)은 파생 변수(연령대, 부채액)를 썼다. A5-2는 임의 컬럼 추가를 금지하므로, **같은 하이퍼파라미터로 원본 6개 변수만 써서 다시 학습**한다.
분할(8:2 층화, seed 42)도 같아서 Test 2,000명이 A5-1과 같은 고객이다. 아래 실행이 학습·SHAP·그래프를 모두 만든다(SHAP 계산에 약 1분)."""),
    ("code", """result = analysis_shap.run(df)
m = result["model"]
ref = m["a5_1"]
pd.DataFrame({
    "A5-2 (원본 6개)": {"CV F1": m["cv"]["f1_mean"], **{k: m["test"][k] for k in ("precision", "recall", "f1", "roc_auc", "pr_auc")}},
    "A5-1 (6개 + 파생)": {"CV F1": ref["cv"]["f1_mean"], **{k: ref["test"][k] for k in ("precision", "recall", "f1", "roc_auc", "pr_auc")}},
}).round(3)"""),
    ("md", """파생 변수를 빼도 성능이 거의 같다. 부채액(소득×부채 비율)은 두 원본 변수로 트리가 직접 나눌 수 있고, 연령대는 노이즈 변수(나이)를 다시 쓴 것이기 때문이다.

## 2. SHAP의 기준값과 가법성

SHAP은 예측 = 기준값 + 변수별 기여의 합으로 나눈다. 기준값은 0.12(실제 연체율)가 아니라 약 0.50이다. `class_weight="balanced"`가 연체 표본에 약 7배 가중치를 주어 학습했기 때문에 모델 점수의 평균이 0.5 근처로 옮겨졌다."""),
    ("code", """print(f"기준값 E[f(X)] = {result['base_value']:.4f}")
print(f"가법성 최대 오차 = {result['additivity_error']:.1e}")
case = result["cases"]["reject_case"]
total = case["base_value"] + sum(c["shap"] for c in case["contributions"])
print(f"거절 사례: {case['base_value']:.4f} + {total - case['base_value']:+.4f} = {total:.4f} (모델 확률 {case['proba']:.4f})")"""),
    ("md", """## 3. Global — Summary Plot"""),
    ("code", """display(pd.DataFrame(result["global"]).set_index("feature"))
display(Image(FIGURES_DIR / "04_shap_summary.png"))
display(Image(FIGURES_DIR / "05_shap_importance_bar.png"))"""),
    ("md", """- 상위 3개(소득, 연체 횟수, 부채 비율)가 영향의 92%를 차지한다. `data_gen.py`의 신용 점수 공식에 들어간 세 변수와 정확히 같다. 나이·소비 점수·카드 수는 공식에 없는 노이즈 변수이고 영향도 작다.
- 방향: 소득은 낮을수록, 연체 횟수와 부채 비율은 높을수록 연체 점수를 올린다(순위 상관 −0.93, +0.87, +0.90).
- 정답 공식을 아는 합성 데이터라서 설명이 맞는지 직접 검증할 수 있다. 실제 데이터에서는 이런 검증이 불가능하므로 SHAP은 "모델이 무엇을 보는가"이지 "세상의 인과"가 아니다.

## 4. Local — 승인·거절 사례"""),
    ("code", """for key in ("reject_case", "approve_case"):
    c = result["cases"][key]
    display(Markdown(f"**{key}** · C{c['cluster']} {clustering['personas'][c['cluster']]['ko']} · 확률 {c['proba']:.3f} · "
                     f"실제 연체 {c['actual_overdue']} · 실제 신용 점수 {c['credit_score']:.0f}"))
    display(pd.DataFrame(c["contributions"]).set_index("feature"))
    for line in explain.narrate(c):
        print("-", line)
display(Image(FIGURES_DIR / "06_waterfall_reject.png"))
display(Image(FIGURES_DIR / "07_waterfall_approve.png"))"""),
    ("md", """## 5. Dependence Plot

변수 선택: Summary 상위 2개(소득, 연체 횟수) + 비즈니스 변수 1개(부채 비율: 대출 규제와 상담에서 직접 다루는 변수)."""),
    ("code", """dep = result["dependence"]
print("연체 횟수별 소득 SHAP이 음수로 바뀌는 소득:", dep["income_crossing"])
print("생성 공식상 점수 292점 경계 소득(부채 비율 0.5):", {k: round(v) for k, v in dep["theoretical_income_boundary"].items()})
display(pd.DataFrame(dep["income_by_overdue"]).pivot(index="bin", columns="group", values="shap_mean").round(3))
for f in dep["features"]:
    n = 8 + dep["features"].index(f)
    display(Image(FIGURES_DIR / f"{n:02d}_dependence_{f}.png"))"""),
    ("md", """## 6. 페르소나와 연결"""),
    ("code", """names = [f"C{p['cluster']} {p['ko']}" for p in clustering["personas"]]
cs = pd.DataFrame([r["mean_shap"] | {"mean_proba": r["mean_proba"], "n_test": r["n_test"]} for r in result["cluster_shap"]], index=names)
display(cs.round(3))
display(pd.DataFrame(result["cluster_band_crosstab"]).T.set_axis(names))
display(Image(FIGURES_DIR / "11_cluster_shap.png"))
display(Image(FIGURES_DIR / "12_persona_cases.png"))"""),
    ("md", """- C0(연체 반복형)는 연체 횟수 SHAP 평균이 +0.25로 위험을 끌어올린다. C5(저부채 고소비 우량형)는 부채 비율 SHAP 평균이 −0.16으로 위험을 끌어내린다.
- 소득은 어느 군집도 구별하지 않는다(모든 군집에서 z가 ±0.11 이내). 그런데 모델이 가장 중요하게 보는 변수는 소득이다. 군집화는 모든 변수를 똑같은 거리로 다루고, 분류 모델은 정답과 관련된 변수만 본다. 그래서 같은 페르소나 안에도 위험이 크게 다른 고객이 섞인다. 페르소나는 마케팅 단위로 쓰고, 심사는 개별 점수와 SHAP 근거로 해야 한다."""),
]


def build(cells, path):
    nb = new_notebook()
    nb.cells = [new_markdown_cell(src) if kind == "md" else new_code_cell(src) for kind, src in cells]
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python"}
    nbformat.write(nb, path)
    print(f"Built {path.relative_to(ROOT)} ({len(cells)} cells)")


if __name__ == "__main__":
    (ROOT / "notebooks").mkdir(exist_ok=True)
    build(CLUSTERING, ROOT / "notebooks" / "analysis_clustering.ipynb")
    build(SHAP, ROOT / "notebooks" / "analysis_shap.ipynb")
