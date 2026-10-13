# A6-1 — minigrad: NumPy로 만든 미니 딥러닝 프레임워크

[심화 과정 목차](../README.md)

## 프로젝트 개요

`minigrad`는 NumPy만으로 구현한 작은 딥러닝 프레임워크다. PyTorch처럼 연산을 실행하는 순간 계산 그래프가 만들어지고(define-by-run), `backward()` 한 번으로 모든 매개변수의 기울기가 연쇄 법칙에 따라 채워진다.

이 프로젝트는 「구현 → 검증 → 실험」 순서로 진행한다.

1. **구현**: Tensor·AutoGrad 엔진, 레이어, 초기화, 손실, 옵티마이저, 데이터 로더
2. **검증**: 모든 연산과 레이어의 역전파를 수치 미분과 비교한다(Gradient Checking, 상대 오차 1e-7 미만).
3. **실험**: 초기화(Zero/Random/He/Xavier)가 학습에 미치는 영향, XOR·MNIST 학습, 보너스로 Dropout·L2·추가 활성화 함수

딥러닝 전용 라이브러리(PyTorch, TensorFlow)와 자동 데이터 로더는 쓰지 않는다. MNIST는 IDX(UBYTE) 바이너리를 직접 파싱한다. Matplotlib은 그림을 그리는 스크립트에서만 쓴다.

## 설치 방법

Python 3.10 이상이 필요하다. 환경은 [uv](https://docs.astral.sh/uv/)로 관리한다. 이 README가 있는 폴더에서 실행한다.

```powershell
uv sync
```

`uv sync`는 `.python-version`(3.12)과 `uv.lock`에 맞춰 `.venv`를 만들고, `minigrad` 패키지(`src/minigrad`)를 편집 가능 모드로 설치한다. uv가 없으면 다음처럼 설치한다.

```powershell
pip install -r requirements.txt
```

`requirements.txt`는 `pyproject.toml`의 의존성을 옮긴 사본이며, 마지막 줄 `-e .`가 패키지 자체를 설치한다.

MNIST(약 11MB)는 처음 필요할 때 `data/mnist/`에 자동으로 내려받는다. 파일마다 SHA-256으로 검증하고 git에는 넣지 않는다. 미리 받아 두려면 `uv run python scripts/download_mnist.py`를 실행한다.

## 실행 방법

전체를 순서대로 실행한다. 단일 스레드 기준 약 5분 걸린다.

```powershell
uv run python scripts/run_all.py
```

스크립트를 하나씩 실행하려면 아래 순서를 따른다.

| 순서 | 명령 | 하는 일 | 결과 |
| --- | --- | --- | --- |
| 1 | `uv run python scripts/gradient_check.py` | 연산 13종, 레이어 8종, 손실 5종, 2층 MLP 전체의 역전파를 수치 미분과 비교 | `reports/gradient_check.log` |
| 2 | `uv run python scripts/train_xor.py` | He 초기화로 XOR 학습. `--init zero`이면 학습 실패를 재현 | `reports/train_xor_*.log` |
| 3 | `uv run python scripts/init_experiment.py` | 초기화 비교: XOR seed 20개, 대칭성, 10층 망의 기울기 소실·폭주, MNIST, 민감도 | `figures/init_*.png`, `reports/init_experiment.log` |
| 4 | `uv run python scripts/train_mnist.py` | MNIST 1 epoch 분류. `--epochs 5`, `--optimizer adam`으로 바꿀 수 있다 | `figures/mnist_training.png` |
| 5 | `uv run python scripts/bonus_activations.py` | 보너스: Tanh·LeakyReLU·ELU의 도함수, 깊은 망 기울기, Two Moons 비교 | `figures/bonus_activations.png` |
| 6 | `uv run python scripts/bonus_regularization.py` | 보너스: Inverted Dropout과 L2의 과적합 억제 | `figures/bonus_regularization.png` |

테스트는 미션 체크리스트와 단위 동작을 검사한다. MNIST 파일이 없으면 MNIST 테스트 1개는 건너뛴다.

```powershell
uv run python -m unittest discover -s tests -v
```

모든 실험은 seed를 고정한다. 같은 환경에서 다시 실행하면 같은 숫자가 나온다.

## 모듈 구조

저장소의 폴더 구성은 다음과 같다.

| 경로 | 내용 |
| --- | --- |
| `src/minigrad/` | 프레임워크 소스 (아래 상세) |
| `scripts/` | 검증·학습·실험 스크립트와 `run_all.py` |
| `tests/` | 단위 테스트와 미션 체크리스트 테스트 32개 |
| `figures/` | 초기화 비교 등 그림 6개 |
| `reports/` | 검증·실험 리포트, 실행 로그(`*.log`), 수치(`*.json`) |
| `study/` | 단일 HTML 학습 자료와 그 편집 원본 |
| `tools/` | 학습 자료 빌드·검증 도구 |
| `pyproject.toml`, `uv.lock`, `.python-version` | uv 환경 정의 |
| `requirements.txt` | uv 없이 설치할 때 쓰는 의존성 목록 |

```text
src/minigrad/
├── core/
│   ├── tensor.py     Tensor(data, grad, _backward, _prev, _op)와 연산별 국소 미분
│   └── autograd.py   위상 정렬과 역전파 엔진, no_grad
├── nn/
│   ├── layers.py     Module, Parameter, Linear, ReLU, LeakyReLU, ELU, Sigmoid, Tanh, Softmax, Dropout, Sequential
│   ├── init.py       zero, random, he, xavier 초기화
│   └── losses.py     MSE, BCE, BCEWithLogits, CrossEntropy, NLL
├── optim/
│   ├── optimizer.py  공통 부분 (zero_grad, L2 weight decay)
│   ├── sgd.py        SGD (+momentum)
│   └── adam.py       Adam (편향 보정)
├── data/
│   ├── mnist.py      MNIST 내려받기·SHA-256 검증·IDX 파싱
│   └── loader.py     DataLoader, XOR, Two Moons
└── gradcheck.py      수치 미분, 상대 오차, check_gradients
```

```text
        core (Tensor, autograd)          ← NumPy만 사용
          ▲            ▲
          │            │
   nn (레이어·손실)   gradcheck
          ▲
          │ Parameter를 넘겨받음
   optim (SGD, Adam)          data (NumPy만 사용, 다른 모듈과 독립)
```

- **core**: 다른 모듈을 모른다. Tensor 연산이 그래프를 만들고 `autograd.backward`가 그 그래프를 거꾸로 훑는다.
- **nn**: core의 Tensor 연산을 조합해 레이어를 만든다. 레이어에는 역전파 코드가 없다. Linear의 기울기는 `@`와 `+` 연산의 `_backward`에서 나온다.
- **optim**: `.data`와 `.grad`가 있는 매개변수 목록만 받는다. nn을 import하지 않는다.
- **data**: Tensor가 아닌 NumPy 배열을 돌려준다. 학습 루프에서 `Tensor(xb)`로 감싼다.

## 사용 예시

### Tensor 생성 → 연산 → backward

```python
from minigrad import Tensor

x = Tensor(2.0, requires_grad=True)
y = Tensor(3.0, requires_grad=True)
loss = (x * y + y) ** 2      # 연산마다 그래프 노드가 생긴다
loss.backward()              # dL/dL = 1에서 시작해 연쇄 법칙으로 전파
print(loss.item(), x.grad, y.grad)   # 81.0  54.0  54.0
```

`(x*y + y)² = 81`이다. `∂L/∂x = 2(xy+y)·y = 54`, `∂L/∂y = 2(xy+y)(x+1) = 54`다.

### 모델 학습

```python
import numpy as np
from minigrad import Tensor, nn, optim
from minigrad.data import xor_dataset

X, y = xor_dataset()
model = nn.Sequential(
    nn.Linear(2, 32, init="he"), nn.ReLU(),
    nn.Linear(32, 32, init="he"), nn.ReLU(),
    nn.Linear(32, 1, init="he"), nn.Sigmoid(),
)
opt = optim.Adam(model.parameters(), lr=0.01)
for epoch in range(100):
    loss = nn.binary_cross_entropy(model(Tensor(X)), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
```

초기화는 `init="zero" | "random" | "he" | "xavier"`로 고른다. `nn.mlp([2, 32, 32, 1], init="he", output=nn.Sigmoid)`처럼 한 줄로 만들 수도 있다.

### Gradient Checking

```python
import numpy as np
from minigrad import Tensor, nn
from minigrad.gradcheck import check_gradients

layer = nn.Linear(5, 3)
x = Tensor(np.random.randn(4, 5), requires_grad=True)
for r in check_gradients(lambda: (layer(x) ** 2).sum(), [x, layer.W, layer.b], ["x", "W", "b"]):
    print(r.line())   # [Pass] W  Gradient Check - Analytic: ..., Numerical: ..., Diff: 1.2e-11
```

## 실험 결과 요약

상세한 수치와 해석은 [검증 리포트](reports/VERIFICATION_REPORT.md)와 [실험 리포트](reports/EXPERIMENT_REPORT.md)에 있다.

### Gradient Check — 통과

연산·레이어·손실·전체 모델의 텐서 38개를 검사했다. 모두 상대 오차 1e-7 미만이고, 최대값은 5.2e-11(CrossEntropy)이다. 일부러 틀린 역전파(2x 대신 x)를 넣으면 상대 오차가 1/3로 실패하는 것도 테스트로 확인했다.

### 초기화 실험

XOR(2-32-32-1, ReLU, Adam lr=0.01, seed 20개의 중앙값)

| Initialization | Epoch 5 Loss | Epoch 50 Loss | 100 epoch 내 Loss < 0.1 | Converged? |
| --- | ---: | ---: | ---: | --- |
| Zero | 0.6931 | 0.6931 | 0/20 | No (Stuck, 변화량 정확히 0) |
| Random N(0,1) | 0.7028 | 0.0036 | 17/20 | 대부분 빠름, 3개 seed는 포화로 정지 |
| He | 0.4877 | 0.0082 | 20/20 | Yes (모든 seed) |
| Xavier (선택) | 0.6175 | 0.0123 | 20/20 | Yes (모든 seed) |

![초기화 비교](figures/init_comparison.png)

- **Zero**: 모든 은닉 뉴런이 같은 값을 갖고 같은 기울기를 받는다(대칭성). ReLU에서는 그 값이 0이라 기울기 자체가 0이다. loss는 ln 2 = 0.6931에서 1e-16도 움직이지 않는다.
- **He**: seed 20개 모두 수렴했다. 결과 편차가 가장 작다.
- **Random**: 이 작은 망에서는 중앙값으로 He보다 빨리 수렴했다. 입력이 2차원이라 첫 층의 He 표준편차가 √(2/2) = 1로 Random과 같기 때문이다. 실패한 3개 seed는 초기 출력 로짓이 ±40 수준이었다. Sigmoid가 0이나 1로 포화되면서 BCE의 clip 구간 밖으로 나가 기울기가 0이 된 경우다. 안정형 BCE(로짓 입력)로 바꾸면 20/20이 성공한다.
- **규모가 커지면 차이가 커진다**: 10층 ReLU 망에서 Random은 활성값이 층마다 약 11배 커져 10층에서 2.6e10이 됐다. Xavier는 층마다 약 0.7배로 줄어 2.3e-2가 됐다(소실). He는 0.82에서 0.75로 거의 일정했다. MNIST 1 epoch에서는 Random이 첫 loss 110, 테스트 88.0%였고 He는 93.8%였다.

### XOR·MNIST

| 검증 항목 | 기준 | 결과 |
| --- | --- | --- |
| Gradient Check | 모든 레이어 상대 오차 < 1e-7 | 38/38 통과, 최대 5.2e-11 |
| XOR (He) | 100 epoch 내 Loss < 0.1 또는 정확도 ≥ 95% | epoch 30에 0.1 미만, epoch 100 loss 0.0019, 정확도 100% |
| MNIST | 1 epoch 정확도 ≥ 80% | 테스트 93.76% (784-128-10, SGD lr=0.1, 약 2초) |
| Zero Init 실패 재현 | 50 epoch 후 Loss 감소 없음 | loss 0.693147 그대로, 최대 변화량 0 |

### 보너스

- **Dropout·L2**: MNIST 1,000장으로 과적합을 만들고 하이퍼파라미터는 검증 세트로 골랐다. Dropout(p=0.2)은 테스트 정확도를 90.58%에서 91.54%로 올렸다. L2는 정확도 변화가 ±0.3%p로 작았다. 대신 가중치 노름(34.1 → λ=0.01일 때 7.9)과 테스트 손실(0.514 → 0.329)을 크게 줄였다. 과신이 줄었다는 뜻이다.
- **활성화 함수**: Tanh·LeakyReLU·ELU의 autograd 도함수가 손으로 유도한 공식과 1e-16 이내로 일치한다. 8층 망에서 Sigmoid는 입력 쪽 기울기가 출력 쪽의 1.6e-5배로 소실되었다. Two Moons 테스트 정확도는 Tanh 97.2%, ELU 97.1%, LeakyReLU 96.3%, ReLU 96.1%, Sigmoid 91.1%였다.

## 미션 자가 체크리스트

| 항목 | 확인 방법 | 결과 |
| --- | --- | --- |
| `gradient_check.py` 실행 시 모든 레이어 오차 1e-7 이하 | `scripts/gradient_check.py`, `tests/test_requirements.py` | 통과 (최대 5.2e-11) |
| Zero Init으로 학습 실패 재현 | `train_xor.py --init zero --epochs 50` | 통과 (loss 0.6931 고정) |
| He Init으로 XOR 정상 동작 | `train_xor.py` | 통과 (loss 0.0019, 정확도 100%) |
| 초기화 비교 그래프가 `figures/`에 있음 | `figures/init_comparison.png` 외 2개 | 통과 |
| README에 설치·실행 방법 명시 | 이 문서 | 통과 |
| MNIST 1 epoch 정확도 80% 이상 | `train_mnist.py` | 통과 (93.76%) |

## 구현 메모

- **float64**: 모든 텐서의 기본 자료형이다. float32에서는 ε=1e-5 중심차분의 반올림 오차가 1e-7 기준보다 커진다.
- **상대 오차**: `‖a−n‖ / (‖a‖+‖n‖)`을 텐서 단위로 계산한다. 원소별 `|a−n|/|a|`는 기울기가 0에 가까운 원소에서 의미 없이 커진다.
- **꺾이는 점**: ReLU·LeakyReLU·ELU 검사 입력은 0에서 0.05 이상 떨어뜨렸다. x가 0에서 ε 안에 있으면 x±ε가 꺾임을 넘나들어 수치 미분 자체가 틀린 값이 된다. x=0에서의 미분은 관례대로 0(LeakyReLU는 α)이다.
- **XOR의 epoch**: 샘플이 4개뿐이라 1 epoch = 전체 배치 1 스텝이다.
- **Xavier 공식**: 미션 표기 N(0, √(2/(n_in+n_out)))의 두 번째 값을 표준편차로 해석했다. He도 같다.
- **L2와 Adam**: `weight_decay`는 기울기에 λw를 더하는 고전적 L2다. AdamW의 분리형 감쇠와는 다르다.
- **손실**: 출력 Sigmoid + BCE를 분리해 쓰면 포화된 출력에서 기울기가 사라질 수 있다. 그래서 `binary_cross_entropy_with_logits`를 함께 제공한다. 다중 분류의 `cross_entropy`도 같은 이유로 log-softmax를 쓴다.

## 테스트 환경

| 환경 | 결과 |
| --- | --- |
| Windows 11, Python 3.12.13, NumPy 2.5.4, Matplotlib 3.11.2 (`uv.lock`) | 테스트 32개, 전체 스크립트, HTML 검증 통과 |
| Windows 11, Python 3.10.21, NumPy 1.23.5, Matplotlib 3.6.3 (최소 버전) | 테스트 32개 통과, 한글 그림 출력 확인 |

## 학습 자료

[study/a6-1.html](study/a6-1.html): 하나의 파일로 된 오프라인 학습 자료. 계산 그래프 단계 실행, 역전파 손계산 연습, 초기화 실험 위젯이 들어 있다.
