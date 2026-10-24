# Mac에서 A5-1 실행하기

Mac에서는 `run_mac_demo.command` 하나로 환경 준비, 라이브러리 검사, 전체 분석을 실행한다. Homebrew·Conda 설치, 관리자 권한, 셸 설정 파일 변경은 필요 없다.

**Intel Mac(x86_64, macOS 11 이상)**에서는 프로젝트에 동봉한 OpenMP 런타임(`libomp` 23.1.3)을 사용한다. scikit-learn 패키지에 들어 있는 `libomp`에는 XGBoost 3.4.1이 요구하는 `___kmpc_dispatch_deinit` 심벌이 없어 XGBoost를 불러오지 못하기 때문이다. 동봉 파일은 이번 실행에만 연결되며 시스템이나 `.venv`에 설치하지 않는다. 출처·해시·라이선스는 [`environment/mac-intel-openmp/`](environment/mac-intel-openmp/README.md)에 있다.

Apple Silicon Mac에서는 동봉 파일을 쓰지 않는다. 현재 환경으로 실행되는지 검사하고, `libomp` 오류가 나면 이미 설치된 위치(패키지 내부, Homebrew 경로 등)에서 동작하는 파일을 찾아 연결한다.

## 처음 준비하기

1. 저장소를 clone하고 터미널에서 `02_Advanced/A5-1` 폴더로 이동한다.
2. `uv`가 없으면 설치한다.

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. 환경을 만들고 노트북 커널을 등록한 뒤, 커널이 동작하는지 확인한다. 설치 직후에도 셸을 다시 열 필요가 없다.

   ```bash
   bash run_mac_demo.command --install-kernel
   .venv/bin/python tools/check_notebook_kernel.py --kernel a5-1-mac-demo
   ```

첫 명령은 `uv.lock`대로 `.venv`를 만들고, `libomp`와 두 모델의 작은 학습을 검사하고, `finance_data.csv`가 없으면 생성한 뒤, 이 Mac 경로로 Jupyter 커널을 등록한다. 두 번째 명령은 등록한 커널에서 노트북 첫 셀과 데이터 10,000행 로딩을 확인한다. Python과 패키지를 내려받느라 인터넷 연결이 필요할 수 있다.

`.venv/`, `finance_data.csv`, 커널 등록 파일(`~/Library/Jupyter/kernels/`)은 Mac마다 위 명령으로 만든다. 다른 컴퓨터에서 복사하거나 커밋하지 않는다.

## 전체 분석 실행하기

Finder에서 `run_mac_demo.command`를 더블클릭하거나, A5-1 폴더에서 실행한다.

```bash
bash run_mac_demo.command
```

환경 준비 → 런타임 검사 → 두 모델의 작은 학습·예측 검사 → 데이터 준비 → 전체 분석 순서로 진행한다. 결과는 `results/mac-demo/`(`report.md`, `metrics.json`, `figures/` 등)에 저장되며, 다시 실행하면 이 폴더를 갱신한다. `results/report.md`와 학습 HTML은 바꾸지 않는다.

전체 모델 비교라 시간이 걸린다(Windows, 코어 2개 기준 약 12분). `Ctrl+C`로 중단할 수 있다. 끝나거나 실패한 뒤에는 Enter를 누를 때까지 창이 열려 있다.

라이브러리 로딩 검사만 하려면 다음을 실행한다.

```bash
bash run_mac_demo.command --check-only
```

## 노트북을 셀별로 실행하기

‘처음 준비하기’의 `--install-kernel`을 실행했다면 커널이 등록되어 있다. 이 명령은 전체 분석을 실행하지 않는다.

VS Code에 Microsoft Python(`ms-python.python`)·Jupyter(`ms-toolsai.jupyter`) 확장을 설치하고, **A5-1 폴더 전체**를 연 뒤 노트북을 연다(처음 학습할 때는 `notebooks/learning_walkthrough.ipynb`).

1. 노트북 오른쪽 위의 커널 이름 또는 **Select Kernel**을 누른다.
2. **Select Another Kernel…** → **Jupyter Kernel…** → **A5-1 Mac (uv + libomp)**를 선택한다. Python Environments 목록에는 나오지 않는다.
3. 목록에 없으면 `Cmd+Shift+P` → **Developer: Reload Window**를 실행한 뒤 다시 선택한다.
4. 오른쪽 위에 **A5-1 Mac (uv + libomp)**가 표시되는지 확인하고, 커널을 재시작한 뒤 첫 코드 셀부터 순서대로 실행한다. `analysis_report.ipynb`는 첫 셀에 `Python:` 경로를 출력하므로 이 프로젝트의 `.venv/bin/python`인지도 확인할 수 있다.

이 커널은 프로젝트 `.venv`의 Python과 `libomp` 경로를 시작할 때부터 사용하고, 프로젝트 루트를 `PYTHONPATH`에 넣어 `notebooks/`에서도 `src`를 불러올 수 있게 한다. 프로젝트 폴더를 옮기거나 다른 Mac에 clone하면 `--install-kernel`을 다시 실행한다.

노트북은 분석 모듈을 셀별로 호출해 중간 표·그래프를 보여준다. 그래프는 `results/figures/`에 저장되고, 노트북을 저장하면 셀 출력이 `.ipynb`에 남는다. `results/mac-demo/`는 노트북이 아니라 `run_mac_demo.command`가 만든다.

## 문제 해결

| 증상 | 해결 |
| --- | --- |
| 더블클릭해도 실행되지 않거나 macOS가 실행을 막는다 | 터미널에 `bash `(뒤에 공백)를 입력하고 `run_mac_demo.command`를 창으로 끌어다 놓은 뒤 Enter를 누른다 |
| `uv를 찾지 못했습니다` | ‘처음 준비하기’의 uv 설치 명령을 실행한다 |
| 런타임 해시가 다르거나 `libomp.dylib`가 없다는 오류 | `environment/mac-intel-openmp/` 폴더 전체를 저장소에서 다시 가져온다 |
| `macOS 11 이상이 필요합니다` | 동봉 런타임은 macOS 11 미만을 지원하지 않는다 |
| 노트북에서 `ModuleNotFoundError: No module named 'src'` 또는 XGBoost 로딩 오류 | 일반 Python 환경 대신 **A5-1 Mac (uv + libomp)** 커널을 선택했는지 확인한다 |
| 그 밖의 실패 | 터미널 창에 표시된 오류 전체를 확인한다. 검사에 실패한 라이브러리로는 분석을 진행하지 않는다 |

## 실행기가 하는 일

- `uv sync --locked`로 잠금 파일을 바꾸지 않고 `.venv`를 준비한다. Python 버전은 `.python-version`을 따른다.
- Intel Mac에서는 동봉 `libomp.dylib`의 SHA-256, Intel 64비트 형식, macOS 버전을 확인한다.
- 별도 Python 프로세스에서 scikit-learn과 XGBoost로 작은 데이터를 학습·예측해 실제로 동작하는지 확인한다. OpenMP 중복 로딩 오류를 무시하는 설정은 쓰지 않는다.
- 검사를 통과한 `libomp` 폴더를 `DYLD_LIBRARY_PATH`로 분석 프로세스에만 전달한다. 다른 터미널에는 적용되지 않으며, 노트북은 등록한 커널을 통해 같은 설정을 쓴다.
- `finance_data.csv`가 없을 때만 `data_gen.py`로 생성한다.
