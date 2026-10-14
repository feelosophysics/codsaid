"""Train/Validation 성능 격차로 편향(Bias)·분산(Variance)을 진단한다.

진단 표 (미션 기준)
    상태            Train Loss   Validation Loss       해결책
    High Bias       높음         높음 (Train과 비슷)    모델 복잡도↑, 학습 더 오래
    High Variance   낮음         높음 (큰 격차)         정규화, 데이터↑

'높다'를 판단하려면 기준선이 필요하다.
- 분류: 오류율을 쓰고, 기준선은 사람 수준(또는 Bayes) 오류율이다. 꽃 사진은 사람이 거의 틀리지 않으므로 0으로 둔다.
- 시계열: 손실 크기가 구간의 변동성에 따라 달라진다. 그래서 같은 구간의 Naive 예측 손실로 나눈
  상대 손실(skill = 모델 MSE / Naive MSE)을 쓴다. skill ≥ 1이면 '어제 값'보다 못하다는 뜻이다.
"""
from dataclasses import asdict, dataclass

REMEDIES = {
    "high_bias": "모델 복잡도↑(은닉 크기·층·입력 피처), 학습 더 오래, 정규화 완화",
    "high_variance": "정규화(Dropout·Weight decay·Early stopping), 데이터↑(증강·수집), 학습 범위 축소(Layer freezing)",
    "high_bias_and_variance": "먼저 편향을 줄이고(표현력↑) 이어서 분산을 줄인다(정규화·데이터↑)",
    "good_fit": "현재 설정 유지, Test는 마지막에 한 번만 평가",
}
LABELS = {
    "high_bias": "High Bias (Underfitting)",
    "high_variance": "High Variance (Overfitting)",
    "high_bias_and_variance": "High Bias + High Variance",
    "good_fit": "적정 (Good fit)",
}


@dataclass
class Diagnosis:
    state: str
    label: str
    train: float
    validation: float
    avoidable_bias: float      # Train이 기준선보다 얼마나 나쁜가
    variance_gap: float        # Validation이 Train보다 얼마나 나쁜가
    remedy: str
    rule: str

    def to_dict(self):
        return asdict(self)


def _classify(bias, gap, bias_tol, gap_tol):
    high_bias, high_variance = bias > bias_tol, gap > gap_tol
    if high_bias and high_variance:
        return "high_bias_and_variance"
    if high_bias:
        return "high_bias"
    if high_variance:
        return "high_variance"
    return "good_fit"


def diagnose_classification(train_error, validation_error, human_error=0.0, bias_tol=0.05, gap_tol=0.05):
    """오류율(0~1)로 진단한다. 회피 가능 편향 = Train − 사람, 분산 = Validation − Train."""
    bias = train_error - human_error
    gap = validation_error - train_error
    state = _classify(bias, gap, bias_tol, gap_tol)
    rule = f"회피 가능 편향 {bias:.3f} (기준 {bias_tol}), Train→Validation 격차 {gap:.3f} (기준 {gap_tol})"
    return Diagnosis(state, LABELS[state], train_error, validation_error, bias, gap, REMEDIES[state], rule)


def diagnose_forecast(train_loss, validation_loss, train_naive, validation_naive, bias_tol=0.95, gap_tol=0.10):
    """Naive 대비 상대 손실로 진단한다.

    skill_train = Train MSE / Train Naive MSE. bias_tol(0.95) 이상이면 학습 구간에서조차
    '어제 값'보다 5% 넘게 낫지 못하다는 뜻이다 → 편향이 크다(또는 데이터 자체가 예측 불가능).
    격차 = skill_validation − skill_train. gap_tol(0.10) 초과면 분산이 크다.
    """
    skill_train = train_loss / train_naive
    skill_validation = validation_loss / validation_naive
    bias = skill_train - bias_tol
    gap = skill_validation - skill_train
    state = _classify(bias, gap, 0.0, gap_tol)
    rule = (f"Train skill {skill_train:.3f} (Naive=1, {bias_tol} 이상이면 편향), "
            f"Validation skill {skill_validation:.3f}, 격차 {gap:.3f} (기준 {gap_tol})")
    return Diagnosis(state, LABELS[state], skill_train, skill_validation, bias, gap, REMEDIES[state], rule)
