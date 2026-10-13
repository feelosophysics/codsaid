"""프로젝트 전체에서 공유하는 상수."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "finance_data.csv"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
# 앙상블 학습에 쓸 CPU 코어 수. 다른 작업과 함께 돌려도 노트북이 멈추지 않게 기본값을 낮게 둔다.
# 전용으로 돌릴 때는 A5_N_JOBS=-1(모든 코어)로 바꾼다. 결과 수치는 코어 수와 무관하다.
N_JOBS = int(os.environ.get("A5_N_JOBS", "2"))

# 원본 6개 입력 변수. 두 타깃은 서로의 입력으로 쓰지 않는다.
# is_overdue는 credit_score로 만들어졌으므로 credit_score를 분류 입력에 넣으면 정답 누수가 된다.
FEATURES = [
    "age",
    "annual_income",
    "spending_score",
    "debt_ratio",
    "credit_card_count",
    "overdue_count_6m",
]
REGRESSION_TARGET = "credit_score"
CLASSIFICATION_TARGET = "is_overdue"

ALPHAS = [0.01, 0.1, 1, 10, 100]
