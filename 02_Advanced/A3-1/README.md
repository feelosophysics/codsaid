# A3-1 — 문서 이미지 보정과 스캔

비스듬히 찍은 문서 사진에서 종이를 찾아 정면에서 본 것처럼 펴는 문서 스캐너를 OpenCV·NumPy로 구현한다. 그레이스케일·가우시안 블러 → Canny 엣지 → 윤곽선과 `approxPolyDP` → 꼭짓점 정렬(직접 구현) → 투시 변환 → 적응형 이진화로 이어지는 규칙 기반 파이프라인이다. 단계별 윈도우와 트랙바로 파라미터를 실시간 조절할 수 있다. 20장 테스트셋으로 성공률을 재고, 파라미터 전수 탐색과 규칙 추가 실험으로 "규칙 기반의 한계"를 데이터로 보인다. 보너스 3종(NumPy 컨볼루션, 종횡비 자동 보정, PDF 내보내기)과 선택 과제(웹캠)도 포함한다.

딥러닝 프레임워크와 OCR 라이브러리는 쓰지 않는다. 좌표 정렬·면적·볼록성 판정은 `src/geometry.py`에서 NumPy만으로 구현했고, 테스트가 금지 라이브러리 import 여부를 검사한다.

## 실행

### 학습과 시연 시작점

[사진 한 장을 스캔본으로: 실행 노트북](notebooks/scanner_walkthrough.ipynb)을 위에서 아래로 실행한다.
E01의 한 픽셀 밝기·블러, 후보 선택, 좌표 정렬, 투시 행렬 계산을 펼친 뒤 기존 `scan()` 결과와 대조한다.
중간 이미지·배열 표를 읽고, 같은 조건의 20장 평가·266개 파라미터 조합·실패 그림을 거쳐 앱 시연으로 이어진다.
거리 기반 변환으로 기본 기하를 배운 뒤 앱 기본값인 Zhang 종횡비 보정을 비교하므로, 보너스가 기본 설정에 연결된 지점도 확인할 수 있다.

```powershell
uv sync --group dev
uv run --group dev python tools/build_learning_notebook.py --execute
```

VS Code/Jupyter에서는 A3-1의 `.venv` Python을 커널로 선택하고 노트북을 연다.
노트북은 A3-1 또는 `notebooks`를 작업 디렉터리로 실행할 수 있다. 생성기는 셀 원본을 관리하며
`--execute`는 새 커널에서 전체 실행한 출력을 저장한다. 전체 탐색은 5,320회 검출하므로 시간이 걸린다.
원본 사진과 기존 `outputs` 실험 결과는 덮어쓰지 않는다.

학습 순서는 **노트북 1~8절 → 9절 파라미터 변화 → 10~11절 평가·실패 → 13절 앱 시연**이다.
12절은 보너스·규칙 추가 실험이다. [기존 코드 해설](study/code-walkthrough.md)은 문법과 함수 상세를 찾아보는 자료로,
[브라우저 위젯](study/a3-1.html)은 원리 보조 자료로 사용한다.
정량 성공률은 합성 사진의 꼭짓점 위치 평가이며, 실제 사진의 가독성이나 OCR 성능을 의미하지 않는다.

환경은 [uv](https://docs.astral.sh/uv/)로 관리한다. 이 README가 있는 A3-1 폴더에서 실행한다.

```powershell
uv sync                                     # .venv 생성, 의존성 설치
uv run python -m src.app data/synthetic/E01.jpg   # 스캐너 앱 (윈도우 5개 + 트랙바)
uv run python -m src.run_all                # 전체 실험, 그림과 results.json을 outputs/에 저장 (약 1~2분)
uv run python tools/build_report.py         # REPORT.md 갱신
uv run python -m unittest discover -s tests -v
```

uv 없이 쓰려면 `python -m venv .venv` 후 `pip install -r requirements.txt`를 실행한다.

### 스캐너 앱

```powershell
uv run python -m src.app                    # 실행 후 이미지 경로를 묻는다
uv run python -m src.app 사진.jpg --pdf     # s로 저장할 때 PDF도 만든다
uv run python -m src.app 사진.jpg --no-gui --blur 7 --low 30 --high 120 --out outputs/cli
```

- 윈도우: `1 Original`, `2 Preprocessed`, `3 Edges`, `4 Contours`(후보 초록, 선택 빨강, TL·TR·BR·BL 표시), `5 Result`(투시 변환 + 적응형 이진화)
- 트랙바: Blur Kernel, Canny Low, Canny High, Thresh Block(0이면 자동), Thresh C
- 키: `s` 저장(`outputs/app/scanned_이름.png`, `warped_이름.jpg`, 단계별 이미지), `q`/`Esc` 종료
- `--no-gui`: 창을 띄울 수 없는 환경(Colab 등)용. 파라미터를 명령줄로 받고 단계별 이미지를 파일로 저장한다.
- 한글 경로의 이미지도 읽는다(`src/image_io.py`).

### 웹캠 (선택 과제)

```powershell
uv run python -m src.webcam                 # 0번 카메라, s 저장, q 종료
uv run python -m src.webcam --source 영상.mp4
```

실시간 프레임에서는 검출만 하고, `s`를 누르면 그 프레임을 원본 해상도로 변환해 `outputs/webcam/`에 저장한다. Windows에서 카메라가 열리지 않으면 설정 → 개인 정보 → 카메라에서 데스크톱 앱 접근을 허용한다. 카메라가 없는 환경이어서 프레임 처리 함수(`process_frame`)만 테스트로 검증했다.

### CPU 사용

`run_all`의 파라미터 탐색은 5,320회 검출을 한다. 기본값으로 OpenCV 스레드를 2개로 제한한다(`--threads`). 다른 작업과 함께 돌릴 때는 `--threads 1`, 탐색을 건너뛰려면 `--quick`을 쓴다. 단일 스레드 기준 전체 약 100초다.

## 구조

| 경로 | 내용 |
| --- | --- |
| `src/scanner.py` | 파이프라인 본체: `ScanParams`, `scan()`, 단계별 함수, 시각화 |
| `src/geometry.py` | 꼭짓점 정렬(직접 구현), 신발끈 면적, 볼록성, 종횡비 계산(보너스 2), 꼭짓점 오차 |
| `src/app.py` | 트랙바 GUI 앱과 `--no-gui` 모드 |
| `src/webcam.py` | 웹캠 실시간 검출 (선택 과제) |
| `src/convolution.py` | NumPy 가우시안 블러: 이중 for문·벡터화·sliding window·분리형 (보너스 1) |
| `src/pdf_export.py` | 여러 장을 한 PDF로 (보너스 3, Pillow) |
| `src/synthetic.py` | 합성 테스트 사진 20장과 정답 꼭짓점 생성 |
| `src/eda.py` | 히스토그램, 문서 경계 대비, 밝기 감소 실험 |
| `src/evaluate.py` | 판정 기준, 조건별 성공률, 파라미터 전수 탐색, 규칙 추가 실험 |
| `src/figures.py`, `src/run_all.py` | 보고서 그림과 전체 실험 실행 |
| `tools/build_report.py` | `REPORT.template.md` + `results.json` → `REPORT.md` |
| `tools/annotate_corners.py` | 직접 찍은 사진에 정답 꼭짓점과 조건을 기록 |
| `data/synthetic/` | 테스트 이미지 20장과 `labels.json`(촬영 조건, 정답 꼭짓점) |
| `outputs/` | 그림, `results.json`, `scans/`(변환·이진화 결과), `scans.pdf` |
| `tests/test_requirements.py` | 요구사항별 테스트 33개 |
| `study/a3-1.html` | 탑다운 HTML 학습 자료 |
| `study/code-walkthrough.md` | 코드 읽기 가이드: 함수 단위 데이터 흐름, 숫자 추적표, 확인 질문 |

## 요구사항 대응

| 요구사항 | 구현 | 확인 |
| --- | --- | --- |
| 이미지 경로 입력 시 즉시 동작 | `src.app` 인자 또는 입력 프롬프트 | 앱 실행 |
| 단계별 윈도우 5개, 트랙바(블러·Canny) | `app.run_gui`, `scanner.stage_images` | 앱 실행, `outputs/05_pipeline_*.png` |
| 복잡한 배경에서 영수증·A4·명함 검출, 투시 변환 | `scanner.scan` | `outputs/06_detection.png` |
| 적응형 이진화, jpg/png 저장 | `scanner.enhance`, `app.save_outputs` | `outputs/scans/`, `outputs/14_threshold.png` |
| 웹캠 실시간 검출·s 저장·q 종료 | `src.webcam` | `TestWebcamFrame` |
| 20장 데이터, 조건 기록 | `data/synthetic/labels.json` | `TestDatasetAndEvaluation` |
| EDA: 히스토그램, 쉬운·어려운 비교, 어두운 이미지 설명 | `src/eda.py` | `outputs/02~04`, 보고서 2장 |
| Gray·가우시안 블러·Canny | `scanner.preprocess`, `scanner.detect_edges` | `TestPipeline` |
| 닫힌 윤곽선, 면적 필터, approxPolyDP 4점, 시각화 | `scanner.find_document_quad`, `scanner.draw_contours` | `TestPipeline` |
| 좌표 정렬 직접 구현 | `geometry.order_points` | `TestCoordinateOrdering` |
| getPerspectiveTransform·warpPerspective | `scanner.warp_document` | `TestPipeline` |
| 20장 성공 여부, 조건별 성공률, 실패 3건 이상 분석 | `src/evaluate.py` | [REPORT.md](REPORT.md) 4~5장 (실패·부분 성공 8건) |
| 보고서 5개 항목 | [REPORT.md](REPORT.md) | 4~8장 |
| 보너스 1·2·3 | `convolution.py`, `geometry.estimate_aspect_ratio`, `pdf_export.py` | 보고서 9장, `TestConvolutionBonus`·`TestAspectRatio`·`TestPdfBonus` |

## 주요 결과

기본 파라미터(블러 5, Canny 50/150), 성공 = 최대 꼭짓점 오차가 정답 대각선의 2% 이하.

| 조건 | 테스트 수 | 성공 | 부분 성공 | 실패 | 성공률 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 단순 배경 + 정면 | 5 | 4 | 1 | 0 | 80% |
| 그림자 있음 | 5 | 3 | 0 | 2 | 60% |
| 45도 이상 기울어짐 | 5 | 4 | 1 | 0 | 80% |
| 복잡한 배경 | 5 | 1 | 0 | 4 | 20% |
| **전체** | 20 | 12 | 2 | 6 | 60% |

- **파라미터 딜레마**: 블러·Canny 266개 조합 중 최고 단일 조합이 14/20, 이미지별 최적 조합을 따로 골라도 16/20이다. 저조도(S04)는 낮은 임계값, 체크무늬 배경(C02)은 높은 임계값에서만 성공해 성공 영역이 겹치지 않는다.
- **규칙 추가**: 색 채널별 엣지, 자동 임계값, CLAHE, 근사 허용 오차를 모두 더해도 15/20이다. 남은 실패(빛 반사, 흰 배경 위 흰 종이, 손가락 가림, 체크무늬)는 "어떤 엣지가 문서 경계인가"를 판단해야 풀린다.
- **어두운 이미지**: 밝기를 k배로 줄이면 문서 경계 기울기도 k배가 된다. 기울기가 Canny high 아래로 내려가는 ×0.35~×0.25 사이에서 경계 검출률이 100%에서 0%로 떨어진다.
- **보너스 2**: 50° 이상 기울어진 A4·레터(T01·T02·T05)에서 변 길이로 정한 종횡비는 오차가 89~142%였다. 원근 보정(Zhang & He)은 0.3~5.1%로 줄였다.

자세한 분석은 [REPORT.md](REPORT.md)에 있다.

## 데이터

직접 찍은 사진과 LMS 표준 테스트셋이 없어 합성 사진 20장으로 진행했다(`uv run python -m src.synthetic`로 다시 만들 수 있다. 시드 고정). 정답 꼭짓점을 정확히 알아 성공 여부를 픽셀 오차로 판정할 수 있다. 대신 렌즈 왜곡·자동 노출·복잡한 실제 그림자는 없다.

직접 찍은 사진으로 평가하려면:

```powershell
# data/real/에 사진을 넣은 뒤
uv run python tools/annotate_corners.py data/real        # 모서리 4개 클릭, 1~4로 조건 선택
uv run python -m src.run_all --data data/real --out outputs/real
```

## HTML 학습 자료

[`study/a3-1.html`](study/a3-1.html)을 브라우저에서 연다(인터넷 불필요). 완성된 스캐너를 먼저 돌려 본 뒤 각 단계의 원리로 내려가는 탑다운 순서다. 브라우저 안에서 히스토그램·컨볼루션·Canny 트랙바·Douglas–Peucker·꼭짓점 정렬·호모그래피·종횡비·적응형 이진화를 직접 조작해 볼 수 있다.

작성 당시 Node.js로 페이지의 계산 함수를 실행해 Python·OpenCV 결과와 비교했다. Canny·적응형 이진화 픽셀 일치율, approxPolyDP 꼭짓점 수, 꼭짓점 정렬, 호모그래피, 종횡비 등 664회를 비교했다.

## 코드 읽기

`src/`의 모든 함수·클래스에 한국어 Google 스타일 docstring을 달았다. 줄 단위 주석은 Python 문법, 배열 shape, 그 코드가 필요한 이유를 설명한다. 새 문법은 처음 나오는 곳에서 자세히, 이후에는 짧게 적었다.

함수 단위 데이터 흐름과 E01 기준 숫자 추적, 예측 질문은 [`study/code-walkthrough.md`](study/code-walkthrough.md)에 있다. 처음이라면 HTML 0–1절로 큰 그림을 본 뒤, 가이드의 읽는 순서대로 `scanner.py` → `geometry.py` → `app.py` → `evaluate.py`를 읽는다.

## 과정 내 위치

[심화 과정 목차](../README.md) · [전체 과정](../../README.md)
