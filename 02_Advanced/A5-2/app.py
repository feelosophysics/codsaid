"""보너스 1: 고객 정보를 넣으면 연체 확률, 페르소나, SHAP 설명을 보여 주는 대시보드.

    uv run python -m src.run_all      # 먼저 군집·정책 결과를 만든다
    uv run streamlit run app.py
"""

import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import streamlit as st

from src import explain, model as clf
from src.analysis_clustering import assign_clusters, load_result
from src.analysis_shap import SHAP_JSON
from src.config import FEATURES
from src.data import load_data, split_data

BAND_KO = {"approve": "승인", "review": "보류(사람 심사)", "reject": "거절"}

st.set_page_config(page_title="A5-2 연체 위험 설명", layout="wide")


@st.cache_resource(show_spinner="모델을 학습하는 중입니다(약 2초)...")
def resources():
    df = load_data()
    split = split_data(df)
    model = clf.build_model().fit(split.X_train, split.y_train)
    clustering = load_result()
    bands = json.loads(SHAP_JSON.read_text(encoding="utf-8"))["bands"]
    return df, split, model, shap.TreeExplainer(model), clustering, bands


try:
    df, split, model, explainer, clustering, bands = resources()
except FileNotFoundError as e:
    st.error(f"{e}\n\n`uv run python data_gen.py`와 `uv run python -m src.run_all`을 먼저 실행하세요.")
    st.stop()

st.title("연체 위험 설명 대시보드")
st.caption("A5-2 보너스 · 합성 데이터(seed 42)로 학습한 Random Forest. 실제 금융 심사에 쓰는 모델이 아닙니다.")

personas = clustering["personas"]
reps = json.loads(SHAP_JSON.read_text(encoding="utf-8"))["cases"]
presets = {"직접 입력(중앙값에서 시작)": split.X_train.median()}
for case in reps["cluster_representatives"]:
    presets[f"C{case['cluster']} {personas[case['cluster']]['ko']} 대표 고객"] = split.X_test.iloc[case["row"]]

with st.sidebar:
    st.header("고객 정보")
    preset = st.selectbox("시작 값", list(presets))
    base = presets[preset]
    lo, hi = df[FEATURES].min(), df[FEATURES].max()
    values = {
        "age": st.slider("나이", int(lo["age"]), int(hi["age"]), int(base["age"])),
        "annual_income": st.number_input("연 소득(만원)", int(lo["annual_income"]), int(hi["annual_income"]),
                                         int(base["annual_income"]), step=100),
        "spending_score": st.slider("소비 점수", int(lo["spending_score"]), int(hi["spending_score"]),
                                    int(base["spending_score"])),
        "debt_ratio": st.slider("부채 비율", 0.0, 1.0, float(base["debt_ratio"]), step=0.01),
        "credit_card_count": st.slider("신용카드 수", int(lo["credit_card_count"]), int(hi["credit_card_count"]),
                                       int(base["credit_card_count"])),
        "overdue_count_6m": st.slider("최근 6개월 연체 횟수", 0, int(hi["overdue_count_6m"]),
                                      int(base["overdue_count_6m"])),
    }

x = pd.DataFrame([values], columns=FEATURES)
proba = float(model.predict_proba(x)[0, 1])
band = str(clf.band_of([proba], bands)[0])
cluster = int(assign_clusters(x, clustering["transform"])[0])
persona = personas[cluster]
explanation = explainer(x)[:, :, 1]
sv = explanation[0]
# 입력 고객은 실제 결과를 모르므로 actual 값(0)은 쓰지 않는다.
case = explain.case_detail(explanation, 0, np.array([proba]), np.array([0]))

c1, c2, c3 = st.columns(3)
c1.metric("모델 연체 점수", f"{proba:.1%}")
c2.metric("판정", BAND_KO[band], help=f"보류 {bands['hold']:.3f} 이상, 거절 {bands['reject']:.1f} 이상")
c3.metric("페르소나", f"C{cluster} {persona['ko']}")

left, right = st.columns([3, 2])
with left:
    st.subheader("왜 이런 판정인가 (Local SHAP)")
    fig = plt.figure(figsize=(8, 4.5))
    shap.plots.waterfall(sv, max_display=len(FEATURES), show=False)
    st.pyplot(fig, clear_figure=True)
    for line in explain.narrate(case):
        st.markdown(f"- {line}")
with right:
    st.subheader("페르소나 전략")
    st.markdown(f"**{persona['ko']}** · {persona['summary']}")
    st.markdown(f"- 대상: {persona['target']}\n- 메시지: {persona['message']}\n- 액션: {persona['action']}")
    st.info("페르소나는 비슷한 고객 묶음일 뿐입니다. 같은 페르소나 안에서도 소득에 따라 위험이 크게 다르므로, "
            "심사는 개별 점수와 SHAP 근거로 합니다.")

st.caption("모델 점수는 class_weight='balanced'로 학습해 평균이 약 50%입니다. 실제 연체 확률(전체 12%)과 "
           "눈금이 다르므로 순위와 판정 기준으로 읽습니다.")
