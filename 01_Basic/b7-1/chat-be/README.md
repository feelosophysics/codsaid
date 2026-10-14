# 현장노트 — 건설 지식 Q&A 챗봇

건설 용어와 절차가 익숙하지 않은 사용자를 위한 웹 챗봇입니다. 로그인한 사용자가 시공·공정, 인허가, 계약·비용, 자재·구조 등의 질문을 하고 답변과 이전 대화를 조회할 수 있습니다.

- [챗봇 서비스](https://b7-1-chat-fe.vercel.app)
- [API 문서](https://b71chatbe.ddns.net/docs)
- [백엔드 저장소](https://github.com/cocoa7-1/chat-be) · [프론트 저장소](https://github.com/cocoa7-1/chat-fe)

## 기능과 시스템 구조

회원가입 → 로그인 → 질문 → AI 답변 스트리밍 → 대화 저장 → 내 기록 조회 순서로 사용합니다. 입력창에서 모델·추론 수준·웹 검색을 선택할 수 있습니다. 웹 검색을 수행한 답변에는 출처가 표시됩니다.

```text
브라우저 ── Vercel: 정적 HTML/CSS/JavaScript
   └──── HTTPS ── EC2 / Caddy ── Uvicorn / FastAPI
                                   ├─ SQLite: 계정·대화 저장
                                   └─ Google AI API: 답변 생성·검색
```

Python 3.12, FastAPI, SQLAlchemy, SQLite, Google GenAI SDK를 사용합니다. 비밀번호는 bcrypt 해시로 저장하고 JWT로 인증합니다. 프론트는 Bearer 헤더를 사용하며 서버는 HttpOnly 쿠키도 지원합니다. AI는 최근 메시지를 문맥으로 받고, 실패한 답변은 다음 요청의 문맥에서 제외합니다.

## 로컬 실행

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

PowerShell의 파일 복사는 `Copy-Item .env.example .env`입니다. 프론트 저장소에서 `python -m http.server 3000`을 실행하고 http://localhost:3000 에 접속합니다. 백엔드 상태는 http://localhost:8000/ , API 명세는 http://localhost:8000/docs 에서 확인합니다.

### 환경 변수

실제 값은 서버 환경 또는 `.env`에 설정합니다. `.env.example`은 비밀 없는 작성 예시이며 `.env`·DB·로그는 `.gitignore` 대상입니다.

| 이름 | 기본값 / 용도 |
|---|---|
| APP_NAME | 서비스 이름 |
| APP_ENV / DEBUG | development / true. 운영은 production / false |
| CORS_ALLOWED_ORIGINS | 허용 Origin JSON 배열. 운영은 ["https://b7-1-chat-fe.vercel.app"], 로컬은 .env.example 참고 |
| HOST / PORT | 개발 실행 바인딩, 0.0.0.0 / 8000 |
| SECRET_KEY / ALGORITHM | JWT 서명 키 / HS256. 운영에는 고유한 랜덤 키 32바이트 이상 필요 |
| ACCESS_TOKEN_EXPIRE_MINUTES / COOKIE_NAME | 토큰1440분 / access_token |
| DATABASE_URL | sqlite:///./chatbot.db |
| GEMINI_API_KEY | 서버 전용 Google API 키. 비어 있으면 Demo 응답 |
| GEMINI_MODEL_NAME | gemma-4-26b-a4b-it |
| GEMINI_SEARCH_ENABLED | true, 요청에서 검색 허용 여부 선택 가능 |
| AI_TIMEOUT_SECONDS / AI_SEARCH_TIMEOUT_SECONDS | 일반60초 / 검색90초, 연결과 전체 스트림에 적용 |
| MAX_HISTORY_MESSAGES | 최근10개 메시지 |
| SYSTEM_INSTRUCTION | 건설 Q&A 시스템 지시문 |
| REGISTER_REQUESTS_PER_MINUTE | 가입 IP당5회/60초 |
| LOGIN_REQUESTS_PER_MINUTE | 로그인·비밀번호 변경 IP당10회/60초 |
| CHAT_REQUESTS_PER_MINUTE / CHAT_GLOBAL_REQUESTS_PER_MINUTE | 사용자6회 / 전체20회/60초 |
| CHAT_USER_CONCURRENCY / CHAT_GLOBAL_CONCURRENCY | 사용자1개 / 전체3개 동시 요청 |

키가 설정됐는데 SDK 초기화가 실패하면 AI_INIT_ERROR를 반환합니다. 운영에 필요한 환경설정과 systemd 예시는 [배포 가이드](docs/deployment.md)에 있습니다.

## API 명세

인증 API에는 `Authorization: Bearer <access_token>`을 전송합니다. 상세 스키마는 Swagger 문서에 있습니다.

| 메서드 | 경로 | 인증 | 기능 |
|---|---|---|---|
| GET | / | 없음 | 서버 상태 |
| POST | /api/v1/auth/register | 없음 | 가입 |
| POST | /api/v1/auth/login | 없음 | 로그인·JWT 발급 |
| POST | /api/v1/auth/logout | 없음 | 인증 쿠키 제거 |
| GET | /api/v1/auth/me | 필요 | 내 계정 |
| PUT | /api/v1/auth/password | 필요 | 비밀번호 변경 |
| GET | /api/v1/chat/models | 필요 | 모델·추론 선택 목록 |
| GET / POST | /api/v1/chat/sessions | 필요 | 내 대화 조회 / 생성 |
| DELETE | /api/v1/chat/sessions/{session_id} | 필요 | 내 대화 삭제 |
| GET | /api/v1/chat/sessions/{session_id}/messages | 필요 | 대화 메시지 |
| POST | /api/v1/chat/stream | 필요 | 질문·SSE 응답 |
| GET | /api/v1/logs | 필요 | 내 기록·페이지네이션 |
| GET | /api/v1/logs/stats | 필요 | 질문/답변·지연시간 통계 |

가입 요청과 응답 예시:

```json
{"username":"demo_user","nickname":"학습자","password":"examplePassword123!"}
```
```json
{"id":1,"username":"demo_user","nickname":"학습자","is_active":true,"is_admin":false,"created_at":"2026-10-05T00:00:00"}
```

가입 성공201, 중복아이디400, 로그인 실패401, 잘못된입력422입니다. 로그인은 username/password를 받고 access_token/token_type/user를 반환합니다. 닉네임은 필수, 비밀번호는8자 이상입니다.

질문 요청 예시:

```json
{"message":"감리와 감독의 차이를 설명해 줘.","session_id":1,"model":"gemma-4-26b-a4b-it","search_enabled":false,"thinking_level":"minimal"}
```

session_id를 생략하면 새 대화를 만듭니다. 질문은1~2,000자이며 공백만 있는 입력은 거절합니다. model/search_enabled/temperature/thinking_level은 선택 필드입니다.

| 모델 | 추론 수준 |
|---|---|
| Gemma4 26B / 31B | minimal(끔), high(켬) |
| Gemini3.8 / 3.7 Flash | low, medium, high |
| Gemini3.6 / 3.5 Flash / 3.5 Flash-Lite | minimal, low, medium, high |

모델 목록의 정확한 ID와 빠른 기본 추론 수준은 모델 API에서 제공합니다. temperature는0~2이며 기본값은 Gemma0.7/Gemini1.0입니다. 모델별 무료 한도는 Google 프로젝트의 AI Studio에서 확인합니다.

```text
event: meta
data: {"session_id":1,"session_title":"건설 질문","user_message_id":1,"request_id":"example"}

data: {"text":"감리는 "}

event: done
data: {"done":true,"message_id":2,"latency_ms":1200,"status":"success","error":null}
```

검색이 실행되면 출처를 답변 본문에 함께 저장하고 done의 search/search_suggestions에 검색 결과 상태를 전달합니다. 검색 허용은 도구 제공이며 실제 실행 여부는 반환 근거로 표시합니다.

## DB 구조와 기록 확인

```text
users (1) ── (N) chat_sessions (1) ── (N) chat_messages
  └────────────────────────────── (N) chat_messages
```

| 테이블 | 주요 필드 |
|---|---|
| users | id, username(unique), nickname, password_hash, is_active, is_admin, created_at |
| chat_sessions | id, user_id(FK), title, created_at, updated_at |
| chat_messages | id, session_id(FK), user_id(FK), role, content, latency_ms, status, error_message, created_at |

질문은 AI 호출 전에 저장하며 답변 또는 오류 안내는 이후 별도 저장합니다. 초기 저장 실패는500과 오류 안내를 반환하고 새 대화/질문을 rollback합니다. AI 실패 시 이미 저장한 질문과 받은 부분 답변은 남습니다. 일반 사용자는 자기 기록만, 관리자만 다른 사용자 기록을 조회할 수 있습니다.

```text
GET /api/v1/logs?limit=10&offset=0&session_id=1
```
```json
{"total":2,"items":[{"id":2,"user_id":1,"username":"demo_user","session_id":1,"role":"assistant","content":"감리는 ...","latency_ms":1200,"status":"success","error_message":null,"created_at":"2026-10-05T00:00:01"}]}
```

필드 설명용 축약 응답입니다. 웹의 내 기록 화면, `scripts/check_logs.py`, `scripts/check_logs.sql`로도 확인할 수 있습니다. DB 모델 변경 시 기존 테이블의 별도 마이그레이션이 필요합니다.

## 오류·로그·테스트

request_received, ai_call_start, ai_call_success/ai_call_failed, db_save_success/db_save_failed 이벤트가 콘솔과 logs/server.log에 기록됩니다. 요청 ID로 처리 단계를 연결합니다. AI 진단 로그는 모델·검색·추론 선택·공급자 상태코드·고정 원인 분류를 포함합니다.

AI_TIMEOUT, AI_RATE_LIMIT, AI_MODEL_UNAVAILABLE, AI_OPTION_UNSUPPORTED, AI_SEARCH_UNSUPPORTED, AI_UNAVAILABLE, AI_EMPTY_RESPONSE 등을 구분합니다. 429 후에는 해당 모델을 짧게 대기시키고, 대기 중 재전송은 DB 저장·AI 호출 전에 거절합니다. SDK 자동 재시도는 꺼져 있습니다. 실패 후 다른 모델을 선택할 수 있으며 앱이 자동으로 모델을 바꾸지는 않습니다.

테스트는 임시SQLite와 빈실제키/가짜SDK로 실행합니다. 운영 DB를 연결한 상태에서 실행하지 마세요.

```bash
DATABASE_URL=sqlite:///./test.db GEMINI_API_KEY="" APP_ENV=test uv run pytest tests/ -q
```

## 팀 역할과 개인별 작업 요약

| 역할 / 작성자 | 작업 요약 |
|---|---|
| 감독 / dolphin1404 (Kyumin Lee) | PR 템플릿 작성, 리뷰·통합 관리 담당 |
| 인증 / bwmin | 닉네임 모델·스키마, 비밀번호 정책/변경 API, 검증 오류 처리와 인증 회귀 테스트 |
| AI·채팅 / heeyoung35 | AI 연동·응답 스트리밍(SSE)·대화 문맥 유지 영역 담당 |
| DB·로그·AI·FE 통합 / feelosophysics (alzznd) | 초기 BE/AI/SSE·문맥 구현, 페이지네이션·통계·CLI/SQL·DB테스트, 도메인 프롬프트·문서, FE연동/UI·AI옵션/오류·운영 보완 |

Git 이력의 alzznd와 feelosophysics는 같은 작성자입니다. 위 구현 요약은 실제 커밋 기준입니다. 개인 작업 브랜치 → develop 대상 PR → develop → main PR 흐름으로 개별 커밋을 보존해 통합합니다. 평가 전 최종 통합·배포는 owner 요청으로 진행하며, 리뷰 요청 상태와 실제 승인 여부는 PR에서 확인할 수 있습니다.

운영 기준은 두 저장소의 main입니다. FE는 Vercel Production, BE는 기존 EC2의 `/home/ubuntu/apps/chat-be`에서 `chat-be.service`로 실행합니다. DB는 앱 외부의 `/home/ubuntu/chat-data/chatbot.db`에 보존합니다. BE main 병합 뒤 서버 코드 반영·검증·재시작을 별도로 수행합니다. DB 확인은 웹의 내 기록, 위 로그 API 또는 [SQL](scripts/check_logs.sql)·[조회 스크립트](scripts/check_logs.py)를 사용합니다.

## 문서 안내

- [미션 요구사항 원문](docs/mission_requirements.md) · [요구사항 점검표](docs/mission-checklist.md)
- [통합 학습 가이드](docs/deep_dive_study_guide.md)
- [인증](docs/roles/auth_guide.md) · [DB·로그](docs/roles/log_db_guide.md) · [AI·채팅](docs/roles/chat_api_guide.md)
- [배포](docs/deployment.md) · [건설 도메인 자료](docs/domain_knowledge.md)
