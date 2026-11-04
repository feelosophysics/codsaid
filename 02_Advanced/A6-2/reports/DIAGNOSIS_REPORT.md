# 성능 진단 리포트 (Diagnosis Report)

Train과 Validation의 성능 격차로 각 실험의 상태를 진단하고, 상태에 맞는 해결책을 적용해 그 효과를 다시 잰다.
모든 곡선은 `figures/ts_*_loss_curves.png`, `figures/vision_loss_curves.png`에 있다.

## 진단 기준

| 상태 | Train Loss | Validation Loss | 해결책 |
| --- | --- | --- | --- |
| High Bias | 높음 | 높음 (Train과 비슷) | 모델 복잡도↑, 학습 더 오래, 입력 피처 보강 |
| High Variance | 낮음 | 높음 (큰 격차) | 정규화(Dropout·Weight decay·조기 종료), 데이터↑, 학습 범위 축소 |

'높다'를 판단하는 기준선은 다음과 같이 정했다 (`src/perfdiag/diagnosis.py`).

- **이미지 분류**: 오류율을 쓴다. 꽃 사진은 사람이 거의 틀리지 않으므로 기준 오류율(사람 수준)을 0으로 둔다.
  Train 오류율 > 0.05이면 편향, Validation − Train 오류율 > 0.05이면 분산이다.
- **시계열**: 구간마다 변동성이 달라 손실 크기를 그대로 비교할 수 없다. 같은 구간의 Naive 손실로 나눈 skill(= 모델 MSE ÷ Naive MSE)을 쓴다. Train skill ≥ 0.95이면 학습 구간에서도 '전날 값'보다 5% 넘게 낫지 못한 것이므로 편향으로 본다. Validation skill − Train skill > 0.10이면 분산이다.

## 시계열: AAPL 종가

| 실험 | Train skill | Validation skill | 격차 | 진단 | epoch | Test MAE (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| LSTM·수준값(v1) | 1.472 | 1.685 | 0.213 | High Bias + High Variance | 150 (복원 146) | 6.0866 |
| GRU·수준값(v1) | 2.129 | 2.292 | 0.163 | High Bias + High Variance | 32 (복원 12) | 9.3351 |
| LSTM·변화량(v2) | 0.989 | 0.996 | 0.006 | High Bias (Underfitting) | 21 (복원 1) | 2.4321 |
| GRU·변화량(v2) ★ | 0.999 | 0.996 | -0.003 | High Bias (Underfitting) | 21 (복원 1) | 2.4417 |
| LSTM 은닉 2 | 0.995 | 0.999 | 0.005 | High Bias (Underfitting) | 30 (복원 10) | 2.4474 |
| LSTM 128×2 (규제 없음) | 0.019 | 2.947 | 2.928 | High Variance (Overfitting) | 100 (복원 100) | 4.3121 |
| LSTM 128×2 + 규제 | 0.996 | 0.998 | 0.001 | High Bias (Underfitting) | 21 (복원 1) | 2.4347 |

★ = Validation MAE로 고른 최종 모델. skill과 epoch은 대표 seed(Validation 손실 최저) 기준, Test MAE는 seed 평균이다.

**관찰과 처방**

1. **v1 수준값 → v2 변화량**: v1 LSTM은 High Bias + High Variance로 진단됐다 (Train skill 1.472, Validation skill 1.685). Train에서도 Naive보다 못한 것은 모델 용량 문제가 아니라 문제 설정 문제다. 수준값을 MinMax로 넣으면 Train 범위 밖의 가격을 외삽해야 하고, 출력이 전날 값을 그대로 따라가지 못해 늦게 반응한다. 출력을 변화량으로 바꾸자 Test MAE가 6.0866 → 2.4321로 60.0% 줄었다.
2. **분산 확인 → 정규화**: 은닉 128×2층을 규제·조기 종료 없이 100 epoch 학습하면 Train skill 0.019, Validation skill 2.947으로 격차 2.928의 High Variance (Overfitting)가 된다. Dropout 0.3, Weight decay 1e-4, 조기 종료를 적용하면 진단이 High Bias (Underfitting)로 바뀌고, Test MAE가 4.3121 → 2.4347로 43.5% 줄었다.
3. **남은 편향의 정체**: v2 LSTM은 Train skill 0.989로 편향 판정이다. 그러나 은닉 2짜리 모델(Train skill 0.995)과 128×2층 모델이 모두 같은 자리에 머물고, 128×2층은 규제를 풀면 Train만 외운다. 따라서 이 편향은 표현력 부족이 아니다. 과거 가격만으로는 다음 날 변화를 거의 예측할 수 없는 데이터 자체의 한계(랜덤워크에 가까운 주가, Bayes 오차 ≈ Naive)다. 처방표대로 복잡도를 올리면 분산만 커진다. 이 경우 처방은 모델이 아니라 입력 정보다. 예를 들어 거시 지표, 뉴스, 다른 종목처럼 미래와 관련된 새 정보가 필요하다.

## 시계열: 서울 일평균 기온

| 실험 | Train skill | Validation skill | 격차 | 진단 | epoch | Test MAE (°C) |
| --- | --- | --- | --- | --- | --- | --- |
| LSTM·수준값(v1) | 0.864 | 0.899 | 0.035 | 적정 (Good fit) | 115 (복원 95) | 1.5349 |
| GRU·수준값(v1) | 0.884 | 0.903 | 0.019 | 적정 (Good fit) | 98 (복원 78) | 1.5414 |
| LSTM·변화량(v2) | 0.497 | 0.593 | 0.095 | 적정 (Good fit) | 48 (복원 28) | 1.3973 |
| GRU·변화량(v2) | 0.546 | 0.595 | 0.049 | 적정 (Good fit) | 45 (복원 25) | 1.3999 |
| LSTM 은닉 2 | 0.576 | 0.623 | 0.047 | 적정 (Good fit) | 150 (복원 149) | 1.3925 |
| LSTM 128×2 (규제 없음) | 0.008 | 0.895 | 0.887 | High Variance (Overfitting) | 100 (복원 100) | 1.7554 |
| LSTM 128×2 + 규제 ★ | 0.552 | 0.595 | 0.044 | 적정 (Good fit) | 34 (복원 14) | 1.4005 |

★ = Validation MAE로 고른 최종 모델. skill과 epoch은 대표 seed(Validation 손실 최저) 기준, Test MAE는 seed 평균이다.

**관찰과 처방**

1. **v1 수준값 → v2 변화량**: v1 LSTM은 적정 (Good fit)로 진단됐다 (Train skill 0.864, Validation skill 0.899). 출력을 변화량으로 바꾸자 Test MAE가 1.5349 → 1.3973로 9.0% 줄었다.
2. **분산 확인 → 정규화**: 은닉 128×2층을 규제·조기 종료 없이 100 epoch 학습하면 Train skill 0.008, Validation skill 0.895으로 격차 0.887의 High Variance (Overfitting)가 된다. Dropout 0.3, Weight decay 1e-4, 조기 종료를 적용하면 진단이 적정 (Good fit)로 바뀌고, Test MAE가 1.7554 → 1.4005로 20.2% 줄었다.
3. **작은 모델로 충분하다**: 은닉 2짜리 모델도 적정 (Good fit)이고, Test MAE 1.3925로 큰 모델과 비슷하다. 기온의 하루 변화는 소수의 선형에 가까운 관계(계절, 전날 변화, 기압·습도)로 대부분 설명된다는 뜻이다. v2 LSTM은 Train skill 0.497, Validation skill 0.593로 적정 (Good fit)다.

## 이미지: Few-shot 전이 학습 (꽃 8종)

| 사진 수/클래스 | 전략 | Train 정확도 | Validation 정확도 | Test 정확도 | 격차(오류율) | 진단 |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | Linear Probing(fc만) | 100.0% | 86.2% | 92.3% | 0.138 | High Variance (Overfitting) |
| 5 | 부분 미세 조정(layer4+fc) | 100.0% | 92.5% | 94.2% | 0.075 | High Variance (Overfitting) |
| 5 | 전체 Fine-tuning | 100.0% | 93.8% | 91.4% | 0.062 | High Variance (Overfitting) |
| 10 | Linear Probing(fc만) | 100.0% | 91.2% | 95.4% | 0.087 | High Variance (Overfitting) |
| 10 | 부분 미세 조정(layer4+fc) | 100.0% | 96.2% | 97.8% | 0.037 | 적정 (Good fit) |
| 10 | 전체 Fine-tuning | 100.0% | 96.2% | 98.2% | 0.037 | 적정 (Good fit) |
| 20 | Linear Probing(fc만) | 100.0% | 96.2% | 95.7% | 0.037 | 적정 (Good fit) |
| 20 | 부분 미세 조정(layer4+fc) | 100.0% | 96.2% | 98.2% | 0.037 | 적정 (Good fit) |
| 20 | 전체 Fine-tuning ★ | 100.0% | 98.8% | 97.5% | 0.013 | 적정 (Good fit) |
| 20 | 직접 학습(무작위 초기화) | 95.6% | 80.0% | 85.2% | 0.156 | High Variance (Overfitting) |

★ = 주 모델 (가장 많은 사진 수에서 Validation 정확도가 가장 높은 사전학습 모델). 모두 seed 0 한 번씩이다.

**관찰과 처방**

1. **사진이 적을수록 분산이 크다.** 사전학습 모델은 모두 Train 정확도 100%에 이르고, 격차(Validation − Train 오류율)는 5장 0.062~0.138, 10장 0.037~0.087, 20장 0.013~0.037다. 5장에서는 모든 전략이 High Variance였고, 사진을 늘리자 격차가 줄었다(처방 '데이터↑'의 효과).
2. **Freezing 범위: 교과서 규칙과 다른 결과.** 흔한 규칙은 '데이터가 아주 적으면 분류기만(Linear Probing)'이다. 이 실험에서 Linear Probing은 어느 사진 수에서도 Validation 최선이 아니었고, 사진이 가장 적은 5장에서 오히려 차이가 가장 컸다(LP vs 몸통까지 학습한 최선: 5장 86.2% vs 93.8%, 10장 91.2% vs 96.2%, 20장 96.2% vs 98.8%). 이유로 세 가지를 본다. (1) ImageNet에는 민들레·머위 같은 클래스가 없어서, 마지막 블록의 특징이 이 둘을 가르도록 다듬어져 있지 않다(도메인 차이). (2) 몸통 학습률을 분류기의 1/10(1e-4)로 두고 epoch을 20~30회로 제한한 것 자체가 강한 규제로 작용해, 5장에서도 미세 조정이 무너지지 않았다. (3) 얼린 BatchNorm이 작은 미니배치 통계로 흔들리지 않는다. 결론: 최적 범위는 데이터 크기만이 아니라 사전학습 도메인과의 거리로도 정해진다. 이 데이터에서는 layer4+fc(부분)가 모든 사진 수에서 최선이거나 그에 가까운 안전한 선택이었다.
3. **Validation의 해상도 한계**: Validation은 80장이라 1장이 1.25%p다. 전략 간 차이가 1~2장이면 seed를 바꿨을 때 순위가 바뀔 수 있다. 그래서 오차 분석 처방은 seed 3개로 다시 쟀다.
4. **직접 학습 대비 사전학습의 효용**: 같은 20장에서 무작위 초기화 ResNet18은 Test 85.2%(High Variance (Overfitting))이고, 주 모델은 97.5%다. Train 오류율도 0이 되지 못했다. 사진 160장으로는 1,100만 개 파라미터를 처음부터 배울 수 없다. 8종 중 몇 종은 색(분홍 오스테오스페르뭄, 줄무늬 가자니아)만으로 구별되기 때문에 85%까지는 나온다.
5. **오차 분석 기반 처방**: 오분류의 주 원인 '클래스 유사성'에 맞춰 입력 해상도 160 → 224px (주 모델이 이미 전체 미세 조정이라 범위는 그대로)을 적용했다. Test 정확도(seed 3개 평균)가 97.8% → 99.2% (+1.3%p)로 바뀌었다. 자세한 내용은 `reports/ERROR_ANALYSIS.md`에 있다.
