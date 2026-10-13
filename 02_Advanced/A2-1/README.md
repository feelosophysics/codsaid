# A2-1 — AI 수학과 학습 원리

AI 모델이 학습하는 과정을 선형대수·미적분·확률통계로 나누어 NumPy로 직접 구현한다. 행렬 변환과 고유값·SVD, 수치 미분과 Gradient, 2층 신경망 역전파, 경사하강법과 Momentum, 손실 함수와 최대우도추정(MLE)의 연결을 코드·그림·노트북으로 확인한다. 선택 보너스 3종(Adam, Newton Method, 정보 이론)도 포함한다.

계산은 NumPy, 시각화는 Matplotlib만 사용한다. 자동 미분 라이브러리와 scikit-learn은 사용하지 않는다. `np.linalg.eig`는 Power Iteration 결과를 비교하는 검증 함수에서만 호출한다.

## 실행

환경은 [uv](https://docs.astral.sh/uv/)로 관리한다. 이 README가 있는 A2-1 폴더에서 실행한다.

```powershell
uv sync
uv run python -m src.run_all
uv run python -m unittest discover -s tests -v
```

`uv sync`는 `.python-version`(3.12)과 `uv.lock`에 맞춰 `.venv`를 만들고 노트북 도구(dev 그룹)까지 설치한다. `src.run_all`은 모든 실험을 `np.random.seed(42)`로 실행하고 그림 19개와 수치 요약 `summary.json`을 `outputs/`에 저장한다. 테스트 32개는 미션의 수치 기준을 그대로 검사한다.

노트북은 VS Code나 Jupyter에서 `.venv`의 Python을 커널로 선택해 처음부터 실행한다. 별도 Jupyter 설치 없이 두 노트북을 실행하고 출력을 저장하려면:

```powershell
uv run python tools/execute_notebooks.py
```

uv가 없는 환경에서는 `pip install -r requirements.txt`로 계산·시각화 라이브러리만 설치할 수 있다. 의존성의 원본은 `pyproject.toml`이며 `requirements.txt`는 같은 최소 버전을 적은 사본이다.

| 검증 조합 | 결과 |
| --- | --- |
| Windows, Python 3.12.14, NumPy 2.5.4, Matplotlib 3.11.2 (`uv.lock`) | 테스트 32개, 전체 실험, 노트북 2개, HTML 검증 통과 |
| Windows, Python 3.8.20, NumPy 1.21.6, Matplotlib 3.4.3 (미션 최소 버전) | 테스트 32개, 전체 실험 통과 |

## 구조

| 경로 | 내용 |
| --- | --- |
| `src/linear_algebra.py` | 회전·스케일링·전단 행렬, 행렬식과 신발끈 면적, Power Iteration, SVD 압축과 시각화 |
| `src/calculus.py` | 중심차분 미분, 다변수 Gradient·Hessian, 등고선–Gradient 수직 검증과 시각화 |
| `src/neural_net.py` | 2층 신경망 순전파·역전파, BCE, 고정 손계산 예제 |
| `src/optimizer.py` | `VanillaGD`, `Momentum`, `Adam`, `NewtonMethod` 클래스, 테스트 함수, 수렴 경로 시각화 |
| `src/probability.py` | 정규분포 PDF, 베르누이 PMF, 소프트맥스, MSE·가우시안 NLL·BCE·Categorical CE |
| `src/information.py` | 엔트로피, Cross-Entropy, KL-Divergence (보너스) |
| `src/run_all.py` | 전체 실험 실행, 그림과 `summary.json` 저장 |
| `notebooks/backprop_derivation.ipynb` | 역전파 수식 유도, 고정 예제 손계산, NumPy·수치 미분 검증 |
| `notebooks/probability_loss.ipynb` | 분포 시각화, 소프트맥스, MSE–MLE·CE–MLE 유도, 정보 이론 |
| `tests/test_requirements.py` | 요구사항별 수치 검증 32개 |
| `data/grace_hopper_128.png` | SVD 실험용 128x128 흑백 이미지 |
| `tools/prepare_image.py` | 위 이미지를 만드는 전처리 |
| `tools/execute_notebooks.py` | 두 노트북을 실행하고 출력 저장 |
| `study/a2-1.html` | 탑다운 HTML 학습 자료 (`tools/build_study_guide.py`로 생성, `tools/verify_study_guide.py`로 검증) |
| `pyproject.toml`, `uv.lock`, `.python-version` | uv 환경 정의 |
| `requirements.txt` | uv 없이 설치할 때 쓰는 의존성 목록 |

## 주요 결과

### 1. 선형대수

| 변환 | det | 변환 후/전 면적비 | 오차 |
| --- | ---: | ---: | ---: |
| 회전 R(45°) | 1.0000 | 1.0000 | 0% |
| 스케일링 S(2, 0.5) | 1.0000 | 1.0000 | 0% |
| 전단 Sh(1.0) | 1.0000 | 1.0000 | 6.7e-14% |
| 일반 [[2,1],[1,3]] | 5.0000 | 5.0000 | 0% |
| 반사+스케일 [[0,2],[1,0]] | −2.0000 | 2.0000 | 0% |

요구된 세 변환은 모두 det=1인 면적 보존 변환이다. 그래서 det≠1인 두 행렬로도 `|det| = 면적비`를 확인했다. 음수 행렬식은 면적이 아니라 방향이 뒤집힌다는 뜻이다. 면적은 100개 점으로 만든 다각형의 신발끈 공식으로 계산했다. 선형 변환은 모든 도형의 면적을 같은 비율로 바꾸므로, 다각형 근사에서도 면적비는 |det|와 정확히 같다.

- 그림: [세 변환 비교](outputs/04_transforms_overview.png), [회전](outputs/01_rotation.png), [스케일링](outputs/02_scaling.png), [전단](outputs/03_shear.png)
- Power Iteration, A=[[4,1],[1,3]]: tol=1e-6에서 23회 만에 λ=4.6180, v=[0.8507, 0.5257]. `np.linalg.eig`와 고유값 오차 3.8e-11%, 고유벡터 각도 차 5.1e-5°다. 오차는 (λ₂/λ₁)^(2t)로 줄어든다 ([그림](outputs/05_power_iteration.png)). 6x6 무작위 대칭 행렬에서도 26회 만에 일치했다.
- SVD 압축, 128x128 이미지 ([그림](outputs/06_svd_compression.png), [특이값](outputs/07_singular_values.png)):

| k | 저장 비율 | 에너지 보존 | 상대 오차 | PSNR |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 0.157 | 95.41% | 0.214 | 20.89 dB |
| 50 | 0.784 | 99.77% | 0.048 | 33.84 dB |
| 100 | 1.569 | 100.00% | 0.004 | 54.45 dB |

rank-k 근사는 U의 m·k개, σ의 k개, V의 n·k개 값을 저장한다. 128x128에서는 k < 63.75일 때만 원본보다 작다. k=100은 화질이 원본과 거의 같지만 저장량은 1.57배다.

### 2. 미적분

- f(x)=x²의 x=3 중심차분 미분값은 6.0000000000이고, 해석적 미분값 6과의 오차는 3.9e-11이다.
- 등고선 위 점에서 Gradient와 등고선 접선의 |cos|는 최대 9.6e-12다. 두 방향을 독립적으로 구했다. 접선은 등고선 위 이웃 점의 차이, Gradient는 수치 미분으로 계산했다 ([그림](outputs/08_gradient_field.png)). 그림은 축 비율을 같게 맞춰야 수직이 그대로 보인다.
- h를 줄이면 절단 오차가 줄지만, 지나치게 작으면 반올림 오차가 커진다. 중심차분의 오차는 h≈1e-5 부근에서 가장 작다 ([그림](outputs/09_derivative_error.png)).

### 3. 역전파 (x=[1,0], y=1)

| 값 | shape | 결과 |
| --- | --- | --- |
| z1, a1 | (2,) | [0.1, 0.3], [0.5250, 0.5744] |
| z2, ŷ, L | () | 0.6072, 0.6473, 0.4350 |
| ∂L/∂ŷ, ∂L/∂z2 | () | −1.5449, −0.3527 |
| ∂L/∂W2, ∂L/∂a1 | (2,) | [−0.1852, −0.2026], [−0.1764, −0.2116] |
| ∂L/∂z1 | (2,) | [−0.0440, −0.0517] |
| ∂L/∂W1 | (2,2) | [[−0.0440, 0], [−0.0517, 0]] |

손계산과 NumPy 결과는 소수점 4자리까지 모두 일치한다. 수치 미분과의 최대 차이는 1.1e-11이다. 정답 값은 결과 예시와 같은 y=1로 정했다. 결과 예시의 ∂L/∂z1 두 번째 값은 −0.0513이지만, −0.2116×0.2445 = −0.0517이므로 이 구현은 −0.0517을 사용한다.

### 4. 최적화 (시작점 (5, 5))

- **Vanilla GD, x²+y², lr=0.1, 100회**: (1.0e-9, 1.0e-9)에 도달해 반경 0.1 조건을 만족한다 ([그림](outputs/10_gd_quadratic.png)).
- **학습률과 발산** ([그림](outputs/11_lr_divergence.png)): x²+y²에서는 x_{t+1} = (1−2·lr)·x_t이므로 lr<1이면 수렴한다. lr=1이면 같은 크기로 진동하고, lr>1이면 발산한다. 따라서 lr=0.5는 발산하지 않고 한 번에 원점에 도달한다. 발산 그래프는 lr=1.1(100회 후 ‖θ‖=5.9e8)과 x²+10y²의 lr=0.5(|1−20·0.5|=9, 20회 후 6.1e19)로 보였다. 일반적인 안정 조건은 lr < 2/최대 곡률이다.
- **Momentum(β=0.9)**:

| 함수, lr | VanillaGD | Momentum |
| --- | --- | --- |
| x²+y², 0.1: 100회 후 ‖θ‖ | 1.4e-9 | 2.0e-2 |
| x²+10y², 0.01: 100회 후 ‖θ‖ | 0.663 | 0.026 |
| x²+10y², 0.09: 100회 후 ‖θ‖ | 1.2e-8 | 0.025 |

x²+10y²에서 lr이 작으면 GD는 완만한 x 방향으로 천천히 이동한다. Momentum은 같은 방향의 기울기를 누적해 25배 이상 가까이 도달한다. ‖θ‖<1e-3까지 반복 수는 lr=0.002에서 GD 2126회, Momentum 149회다. 그러나 lr을 GD의 한계 가까이 키우면 GD가 더 빠르다. β=0.9에서는 Momentum의 수렴률이 약 √β≈0.95로 제한되기 때문이다 ([그림](outputs/13_gd_vs_momentum_elliptic.png), [x²+y² 비교](outputs/12_gd_vs_momentum_quadratic.png)). β=0.9는 조건수가 훨씬 큰 골짜기에 맞는 값이다. 조건수가 10인 이 함수에서는 관성이 과해 진동한다.

### 5. 확률/통계

- 정규분포 N(0,1)·N(2,0.5)의 PDF와 베르누이 B(0.3)·B(0.7)의 PMF를 각각 한 Figure에 그렸다 ([PDF](outputs/16_normal_pdf.png), [PMF](outputs/17_bernoulli_pmf.png)). N(μ, σ²) 표기에 따라 0.5는 분산(σ≈0.707)으로 처리했다.
- 소프트맥스 출력의 합과 1의 차이는 0이며, 기준은 1e-6이다. 최댓값을 빼는 안정화로 [1000, 1001, 1002]도 overflow 없이 계산한다.
- MSE 최소화와 가우시안 NLL 최소화의 최적 w는 1.505로 같다. BCE 최소화와 베르누이 우도 최대화의 최적 w도 1.745로 같다 ([그림](outputs/18_loss_mle.png)). 수식 유도는 노트북에 있다.

## 보너스

| 과제 | 결과 |
| --- | --- |
| Adam | 같은 lr=0.1에서 x²+10y²의 GD는 y 방향에서 영원히 진동한다(1−20·0.1=−1). Adam은 좌표별 기울기 크기로 나누므로 144회 만에 1e-3에 도달한다. Momentum은 159회가 걸린다. 첫 이동 폭이 곡률과 무관하게 좌표마다 lr이다 ([그림](outputs/14_adam_comparison.png)). |
| Newton Method | x²+10y²에서 1회 만에 최솟값에 도달한다. Rosenbrock에서는 Newton 5회, GD(lr=0.001) 17,695회가 걸린다. 대신 Hessian 계산·풀이 비용이 들고, x²−y²에서는 안장점으로 곧장 이동한다. 같은 위치에서 GD는 안장점에서 벗어난다 ([그림](outputs/15_newton_method.png)). |
| 정보 이론 | p=[0.7,0.2,0.1], q=[0.4,0.4,0.2]에서 H(p)=0.8018, H(p,q)=0.9856, KL(p‖q)=0.1838, KL(q‖p)=0.1920이다. H(p,q)=H(p)+KL(p‖q)이고, KL은 대칭이 아니다 ([그림](outputs/19_information_theory.png)). |

## 해석 결정

미션 설명이 비어 있거나, 서로 충돌하거나, 수학적으로 성립하지 않는 부분은 아래처럼 처리했다. 근거는 위 결과 섹션과 HTML 학습 자료 14장에 있다.

| 항목 | 미션 설명 | 이 구현의 처리 | 이유 |
| --- | --- | --- | --- |
| 손계산 정답 y | 값이 비어 있음 | y = 1 | 결과 예시가 y = 1을 사용 |
| SVD 이미지 크기 | 64x64 이하 권장, k=10·50·100 비교 | 128x128 흑백 | 64x64는 rank가 최대 64라 k=100 비교가 불가능 |
| N(2, 0.5) | 두 번째 값의 의미가 명시되지 않음 | 분산 0.5 (σ≈0.707) | N(μ, σ²) 표준 표기 |
| 발산 확인 | "lr=0.5 이상에서 발산" | x²+y²의 실제 경계 lr=1을 보이고, 발산은 lr=1.1과 x²+10y²의 lr=0.5로 제시 | x²+y²에서 lr=0.5는 (1−2·0.5)=0이라 한 번에 수렴 |
| Momentum 이점 | 타원에서 이점 확인 | 작은 lr(0.01)에서 이점을 보이고, 큰 lr(0.09)에서 GD가 더 빠른 결과도 함께 기록 | β=0.9의 수렴률은 √β≈0.95에서 더 좋아지지 않음 |
| 역전파 결과 예시 | ∂L/∂z1 = [−0.0440, −0.0513] | [−0.0440, −0.0517] | −0.2116×0.2445 = −0.0517, NumPy·수치 미분도 같음 |
| 회전 R(θ), 전단 Sh(k) | θ, k 값이 지정되지 않음 | θ=45°, x 방향 전단 k=1 | 변환이 그림에서 잘 보이는 값 |
| det와 면적비 | 세 변환으로 확인 | det=5, det=−2 행렬을 추가로 확인 | 요구된 세 변환은 모두 det=1이라 관계를 구별하지 못함 |

## 데이터

SVD 실험 이미지는 Matplotlib 배포본의 `sample_data/grace_hopper.jpg`(Grace Hopper 제독의 미 해군 공식 초상, 퍼블릭 도메인)를 사용했다. 위쪽 512x512를 흑백으로 바꾸고 4x4 블록 평균으로 128x128로 줄였다(`tools/prepare_image.py`). 64x64 이하에서는 rank가 최대 64라서 k=100 비교가 불가능하다. 그래서 k=10, 50, 100을 모두 의미 있게 비교할 수 있는 128x128을 사용했다.

## HTML 학습 자료

[`study/a2-1.html`](study/a2-1.html)을 브라우저에서 연다. 학습 루프 전체를 먼저 보고 각 수학 부품으로 내려가는 탑다운 순서로 구성했다. 생성·검증 방법은 [`study/README.md`](study/README.md)에 있다.

## 과정 내 위치

[심화 과정 목차](../README.md) · [전체 과정](../../README.md)
