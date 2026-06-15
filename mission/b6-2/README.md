# AI 기반 Git 커밋 & PR 자동 생성기

이 프로젝트는 Git 리포지토리의 변경 사항(`git diff`, `git status`)을 감지하고, Google Gemini AI API를 활용하여 규칙과 컨벤션에 맞는 커밋 메시지와 Pull Request(PR) 초안을 자동으로 생성하는 CLI 도구입니다.

## 주요 기능
- **대화형 Git 연동 (Interactive Commit Flow)**: CLI 환경 내에서 Stage되지 않은 변경 사항(unstaged)을 자동 감지하여 일괄 스테이징(`git add .`)하고, 생성된 커밋 메시지를 검토한 뒤 즉시 실제 로컬 커밋(`git commit`)까지 실행할 수 있도록 대화형 프롬프트를 제공합니다.
- **커밋 메시지 생성**: 변경 사항을 요약하여 제목과 본문을 포함한 커밋 메시지를 생성합니다.
- **PR 초안 생성**: Why, What, How to Test 구조에 맞춘 PR 템플릿을 생성합니다.
- **팀 컨벤션 적용**: `.ai-gitgen.yml` 설정 파일을 통해 커스텀 커밋 프리픽스와 PR 요구사항을 쉽게 적용할 수 있습니다.
- **안전 모드 (Safe Mode)**: 민감한 정보(이메일, API 키 등)를 마스킹 처리하고, 전송되는 줄 수를 제한하여 토큰 낭비와 정보 유출을 방지합니다.

---

## 🚀 설치 및 환경 설정

> [!NOTE]
> **교육장 환경 및 자동화 셋업 안내**
> 이 프로젝트에는 교육장 환경(sudo 권한 제한, 전역 라이브러리 설치 불가 등) 및 개별 PC 환경에서의 편의를 돕기 위해 파이썬 가상환경 빌드를 자동화한 `setup.sh` 셸 스크립트가 제공됩니다.

### 1. 가상환경 구축 및 의존성 자동 설치

프로젝트 루트 디렉토리에서 아래 명령어를 단 1회 실행하여 가상환경 생성, 패치, 패키지 설치를 한 번에 자동 완료할 수 있습니다.

```bash
# 1. 자동 빌드 및 설정 스크립트 실행 (최초 1회)
bash setup.sh

# 2. 가상환경 활성화
source .venv/bin/activate
```

#### 💡 `setup.sh` 자동화 스크립트의 장점 및 수행 역할
- **파이썬 3.10+ 자동 검사**: 시스템 내에 설치된 파이썬 버전들 중 3.10 이상 버전을 자동으로 탐색하여 적합한 인터프리터로 가상환경(`.venv`)을 생성합니다.
- **Alias(별칭) 충돌 및 우선순위 문제 해결**: 터미널 환경(예: 교육장 iMac 환경 등)에 글로벌 `python` 또는 `pip` 별칭(alias)이 지정되어 있을 경우 가상환경 바이너리가 무시되는 현상이 발생합니다. `setup.sh`는 가상환경 활성화 파일(`.venv/bin/activate`)을 패치하여 임시 백업 및 unalias 처리를 하므로, 별도의 바이너리 경로(`.venv/bin/python` 등) 직접 지정을 매번 수행하지 않아도 정상적으로 작동하도록 원천 우회합니다.
- **자동 라이브러리 설치**: 생성 직후 `requirements.txt`를 감지하여 실행에 필요한 `python-dotenv`, `pyyaml` 라이브러리를 자동으로 다운로드합니다.

### 2. API Key 설정 (필수)

Google Gemini AI를 사용하기 위해서는 API Key 발급 및 등록이 필요합니다. **보안을 위해 `.env` 파일 방식을 강력히 권장합니다.**

1. [Google AI Studio](https://aistudio.google.com/)에 접속하여 API 키를 발급받습니다.
2. **방법 A: `.env` 파일 사용 (추천 - 보안 강화)**
   - 프로젝트 루트 디렉토리에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
     ```bash
     cp .env.example .env
     ```
   - `.env` 파일을 텍스트 에디터로 열어 실제 발급받은 API 키를 입력합니다.
     ```env
     AI_API_KEY=여러분의_발급된_API_키
     ```
   - 이 프로젝트의 `.gitignore`에는 이미 `.env`가 등록되어 있으므로, 실제 키가 포함된 파일이 깃허브 등에 유출되지 않습니다.
3. **방법 B: 터미널 세션 환경변수 직접 등록 (임시 사용)**
   - 파일을 만들지 않고 터미널 세션 동안에만 임시로 등록해 사용하려면 아래 명령을 사용합니다.
     ```bash
     export AI_API_KEY="여러분의_발급된_API_키"
     ```

---

## 💻 사용 방법

**주의사항**: 반드시 Git이 초기화(`git init`)된 디렉토리 안에서 실행해야 하며, 변경된 파일(`git add` 전 또는 후 모두 가능)이 있어야 결과가 생성됩니다.
가상환경이 활성화된 상태(`(.venv)` 표시 확인)에서 아래 명령어를 실행하세요.


### 1. 커밋 메시지 생성 (대화형 워크플로우 지원)

```bash
python main.py commit
```

이 명령어는 저장소 내 변경 사항을 분석하여 커밋 메시지를 자동 생성할 뿐만 아니라, **자동 스테이징 및 최종 커밋까지 일련의 과정을 CLI 환경에서 확인하며 진행하는 대화형(Interactive) 흐름**을 지원합니다.

#### 💡 작동 시나리오 및 흐름 설명
1. **Unstaged 변경 사항 감지 및 자동 Stage 여부 확인**:
   - 아직 스테이징(`git add`)하지 않은 변경 사항이나 신규 파일(untracked)이 감지되면, 모두 한꺼번에 stage(`git add .`)하고 진행할지 사용자에게 질문합니다.
     - **`y` (또는 `yes`) 입력 시**: 자동으로 전체 변경 사항을 스테이징 처리한 뒤 커밋 메시지 생성을 진행합니다.
     - **`n` (또는 `no`) 입력 시**: 이미 스테이징(Staged)되어 있는 변경 사항만을 대상으로 커밋 메시지를 생성합니다. (단, 최종적으로 스테이징된 변경 사항이 전혀 없다면 작업을 안전하게 종료합니다.)
2. **최종 커밋 여부 확인 및 자동 커밋 실행**:
   - AI가 생성한 커밋 메시지 초안을 화면에 구분선과 함께 출력한 뒤, 이 메시지를 사용하여 실제 Git 커밋을 완료할지 다시 한번 묻습니다.
     - **`y` (또는 `yes`) 입력 시**: 터미널에 생성된 메시지 그대로 로컬 커밋(`git commit -m "..."`)이 실행됩니다.
     - **`n` (또는 `no`) 입력 시**: 커밋을 실행하지 않고 종료하며, 사용자는 생성된 텍스트를 직접 수정하거나 복사하여 수동으로 커밋할 수 있습니다.

#### 🖥️ 터미널 출력 예시 (전체 대화형 흐름)

```
$ python main.py commit
unstaged 변경 사항이 있습니다. 모두 stage(git add .)하고 진행할까요? (y/n): y
[INFO] 모든 변경 사항을 성공적으로 stage(git add .) 하였습니다.
[INFO] .ai-gitgen.yml 컨벤션 파일을 성공적으로 불러왔습니다.
[INFO] AI API 요청 중...
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
feat: AI 기반 Git 커밋 & PR 자동 생성 기능 추가

- `main.py` 파일에 argparse를 활용한 CLI 기본 구조 및 Gemini API 연동 로직 추가
- `.ai-gitgen.yml` 파일을 추가하여 커밋/PR 템플릿 컨벤션을 정의할 수 있도록 구현
----------------------

이 메시지로 커밋하시겠습니까? (y/n): y
[INFO] 커밋이 성공적으로 완료되었습니다!
```

### 2. PR 초안 생성
```bash
python main.py pr
```

**출력 예시:**
```
[INFO] Git status 수집 완료: 변경 감지
[INFO] Git diff 수집 완료: 120줄
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Draft ---
AI 기반 커밋 & PR 자동화 툴 개발 완료

## Why (변경 배경)
- 개발 과정에서 커밋 메시지와 PR을 작성하는 데 드는 시간과 노력을 줄이기 위해 자동화 도구가 필요했습니다.

## What (핵심 변경 사항)
- `main.py`를 통해 `commit` 및 `pr` 명령어 구현
- Google Gemini API를 활용하여 `git diff` 기반 요약 기능 추가

## How to Test (테스트 방법)
- 환경변수 `AI_API_KEY` 설정 후 `python main.py commit` 실행
- 정상적으로 마크다운 형태의 결과물이 출력되는지 확인
-----------------
```

### 3. 예외 상황 처리 예시

**API Key가 설정되지 않은 상태로 실행 시:**
```bash
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
## 예) export AI_API_KEY="여러분의_API_KEY"
```

**Git 변경 사항이 없는 상태로 실행 시:**
```bash
[INFO] 변경 사항이 없습니다. 커밋/PR 메시지를 생성하지 않고 종료합니다.
```

### 4. 안전 모드 (Safe Mode) 사용
민감한 정보 유출을 막기 위해 켜두는 것을 권장합니다.
```bash
python main.py --safe-mode commit
```
- 200줄 이상의 diff는 200줄로 잘립니다.
- 이메일 형태나 API 토큰 형태를 정규식으로 감지하여 `***MASKED***` 로 치환한 뒤 AI에게 전송합니다.

### 5. CLI 옵션을 통한 모델 튜닝 및 결과 비교
원하는 대로 AI 모델과 응답 방식을 조절할 수 있습니다.
- `--model`: 사용할 AI 모델 (기본: `gemma-4-31b-it`)
- `--temperature`: 창의성 조절 (0.0~1.0, 기본: `0.7`)
- `--max-tokens`: 토큰 생성 제한 (기본: `1000`)
- `--safe-lines`: 안전 모드 활성화 시 전송할 최대 diff 라인 수 (기본: `200`)
- `--thinking-level`: Gemma 4 모델 사용 시 사고 수준 설정 (`high` 또는 `unspecified`, 기본: `unspecified`)

**Temperature 변경 비교 테스트:**
```bash
# --temperature 0.0 으로 실행한 결과 (보수적/일관된 출력)
$ python main.py --temperature 0.0 pr
[INFO] Git status 수집 완료: 변경 감지
[INFO] Git diff 수집 완료: 44줄
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Draft ---
# [추가] 통계 계산 및 리포트 포맷팅 유틸리티 구현

## Why (변경 배경)
- 데이터 분석 및 결과 보고를 위해 평균, 분산, 표준편차와 같은 기본적인 통계 수치를 계산하고 이를 정형화된 텍스트로 출력하는 공통 기능이 필요합니다.

## What (핵심 변경 사항)
- `temp_utility.py` 파일 신규 생성
- `calculate_statistics` 함수 구현: 숫자 리스트를 입력받아 평균(mean), 분산(variance), 표준편차(std_dev)를 계산하여 딕셔너리로 반환 (빈 리스트 처리 포함)
- `format_report` 함수 구현: 통계 결과 딕셔너리를 읽기 쉬운 문자열 리포트 형식으로 포맷팅

## How to Test (테스트 방법)
- `calculate_statistics` 함수에 숫자 리스트를 전달하여 계산된 통계 값이 수학적으로 정확한지 확인합니다.
- 빈 리스트를 입력했을 때 에러 없이 기본값(0.0)들이 반환되는지 확인합니다.
- `format_report` 함수에 통계 딕셔너리를 전달하여 출력되는 문자열의 형식이 의도한 리포트 양식과 일치하는지 확인합니다.
-----------------

# --temperature 1.0 으로 실행한 결과 (창의적/다양한 표현의 출력)
$ python main.py --temperature 1.0 pr
[INFO] Git status 수집 완료: 변경 감지
[INFO] Git diff 수집 완료: 44줄
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Draft ---
# [Feature] 통계 계산 및 리포트 생성을 위한 utility 모듈 추가

## Why (변경 배경)
- 데이터 분석 및 결과 보고를 위해 평균, 분산, 표준편차와 같은 기본적인 통계 수치를 반복적으로 계산해야 하는 필요성이 발생했습니다.
- 계산된 수치를 일관된 형식으로 출력하기 위한 공통 포맷팅 함수가 필요합니다.

## What (핵심 변경 사항)
- `temp_utility.py` 파일 신규 생성
- `calculate_statistics` 함수 구현: 숫자 리스트를 입력받아 평균(mean), 분산(variance), 표준편차(std_dev)를 계산하여 딕셔너리 형태로 반환 (빈 리스트 처리 로직 포함)
- `format_report` 함수 구현: 통계 결과 딕셔너리를 가독성 좋은 문자열 리포트 형식으로 변환

## How to Test (테스트 방법)
- `calculate_statistics` 함수에 다양한 숫자 리스트를 입력하여 계산 값이 수학적으로 정확한지 확인합니다.
- 빈 리스트 `[]`를 입력했을 때 모든 값이 `0.0`으로 반환되는 예외 처리 동작을 확인합니다.
- `format_report` 함수에 통계 딕셔너리를 전달하여 지정된 포맷(소수점 4자리)으로 리포트가 출력되는지 확인합니다.
-----------------
```

**Max Tokens 제한 테스트:**
```bash
# --max-tokens 값을 작게 주어 텍스트가 잘리는 현상 확인 결과
$ python main.py --max-tokens 50 pr
[INFO] Git status 수집 완료: 변경 감지
[INFO] Git diff 수집 완료: 44줄
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Draft ---
*   Input: Git status and diff showing the creation of a new file `temp_utility.py`.
    *   File Content: Contains two functions: `calculate_statistics` (calculates mean, variance, std_
-----------------
```

---

## 🛠 컨벤션 커스터마이징

프로젝트 루트 폴더에 있는 `.ai-gitgen.yml` 파일을 열어서, 팀에서 사용하는 커밋 규칙이나 PR 템플릿 항목을 수정할 수 있습니다. 프로그램 실행 시 자동으로 이 파일을 읽고 규칙을 반영하여 생성합니다.

---

## ⚠️ 주의사항 및 요금 안내
- **민감 정보**: `git diff`에 사내 비밀번호나 진짜 서비스용 API Key가 하드코딩되지 않았는지 실행 전 확인하세요. 불안하다면 `--safe-mode`를 꼭 사용하세요.
- **요금**: gemma-4-31b-it 및 Gemini 모델은 무료 할당량(Free Tier) 범위 내에서 비용 없이 사용할 수 있지만, 한도 초과 시 과금 또는 호출 제한이 발생할 수 있습니다. `max-tokens`를 제한해둔 이유도 이러한 비용 및 자원 낭비를 막기 위함입니다.

---

## 🎁 보너스 과제 제출 및 증빙

### 1. 실제 리포지토리에 적용하여 PR 1건 완성하기 (보너스 5.1)
- **PR 링크**: https://github.com/feelosophysics/glad/pull/1/commits
- **AI 초안 ➡️ 최종 PR 변경점 요약본** (무엇을 왜 고쳤는지):
  - **수정 사항 (What)**:
    1. AI 초안의 문체와 표현을 더 자연스럽고 간결한 개발자 톤(명확한 개조식)으로 정제했습니다.
    2. `How to Test` 섹션의 실행 예시 명령어에서 가상환경 바이너리 경로(`.venv/bin/python`)와 실제 파일 인자 전달 방법을 더 구체화하고 명확하게 수정했습니다.
    3. `What` 섹션의 변경 사항 목록에 `.gitignore` 및 `.env.example` 관련 설정 파일 추가에 대한 누락된 설명을 보강했습니다.
  - **수정 이유 (Why)**:
    - AI가 생성한 초안은 문장이 약간 기계적이고 장황한 부분이 있어, 실제 협업 시 리뷰어가 한눈에 알아보기 쉽도록 가독성을 높이기 위해 요약 및 다듬기 과정을 거쳤습니다. 또한 로컬 환경의 특수한 실행 조건(iMac 등의 시스템 파이썬 별칭 문제 등)을 고려해, 테스트 방법의 명령어를 구체적인 절대/상대 경로로 안내하여 오작동을 예방하고자 했습니다.

- **AI 생성 초안 (Before)**:
  ````markdown
  feat: AI Git 생성기 초기 설정 및 핵심 기능 구현

  ## Why (변경 배경)
  - AI Git 생성기 프로젝트의 기반을 마련하고, Git 변경 사항을 분석하여 커밋 메시지 및 PR 초안을 자동으로 생성하는 핵심 기능을 구현하기 위함입니다.
  - 팀 컨벤션을 `.ai-gitgen.yml` 파일로 관리하여 일관된 커밋 및 PR 작성을 돕고, 개발 효율성을 높이고자 합니다.

  ## What (핵심 변경 사항)
  - `ai-gitgen.yml` 파일:
    - 커밋 메시지 접두사(prefix_rules) 목록을 정의했습니다.
    - 커밋 메시지 및 PR 초안 생성 시 추가 요구사항(format_requirements, additional_requirements)을 명시했습니다.
    - 이 파일을 통해 팀의 Git 컨벤션을 중앙에서 관리할 수 있습니다.
  - `main.py` 파일:
    - Git 저장소의 상태(`get_git_status()`) 및 변경 내용(`get_git_diff()`)을 가져오는 기능을 구현했습니다.
    - 민감한 정보를 마스킹하고 diff 길이를 제한하는 안전 모드(`apply_safe_mode()`)를 추가하여 보안을 강화했습니다.
    - `.ai-gitgen.yml` 파일을 읽어 팀 컨벤션을 불러오는 `load_convention()` 함수를 구현했습니다.
    - Google Gemini REST API를 호출하여 AI 응답을 받는 `call_gemini_api()` 함수를 구현했습니다.
    - 이 파일은 Git 변경 사항을 기반으로 커밋 메시지 및 PR 초안을 생성하는 AI Git 생성기의 핵심 로직을 담당합니다.

  ## How to Test (테스트 방법)
  - 로컬 Git 저장소에서 `main.py`를 실행하여 현재 변경 사항에 대한 커밋 메시지 또는 PR 초안이 정상적으로 생성되는지 확인합니다.
  - `.env` 파일에 `AI_API_KEY`를 올바르게 설정한 후 테스트를 진행합니다.
  - `ai-gitgen.yml` 파일의 내용을 변경하여 AI가 생성하는 커밋 메시지 및 PR 초안에 반영되는지 확인합니다.
  - 의도적으로 큰 변경사항을 만들거나 민감 정보가 포함된 변경사항을 만들어 안전 모드가 올바르게 동작하는지 확인합니다.
  ````

- **최종 반영 PR (After)**:
  ````markdown
  feat: AI 기반 Git 커밋 메시지 및 PR 초안 자동 생성기 구현

  ## 💡 Why (변경 배경)
  - 로컬 개발 및 협업 과정에서 커밋 메시지와 Pull Request 설명을 작성하는 데 소요되는 반복적인 시간을 줄이고자 합니다.
  - 프로젝트 변경 사항(`git diff` 및 `git status`)을 AI가 자동으로 분석하여 일관된 형식의 초안을 생성함으로써 코드 리뷰 프로세스의 생산성을 높이고자 도입했습니다.
  - 팀마다 다른 Git 컨벤션을 유연하게 적용할 수 있도록 유연한 템플릿 환경을 구성했습니다.

  ## 🛠️ What (핵심 변경 사항)
  - **`main.py` (핵심 CLI 애플리케이션)**:
    - `git status` 및 `git diff`를 통해 변경 내용과 파일 목록을 자동으로 수집하는 함수 구현
    - 환경변수(`AI_API_KEY`) 기반으로 Google Gemini API와 통신하여 결과를 생성하는 REST API 연동 로직 추가
    - 민감한 개인 정보(이메일, API Key 등)를 정규식으로 마스킹하고, 토큰 절약을 위해 diff 길이를 200줄로 제한하는 **안전 모드(`--safe-mode`)** 추가
  - **`.ai-gitgen.yml` (팀 컨벤션 정의 설정 파일)**:
    - 커밋 제목의 접두사 규칙(feat, fix, docs 등) 및 커밋/PR 생성 시의 세부 스타일(존댓말 권장, 파일 역할 기재 등) 설정
  - **`.env.example` 및 `.gitignore`**:
    - API Key 유출 방지를 위해 `.env` 파일을 로컬에서 안전하게 관리할 수 있도록 가이드 파일 및 예외 경로 추가

  ## 🧪 How to Test (테스트 방법)
  1. 로컬 가상환경 진입 및 의존성 설치:
     ```bash
     source .venv/bin/activate
     pip install python-dotenv pyyaml
     ```
  2. `.env` 파일에 발급받은 `AI_API_KEY` 환경변수 설정
  3. 임의의 코드 파일 변경 후 CLI 실행:
     - 커밋 메시지 생성: `.venv/bin/python main.py commit`
     - PR 초안 생성: `.venv/bin/python main.py pr`
     - 안전 모드 테스트: `.venv/bin/python main.py --safe-mode pr`
  ````

### 2. 커밋/PR 템플릿 커스터마이징 (보너스 5.2)
- **팀 컨벤션 정의 및 적용 방법**:
  - 프로젝트 루트에 `.ai-gitgen.yml` 설정 파일을 정의하여 팀의 Git 컨벤션(커밋 메시지 제목 접두사 규칙 및 PR 추가 요구사항)을 구성했습니다.
  - `main.py`는 `pyyaml` 라이브러리를 사용해 이 설정 파일을 파싱하며, 실행 시 AI API의 프롬프트 컨텍스트에 설정된 규칙들을 주입하여 일관된 템플릿과 스타일의 커밋/PR 생성을 보장합니다.
- **컨벤션 적용 전/후 생성 결과 비교**:
  - **적용 전 (기본 프롬프트)**:
    AI가 임의의 접두사(예: `feat:`, `update:`)를 선택하거나, 설명 형식을 자유롭게 생성하여 일관성이 부족함.
  - **적용 후 (컨벤션 적용)**:
    YAML 파일에 정의된 `feat:`, `fix:`, `docs:` 등 정해진 접두사만을 엄격하게 선택하며, PR의 경우 "해요체"를 사용하여 친절한 톤앤매너와 파일별 역할 변화에 초점을 맞춰 일관되게 생성됨.

### 3. 안전 모드 고도화 (보너스 5.3)
- **안전 모드(safe-mode) 정책**:
  - **전송 범위 조절 기능**: `--safe-lines` (또는 `-safe-lines`) 옵션을 추가하여 안전 모드 활성화 시 전송할 최대 `git diff` 라인 수를 사용자 환경에 맞게 조절 가능합니다. (기본값: `200`줄)
  - **민감 정보 마스킹 확장**: 정규표현식(Regex)을 이용해 다음과 같은 민감 데이터를 자동으로 검출하고 치환합니다.
    1. 이메일 주소: `***@***.***`로 치환
    2. API Key (`sk-` 접두사로 시작하는 20자 이상의 토큰): `sk-***MASKED***`로 치환
    3. Bearer 토큰: `Bearer ***MASKED***`로 치환
    4. IPv4 주소: `***.***.***.***`로 치환
    5. 비밀번호/시크릿 키 패턴 (`password`, `secret`, `passwd` 등 변수 대입식): `password="su***********************"` 형태로 앞부분 2글자만 남기고 나머지는 별표(`*`)로 마스킹 처리하여 누출 방지
- **safe-mode ON/OFF 결과 차이 비교**:
  - **원본 변경 내용 (Safe Mode OFF)**:
    ```diff
    + test_email = "developer@company.com"
    + test_api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"
    + test_bearer = "Bearer abcdef123456"
    + test_ip = "192.168.1.100"
    + password = "super_secret_password_123"
    + client_secret = "my_private_secret"
    ```
  - **치환 및 단축 처리 내용 (Safe Mode ON)**:
    ```diff
    [INFO] 안전 모드(safe-mode)가 활성화되었습니다. 민감 정보를 마스킹하고 길이를 200줄로 제한합니다.

    + test_email = "***@***.***"
    + test_api_key = "sk-***MASKED***"
    + test_bearer = "Bearer ***MASKED***"
    + test_ip = "***.***.***.***"
    + password="su***********************"
    + client_secret="my***************"
    ```

