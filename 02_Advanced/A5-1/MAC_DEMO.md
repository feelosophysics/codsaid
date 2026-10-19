# Mac에서 A5-1 시연하기

기존 uv 프로젝트를 사용한다. Intel Mac에서는 프로젝트에 동봉한 OpenMP 23.1.3을 이번 실행에만 연결한다. **Intel x86_64, macOS 11 이상**이 필요하다. Homebrew·Conda 설치, 관리자 권한, 시스템·패키지 바이너리 수정, 셸 설정 파일 변경은 필요하지 않다.

아이맥의 이전 로그에서 scikit-learn의 `libomp`에는 XGBoost 3.4.1이 요구하는 `___kmpc_dispatch_deinit` 심벌이 없는 것을 확인했다. 그래서 Intel에서는 기존 파일을 재사용하는 대신 해당 심벌이 있는 동봉 파일을 우선 사용한다.

## 실행

1. 아이맥에 최신 A5-1 폴더를 가져온다. `run_mac_demo.command`, `tools/mac_demo.py`, **`environment/mac-intel-openmp/` 전체**가 필요하다. Windows의 `.venv`는 가져오지 않는다. 아이맥에서 이미 만든 `.venv`는 그대로 사용한다.
2. Finder에서 `run_mac_demo.command`를 더블클릭한다.
3. 터미널에서 환경 준비 → 동봉 런타임 무결성 검사 → 두 모델의 작은 학습·예측 검사 → 데이터 준비 → 전체 분석 순서로 진행된다. Python 패키지 준비에는 인터넷 연결이 필요할 수 있지만 동봉 `libomp`를 따로 다운로드하거나 설치하지 않는다.

다운로드·압축 해제 방식에 따라 실행 권한이 없을 수 있다. 그때는 **터미널에 `bash `를 입력하고(뒤에 공백), `.command` 파일을 창으로 끌어다 놓은 뒤 Enter**를 누른다. 긴 경로나 따옴표를 직접 입력할 필요가 없다. macOS가 다운로드한 파일의 실행을 차단하면 파일 출처를 확인하고 교육장 안내에 따라 연다.

프로젝트 폴더에서 짧은 명령으로 실행할 수도 있다.

```bash
bash run_mac_demo.command
```

로딩 검사만 할 때:

```bash
bash run_mac_demo.command --check-only
```

## 동작과 결과

### 노트북을 셀별로 실행하기

A5-1 폴더에서 아래 명령을 한 번 실행한다. 라이브러리 검사 후 사용자 전용 커널을 등록하며 전체 분석은 실행하지 않는다. 입력 CSV가 없으면 먼저 생성한다.

```bash
bash run_mac_demo.command --install-kernel
```

VS Code나 Jupyter에서 `notebooks/analysis_report.ipynb`를 열고 **A5-1 Mac (uv + libomp)** 커널을 선택한다. VS Code에서는 커널 선택 → 다른 커널 선택 → Jupyter 커널 목록에서 찾을 수 있다. 목록이 갱신되지 않으면 편집기를 다시 연다. 이미 실행 중인 커널은 종료·재시작하고 첫 셀부터 순서대로 실행한다.

이 커널은 현재 프로젝트 `.venv`의 Python과 동봉 libomp 경로를 시작 시점부터 사용한다. `PYTHONPATH`에 프로젝트 루트를 지정해 노트북 폴더에서 실행해도 `src`를 찾을 수 있다. 패키지 추가 설치나 시스템 설정 변경은 없지만 사용자 Jupyter 커널 등록 파일은 남는다. 다른 Mac에 클론하거나 프로젝트 폴더를 이동하면 다시 등록한다. 등록 파일은 Git으로 전달하지 않는다.

기본 스크립트는 `src.run_all`로 전체 분석과 `results/mac-demo/` 보고서를 만든다. 노트북은 사용자가 셀별로 같은 분석 모듈을 호출하고 중간 표·그래프를 확인한다. 현재 노트북의 차트는 `results/figures/`에 저장되어 기존 차트를 갱신하며, 노트북 저장 시 셀 출력도 `.ipynb`에 남을 수 있다. 노트북 실행만으로 `results/mac-demo/report.md`가 새로 생성되는 것은 아니다.

### 실행 설정

- `uv sync --locked`로 잠금 파일을 변경하지 않고 `.venv`를 준비한다. Python 버전은 기존 `.python-version`을 따른다.
- Intel에서는 `environment/mac-intel-openmp/libomp.dylib`의 고정 SHA-256, Intel 64비트 헤더, macOS 버전을 확인한다. 라이브러리가 빠져 있으면 폴더 전체를 다시 가져오라는 안내를 표시한다. 라이선스와 출처·해시는 같은 폴더에 있다.
- 별도 Python 프로세스에서 scikit-learn과 XGBoost를 함께 불러 각각 작은 데이터로 학습·예측한다. 실패한 라이브러리로 전체 분석을 진행하지 않는다. OpenMP 중복 오류를 무시하는 설정을 사용하지 않는다.
- Apple Silicon에서는 기존 로컬 탐색 방식만 사용하며 동봉 Intel 파일은 연결하지 않는다. Apple Silicon용 별도 런타임을 제공하는 도구는 아니다.
- 성공한 폴더를 `DYLD_LIBRARY_PATH`로 분석 프로세스와 그 자식 프로세스에 전달한다. 연결은 이번 실행에만 유효하며, 노트북이나 다른 터미널에는 적용되지 않는다.
- `finance_data.csv`가 없을 때만 기존 `data_gen.py`로 생성한다.
- 결과는 **`results/mac-demo/`**에 저장한다. 같은 시연을 다시 실행하면 이 폴더의 결과를 갱신한다. 기존 `results/report.md`와 학습 HTML은 갱신하지 않는다.
- 전체 모델 비교를 실행하므로 즉시 끝나는 데모가 아니다. Windows의 기존 기록은 약 12분이며 Mac 소요 시간은 별도 확인이 필요하다. Ctrl+C로 중단할 수 있다.
- 실패하면 창에 표시된 오류 전체를 전달한다. 정상 종료나 실패 후 Enter를 누를 때까지 터미널 창을 유지한다.

이 도구는 Windows에서 구문·제어 흐름·동봉 파일 해시·Intel Mach-O 아키텍처·필수 심벌을 확인했다. Intel Mac에서의 실제 학습 검사와 Finder 실행은 현장 확인이 필요하다. 먼저 `--check-only`를 통과시킨 뒤 전체 분석을 실행하는 것을 권장한다.
