# A5-1 시각 학습 장치

미션의 개념을 직접 이해하고, 배운 내용을 초보자에게 설명할 때 사용하는 오프라인 HTML 장면이다. 화면의 움직임은 실제 저장 예측 결과와 연결되어 있다. 기계 구조는 입력·출력과 판정 관계를 보여주는 비유다.

## 1. 같은 고객, 두 가지 예측

[`two-predictions.html`](two-predictions.html)을 연다.

1. 고객 A를 선택하고 입력 변수 6개를 함께 읽는다. 실제 신용 점수와 연체 여부는 입력에 없다.
2. “신용 점수는 몇 점일까?”와 “연체할까?”라는 서로 다른 질문을 제시한다.
3. **두 모델로 예측하기**를 누른다. 위 계측기는 Lasso의 신용 점수, 아래 계측기는 Random Forest의 연체 예측 점수를 표시한다.
4. **정답 공개하고 비교하기**를 누른다. 회귀는 실제 점수와의 오차, 분류는 실제 연체 여부와 판정의 일치를 확인한다.
5. 고객 B·C에서도 반복한 뒤 “입력이 같아도 왜 출력과 평가가 다른가?”를 학습자 자신의 말로 설명하게 한다.

고객 선택은 Test 2,000명 전체를 지원한다. 고객 A·B·C는 이해를 돕는 사례이며 전체 성능을 대표하는 표본이 아니다. 화면은 한 고객의 결과와 Test 전체 성능을 분리한다. 방향키로 고객을 바꾸고 Enter로 예측, R로 정답을 공개할 수 있다.

분류기는 회귀의 예측 점수나 실제 신용 점수를 입력으로 사용하지 않는다. 입력 6개에서 각 모델의 파생 변수·전처리를 거쳐 독립적으로 예측한다. 예측 점수의 확률 보정은 검증하지 않았다.

## 2. 임계값 분류기

[`threshold.html`](threshold.html)을 연다. 문형 검사대는 임계값 t, 작은 카드는 선택한 고객의 예측 점수 p다. p ≥ t이면 연체로 예측한다.

0.5에서 0.2로 낮출 때 FN·FP가 어떻게 달라질지 먼저 예상하고, 0.2 → 0.5 → 0.8 버튼으로 확인한다. ‘놓친 연체자’와 ‘잘못 잡은 정상 고객’을 선택해 실제 사례를 본다. 혼동 행렬과 지표는 같은 Test 2,000명 전체에서 계산한다.

화면의 **기존 학습 자료** 링크는 [`../a5-1.html`](../a5-1.html)의 원본으로 연결된다. 별도 비교 사본은 사용하지 않는다. 같은 RF + class_weight 모델과 같은 임계값을 고르면 계산이 일치한다.

## 재생성

A5-1 폴더에서 실행한다. 기존 `results/test_predictions.json`, `results/metrics.json`과 생성된 `finance_data.csv`가 필요하다.

```powershell
uv run python tools/anatomy/export_dual_predictions.py
node study/anatomy/build-dual.mjs --audit
node study/anatomy/build.mjs --audit
node study/anatomy/verify-dual.mjs
node study/anatomy/verify.mjs
```

`export_dual_predictions.py`는 저장된 Lasso alpha로 Train에서 한 번 학습해 Test 회귀 예측을 재현하고 `results/dual_predictions.json`에 저장한다. 그리드 탐색을 다시 하지 않는다. Test 행 순서와 기존 회귀 지표가 일치하는지 검사한다. 분류는 기존 저장 점수를 그대로 사용한다.

`build-dual.mjs` / `dual.js` / `dual.css`는 두 가지 예측 장면, `build.mjs` / `scene.js` / `style.css`는 임계값 장면의 소스다. `style.css`의 기본 스타일을 두 장면이 공유한다. 생성 HTML은 필요한 CSS·JavaScript·데이터를 내장하므로 파일만 열어도 동작한다.

## 검증과 출처

- 임계값 계산은 `sklearn-reference.json`의 2,908개 임계값에서 scikit-learn과 23,264항목을 대조한다. 모든 저장 점수의 경계값을 포함한다. 기존 종합 학습 자료의 계산 엔진과도 대조한다.
- 회귀 예측은 같은 Train/Test 분할과 저장된 Lasso alpha=0.1로 재현했다. Test 전체 RMSE·MAE·R²가 기존 결과와 허용 오차 1e-9 이내에서 일치한다.
- `verify-dual.mjs`는 두 장면의 데이터 내장·원본 해시·전체 지표·로컬 링크·외부 런타임 의존성 유무를 검사한다.
- `dual-ui-checks.json`, `dual-mobile-checks.json`, `ui-checks.json`, `mobile-checks.json`은 브라우저 검증 시나리오다. 실제 입력으로 단계별 공개·고객 변경·키보드·테마·모바일 배치·동작 줄이기를 확인한다.
- 브라우저 검증 도구는 A5-1 폴더를 현재 작업 경로로 실행한다. 시나리오의 이미지 출력 경로는 `study/anatomy/shots/`를 기준으로 한다.
- `source-manifest.json`, `dual-manifest.json`, `verification.json`, `dual-verification.json`에 생성·수치 검증 근거를 저장한다. `shots/`에는 화면 검증 이미지를 둔다.

데이터는 A5-1의 합성 금융 데이터다. 실존 고객에 관한 결론이나 실제 대출 심사 기준으로 사용하지 않는다. 학습 목적의 Test 탐색이며 운영 임계값 선택 절차를 대신하지 않는다.

도형 라이브러리: [Anatomy](https://github.com/wheresryan22/anatomy), 커밋 `e9488296a44211c42701ff71705b7901470ec78f`, MIT. 재생성에 필요한 최소 라이브러리와 라이선스 고지는 `vendor/`에 보관한다. Anatomy 스킬 설치 폴더 없이도 HTML 열람·장면 빌드·수치 검증이 가능하다. 브라우저 화면 검증 도구는 Anatomy의 `scripts/drive.mjs`를 사용한다.
