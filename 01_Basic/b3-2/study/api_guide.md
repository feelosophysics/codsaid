# Google AI Studio API Key 안전하게 사용하기 가이드

Google AI Studio에서 발급받은 API 키는 개인 비밀번호와 같으므로, **절대 코드에 하드코딩하거나 깃허브(GitHub) 등의 버전 관리 시스템에 업로드해서는 안 됩니다.**

이 가이드에서는 **`.env` 파일**과 **`python-dotenv` 패키지**를 사용하여 API 키를 안전하게 관리하고 프로젝트에 적용하는 방법을 단계별로 안내합니다.

---

## 💡 요약: 왜 이 방법을 쓰나요?
* **하드코딩 방지**: API 키를 코드 외부의 별도 설정 파일(`.env`)에 분리하여 저장합니다.
* **깃허브 유출 방지**: `.env` 파일을 `.gitignore`에 등록하여 Git 추적에서 제외합니다. (현재 이 프로젝트의 [.gitignore](file:///Users/f22losophysics1091/Desktop/check/.gitignore#L151)에는 이미 `.env`가 등록되어 있어 안전합니다!)
* **유연성**: 로컬 개발 환경, 스테이징, 운영 환경마다 서로 다른 API 키를 코드 수정 없이 쉽게 전환할 수 있습니다.

---

## 🛠️ 실습 단계

### 1단계: `.env` 파일 생성 및 API 키 저장

프로젝트 루트 디렉토리(즉, `main.py`가 있는 곳)에 **`.env`** 이름의 파일을 생성하고 다음과 같이 API 키를 입력합니다.

> [!IMPORTANT]
> 파일 이름은 앞의 점(`.`)을 포함하여 반드시 `.env`여야 하며, 키와 값 사이에 공백이 없어야 합니다.

```env
AI_API_KEY=your_google_ai_studio_api_key_here
```
*(예: `AI_API_KEY=AIzaSy...`)*

---

### 2단계: 환경 변수 관리 라이브러리 설치

파이썬에서 `.env` 파일을 자동으로 읽어 환경 변수로 등록해 주는 `python-dotenv` 패키지를 설치합니다. 터미널에서 아래 명령어를 실행하세요.

```bash
pip install python-dotenv
```

---

### 3단계: `.gitignore` 확인 (보안 강화)

프로젝트 루트의 [.gitignore](file:///Users/f22losophysics1091/Desktop/check/.gitignore) 파일에 `.env`가 포함되어 있는지 확인합니다. 
이미 다음과 같이 등록되어 있으므로 `.env` 파일은 실수로 `git commit`을 하더라도 깃허브에 올라가지 않습니다.

```text
# Environments
.env
.envrc
.venv
venv/
```

---

### 4단계: 코드에 적용하기 (`main.py` 수정)

현재 `main.py`는 `os.environ.get("AI_API_KEY")`를 통해 시스템 환경 변수에서 API 키를 가져오도록 구현되어 있습니다. `.env` 파일의 값을 자동으로 가져올 수 있도록 [main.py](file:///Users/f22losophysics1091/Desktop/check/main.py#L1-L13)의 시작 부분에 `dotenv` 로드 코드를 추가하는 것이 좋습니다.

#### 수정 전 (`main.py`)
```python
import os
import sys
# ...
```

#### 수정 후 (`main.py`) - 추천 코드 변경
`python-dotenv`가 설치되어 있으면 자동으로 `.env` 파일을 읽고, 설치되어 있지 않더라도 오류 없이 기존 시스템 환경 변수를 사용할 수 있도록 예외 처리를 적용한 안전한 코드입니다.

```python
import os
import sys
import argparse
import subprocess
import json
import urllib.request
import urllib.error
import re

# .env 파일 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv 라이브러리가 없을 경우 환경 변수에서 직접 읽어오므로 경고를 생략하거나 안내할 수 있습니다.
    pass

try:
    import yaml # pip install pyyaml 이 필요할 수 있음
except ImportError:
    yaml = None # yaml 라이브러리가 없으면 기본 설정 사용
```

---

### 5단계: `.env.example` 공유용 템플릿 생성 (협업 권장 사항)

`.env` 파일은 깃허브에 올리지 않으므로, 다른 사람이 내 프로젝트를 복제(Clone)했을 때 어떤 환경 변수가 필요한지 알 수 없습니다.
이를 해결하기 위해 실제 API 키는 제외하고 **변수명만 명시한 템플릿 파일**인 `.env.example` 파일을 만들어 깃허브에 함께 올립니다.

프로젝트 루트에 `.env.example` 파일을 만들고 아래와 같이 작성합니다.

```env
# Google AI Studio API Key (https://aistudio.google.com/)
AI_API_KEY=your_api_key_here
```

다른 팀원이나 사용자는 이 프로젝트를 가져간 뒤, `.env.example` 파일을 복사하여 `.env`로 이름을 바꾸고 자신의 API 키만 채워 넣으면 바로 작동하게 됩니다.

---

## 🏃 실행 및 테스트 방법

1. 위의 수정 사항을 코드에 반영하고 `.env` 파일을 작성합니다.
2. 터미널에서 다음 명령어를 실행하여 변경 내용에 대한 AI 커밋 메시지 생성이 정상 작동하는지 확인합니다.

```bash
# safe-mode를 함께 켜서 실행하는 것을 추천합니다.
python3 main.py commit --safe-mode
```

정상적으로 API 키가 읽히면, Gemini가 현재 변경사항(diff)을 분석하여 아름답게 작성된 커밋 메시지 초안을 출력할 것입니다!

---

## 🔒 대안: 터미널 세션에 임시 등록하여 사용하기 (파일 저장 없음)

만약 컴퓨터에 어떤 파일 형태로도 API 키를 남기고 싶지 않다면, 터미널 세션에만 임시로 등록하여 사용할 수도 있습니다.

터미널을 열고 다음 명령어를 입력합니다:
```bash
export AI_API_KEY="발급받은_실제_API_키"
```

* **장점**: 디스크에 파일로 저장되지 않으므로 절대 유출될 위험이 없습니다.
* **단점**: 터미널 창을 닫으면 설정이 사라지므로, 새 터미널을 열 때마다 매번 다시 명령어를 실행해야 합니다.
