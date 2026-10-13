# A5-1 HTML 학습 자료

`a5-1.html` 하나를 브라우저에서 열면 인터넷 없이 읽고 조작할 수 있다. 그래프·Test 데이터·예측 확률·Python 소스 사본을 모두 파일에 포함했다.

처음에는 **01 전체 흐름 → 02 데이터 생성 방식 → 03 규칙 베이스라인 → 04 분류 지표** 순서로 읽는다. 02를 먼저 읽으면 이후 모든 숫자가 왜 그렇게 나왔는지 설명된다. 보너스 과제는 06(Custom Transformer), 11(학습 곡선), 12(모듈 구조)에 있다.

## 포함 내용

- 학습 장 12개, 스스로 설명해 보는 점검 질문과 설명 예시
- 원본에서 자동 발췌한 코드 21개와 실제 줄 번호, 11개 파일 소스 탐색
- 직접 조작 실험 4개
  - 규칙 6개를 켜고 끌 때 Test 2,000명의 혼동 행렬·지표·AUC
  - 모델과 임계값을 바꿀 때 혼동 행렬과 Precision·Recall·F1
  - Alpha 5개에서 Ridge·Lasso 계수 비교
  - 승인·보류·거절 임계값을 바꿀 때 구간별 고객 수와 연체율
- `python -m src.run_all`이 만든 그래프 10개와 해석

점검 질문 체크는 스스로 설명해 봤다는 표시일 뿐이다. 자동 채점이 아니며 새로 열면 초기화된다. 합성 데이터 결과이므로 실제 금융 고객에 대한 결론이 아니다.

## 재생성과 검증

A5-1 폴더에서 실행한다. 먼저 분석 결과가 있어야 한다.

```powershell
uv run python -m src.run_all
uv run python tools/build_study_guide.py
uv run python tools/verify_study_guide.py
```

`a5-1.template.html`이 설명과 화면의 편집 원본이다. build 도구는 현재 소스의 코드 발췌, `results/metrics.json`의 수치, `results/figures`의 PNG, `results/test_predictions.json`의 Test 데이터를 HTML에 넣는다. 그리고 `source-manifest.json`과 `calculation-evidence.json`을 저장한다. 본문 수치는 자동으로 바뀌지만, "앙상블이 로지스틱을 이기지 못했다" 같은 해석 문장은 자동으로 바뀌지 않는다. 데이터나 모델을 바꾸면 설명도 다시 검토해야 한다.

verify 도구는 다음을 검사한다.

- 소스·결과·그래프 파일 해시. UTF-8 텍스트는 Git의 LF/CRLF 차이를 LF로 정규화하고, PNG는 원래 바이트로 비교한다.
- 코드 발췌가 원본의 해당 줄과 같은지, 페이지에 표시된 발췌가 원본과 같은지
- 자리표시자, 내부 링크, 스크립트가 찾는 요소, 입력 레이블, 이미지 대체 텍스트
- 내장 Test 데이터가 결과 파일과 같은지

이어서 Node.js로 페이지의 계산 함수를 실행해 scikit-learn 기준값과 대조한다. 규칙 조합, 모델별 임계값, 정책 구간, 저장된 혼동 행렬과 AUC가 대상이다.
