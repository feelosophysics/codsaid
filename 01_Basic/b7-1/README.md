# b7-1 · 현장노트 — 건설 지식 Q&A 챗봇

[기초 과정](../README.md) · [전체 과정](../../README.md)

코디세이 기초 과정 b7-1에서 팀으로 구현한 웹 챗봇의 학습 기록입니다. 회원가입·로그인, 건설 지식 질문과 AI 답변 스트리밍, 대화 저장·조회 기능을 제공합니다.

## 구성과 문서

```text
b7-1/
├── README.md     # 프로젝트 구성과 코드 출처
├── chat-be/      # FastAPI 백엔드, DB, AI 연동, 테스트·학습 문서
│   └── README.md # 백엔드 실행 방법과 API·환경 변수 설명
└── chat-fe/      # HTML·CSS·JavaScript 프론트엔드, 화면 자료
    └── README.md # 프론트엔드 실행 방법과 화면·설정 설명
```

| 자료 | 내용 |
| --- | --- |
| [백엔드 README](chat-be/README.md) | 기능, 로컬 실행, 환경 변수, API, DB, 팀 역할 |
| [프론트엔드 README](chat-fe/README.md) | 화면 구성, API 연결, 실행·배포 방법, 팀 역할 |
| [요구사항 점검표](chat-be/docs/mission-checklist.md) | 구현과 확인 항목 |
| [통합 학습 가이드](chat-be/docs/deep_dive_study_guide.md) | 코드 구조와 학습 설명 |
| [UI 안내](chat-fe/docs/ui-review.md) | 화면 검토와 스크린샷 |

각 프로젝트의 README와 팀 기여 설명은 팀 프로젝트의 구현 기록을 보관합니다. 저장소·배포·PR 안내는 원본 팀 프로젝트 기준입니다.

## 원본과 보관 기준

두 저장소의 `main`을 2026-10-15 KST에 파일 스냅샷으로 보관했습니다.

| 구성 | 원본 저장소 | 기준 커밋 |
| --- | --- | --- |
| 백엔드 | [cocoa7-1/chat-be](https://github.com/cocoa7-1/chat-be) | [`3847bba`](https://github.com/cocoa7-1/chat-be/commit/3847bba40226eb5d99b788d79a9f7b1fbb14497e) |
| 프론트엔드 | [cocoa7-1/chat-fe](https://github.com/cocoa7-1/chat-fe) | [`11d00c6`](https://github.com/cocoa7-1/chat-fe/commit/11d00c6a5963f74572084f295867885617dd97e7) |

코드·문서·스크린샷·설정 예시와 숨김 파일(`.gitignore`, `.github` 등)을 함께 보관합니다. 각 저장소의 `.git`과 커밋·브랜치 이력은 포함하지 않으며, 모든 파일은 `codsaid` 저장소에서 관리합니다. 서브모듈이나 원본과의 자동 동기화 연결은 없습니다. 원본의 후속 변경은 이 사본에 자동 반영되지 않습니다.

하나의 Git 저장소에서 여러 프로젝트를 관리하는 구성을 모노레포라고 합니다. 이 폴더도 백엔드와 프론트엔드를 함께 담지만, 목적은 팀 운영 저장소를 이전하는 것이 아니라 미션 결과물을 보관하는 것입니다. 두 앱의 실행 환경과 의존성은 각각 유지합니다.

## 로컬 실행

`b7-1` 폴더에서 터미널 두 개를 열고 각각 실행합니다. 백엔드는 Python 3.12와 `uv`가 필요하며, 프론트엔드는 별도 빌드가 없습니다.

백엔드(PowerShell):

```powershell
cd chat-be
uv venv --python 3.12
uv pip install -r requirements.txt
Copy-Item .env.example .env
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

프론트엔드(PowerShell):

```powershell
cd chat-fe
python -m http.server 3000
```

브라우저에서 <http://localhost:3000>을 열면 프론트엔드가 로컬 백엔드 <http://localhost:8000>으로 연결합니다. 백엔드 API 문서는 <http://localhost:8000/docs>입니다. 실제 AI 응답에는 백엔드 `.env`의 `GEMINI_API_KEY` 설정이 필요하며, 키가 비어 있으면 데모 응답을 사용합니다. 실행 명령은 각 `chat-be`, `chat-fe` 폴더 안에서 사용합니다.

실제 `.env`, 운영 DB·로그, 설치된 가상환경은 원본 저장소의 추적 파일에 포함되어 있지 않아 이 기록에도 없습니다. 로컬 설정과 데이터는 실행할 때 별도로 생성합니다.

`chat-be/scripts/setup_git_workflow.py`는 원본의 과거 Git 초기화 보조 자료입니다. `git init`·커밋·브랜치·설정을 변경하므로 이 보관 폴더에서 실행하지 마세요. 앱 실행에는 필요하지 않습니다.
