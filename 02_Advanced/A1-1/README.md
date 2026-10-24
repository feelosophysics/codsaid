# A1-1 — 쇼핑몰 고객 분석

고객의 최근 구매·구매 횟수·구매 금액을 분석하고, 상품 텍스트와 이미지 배열을 수치형 피처로 통합하는 Python 프로젝트다. NumPy·Pandas로 전처리와 통계를 계산하고, Matplotlib·Seaborn으로 시각화한다.

기본 데이터는 **로컬에서 생성한 합성 데이터**다. 거래·상품·이미지를 모두 재현할 수 있도록 고정 난수(seed=42)를 사용한다. 실제 고객·실제 상품 사진은 포함하지 않는다. 고객 행동을 의도적으로 구성했으므로 아래 인사이트는 분석 방법을 설명하는 가설이며 실제 시장 효과를 검증한 결과가 아니다.

필수 구현과 선택 보너스 3종(NumPy 이미지 피처, 가입 월별 코호트, Plotly RFM 탐색), 실행 검증, HTML 학습 자료를 제공한다.

## 주석과 함께 학습하기

Python과 AI 개념을 처음 익히는 독자를 위해 `src/`의 모든 함수·클래스에
**한국어 Google 스타일 docstring**과 학습용 주석을 붙였다. 함수의 목적·입력·반환·오류는
docstring에서, 새 문법·데이터 모양 변화·선택 이유는 해당 코드 옆에서 읽는다.
이 미션은 데이터 준비와 통계·규칙 기반 RFM 분석이며 예측 모델을 학습하지 않는다.

처음 학습한다면 [`notebooks/learning_walkthrough.ipynb`](notebooks/learning_walkthrough.ipynb)부터 실행한다(10초 안팎). 클래스 없이 Pandas·NumPy로 한 단계씩 직접 계산한다. 행의 단위 → 표 연결 → 그룹 중앙값 대치 → 이미지 축과 벡터 연산 → IQR → 통계·상관 → RFM 점수와 그룹 → 근거·실행·검증 인사이트 순서로 진행하고, 마지막 장에서 같은 단계를 `DataAnalyzer`로 묶어 결과가 같은지 확인한다. 부록에서 보너스 3종을 다룬다. 출력 읽는 법과 확인 질문을 포함하며 `results/`에 파일을 쓰지 않는다. 내용은 `tools/build_learning_notebook.py`에서 생성하므로, 수정할 때는 이 파일을 고친 뒤 `uv run --group dev python tools/build_learning_notebook.py`와 `uv run --group dev python tools/execute_learning_notebook.py`로 다시 생성·실행한다. 부록 C의 Plotly 차트는 인터넷에 연결되어 있어야 보인다.

이어서 제출용 분석 노트북으로 같은 흐름을 클래스 중심으로 다시 본다.

1. [`notebooks/analysis_report.ipynb`](notebooks/analysis_report.ipynb)를 위에서 아래로 실행한다. 행의 단위 → 결측치 → 이미지 축 → IQR → 통계 → RFM → 차트·해석이 한 파일에서 이어진다.
2. 작은 예제와 실제 입력의 계산을 먼저 따라가고, `DataAnalyzer`의 반환값·내부 상태 및 직접 계산과의 대조 결과를 확인한다. 기본 분석을 시연할 때는 **기본 시연 마무리**에서 멈춰도 된다.
3. 반복 계산과 입력 검증의 구현은 [`src/pipeline.py`](src/pipeline.py), 같은 단계를 묶은 CLI는 [`src/run_analysis.py`](src/run_analysis.py)에서 읽는다.
4. 배열·정책을 조작해 보고 싶으면 [`study/a1-1.html`](study/a1-1.html)을 보조 자료로 사용한다. 내장 소스는 작성 시점의 사본이며 현재 실행 코드는 노트북과 `src/`를 따른다.
5. 기본 흐름을 마친 뒤 노트북의 보너스 절과 [`src/bonus.py`](src/bonus.py)를 읽는다. 차트·해석은 [`src/report.py`](src/report.py), 합성 입력의 생성 조건은 [`src/sample_data.py`](src/sample_data.py)에 있다.

한 번에 모두 외우기보다 **입력의 한 행/축 → 연산 후 모양 → 이 단계의 존재 이유**를
말로 설명해본다. 함수 설명을 보완한 상태와 학습자가 이해한 상태는 구분한다.
HTML 보조 자료의 구성은 [`study/README.md`](study/README.md)를 참고한다.

## 실행

현재 고정한 라이브러리는 **Python 3.12 이상**이 필요하다. 검증 환경은 Windows, Python 3.12.13이다. 이 README가 있는 A1-1 폴더에서 실행한다.

```powershell
uv sync --locked
uv run python -m src.run_analysis
```

샘플 파일은 저장소에 포함했다. 데이터를 같은 조건으로 다시 만들려면 아래처럼 실행한다. 이 옵션은 지정한 데이터 폴더의 샘플 파일을 교체하므로 외부 원본 폴더에는 사용하지 않는다.

```powershell
uv run python -m src.run_analysis --generate-sample --seed 42
uv run python -m unittest discover -s tests -v
```

환경은 uv로 관리한다. `.python-version`은 Python 3.12.13, `pyproject.toml`은 의존성과 노트북 개발 의존성, `uv.lock`은 정확한 버전을 고정한다. Windows와 다른 운영체제에서 같은 uv 명령을 사용한다. uv 없이 설치할 때는 `requirements.txt` 또는 노트북용 `requirements-dev.txt`를 쓴다. 두 파일은 uv.lock에서 내보낸 사본이다.

명령이 성공하면 `results/`에 필수 CSV·JSON·Markdown·차트 6종, `results/bonus/`에 보너스 결과가 저장된다. 핵심 분석에는 NumPy·Pandas·Matplotlib·Seaborn만 직접 사용하며 이미지 처리는 NumPy 배열 연산으로 구현한다. Plotly는 미션에서 허용한 보너스 3의 시각화에만 사용한다. Matplotlib의 설치 의존성에 Pillow가 포함되지만 프로젝트에서 Pillow API로 이미지를 처리하지 않는다.

## 분석 노트북

[`notebooks/analysis_report.ipynb`](notebooks/analysis_report.ipynb)는 계산 과정·실행 결과·해석·차트를 함께 읽는 학습·시연 노트북이다. VS Code나 Jupyter에서 `.venv`의 Python을 커널로 선택하고 **커널 재시작 후 전체 실행**한다. A1-1 또는 `notebooks/` 폴더에서 시작할 수 있다. 입력은 `data/sample/`에서 읽고 결과는 `results/`에 다시 저장한다. 별도 Jupyter 화면 없이 전용 환경에서 실행하려면:

```powershell
uv sync --locked
uv run python tools/execute_notebook.py
```

이 도구는 저장소 안에 임시 커널 설정을 만들어 현재 Python으로 실행한다. Notebook 도구는 실행·표시용이며 분석 로직에 추가 라이브러리를 사용하지 않는다.

노트북에서 상품 가격 대치·이미지 평균과 표준편차·IQR 경계와 후보·고객별 RFM 및 점수·그룹을 직접 계산하고 기존 메서드와 대조한다. 고객 수·주문 수·금액·비중의 합계도 확인한다. 클래스와 NumPy 벡터 연산은 그대로 학습하며, 한 이미지·한 고객을 먼저 확인한 뒤 전체 계산으로 확장한다. 보너스는 기본 분석 뒤에 구분해 두었다.

전체 실행 성공 후 [Markdown 실행 기록](results/notebook_execution.md)을 자동 저장한다. 실행 시각, 환경, 코드 셀별 실행 번호·출력 수·오류 수, 실행 전후 소스·입력 해시와 저장된 노트북 해시를 포함하므로 `.ipynb`를 읽지 않는 환경에서도 실행 근거를 확인할 수 있다. 파일이 변경되면 기록은 이전 실행의 근거이며 위 명령으로 다시 실행해야 한다.

## 분석 방법과 확장 설명

[분석 방법·한계·확장 설계](results/method_notes.md)에 다음 내용을 정리했다.

- IQR과 정규분포를 기준으로 한 z-score 방식의 차이, 비대칭 분포에서의 한계
- 그룹별 결측치 대치에 따른 분산 축소·그룹 간 차이 왜곡과 점검 방법
- NumPy의 내부 루프, 연속 메모리·strides, CPU SIMD의 이점과 적용 조건
- 대규모 이미지의 I/O·메모리 병목과 묶음 처리·샘플링·병렬화의 선택 기준
- 향후 30일 재구매 예측의 타깃·고객별 후보 피처·시간 분할과 미래 정보 누수 방지

필수 메서드는 `load_data()`, `handle_missing_values()`, `detect_outliers()`, `calculate_rfm()`이다. `handle_missing()`도 같은 인자·반환값·검증을 사용하는 호환 메서드로 제공하며 결측치 로직은 `handle_missing_values()` 한 곳에서 관리한다. 머신러닝 절은 후속 설계 제안이며 현재 미션에서 예측 모델을 학습한 결과는 아니다.

## HTML 학습 자료

[`study/a1-1.html`](study/a1-1.html)을 브라우저에서 연다. 한 파일에 설명·코드·실제 차트를 포함해 인터넷 없이 사용할 수 있다. 첫 학습 순서는 **01 전체 흐름 → 02 한 행의 의미 → 07 RFM 계산**을 권장한다.

- 12개 학습 질문과 설명 예시, Python 문법·Class·모듈 위치 안내
- 18개 원본 코드 발췌, 원래 줄 번호와 7개 파일 전체 소스 탐색기
- 파이프라인 단계, 결측치 대치 단위, 이미지 통계, IQR, RFM 기준일·주문 집계·고객 분류 정책 조작
- 실행 결과의 6종 차트와 수치 해석, 관찰과 실행 가설의 구분
- 이미지 고급 피처·가입 코호트 해석과 결과 그림 2종, 오프라인 Plotly RFM 차트

자료의 JavaScript 계산은 작성 당시 Python 결과 25개 사례 및 고객 240명의 점수·그룹과 대조했다. 내장 소스는 작성 시점 사본이며 원본을 수정하는 기능이 아니다. 현재 Python 계산은 노트북과 `src/`에서 확인한다. 포함 내용과 열람 방법은 [`study/README.md`](study/README.md)에 있다.

## 데이터와 구조

| 파일 | 내용 | 기본 규모 |
| --- | --- | --- |
| `data/sample/transactions.csv` | 한 행 = 주문의 상품 한 줄 | 2,842행, 11컬럼, 1,389주문, 240고객 |
| `data/sample/products.csv` | 상품명·카테고리·카탈로그 가격·평점·이미지 연결 | 80행, 6컬럼 |
| `data/sample/images.npy` | 상품별 생성 RGB 배열, 픽셀 범위 0–255 | `(80, 16, 16, 3)` |
| `data/sample/metadata.json` | 생성 출처·난수·규모·주입 조건 | seed=42 |
| `data/sample/customers.csv` | 합성 고객 ID와 가입일 | 240명, 가입일 = 첫 구매 전 0–90일 |
| `src/sample_data.py` | 재현 가능한 데이터 생성 | 결측치·장기 배송·정상 고가 상품 포함 |
| `src/pipeline.py` | `DataAnalyzer`, IQR 함수, 전처리·피처·RFM | 핵심 분석 로직 |
| `src/report.py` | 6종 차트, 통계 해석, 비즈니스 가설 | 결과 저장 |
| `src/run_analysis.py` | 데이터부터 보고서까지 실행 | CLI 진입점 |
| `src/bonus.py` | 이미지 고급 피처·가입 코호트·Plotly 차트 | 보너스 3종 |
| `tests/test_pipeline.py`, `tests/test_bonus.py` | 집계·대치·이미지·코호트·경계 조건 검증 | 21개 테스트 |

상품 조인 직후 16컬럼이며, 문자·단어 수와 이미지 평균·표준편차, 두 이상치 표시 컬럼을 추가하면 22컬럼이다. 기본 결측치 보완 수는 상품 카탈로그 가격 12개·평점 7개, 거래 배송 일수 272개다. 같은 상품의 속성이 여러 거래 행에 나타나므로 거래 행 기준 결측치 수와 상품 기준 대치 수는 다르다.

## 처리 원칙

- 상품 가격·평점은 **상품 테이블의 카테고리별 중앙값**으로 대치한다. 그룹 전체가 비면 전체 중앙값을 사용하고 컬럼 전체가 비면 명시적으로 실패한다. 상품명 누락은 `Unknown product`로 표시한다.
- 배송 일수는 거래 행의 카테고리별 중앙값으로 대치한다. 고객 ID·구매일·구매 금액은 추정하지 않는다.
- 이미지 배치에서 상품 축을 유지하고 나머지 축을 한 번에 줄여 평균·표준편차를 계산한다. 이미지·픽셀을 순회하는 Python 반복문이 없다. 텍스트 피처는 문자열 연산으로 계산한다.
- IQR 탐지는 값에 표시만 붙인다. 배송 일수의 처리 전후 비교는 클리핑한 별도 Series를 사용하며 원본을 유지한다. 기본 배송 이상치는 15행, 경계는 −1.5–10.5일이다.
- 고가 구매가 오류라고 단정하지 않는다. RFM 금액은 거래에 기록된 `amount`를 사용하며, 카탈로그 가격 대치나 차트용 클리핑으로 바꾸지 않는다.
- 잘못된 조인, 중복 `line_id`, 한 주문의 여러 고객·날짜, 거래 금액과 `unit_price × quantity` 불일치는 오류로 처리한다. 유효하지 않은 고객·주문·날짜 또는 양수 구매가 아닌 행은 RFM에서 제외하고 audit에 수를 남긴다.

## RFM 정책

기준일 기본값은 최종 유효 거래일 다음 날이며, 샘플에서는 **2026-10-10**이다. `--reference-date YYYY-MM-DD`로 지정할 수 있다. 미래 구매를 포함한 기준일은 허용하지 않는다.

R은 마지막 구매 이후 일수, F는 **고유 주문 수**, M은 관측 기간의 양수 구매 금액 합계다. 반품 차감 순매출이나 LTV가 아니다. 1–5점은 평균 순위의 백분위를 사용하며 동점은 같은 점수를 받는다. R이 작을수록, F·M이 클수록 높은 점수다. 그룹은 점수 합이 아닌 다음 정책으로 분류한다.

| 우선순위 | 그룹 | 기본 조건 |
| --- | --- | --- |
| 1 | Inactive | R > 90일 |
| 2 | New | R ≤ 30일, F = 1회 |
| 3 | VIP | R ≤ 30일, F ≥ 4회, M ≥ 고객 M의 75백분위 |
| 4 | Loyal | 위 그룹에 속하지 않고 F ≥ 4회 |
| 5 | Regular | 그 외 |

메서드 인자로 최근·비활성 기준, 반복 구매 횟수, 분석 기준일을 바꿀 수 있다. VIP 금액 경계는 기본 실행에서 1,786,650원이다. Inactive는 구매 공백을 뜻하며 확정 이탈을 의미하지 않는다. 임의의 실데이터에서 4개 그룹이 반드시 생기도록 고객을 억지로 나누지 않는다.

## 비즈니스 인사이트

아래는 seed=42 실행의 **합성 데이터 예시**다. 숫자의 근거는 [`results/segment_summary.csv`](results/segment_summary.csv), [그룹별 고객 수](results/figures/03_bar.png), [빈도–구매 금액 산점도](results/figures/05_scatter.png)다. 분석을 다시 실행하면 최신 해석은 [`results/analysis_summary.md`](results/analysis_summary.md)에서 확인한다.

| 그룹 | 고객 수 | 평균 구매 횟수 | 평균 구매 경과 | 매출 비중 |
| --- | ---: | ---: | ---: | ---: |
| VIP | 60 | 13.08회 | 8.33일 | 71.40% |
| Loyal | 60 | 5.92회 | 27.52일 | 16.26% |
| New | 60 | 1.00회 | 4.47일 | 2.66% |
| Inactive | 60 | 3.15회 | 171.93일 | 9.68% |

1. **VIP 유지 가설**
   - 근거: 고객의 25%인 VIP가 매출의 71.40%를 차지하며 평균 13.08회 구매했다.
   - 실행: VIP를 대상으로 멤버십 혜택을 소규모 대조군 실험으로 제공해 재구매 유지를 기대한다. 효과 크기는 아직 측정하지 않았다.
   - 검증: 혜택 비용과 대조군 재구매율이 필요하다. 비용 증가가 추가 이익보다 크면 제안을 기각한다.
2. **구매 공백 고객 복귀 가설**
   - 근거: Inactive 60명의 평균 마지막 구매 경과는 171.93일이며 과거 구매 횟수는 3.15회다.
   - 실행: Inactive 대상의 품목별 구매 간격을 확인하고, 수신 동의가 있는 고객의 복귀 메시지를 대조군과 비교해 재구매 회복을 기대한다.
   - 검증: 품목별 정상 구매 주기·수신 동의·반품 정보가 필요하다. 긴 구매 주기가 정상이라면 이탈 해석을 수정한다.
3. **첫 구매 고객의 두 번째 구매 가설**
   - 근거: New 60명은 최근 구매 경과가 평균 4.47일이고 구매 횟수는 1회다.
   - 실행: New 대상에게 사용 안내와 다음 구매 추천을 제공하고, 대조군과 비교해 두 번째 구매 전환을 기대한다.
   - 검증: 고객별 동일한 추적 기간과 반품 정보가 필요하다. 전환율 차이가 없다면 추천 효과를 주장할 수 없다.

## 통계·차트 해석과 한계

단가 평균 40,497원, 중앙값 37,800원, 표준편차 22,539원, Q1 21,100원, Q3 54,000원이다. 평균·중앙값과 분포를 함께 봐야 고가 상품의 영향을 판단할 수 있다. 거래 행 기준 통계이므로 자주 팔린 상품이 더 많이 반영된다.

단가–금액 Pearson r=0.731, 수량–금액 r=0.605다. `amount=unit_price×quantity`라는 계산식의 영향이 있어 마케팅의 인과 효과로 해석할 수 없다. 이미지 밝기·변동은 의미나 품질을 나타내지 않는다. 월별 매출의 첫·마지막 월은 부분 기간일 수 있으며, 특히 샘플의 10월은 9일까지여서 9월과 단순 비교해 매출 감소를 주장할 수 없다.

| 요구 차트 | 파일 | 읽는 대상 |
| --- | --- | --- |
| 히스토그램 | `results/figures/01_histogram.png` | 단가 분포 |
| 박스플롯 | `results/figures/02_boxplot.png` | 배송 일수 클리핑 전후 |
| 막대그래프 | `results/figures/03_bar.png` | 세그먼트별 고객 수 |
| 히트맵 | `results/figures/04_heatmap.png` | 거래 행 기준 상관행렬 |
| 산점도 | `results/figures/05_scatter.png` | 고객별 고유 주문 수와 구매 금액 |
| 라인차트 | `results/figures/06_line.png` | 월별 유효 양수 구매 금액 |

모든 차트에 제목과 축 레이블이 있다. 시스템 한글 폰트에 의존하지 않도록 차트 레이블은 영어를 사용하고 해석은 한국어로 제공한다.

## 실제 데이터로 교체

외부 원본은 별도 폴더에 보관하고, 아래 입력 규약에 맞춰 변환한 후 경로를 지정한다. 이 구현은 임의의 데이터셋을 자동 추론해 변환하는 수집 도구가 아니다.

```powershell
uv run python -m src.run_analysis --data-dir data/external --output-dir results/external --reference-date 2026-10-10 --observation-end 2026-10-09
```

- `transactions.csv`: `line_id`, `order_id`, `customer_id`, `order_date`, `product_id`, `unit_price`, `quantity`, `amount`, `shipping_days`. 국가·결제수단은 선택 컬럼이다. `amount`는 **행의 총액**이어야 하며 주문 전체 금액을 각 행에 반복해서 넣으면 안 된다.
- `products.csv`: `product_id`, `product_name`, `category`, `catalog_price`, `rating`, `image_index`. 상품 ID는 유일해야 하고 카테고리는 누락되지 않아야 한다.
- `images.npy`: 모든 이미지의 크기와 픽셀 스케일을 통일한 수치 배열. `(N,H,W)` 또는 `(N,H,W,C)` 형태다. `image_index`는 유효한 0부터 시작하는 정수 위치다. pickle 기반 배열은 허용하지 않는다.
- `customers.csv`: 코호트 보너스용 `customer_id`, `signup_date`. 구매하지 않은 가입 고객도 포함한다. 다른 위치면 `--customers-path`로 지정한다. 가입일이 없는 입력에서는 `--skip-bonus`로 필수 분석만 실행한다. 첫 구매일을 가입일로 간주하지 않는다. 이미지 보너스는 0–255 범위의 회색 또는 RGB 배열을 받는다.

결측치 전략·IQR 임계값·그룹 기준은 `DataAnalyzer`의 메서드 인자로 조절한다. 외부 데이터에서는 출처·이용 조건·통화·관측 기간을 별도로 기록하고, 보고서의 합성 데이터 설명과 위 예시 수치를 갱신한다. 잘못된 날짜와 환불 제외 정책, 현재 고객 수, 실제로 생성된 세그먼트 수를 `audit.json`에서 확인한다.

공식 구현 참고: [NumPy의 여러 축 평균 연산](https://numpy.org/doc/stable/reference/generated/numpy.mean.html).

## 보너스 결과

1. **이미지 고급 피처**: 상품 80개의 밝기를 8개 구간으로 나눠 정규화 히스토그램을 계산하고, 이웃 픽셀의 절대 차이 평균과 엔트로피를 추가했다. RGB→밝기 변환·구간 집계·차분은 모두 NumPy 배열 연산이다. `image_features.csv`와 `transactions_with_image_features.csv`에 상품·거래 피처를 저장한다. 기본 분석 표 22컬럼은 유지하고 보너스 표에는 10개 피처를 더한다. 밝기·질감의 요약이며 품질·의미를 판별한 값이 아니다.
2. **가입 코호트**: 합성 가입 고객 240명을 가입 월 기준 12개 코호트로 나눴다. 분모는 코호트 가입자 전체, 분자는 해당 경과 월의 양수 구매 고객 수다. 여러 주문·상품 행은 고객당 한 번만 센다. 관측 종료일 2026-10-09 기준으로 완전히 관측한 칸 66개를 계산하고, 나머지 78개는 NaN/공백으로 남긴다. 가입 월 활동률도 반드시 100%가 아니다. `--observation-end`는 실제로 데이터 수집이 끝난 날로 지정한다. 샘플 가입일은 별도 난수로 생성한 예시이며 실제 유지율을 입증하지 않는다.
3. **인터랙티브 RFM**: [results/bonus/rfm_interactive.html](results/bonus/rfm_interactive.html)에서 고객 240명의 R/F/M·점수를 hover로 확인하고 그룹을 범례로 선택하며 확대·PNG 저장을 할 수 있다. Plotly 라이브러리를 HTML에 포함해 오프라인으로 동작한다. [Plotly 공식 HTML 내보내기 안내](https://plotly.com/python/interactive-html-export/)를 따른다.

계산표·그림과 해석은 [보너스 결과](results/bonus/README.md), 실행된 사례는 분석 노트북, 설명과 조작은 학습 HTML에도 포함했다.

## 과정 내 위치

[심화 과정 목차](../README.md) · [전체 과정](../../README.md)
