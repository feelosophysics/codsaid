# A3-2 — 영상 객체 추적

영상에서 움직이는 사람을 배경 차분으로 찾고, 거리 기반 `Tracker`로 고유 ID를 유지하며 궤적을 그린다. 등록한 물체가 나타나면 ORB/SIFT 특징점 매칭으로 "TARGET DETECTED"를 띄운다. 정답 궤적이 있는 합성 영상으로 ID Switch와 추적 실패를 프레임 단위로 측정했다. 그 결과로 "위치만으로는 객체를 구분할 수 없다"는 한계를 데이터로 보인다. 보너스 4종(NumPy Hungarian, 침입 감지 구역, IoU 매칭, 칼만 예측)을 모두 구현했다.

딥러닝 탐지 모델(YOLO·SSD·R-CNN), `cv2.dnn`, MediaPipe 같은 고수준 AI 라이브러리는 쓰지 않는다. 테스트가 금지 라이브러리 import와 `cv2.dnn` 사용 여부를 검사한다.

## 실행

### 학습과 시연 시작점

[실행 노트북: 한 프레임의 검출에서 시간에 걸친 ID까지](notebooks/tracking_walkthrough.ipynb)를 위에서 아래로 실행한다.
첫 실제 영상 프레임의 전경 마스크·모폴로지·박스·중심점·거리 행렬·ID 갱신을 펼치고 기존 모듈과 대조한다.
배경과 추적기의 상태, 이전 Track 참조와 값 복사의 차이, 병합·미검출·ID 전환의 판정을 확인한 뒤
실제 test 영상 평가와 앱의 일시정지·한 프레임 진행·스냅샷 시연으로 이어진다.

```powershell
uv sync --group dev
uv run --group dev python tools/build_learning_notebook.py --execute
```

VS Code/Jupyter에서 A3-2의 `.venv` Python을 커널로 선택한다. 노트북은 A3-2 또는 `notebooks`를 작업 디렉터리로 실행한다.
생성기는 셀 원본을 관리하고 `--execute`는 새 커널 실행 결과를 저장한다. 기존 영상·`outputs`는 덮어쓰지 않는다.
test 영상 5개, 같은 검출 입력을 쓰는 추적기 변형·민감도 실험, 특징점 조건별·일반화 실험을 다시 계산하므로 수 분이 걸릴 수 있다.
dev 선택 과정·배경 모델 전체 비교·특징점 연속 곡선·속도 측정은 이 노트북의 재실행 범위와 구분한다.

**권장 순서:** 노트북 1~6절(계산·상태) → 7~9절(평가·실패) → 10~11절(등록 물체) → 13절(앱 시연).
12절은 보너스다. [기존 HTML](study/a3-2.html)의 시간 재생 위젯은 계속 활용한다.
HTML은 시간에 따른 비교, 노트북은 실제 Python 배열·객체 확인을 맡는다.

환경은 [uv](https://docs.astral.sh/uv/)로 관리한다. 이 README가 있는 A3-2 폴더에서 실행한다.

```powershell
uv sync                                       # .venv 생성, 의존성 설치
uv run python -m src.synthetic                # 합성 영상 12개와 정답 생성 (약 3분, test 분할은 저장소에 있음)
uv run python -m src.app                      # 분석 앱 (데모: 교차 영상 + 등록 물체)
uv run python -m src.run_all                  # 전체 실험 → outputs/ 그림·results.json (8~14분)
uv run python tools/build_report.py           # REPORT.md 갱신
uv run python -m unittest discover -s tests -v
```

uv 없이 쓰려면 `python -m venv .venv` 후 `pip install -r requirements.txt`를 실행한다.

### 분석 앱

```powershell
uv run python -m src.app --source 0                          # 웹캠 0번
uv run python -m src.app --source 영상.mp4 --target 물체.png  # 내 영상과 등록 물체
uv run python -m src.app --source data/synthetic/target_test.mp4 --feature sift
uv run python -m src.app --kalman --matcher hungarian         # 보너스 추적기
uv run python -m src.app --zone 470,200,120,130               # 침입 구역을 명령줄로 지정
uv run python -m src.app --no-gui --out outputs/cli           # 창 없이 주석 영상·스냅샷 저장
```

- 화면: 초록 박스, ID 라벨(ID마다 다른 바탕색), 빨간 궤적, FPS, 배경 모델과 학습률. 짝이 없지만 아직 지우지 않은 추적은 회색 `n?`로 예측 위치에 표시한다.
- 키: `q`/`Esc` 종료, `s` 스냅샷(`outputs/app/snapshot_*.png`, 원본, 마스크), `p` 일시정지, `n` 일시정지 중 한 프레임, `[`/`]` 배경 학습률 ÷2/×2, `m` 전경 마스크 창, `c` 침입 구역 지우기
- 마우스: 왼쪽 버튼을 끌어 침입 구역 지정. 들어감·나감은 `outputs/app/intrusion_log.csv`에 남는다.
- FPS: 화면 갱신 속도다. 영상 파일은 원래 속도(30fps)로 재생하고, 괄호 안 `proc`는 분석만의 속도다. `--no-realtime`이면 최대 속도로 처리한다.
- 처리 해상도는 가로 640px다(`--width`). 면적 필터 등 파라미터가 이 크기를 기준으로 한다.
- 웹캠이 열리지 않으면 Windows 설정 → 개인 정보 → 카메라에서 데스크톱 앱 접근을 허용한다.

### CPU 사용

OpenCV 스레드를 기본 2개로 제한한다(`--threads`). 분석 파이프라인은 노트북(i5-13420H)에서 프레임당 7~22ms였다(측정 시점에 따라 다름, 보고서 9장). 전체 실험은 8~14분 걸리고, 그중 배경 모델 비교(프레임마다 정답 마스크를 그림)가 절반이다. `--cache 폴더`를 주면 검출 결과, 정답 마스크 통계, 특징점 실험을 저장해 둔다. 영상·파라미터·관련 소스가 같으면 다시 계산하지 않아 재실행이 3~5분으로 줄어든다. `--quick`은 배경 모델 비교와 특징점 곡선을 줄인다.

## 구조

| 경로 | 내용 |
| --- | --- |
| `src/tracker.py` | **`Tracker` 클래스**: 중심점 거리 행렬 → 탐욕 매칭 → 새 ID·삭제·궤적. 선택: Hungarian, IoU, 칼만, 색 히스토그램 |
| `src/motion.py` | 배경 차분(MOG2, 직접 구현한 이동 평균·프레임 차분), 그림자 제거, 열림·닫힘, 윤곽선·면적 필터, 박스·중심점 |
| `src/hungarian.py` | 보너스 1: NumPy만으로 구현한 Hungarian, 탐욕 할당, 게이트 처리 |
| `src/features.py` | ORB/SIFT 특징점, 비율 검정, RANSAC 호모그래피, TARGET DETECTED, 정량 시험 장면 |
| `src/zone.py` | 보너스 2: 침입 구역, 마우스 지정, CSV 로그 |
| `src/pipeline.py` | 프레임 분석(`VideoAnalyzer.process`)과 오버레이 그리기 |
| `src/app.py` | `cv2.VideoCapture` 입력, FPS, 키·마우스 처리, 헤드리스 모드 |
| `src/synthetic.py` | 합성 시나리오 6종 × dev·test 분할, 정답(박스·가시율·이벤트) |
| `src/evaluate.py` | 정답 대응, ID Switch·추적 실패·가림 판정, 기록 템플릿, 전경 마스크 지표 |
| `src/experiments.py`, `src/run_all.py`, `src/figures.py` | 보고서 실험과 그림 |
| `src/cache.py` | 실험 중간 결과 디스크 캐시 (선택) |
| `tools/build_report.py` | `REPORT.template.md` + `results.json` → `REPORT.md` |
| `tools/annotate_events.py` | 직접 찍은 영상의 수동 측정 (키로 이벤트·ID Switch·실패 기록 → CSV) |
| `data/synthetic/` | 테스트 영상(`*_test.mp4`)과 정답 JSON. dev 영상은 생성 명령으로 만든다 |
| `data/target/` | 등록 물체 `target.png`, 일반화 실험용 `same_series.png`·`other.png` |
| `outputs/` | 그림 15개, `results.json`, `measurement_log.csv` |
| `tests/test_requirements.py` | 요구사항별 테스트 31개 |
| `study/a3-2.html` | 탑다운 HTML 학습 자료 |

## 요구사항 대응

| 요구사항 | 구현 | 확인 |
| --- | --- | --- |
| VideoCapture로 웹캠·파일 입력, FPS 표시, q·s·p 키 | `app.run_gui`, `app.handle_key`, `FpsMeter` | `TestAppAndZone` |
| 배경 차분(MOG2 또는 absdiff), 열림·닫힘 | `motion.foreground_mask`, `clean_mask`, `RunningAverageSubtractor` | `TestMotion`, `outputs/02_pipeline.png` |
| 학습률 최소 3가지 관찰 | MOG2 α 4가지 + 이동 평균 α 3가지 | 보고서 4장, `outputs/08_learning_rate.png` |
| 윤곽선, 면적 필터, 박스·중심점 | `motion.find_detections` | `TestMotion` |
| Tracker 별도 파일, 거리 행렬, 최근접 매칭, ID 삭제·신규, 궤적 | `src/tracker.py` | `TestTracker` |
| 등록 이미지 ORB/SIFT 매칭, TARGET DETECTED | `features.TargetMatcher`, `draw_match` | `TestFeatures`, 보고서 3장 |
| ID Switch·추적 실패·조건별 실패율, 기록 템플릿 | `src/evaluate.py`, `outputs/measurement_log.csv` | 보고서 2장 |
| 보고서 6개 항목 | [REPORT.md](REPORT.md) | 2~7장 |
| 보너스 1·2·3·4 | `hungarian.py`, `zone.py`, `Tracker(cost="iou")`, `Tracker(kalman=True)` | 보고서 8장, `TestHungarian`·`TestAppAndZone`·`TestTracker` |
| 딥러닝·dnn·MediaPipe 금지 | — | `TestConstraints` |

## 주요 결과

기본 추적기(탐욕 + 중심점, 거리 60px, 기억 20프레임), MOG2 α=0.002, test 분할.

| 상황 | 테스트 횟수 | ID Switch | 추적 실패 | 비고 |
| --- | ---: | ---: | ---: | --- |
| 단일 객체 이동 | 10 | 0 | 0 | 기둥 가림 49프레임은 실패에서 제외 |
| 두 객체 겹침 | 10 | 8 | 1 | 총 16회, 한 덩어리 검출 204프레임 |
| 객체 일시 정지 | 5 | 2 | 2 | 3초·5초 정지에서 배경으로 흡수 |
| 조명 변화 | 5 | 1 | 2 | 조명 켜짐에서 화면 전체가 전경, 유령 ID 6개 |

- **규칙으로는 겹침을 풀 수 없다.** 칼만 예측은 그대로 지나가는 교차 3가지를 고쳤지만 마주쳤다 돌아서는 경우를 새로 망쳤다. 겹친 동안 검출이 하나뿐이라 두 경우의 위치 정보가 같기 때문이다. 색 히스토그램은 옷이 다르면 8건 → 6건, 같으면 8건 그대로였다. 규칙 8가지 중 최선도 5건이 남았다.
- **배경 학습률 트레이드오프.** 멈춘 사람이 배경이 되기까지의 프레임 수는 ln(0.9)/ln(1−α)로 예측된다(α=0.002: 이론 52.6, 실측 54). 느리게 배우면 정지에 강하고 조명 변화에서 회복하지 못한다. 빠르게 배우면 그 반대다.
- **특징점.** ORB·SIFT는 평면 회전에는 강하다(60°에서 100%). 3D 기울임 60°에서는 둘 다 0%였다. SIFT는 같은 시리즈의 다른 책을 100% 등록 물체로 판정했고, 같은 책의 색 반전은 0%였다.
- **Hungarian**: 무작위 7×7 비용 행렬의 85%에서 탐욕 할당이 최적이 아니었다. 그러나 두 사람 추적에서는 611프레임 중 1프레임만 할당이 달랐다. ID Switch의 원인은 할당 방식이 아니라 비용에 들어간 정보(위치)다.

자세한 분석은 [REPORT.md](REPORT.md)에 있다.

## 데이터

직접 찍은 영상과 표준 테스트셋 대신 합성 영상을 썼다. 사람의 위치와 가려진 비율을 정확히 알아서, 원문의 기준(5프레임 유지, 10프레임 미검출, 50% 가림 제외)을 그대로 코드로 적용할 수 있다. 대신 실제 영상의 렌즈 왜곡, 자동 노출, 옷 무늬, 체형 차이는 없다. 같은 구조의 영상을 dev(시드 11)와 test(시드 23) 두 벌로 만들었다. 파라미터는 dev에서 고르고 test로 보고한다.

직접 찍은 영상으로 측정하려면:

```powershell
# data/real/에 영상을 넣은 뒤 (조건마다 20~30초)
uv run python tools/annotate_events.py data/real/두사람교차.mp4 --condition 겹침
# b 이벤트 시작, i ID Switch +1, f 추적 실패 +1, o 50% 이상 가림 +1, e 이벤트 끝 → outputs/real/measurement_log.csv
```

## HTML 학습 자료

[`study/a3-2.html`](study/a3-2.html)을 브라우저에서 연다(인터넷 불필요). 완성된 추적기가 교차 장면에서 ID를 바꾸는 모습을 먼저 보고, 배경 모델 → 모폴로지 → 할당 → 칼만 → 판정 기준 → 특징점 순서로 내려간다. 실제 test 영상의 검출 결과를 페이지 안의 JS 추적기로 다시 돌려 보며 추적기 설정을 바꿀 수 있다.

작성 당시 Node.js로 페이지의 계산 함수를 실행해 Python 결과와 비교했다. Hungarian 할당, 시나리오 5개 × 추적기 설정 9개의 프레임별 ID, 이벤트별 판정, 이동 평균 배경, 모폴로지, 비율 검정을 합쳐 약 6만 번 비교했다.

## 과정 내 위치

[심화 과정 목차](../README.md) · [전체 과정](../../README.md)

이 미션의 결론("외형을 학습해야 한다")은 A6-1(신경망 학습 엔진)과 A6-2(모델 오류 분석)로 이어진다.
