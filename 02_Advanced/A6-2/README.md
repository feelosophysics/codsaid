# A6-2 — 모델 오류 분석과 개선

[심화 과정 목차](../README.md)

## 프로젝트 개요

모델이 어디서 왜 틀리는지 진단하고 고치는 과정을 두 트랙에 같은 순서로 적용한다.

1. **베이스라인 설정**: 학습 없는 예측기를 먼저 측정한다.
2. **딥러닝 적용**: 시계열은 LSTM·GRU, 이미지는 ResNet18 전이 학습을 쓴다.
3. **진단**: Train/Validation 격차로 편향(High Bias)과 분산(High Variance)을 진단한다. 이미지 트랙은 오분류 사진을 사람이 직접 보고 원인을 태깅한다.
4. **개선과 정량화**: 진단에 맞는 처방을 적용하고, 효과를 베이스라인 대비 몇 %인지 숫자로 보고한다.

| 트랙 | 데이터 | 모델 |
| --- | --- | --- |
| A. Few-shot 전이 학습 | Oxford Flowers 102 중 비슷하게 생긴 데이지형 꽃 8종. 클래스당 Train 5·10·20장, Validation 10장, Test 325장 | ResNet18 (ImageNet 사전학습) — Linear Probing / 부분 미세 조정 / 전체 Fine-tuning / 직접 학습 |
| B. 시계열 예측 | AAPL 일봉 2015–2025(yfinance) + 대조군 서울 일평균 기온(Open-Meteo) | LSTM·GRU (+ 보너스 Attention·Transformer) |

딥러닝 프레임워크는 PyTorch(CPU 빌드)를 쓴다. GPU 없이 i5-13420H 노트북에서 전체를 돌릴 수 있게 설계했다.

## 계산을 따라가는 학습·시연

[notebooks/diagnosis_walkthrough.ipynb](notebooks/diagnosis_walkthrough.ipynb)를 위에서부터 실행한다.
작은 시계열의 첫 윈도우·잔차를 직접 계산한 뒤 실제 CSV의 시간 분할, Train 전용 scaler 상태,
변화량 예측의 원단위 복원, Train/Validation 진단과 모델 선택을 연결한다.
이미지는 클래스 재매핑 → 전처리 → 512차원 특징 → 8개 점수 → 오분류 순서로 확인한다.
동결된 가중치와 BatchNorm 평가 모드도 실제 상태로 대조한다.

`uv sync` 후 이 폴더 `.venv`의 Python 커널을 선택한다. 노트북에서 사용하는 꽃 캐시·ResNet18 가중치는
아래 설치 절차로 먼저 준비한다. 기본 셀은 서울 기온 LSTM/GRU와 꽃 linear probe를 2 epoch씩 실제 학습한다.
은닉 크기·표본 수·epoch이 기존 리포트와 다른 별도 실험이며 기존 성능을 재현하는 실행은 아니다.
기존 HTML은 결과 비교와 인터랙티브 설명, 노트북은 Python 배열·객체 상태 추적에 사용한다.

```powershell
uv run python tools/build_learning_notebook.py
uv run python tools/verify_learning_flow.py --execute
uv run python -m unittest discover -s tests -v
```

생성 명령은 노트북의 출력을 초기화한다. 검증 명령은 새 커널에서 실행하고 셀 원본·출력·HTML 발췌,
현재 CSV·분할과 기존 저장 예측·지표의 대응을 검사한다. 장기 학습이나 태그 검수를 대신하지 않는다.

**해석 경계**: 기존 이미지 처방은 Test 오분류를 본 뒤 선택했다. 같은 Test의 97.8%→99.2%는
탐색적 재평가이며 독립 Test 개선의 증거가 아니다. seed 3개의 표준편차만으로 통계적 유의성을 판단할 수 없다.
원인 태그는 관찰에서 만든 가설이며 사람 검수 전 초안이다. 독립 효과를 확인하려면 처방 고정 후 별도의 미열람 데이터가 필요하다.

## 결과 요약

| 데이터 | 최종 모델 (Validation으로 선택) | Test 성능 | 베이스라인 대비 |
| --- | --- | --- | --- |
| AAPL 종가 | GRU·변화량(v2) | MAE 2.434, RMSE 3.613, MAPE 1.134% | Naive 대비 MAE −0.16% (Diebold-Mariano p = 0.39) → **우수하다고 말할 수 없다** |
| 서울 일평균 기온 | LSTM 128×2 + 규제 | MAE 1.412℃, RMSE 1.909℃ | Naive 대비 MAE +15.3%, 최선의 베이스라인 LinearLag(5) 대비 +9.3% (p < 0.001) |
| 꽃 8종 (클래스당 20장) | ResNet18 전체 Fine-tuning | 정확도 97.5% | 같은 사진 수로 직접 학습하면 85.2% |

- **AAPL**: 주가처럼 랜덤워크에 가까운 데이터에서는 전날 값(Naive)이 사실상 최적이었다. 수준값을 그대로 예측한 LSTM(v1)은 Naive보다 MAE가 2.5배 나빴고, Train에서도 Naive를 넘지 못했다. 변화량을 예측하도록 바꾸자 Naive 수준으로 돌아왔다. 128×2층 LSTM을 규제 없이 학습하면 Train skill 0.02, Validation skill 2.95의 High Variance가 됐다.
- **서울 기온**: 같은 코드가 계절성과 기상 변수 사이의 구조를 배워 모든 베이스라인을 이겼다. 같은 모델이라도 데이터에 따라 결론이 달라진다는 대조군이다.
- **꽃 사진**: Linear Probing은 어느 사진 수에서도 Validation 최선이 아니었다. ImageNet에 없는 민들레·머위를 구별하려면 layer4까지 다듬어야 했다. 오분류 42장 중 23장(55%)이 민들레 ↔ 머위였고, 맨흙·자갈 배경을 머위의 단서로 쓰는 배경 편향도 보였다.
- **누수 재현**: 입력 창에 예측 시점을 넣으면 Test MAE가 2.43 → 0.04, 중심 이동평균 피처를 쓰면 0.22로 '좋아진다'. 누수가 만든 착시다.
- **오차 분석 → 처방**: 태그 초안에서 가장 많은 '클래스 유사성'(62%)을 근거로 입력 해상도를 160 → 224px로 높였다. 같은 Test의 탐색적 재평가에서 정확도(seed 3개)가 97.8 ± 0.3% → 99.2 ± 0.1%(+1.3%p)로 바뀌었다.
- **보너스 1 (Random Search → Coarse-to-Fine, 24회)**: 학습률(η² 0.31)과 규제 강도가 성능을 좌우했고, 은닉 크기·층 수는 거의 영향이 없었다. 탐색 1등 설정은 Test에서 기본 설정보다 낫지 않았다(MAE 1.401 vs 1.397, winner's curse).
- **보너스 2 (Attention)**: 30·90일 창에서 Attention을 붙인 LSTM은 기본 LSTM보다 낫지 않았다. 서울 기온 30일 창에서는 가장 오래된 날에 가중치가 몰렸다. 마지막 은닉 상태에 없는 '한 달 전 기준점'을 가져오는 데 쓰였다.

> 오분류 42건의 태그는 Claude가 사진을 직접 보고 단 **초안**이다(`tagged_by = claude-draft`). 미션 제약(사람이 직접 확인)을 채우려면 아래 '오차 분석 태깅' 절차로 검수해야 한다.

## 최종 결과물

| 미션 요구 | 위치 |
| --- | --- |
| 1. 전이 학습·시계열 모델 소스 코드 | `src/perfdiag/vision/`, `src/perfdiag/timeseries/`, `scripts/` |
| 2. 성능 진단 리포트 | [reports/DIAGNOSIS_REPORT.md](reports/DIAGNOSIS_REPORT.md) |
| 3. 오차 분석표 (30건 이상) | [reports/ERROR_ANALYSIS.md](reports/ERROR_ANALYSIS.md), 원본 `annotations/error_tags.csv` |
| 4. 베이스라인 비교 리포트 | [reports/BASELINE_COMPARISON.md](reports/BASELINE_COMPARISON.md) |
| 5. 시각화 4종 | 아래 '그림' 표 |
| 6. 누수 방지 근거 | [reports/LEAKAGE.md](reports/LEAKAGE.md) |
| 보너스 1·2 | [reports/BONUS.md](reports/BONUS.md) |
| 학습 자료 | [study/a6-2.html](study/a6-2.html) (단일 HTML, 오프라인) |

### 그림

| 필수 시각화 | 파일 |
| --- | --- |
| Train/Validation Loss 곡선 | `figures/ts_aapl_loss_curves.png`, `figures/ts_seoul_loss_curves.png`, `figures/vision_loss_curves.png` |
| 예측 vs 실제 (실제 파란선, 예측 빨간선) | `figures/ts_aapl_prediction.png`, `figures/ts_seoul_prediction.png` |
| 베이스라인 비교 막대그래프 (MAE·RMSE) | `figures/ts_aapl_baseline_bars.png`, `figures/ts_seoul_baseline_bars.png` |
| 오분류 이미지 갤러리 (태그별) | `figures/vision_error_gallery.png` |

추가 그림은 다음과 같다.

- `vision_shots_strategy.png`: 사진 수 × 전략
- `vision_confusion.png`: 혼동 행렬
- `vision_error_tags.png`: 태그 통계
- `ts_leakage_demo.png`: 누수 재현
- `bonus_hparam_search.png`, `bonus_attention.png`: 보너스 실험

## 설치 방법

Python 3.10 이상이 필요하다. 환경은 [uv](https://docs.astral.sh/uv/)로 관리한다. 이 README가 있는 폴더에서 실행한다.

```powershell
uv sync
```

`pyproject.toml`은 PyTorch를 CPU 전용 인덱스에서 받도록 지정한다. CUDA 빌드는 약 2.5GB, CPU 빌드는 약 200MB다. uv가 없으면 다음처럼 설치한다.

```powershell
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

데이터는 다음과 같이 준비한다.

- **시계열**: `data/timeseries/*.csv`를 저장소에 넣어 두었다. 인터넷이 없어도 같은 숫자를 재현한다. 다시 받으려면 `uv run python scripts/fetch_timeseries.py --force`를 실행한다.
- **꽃 이미지**: 처음 실행할 때 자동으로 받는다(`scripts/prepare_flowers.py`).
  - Flowers102 공식 서버가 이 환경에서 초당 약 20KB로 느렸다. 그래서 같은 이미지와 라벨을 담은 Hugging Face 미러(Parquet, 약 346MB)를 커밋 해시로 고정해 받고 SHA-256으로 검증한다.
  - 고른 8종만 `data/flowers_subset/`에 풀고 원본은 지운다. 미션 가이드의 '필요한 클래스만 복사' 방식이다.
- **ResNet18 가중치**: 처음 실행할 때 torchvision이 `~/.cache/torch`에 받는다(약 45MB).

## 실행 방법

전체를 미션 순서대로 실행한다. i5-13420H, CPU 6스레드 기준 약 2시간 30분 걸린다(가장 오래 걸리는 것은 이미지 전이 학습 약 35분, 처방 실험 약 40분, 하이퍼파라미터 탐색 약 25분).

```powershell
uv run python scripts/run_all.py
```

| 순서 | 명령 (`uv run python ...`) | 하는 일 |
| --- | --- | --- |
| 1 | `scripts/ts_baselines.py` | 베이스라인 9개를 측정하고 측정 시각을 기록한다. **딥러닝보다 먼저** 실행한다 |
| 2 | `scripts/ts_deep.py` | LSTM·GRU 7개 실험, 진단, 베이스라인 대비 개선율, Diebold-Mariano 검정을 수행한다. 베이스라인 결과가 없으면 실행을 거부한다 |
| 3 | `scripts/ts_leakage.py` | 누수 체크포인트를 하나씩 어겨 Test 점수가 얼마나 '좋아 보이는지' 잰다 |
| 4 | `scripts/ts_figures.py` | 손실 곡선, 예측 vs 실제, 베이스라인 막대 그림을 만든다 |
| 5 | `scripts/vision_transfer.py` | 사진 수 3종 × Freezing 전략 3종과 직접 학습을 비교하고, 오분류 목록을 만든다 |
| 6 | `scripts/vision_figures.py` | 손실 곡선, 사진 수별 비교, 혼동 행렬 그림을 만든다 |
| 7 | `tools/build_tagging_page.py` | 사람이 오분류에 태그를 다는 HTML(`annotations/tagging.html`)을 만든다 |
| 8 | `scripts/vision_error_analysis.py` | 태그 통계와 태그별 갤러리를 만든다 |
| 9 | `scripts/vision_improve.py` | 주 원인 태그에 맞춘 처방을 적용하고 seed 3개로 효과를 잰다 |
| 10 | `scripts/bonus_hparam_search.py`, `scripts/bonus_attention.py`, `scripts/bonus_figures.py` | 보너스 실험 |
| 11 | `tools/build_reports.py` | 리포트 5종을 만든다 |

CPU 부하는 환경 변수 `PERFDIAG_THREADS`(기본 6)로 조절한다. 우선순위를 낮추는 `PERFDIAG_LOW_PRIORITY=1`도 있다. 다만 Windows 11은 낮은 우선순위 프로세스를 효율 코어로 보내므로 학습이 몇 배 느려진다. 모든 실험은 seed를 고정한다.

### 오차 분석 태깅 (Human-in-the-loop)

미션은 오분류 사진을 사람이 직접 확인하고 태깅하라고 요구한다. 진행 순서는 다음과 같다.

1. `tools/build_tagging_page.py`가 `annotations/tagging.html`을 만든다. 각 오분류 사진 옆에 실제 클래스와 예측 클래스의 Train 사진이 3장씩 나란히 나온다.
2. Claude가 사진을 직접 보고 단 초안을 `annotations/error_tags.csv`에 넣어 두었다(`tagged_by = claude-draft`).
3. 브라우저에서 HTML을 열어 태그를 확인·수정하고 '검수 완료'에 체크한 뒤 **CSV 저장**을 누른다. 받은 파일로 `annotations/error_tags.csv`를 바꾼다.
4. `scripts/vision_error_analysis.py` → `tools/build_reports.py`를 다시 실행한다. 리포트의 '검수 상태'가 갱신된다. `study/a6-2.html`은 작성 당시 기준이라 갱신되지 않는다.

### 테스트

미션 요구 사항과 누수 방지 체크포인트를 코드로 검사한다.

```powershell
uv run python -m unittest discover -s tests -v
```

## 폴더 구조

```text
src/perfdiag/
├── common.py          경로, seed, CPU 스레드 제한, JSON
├── metrics.py         MAE·RMSE·MAPE, 개선율, Diebold-Mariano 검정
├── diagnosis.py       편향/분산 진단 규칙 (분류: 오류율, 시계열: Naive 대비 skill)
├── plots.py           그림 공통 설정
├── timeseries/
│   ├── data.py        내려받기, 후행 피처, 시간순 분할, Train 전용 Scaler, 윈도우
│   ├── baselines.py   Naive, SMA, EMA, 선형 추세, 선형 지연
│   ├── models.py      LSTM·GRU, LSTM+Attention, Transformer
│   └── train.py       학습(조기 종료)·평가·진단
└── vision/
    ├── data.py        Flowers102 미러, 클래스 선별, 분할, 메모리 캐시
    ├── models.py      TransferNet: Layer Freezing 전략 4종
    └── train.py       증강, 학습·평가 루프
scripts/               실험 스크립트와 run_all.py
tools/                 태깅 도구, 리포트·학습 자료 빌드·검증
data/timeseries/       AAPL·서울 기온 스냅샷 CSV
annotations/           오분류 태그 (error_tags.csv)
results/               실험 결과 JSON·CSV
figures/               그림
reports/               리포트 5종과 실행 로그(logs/)
study/                 단일 HTML 학습 자료와 편집 원본
tests/                 미션 체크리스트 테스트
```
