# 검증 리포트: Gradient Checking

[README](../README.md) · [실험 리포트](EXPERIMENT_REPORT.md)

재현 명령은 `uv run python scripts/gradient_check.py`다. 실행 로그 전체는 [gradient_check.log](gradient_check.log), 수치는 [gradient_check.json](gradient_check.json)에 있다. 모든 검사를 통과하면 종료 코드 0, 하나라도 실패하면 1을 낸다.

## 결론

연산·레이어·손실·전체 모델의 텐서 38개 모두 상대 오차 1e-7 미만이다. 최대 상대 오차는 **5.2e-11**(CrossEntropyLoss)로, 기준보다 세 자릿수 이상 작다.

## 방법

| 항목 | 설정 |
| --- | --- |
| 수치 기울기 | 중심차분 `[f(x+ε) − f(x−ε)] / (2ε)`, ε = 1e-5. 원소마다 하나씩 움직인다 |
| 해석 기울기 | `loss.backward()` 한 번으로 얻은 `.grad` |
| 비교 지표 | 상대 오차 `‖a − n‖₂ / (‖a‖₂ + ‖n‖₂)`. 텐서 전체를 한 번에 비교한다 |
| 기준 | 1e-7 미만 |
| 자료형 | float64 |
| 로그 대표값 | 텐서에서 \|analytic\|이 가장 큰 원소의 두 기울기 |

설계에서 고려한 점은 다음과 같다.

- **무작위 투영 손실**: 레이어 하나를 검사할 때 손실을 `L = Σ layer(x) ⊙ R`로 둔다(R은 고정된 무작위 행렬). `Σ layer(x)`를 쓰면 모든 출력이 같은 기울기를 받는다. 그러면 Softmax처럼 출력 합이 상수인 레이어는 기울기가 0이 되어 아무것도 검사하지 못한다.
- **꺾이는 점 회피**: ReLU·LeakyReLU·ELU의 입력은 0에서 0.05 이상 떨어뜨렸다. x가 0에서 ε 안에 있으면 x±ε가 꺾임의 양쪽에 걸려, 구현이 맞아도 수치 미분이 틀린 값을 낸다.
- **Dropout 마스크 고정**: 손실을 계산할 때마다 같은 seed로 난수 생성기를 되돌린다. f(x+ε)와 f(x−ε)가 같은 마스크를 쓰게 하기 위해서다.
- **편향 흔들기**: MLP 검사에서는 0으로 초기화된 편향에 작은 잡음을 더했다. 모든 매개변수가 일반적인 위치에서 검사되도록 하기 위해서다.
- **브로드캐스팅**: `(4,3)`과 `(3,)`, `(4,1)`처럼 shape가 다른 피연산자로 검사해 `unbroadcast`의 기울기 합산을 확인했다.

## 결과

| 묶음 | 대상 | 검사한 텐서 | 최대 상대 오차 |
| --- | --- | ---: | ---: |
| 기본 연산 | Add, Sub, Mul, Div (브로드캐스팅), MatMul, Pow, Exp, Log, Sum, Mean, Reshape+Transpose, Getitem, 재사용 노드 | 19 | 3.9e-11 |
| 레이어 | Linear (입력·W·b), ReLU, Sigmoid, Softmax, Tanh, LeakyReLU, ELU, Dropout | 10 | 3.2e-11 |
| 손실 | MSE, BCE, BCEWithLogits, CrossEntropy, Softmax+NLL | 5 | 5.2e-11 |
| 전체 모델 | Linear_1 → ReLU → Linear_2 → CrossEntropy의 W·b 4개 | 4 | 4.3e-11 |
| 합계 | | **38** | **5.2e-11** |

미션의 로그 예시와 같은 형식의 발췌다.

```text
[Pass] Linear.W                     Gradient Check - Analytic:  3.759488, Numerical:  3.759488, Diff: 9.8e-12
[Pass] Linear.b                     Gradient Check - Analytic:  3.436624, Numerical:  3.436624, Diff: 3.3e-12
[Pass] Softmax.input                Gradient Check - Analytic:  0.397244, Numerical:  0.397244, Diff: 3.2e-11
[Pass] Linear_1.W                   Gradient Check - Analytic: -0.264922, Numerical: -0.264922, Diff: 4.3e-11
[Pass] Linear_2.W                   Gradient Check - Analytic: -0.268260, Numerical: -0.268260, Diff: 2.9e-11
All 38 gradient checks passed! Maximum difference: 5.2e-11 < 1e-07 ✓  (CrossEntropyLoss.logits)
```

## 검사가 버그를 잡는다는 증거 (음성 대조)

통과만 보여서는 검사가 너무 느슨한지 알 수 없다. 그래서 `tests/test_tensor.py`의 `test_wrong_backward_fails_the_check`에서 `x²`의 미분을 `2x` 대신 `x`로 일부러 틀리게 넣었다. 상대 오차가 이론값 `‖x − 2x‖ / (‖x‖ + ‖2x‖) = 1/3`로 나와 검사가 실패한다. 실제 버그는 보통 1e-3 이상의 오차를 만든다. 올바른 구현의 1e-11과는 여덟 자릿수 이상 차이가 난다.

## 함께 실행되는 테스트

`uv run python -m unittest discover -s tests -v`는 32개 테스트를 실행한다. 그중 검증과 관련된 것은 다음과 같다.

| 테스트 | 확인하는 것 |
| --- | --- |
| `test_gradient_check_all_layers_below_1e7` | 위 38개 검사를 다시 실행하고, 필수 레이어 8종이 모두 포함되었는지 확인 |
| `test_wrong_backward_fails_the_check` | 음성 대조 |
| `test_chain_rule_scalar`, `test_four_operations`, `test_matmul_gradient_shapes_and_values` | 손으로 계산한 값과 비교 |
| `test_broadcast_gradient_is_summed`, `test_reused_node_accumulates` | 브로드캐스팅 합산과 기울기 누적 |
| `test_deep_graph_has_no_recursion_limit` | 5,000단 그래프에서 역전파 |
| `test_cross_entropy_gradient_is_softmax_minus_onehot` | CE의 기울기가 `(softmax − onehot)/N`인지 |
| `test_bce_with_logits_matches_and_survives_saturation` | 두 BCE의 값이 같고, 포화 시 분리형만 기울기가 0이 되는지 |

## 검증 환경

| 환경 | 결과 |
| --- | --- |
| Windows 11, Python 3.12.13, NumPy 2.5.4, Matplotlib 3.11.2 (`uv.lock`) | 검사 38개, 테스트 32개 통과 |
| Windows 11, Python 3.10.21, NumPy 1.23.5, Matplotlib 3.6.3 (최소 버전) | 테스트 32개 통과 |
