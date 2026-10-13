import pandas as pd
import numpy as np
import random

# 1. 데이터 생성 설정
N_SAMPLES = 10000  # 샘플 개수
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# 2. Feature 생성 (가상의 고객 정보)
data = {
    'age': np.random.randint(20, 70, N_SAMPLES),  # 나이
    'annual_income': np.random.normal(5000, 2000, N_SAMPLES).round(0), # 연 소득 (단위: 만원)
    'spending_score': np.random.randint(1, 100, N_SAMPLES), # 소비 점수
    'debt_ratio': np.random.uniform(0, 1, N_SAMPLES).round(2), # 소득 대비 부채 비율
    'credit_card_count': np.random.randint(1, 10, N_SAMPLES), # 보유 신용카드 수
    'overdue_count_6m': np.random.poisson(0.5, N_SAMPLES) # 최근 6개월 연체 횟수 (Poisson 분포)
}

df = pd.DataFrame(data)

# 소득이 음수인 경우 0으로 처리 (노이즈 수정)
df['annual_income'] = df['annual_income'].apply(lambda x: max(x, 1500))

# 3. Target 1 생성: 신용 점수 (Credit Score) - 회귀 문제용
# 규칙: 소득이 높고 연체가 적을수록 점수가 높음 + 랜덤 노이즈
df['credit_score'] = (
    300
    + (df['annual_income'] / 100) * 3
    - (df['overdue_count_6m'] * 50)
    - (df['debt_ratio'] * 100)
    + np.random.normal(0, 30, N_SAMPLES) # 노이즈 추가
)

# 신용점수 범위 제한 (0 ~ 1000점)
df['credit_score'] = df['credit_score'].clip(0, 1000).round(0)

# 4. Target 2 생성: 연체 여부 (Overdue) - 분류 문제용
# 규칙: 신용점수가 낮고 부채 비율이 높으면 연체 확률 증가 (불균형 데이터 생성)
# 기본 연체율을 낮게 설정하여 '데이터 불균형' 상황 연출
threshold = df['credit_score'].quantile(0.15) # 하위 15% 점수 기준
df['is_overdue'] = np.where(
    (df['credit_score'] < threshold) & (np.random.rand(N_SAMPLES) > 0.2),
    1, # 연체 (Positive)
    0  # 정상 (Negative)
)

# 데이터 셔플
df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

# 5. 파일 저장
df.to_csv('finance_data.csv', index=False)

print(f"데이터 생성 완료: finance_data.csv")
print(f"전체 샘플 수: {len(df)}")
print(f"연체(1) 비율: {df['is_overdue'].mean()*100:.2f}% (불균형 데이터 확인)")
