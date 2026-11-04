"""프로젝트 전체에서 공유하는 상수."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "finance_data.csv"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
# A5-1 결과(같은 저장소의 이웃 폴더). 있으면 모델 설정이 같은지 대조하는 데만 쓴다.
A5_1_METRICS = ROOT.parent / "A5-1" / "results" / "metrics.json"

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
# 학습·군집화에 쓸 CPU 코어 수. 다른 작업과 함께 돌려도 노트북이 멈추지 않게 기본값을 낮게 둔다.
# 전용으로 돌릴 때는 A5_N_JOBS=-1(모든 코어)로 바꾼다. 결과 수치는 코어 수와 무관하다.
N_JOBS = int(os.environ.get("A5_N_JOBS", "2"))

# 원본 6개 입력 변수. 군집화와 분류 모두 이 6개만 쓴다(미션 데이터 정책: 임의 컬럼 추가 금지).
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
TARGETS = [REGRESSION_TARGET, CLASSIFICATION_TARGET]

# 군집 수 후보. 영업·심사 조직이 구분해 운영할 수 있는 페르소나 수를 8개 이하로 본다.
K_RANGE = range(2, 9)
# 시드를 바꿔 K-Means를 여러 번 돌려 Silhouette의 흔들림과 군집 안정성(ARI)을 잰다.
STABILITY_SEEDS = range(5)
SILHOUETTE_SAMPLE = 4000
# 시드만 바꿔도 군집 구성이 크게 바뀌는 K는 페르소나로 운영할 수 없다고 본다.
# ARI는 우연히 일치하는 수준을 0, 완전히 일치하면 1로 맞춘 값이다. 0.5 미만이면 시드마다 다른 군집이 나온다.
MIN_STABILITY_ARI = 0.5

# A5-1 최종 모델(RF + class_weight)의 GridSearchCV 결과를 그대로 쓴다.
# A5-1과 달리 파생 변수 없이 원본 6개 변수로 다시 학습한다.
RF_PARAMS = {
    "n_estimators": 400,
    "max_depth": 12,
    "min_samples_leaf": 1,
    "class_weight": "balanced",
}
# 미션 정의: 연체 예측 확률이 0.5 이상이면 거절(고위험) 판정이다.
REJECT_THRESHOLD = 0.5
# A5-1 승인·보류·거절 정책: 보류 구간은 연체자의 95%를 사람 심사 이상으로 보내도록 정한다.
HOLD_RECALL_TARGET = 0.95


def limit_threads(n_jobs: int = N_JOBS):
    """K-Means(OpenMP)와 PCA(BLAS)가 모든 코어를 쓰지 않도록 스레드 수를 제한한다.

    scikit-learn을 import한 뒤에 호출해야 해당 라이브러리에 적용된다.
    """
    from threadpoolctl import threadpool_limits

    if n_jobs and n_jobs > 0:
        threadpool_limits(limits=n_jobs)
