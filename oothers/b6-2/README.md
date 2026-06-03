# AI 기반 Git 커밋 & PR 자동 생성기

이 프로젝트는 Git 리포지토리의 변경 사항(`git diff`, `git status`)을 감지하고, Google Gemini AI API를 활용하여 규칙과 컨벤션에 맞는 커밋 메시지와 Pull Request(PR) 초안을 자동으로 생성하는 CLI 도구입니다.

## 주요 기능
- **커밋 메시지 생성**: 변경 사항을 요약하여 제목과 본문을 포함한 커밋 메시지를 생성합니다.
- **PR 초안 생성**: Why, What, How to Test 구조에 맞춘 PR 템플릿을 생성합니다.
- **팀 컨벤션 적용**: `.ai-gitgen.yml` 설정 파일을 통해 커스텀 커밋 프리픽스와 PR 요구사항을 쉽게 적용할 수 있습니다.
- **안전 모드 (Safe Mode)**: 민감한 정보(이메일, API 키 등)를 마스킹 처리하고, 전송되는 줄 수를 제한하여 토큰 낭비와 정보 유출을 방지합니다.

---

## 🚀 설치 및 환경 설정

### 1. 파이썬 라이브러리 설치
이 도구는 기본 파이썬 라이브러리를 사용하지만, 컨벤션 설정(`.ai-gitgen.yml`)을 사용하기 위해서는 `pyyaml` 라이브러리가 필요합니다.
```bash
pip install pyyaml
```

### 2. API Key 설정 (필수)
Google Gemini AI를 사용하기 위해서는 API Key 발급이 필요합니다.
1. [Google AI Studio](https://aistudio.google.com/) 에 접속하여 API 키를 발급받습니다.
2. 발급받은 키를 터미널 환경변수에 등록합니다.
   - **Mac/Linux:** `export AI_API_KEY="여러분의_발급된_API_키"`
   - **Windows(CMD):** `set AI_API_KEY="여러분의_발급된_API_키"`
   - **Windows(PowerShell):** `$env:AI_API_KEY="여러분의_발급된_API_키"`

---

## 💻 사용 방법

**주의사항**: 반드시 Git이 초기화(`git init`)된 디렉토리 안에서 실행해야 하며, 변경된 파일(`git add` 전 또는 후 모두 가능)이 있어야 결과가 생성됩니다.

### 1. 커밋 메시지 생성
```bash
python main.py commit
```

**출력 예시:**
```
[INFO] Git status 수집 완료: 변경 감지
[INFO] Git diff 수집 완료: 45줄
[INFO] .ai-gitgen.yml 컨벤션 파일을 성공적으로 불러왔습니다.
[INFO] AI API 요청 중...
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
feat: AI 기반 Git 커밋 & PR 자동 생성 기능 추가

- `main.py` 파일에 argparse를 활용한 CLI 기본 구조 및 Gemini API 연동 로직 추가
- `.ai-gitgen.yml` 파일을 추가하여 커밋/PR 템플릿 컨벤션을 정의할 수 있도록 구현
----------------------
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

### 3. 안전 모드 (Safe Mode) 사용
민감한 정보 유출을 막기 위해 켜두는 것을 권장합니다.
```bash
python main.py commit --safe-mode
```
- 200줄 이상의 diff는 200줄로 잘립니다.
- 이메일 형태나 API 토큰 형태를 정규식으로 감지하여 `***MASKED***` 로 치환한 뒤 AI에게 전송합니다.

### 4. 추가 CLI 옵션
원하는 대로 AI 모델과 응답 방식을 조절할 수 있습니다.
- `--model`: 사용할 AI 모델 (기본: `gemini-1.5-flash`)
- `--temperature`: 창의성 조절 (0.0~1.0, 기본: `0.7`)
- `--max-tokens`: 토큰 생성 제한 (기본: `500`)

예시:
```bash
python main.py pr --temperature 0.2 --max-tokens 800
```

---

## 🛠 컨벤션 커스터마이징 (Bonus 5.2)

프로젝트 루트 폴더에 있는 `.ai-gitgen.yml` 파일을 열어서, 팀에서 사용하는 커밋 규칙이나 PR 템플릿 항목을 수정할 수 있습니다. 프로그램 실행 시 자동으로 이 파일을 읽고 규칙을 반영하여 생성합니다.

---

## ⚠️ 주의사항 및 요금 안내
- **민감 정보**: `git diff`에 사내 비밀번호나 진짜 서비스용 API Key가 하드코딩되지 않았는지 실행 전 확인하세요. 불안하다면 `--safe-mode`를 꼭 사용하세요.
- **요금**: Gemini 1.5 Flash는 무료 할당량(Free Tier) 범위 내에서 비용 없이 사용할 수 있지만, 한도 초과 시 과금될 수 있습니다. `max-tokens`를 제한해둔 이유도 이러한 비용 및 자원 낭비를 막기 위함입니다.
