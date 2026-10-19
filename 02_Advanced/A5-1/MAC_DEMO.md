# Mac에서 A5-1 시연하기

기존 uv 프로젝트를 사용한다. Homebrew 설치·권한 변경 없이 현재 가상환경과 알려진 로컬 설치 위치의 `libomp.dylib`를 찾고, XGBoost가 실제로 불러오는 데 성공한 경로만 이번 실행에 적용한다. 파일 복사, 패키지 바이너리 수정, 셸 설정 파일 변경은 하지 않는다.

## 실행

1. 아이맥에 최신 A5-1 폴더를 가져온다. `run_mac_demo.command`와 `tools/mac_demo.py`가 모두 필요하다. Windows의 `.venv`는 가져오지 않는다.
2. Finder에서 `run_mac_demo.command`를 더블클릭한다.
3. 터미널에서 환경 준비 → XGBoost 로딩 검사 → 데이터 준비 → 전체 분석 순서로 진행된다. 처음에는 인터넷 연결이 필요할 수 있다.

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

- `uv sync --locked`로 잠금 파일을 변경하지 않고 `.venv`를 준비한다. Python 버전은 기존 `.python-version`을 따른다.
- 먼저 원래 설정으로 XGBoost를 불러본다. `libomp` 관련 실패일 때만 현재 Python의 scikit-learn 내부와 Homebrew·사용자 라이브러리의 알려진 위치를 차례로 검사한다.
- 각 후보는 별도 Python 프로세스에서 실제 `import xgboost`로 검사한다. CPU·버전 호환 여부를 파일 이름만으로 추정하지 않는다.
- 성공한 폴더를 `DYLD_LIBRARY_PATH`로 분석 프로세스와 그 자식 프로세스에 전달한다. 연결은 이번 실행에만 유효하며, 노트북이나 다른 터미널에는 적용되지 않는다.
- `finance_data.csv`가 없을 때만 기존 `data_gen.py`로 생성한다.
- 결과는 **`results/mac-demo/`**에 저장한다. 같은 시연을 다시 실행하면 이 폴더의 결과를 갱신한다. 기존 `results/report.md`와 학습 HTML은 갱신하지 않는다.
- 전체 모델 비교를 실행하므로 즉시 끝나는 데모가 아니다. Windows의 기존 기록은 약 12분이며 Mac 소요 시간은 별도 확인이 필요하다. Ctrl+C로 중단할 수 있다.
- 실패하면 창에 표시된 오류 전체를 전달한다. 정상 종료나 실패 후 Enter를 누를 때까지 터미널 창을 유지한다.

이 도구는 Windows에서 구문과 제어 흐름을 확인했다. Intel Mac에서의 네이티브 라이브러리 로딩과 Finder 실행은 아직 현장 확인이 필요하다.
