# 학습 프로젝트의 Python 3.12.13 환경 전환

검증일: 2026-10-20, Windows.

기존 가상환경이 있는 심화 미션 10개를 확인했다. 마이너 버전 추적 방식이던 9개 환경을 Python **3.12.13의 정확한 설치 경로**를 사용하는 방식으로 순서대로 재생성했다. 이미 전환된 A5-1은 재생성 없이 같은 기준으로 검증했다. 각 미션의 `.python-version`도 `3.12.13`이다.

10개 모두 전후 패키지 목록이 일치하며 `uv pip check`를 통과했다. `pyproject.toml`과 `uv.lock`의 전후 SHA-256이 일치한다. 기존 공통 Python 설치를 재사용했고 프로젝트별 패키지 버전 차이도 보존했다. 테스트는 총 **271개**, 실패와 건너뜀은 모두 **0개**다.

| 미션 | 처리 | 유지한 패키지 수 | 통과 테스트 | 실제 실행 범위 | 기록 |
| --- | --- | ---: | ---: | --- | --- |
| A1-1 | 재생성 | 49 | 21 | 상거래 분석 전체·보너스 결과 생성, Jupyter 커널 | [검증](../02_Advanced/A1-1/environment/2026-10-20-python31213/verification.json) |
| A2-1 | 재생성 | 44 | 32 | 선형대수·미적분·역전파·최적화·확률 실험 전체, Jupyter 커널 | [검증](../02_Advanced/A2-1/environment/2026-10-20-python31213/verification.json) |
| A3-1 | 재생성 | 12 | 33 | 기존 E01 이미지로 문서 스캐너 CLI 실행, 단계별 이미지 저장 | [검증](../02_Advanced/A3-1/environment/2026-10-20-python31213-attempt2/verification.json) |
| A3-2 | 재생성 | 12 | 31 | 기존 데모 영상 60프레임 추적·주석 영상 저장 | [검증](../02_Advanced/A3-2/environment/2026-10-20-python31213/verification.json) |
| A4-1 | 재생성 | 17 | 22 | 저장된 20 Newsgroups 코퍼스에서 TF-IDF·BM25 검색 CLI | [검증](../02_Advanced/A4-1/environment/2026-10-20-python31213/verification.json) |
| A4-2 | 재생성 | 17 | 44 | 정보 추출·감성·속성 분석·개인정보 마스킹 CLI | [검증](../02_Advanced/A4-2/environment/2026-10-20-python31213/verification.json) |
| A5-1 | 기존 환경 재검증 | 56 | 17 | 실제 신용 데이터로 Ridge·SMOTE/로지스틱·XGBoost 학습과 예측, Jupyter 커널 | [검증](../02_Advanced/A5-1/environment/2026-10-20-python31213/verification.json) |
| A5-2 | 재생성 | 79 | 22 | 실제 고객 데이터의 KMeans 탐색·RF 학습·TreeSHAP 계산, Jupyter 커널 | [검증](../02_Advanced/A5-2/environment/2026-10-20-python31213/verification.json) |
| A6-1 | 재생성 | 12 | 32 | MiniGrad의 XOR 100 epoch 학습, 손실·정확도 검사 | [검증](../02_Advanced/A6-1/environment/2026-10-20-python31213/verification.json) |
| A6-2 | 재생성 | 45 | 17 | 실제 AAPL 데이터의 4종 예측 모델 학습·추론, 사전학습 ResNet18의 순전파·역전파·분류기 갱신 | [검증](../02_Advanced/A6-2/environment/2026-10-20-python31213/verification.json) |

패키지 수는 프로젝트별 설치 수이며 editable 프로젝트 자체를 포함한다. 예를 들어 A1-1의 NumPy 2.5.3과 나머지 환경의 2.5.4를 각각 유지했다. A6-2의 PyTorch 2.14.1+cpu, torchvision 0.29.1+cpu도 유지했다.

## 실행 검증의 범위

모든 프로젝트에서 포함된 `unittest` 전체를 새 환경으로 실행했다. 실제 실행은 [공통 검증 코드](../tools/verify_python_runtime.py)에 조건과 함께 보존했다.

- A1-1·A2-1은 전체 분석·실험을 실행했고, 결과는 검증용 임시 경로로 보냈다.
- A3-1·A3-2는 창 없는 모드로 실제 이미지·영상을 처리했다.
- A5-1은 실제 데이터의 Train 1,000행과 Test 64행으로 회귀·불균형 처리·XGBoost 실행을 확인했다. 전체 교차 검증·하이퍼파라미터 탐색은 반복하지 않았다.
- A5-2는 1,000행 군집 탐색과 RF 학습, Test 16행의 SHAP 값 및 가법성을 검사했다. 대시보드 UI와 전체 실험 보고서 생성은 이번 검증 범위에 포함하지 않았다.
- A6-1은 XOR 학습을 100 epoch 실행했다. A6-2는 LSTM·GRU·Attention LSTM·Transformer를 각각 3회 갱신하고 추론을 검사했다. ResNet18은 캐시의 사전학습 가중치를 사용해 순전파·역전파·FC 갱신을 검사했다. 약 2시간 30분이 필요한 A6-2 전체 실험은 반복하지 않았다.
- A1-1·A2-1·A5-1·A5-2는 해당 환경의 Python으로 실제 Jupyter 커널을 시작해 Python 3.12.13·NumPy import·계산을 확인하고 종료했다. 전역 커널을 등록하지 않았다.

환경 설치와 테스트는 Windows 실행기 생성·파일 권한을 고려해 Codex 샌드박스 밖에서 수행했다. 이후 10개 모두 Codex 샌드박스 안에서 `uv run --offline --no-sync --no-python-downloads`로 정확한 Python 경로와 주요 라이브러리 import를 재확인했다. A6-2는 샌드박스 안의 CPU 역전파 계산도 확인했다. 각 검증 폴더의 `sandbox.json`에 결과가 있다.

## 복원과 보존

기본 복원은 오프라인으로 진행했다. 캐시에 없던 OpenCV·SciPy·PyArrow·PyTorch 등의 패키지는 `uv.lock`의 고정 버전·배포 파일로 내려받았다. 모든 환경에서 설치 후 목록을 전환 전과 다시 대조했다.

A3-1의 첫 시도는 OpenCV 캐시 누락으로 중단돼 이전 환경을 복구했고, 두 번째 시도에서 같은 버전을 복원해 검증했다. 첫 시도의 기록도 남아 있다. 검증이 완료된 이전 환경과 임시 결과는 작업공간의 캐시 정리 절차로 제거했다. 재설치에 사용하는 공유 uv 캐시는 보존했다. [정리 결과](python-environment-migration-2026-10-20-cleanup.json)에 소유 작업·대상·처리 결과가 있다. [전체 결과 JSON](python-environment-migration-2026-10-20.json)에서 프로젝트별 패키지 수·테스트 수·샌드박스 검증·기록 경로를 확인할 수 있다.

기존 보고서와 노트북을 재생성하는 대신 전환 전후 환경 구성·패키지 목록과 실제 실행의 명령·종료 결과를 각 프로젝트의 `environment` 폴더에 보존했다. [전환 도구와 사용법](../tools/README.md)을 함께 관리한다. 정확한 패치 버전 지정과 이번 실행 통과는 향후 모든 Windows 앱 제어 판정을 보장하지 않는다.
