# A5-1 실행 결과

`python -m src.run_all`이 생성한다. 모든 수치는 seed 42 합성 데이터, Test 2,000건 기준이다.

## 회귀: 신용 점수

| 모델 | 선택 Alpha | RMSE | MAE | R² |
| --- | --- | --- | --- | --- |
| Mean baseline | - | 80.87 | 64.73 | -0.0004 |
| LinearRegression | - | 30.13 | 23.94 | 0.8611 |
| Ridge | 10.0 | 30.13 | 23.94 | 0.8611 |
| Lasso | 0.1 | 30.13 | 23.93 | 0.8612 |

Alpha별 Lasso 계수가 0이 된 변수:

- alpha=0.01: age_group_20-29, age_group_60-69 (Test RMSE 30.13)
- alpha=0.1: age_group_20-29, age_group_30-39, age_group_60-69 (Test RMSE 30.13)
- alpha=1: age, spending_score, credit_card_count, debt_amount, age_group_20-29, age_group_30-39, age_group_40-49, age_group_50-59, age_group_60-69 (Test RMSE 30.22)
- alpha=10: age, spending_score, credit_card_count, debt_amount, age_group_20-29, age_group_30-39, age_group_40-49, age_group_50-59, age_group_60-69 (Test RMSE 35.24)
- alpha=100: age, annual_income, spending_score, debt_ratio, credit_card_count, overdue_count_6m, debt_amount, age_group_20-29, age_group_30-39, age_group_40-49, age_group_50-59, age_group_60-69 (Test RMSE 80.87)

## 분류: 연체 위험

| 모델 | CV F1 (평균±표준편차) | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rule baseline | - | 0.513 | 0.195 | 0.975 | 0.325 | 0.859 | 0.459 |
| LogReg (no handling) | 0.612±0.051 | 0.917 | 0.692 | 0.562 | 0.621 | 0.950 | 0.685 |
| LogReg + class_weight | 0.645±0.021 | 0.877 | 0.493 | 0.875 | 0.631 | 0.949 | 0.683 |
| LogReg + SMOTE | 0.655±0.023 | 0.882 | 0.505 | 0.858 | 0.636 | 0.949 | 0.683 |
| RF + class_weight | 0.660±0.018 | 0.896 | 0.546 | 0.796 | 0.647 | 0.940 | 0.634 |
| RF + SMOTE | 0.665±0.018 | 0.901 | 0.564 | 0.787 | 0.657 | 0.938 | 0.602 |
| XGB + scale_pos_weight | 0.656±0.018 | 0.883 | 0.508 | 0.833 | 0.631 | 0.945 | 0.671 |

- CV F1 최고: RF + SMOTE. 1-표준오차 기준 0.657 이상: RF + class_weight, RF + SMOTE.
- 최종 모델: **RF + class_weight** (기준 안에서 가장 단순한 모델).
- 참고 상한(생성 규칙을 아는 경우): Precision 0.800, Recall 1.000, F1 0.889.

튜닝 결과:

- RF + class_weight: {'max_depth': 12, 'min_samples_leaf': 1, 'n_estimators': 400} (조합 30개)
- RF + SMOTE: {'max_depth': 16, 'min_samples_leaf': 1, 'n_estimators': 400} (조합 30개)
- XGB + scale_pos_weight: {'learning_rate': 0.1, 'max_depth': 4, 'n_estimators': 200} (조합 16개)

## 승인·보류·거절 정책 (최종 모델)

Train OOF 예측으로 정한 임계값: 보류 ≥ 0.190 (재현율 95% 유지), 거절 ≥ 0.557 (OOF F1 최대).

| 구간 | 고객 수 | 비중 | 실제 연체 | 연체율 |
| --- | --- | --- | --- | --- |
| approve | 1422 | 71.1% | 14 | 1.0% |
| hold | 263 | 13.2% | 47 | 17.9% |
| reject | 315 | 15.8% | 179 | 56.8% |

## 특징 중요도 (Test permutation, PR-AUC 감소)

- RF + class_weight: annual_income 0.403, overdue_count_6m 0.239, debt_ratio 0.188, credit_card_count 0.008, age 0.000, spending_score -0.006
- LogReg + class_weight: annual_income 0.410, overdue_count_6m 0.301, debt_ratio 0.167, credit_card_count 0.000, spending_score -0.000, age -0.002

## 학습 곡선 (마지막 지점의 Train − Validation 차이)

- RF + class_weight (F1): F1 차이 0.170
- LogReg + class_weight (F1): F1 차이 0.003
- Lasso alpha=0.1 (RMSE): RMSE 차이 -0.049
