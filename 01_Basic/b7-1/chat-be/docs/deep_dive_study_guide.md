# 챗봇 학습 가이드

사용자 행동부터 서버 처리와 DB 저장까지 읽는 공통 학습 가이드입니다. 역할별 문서는 담당 영역의 코드와 실습을 다룹니다.

실행·API는 [README](../README.md), 평가요건은 [미션 원문](mission_requirements.md)과 [점검표](mission-checklist.md), 배포는 [배포 가이드](deployment.md)를 참고합니다.

## 1. 먼저 이해할 전체 흐름

학습 목표는 사용자 행동부터 서버 처리와 DB 결과까지 자신의 말로 설명하는 것이다. 회차별로 개념 → 실제 코드 → 정상 결과 예측 → 실패 조건 → 설명 또는 실습 순서로 읽는다. 모르는 용어가 나오면 그 지점에서 멈추고 질문한다.

```text
브라우저 → Vercel: HTML/CSS/JavaScript 화면 받기
브라우저 → 백엔드 HTTPS → Caddy → Uvicorn → FastAPI
                                           ├─ SQLite: 계정·대화 저장
                                           └─ Google AI API: 답변 생성
```

브라우저는 Vercel에서 받은 JavaScript로 백엔드에 직접 요청한다. 프런트엔드와 백엔드는 별도 저장소·배포다. BE 변경이 FE에 자동 반영되는 것은 아니다.

Vercel 운영 주소는 운영용으로 지정된 배포를, `…-git-…` 브랜치 주소는 해당 브랜치의 최신 배포를 가리킨다. 둘이 같은 배포를 가리킬 수도 있다. 현재 FE README에는 Production 추적 브랜치가 `dev/log-frontend-integration`으로 기록돼 있다. 실제 별칭 대상은 Vercel에서 확인한다. 로그인 토큰은 브라우저의 주소별 localStorage에 저장되므로 주소가 달라지면 다시 로그인할 수 있다.

## 2. 용어를 역할별로 구분하기

| 용어 | 의미 | 우리 프로젝트에서의 위치 |
|---|---|---|
| API | 다른 프로그램에 요청하는 접점 | 로그인·대화 조회·질문 요청 |
| HTTP | 요청과 응답을 전달하는 규칙 | GET·POST·DELETE, 상태 코드·헤더 |
| REST | 자원과 일관된 인터페이스 등으로 API를 설계하는 스타일 | `/chat/sessions` 조회·생성·삭제 |
| FastAPI | 파이썬 웹 프레임워크 | 요청을 함수에 연결하고 데이터 검사·응답 처리 |
| Uvicorn | FastAPI 앱을 실행하는 ASGI 서버 | HTTP 연결을 받아 앱에 전달 |
| JSON | 데이터를 표현하는 형식 | 요청 본문·일반 API 응답·SSE의 data 내용 |
| SSE | Server-Sent Events, 서버가 이벤트를 순차 전송하는 방식 | AI 답변 조각과 meta·done·error 이벤트 |
| SSR | Server-Side Rendering, 서버에서 HTML을 만드는 방식 | 현재 화면은 정적 FE와 브라우저 JavaScript로 구성 |
| SEO | 검색엔진이 콘텐츠를 찾고 이해하도록 돕는 최적화 | SSE와 별개. SSR 설명과 혼동하지 않기 |
| ORM | 객체를 통해 DB 작업을 표현하는 도구 | SQLAlchemy의 모델·Session·쿼리 |

REST는 설치하는 라이브러리가 아니고 FastAPI는 REST API를 구현할 수 있는 도구다. JSON을 사용하거나 GET·POST를 나누는 것만으로 REST의 모든 제약을 충족했다고 단정하지 않는다. 스트리밍은 순차 처리·전달이라는 넓은 개념이며 SSE는 그 구현 방식 중 하나다. GraphQL·RPC는 다른 API 접근 방식이고, WebSocket은 양방향 통신 방식이다.

REST는 Roy Fielding이 2000년 논문에서 정리했다. FastAPI는 파이썬 타입 표기와 기존 Starlette·Pydantic을 활용해 반복되는 API 개발 작업을 줄이는 방향으로 만들어졌다. 참고: [REST 원문](https://ics.uci.edu/~fielding/pubs/dissertation/abstract.htm), [FastAPI 개발 배경](https://fastapi.tiangolo.com/history-design-future/), [SSE 표준](https://html.spec.whatwg.org/multipage/server-sent-events.html).

## 3. 파이썬 문법과 FastAPI 연결

```python
@app.get('/hello')
def hello():
    return {'message': '안녕'}
```

`@`는 파이썬 데코레이터 문법이다. 개념적으로 `hello = app.get('/hello')(hello)`와 같다. 여기서는 함수 정의 시 GET `/hello` 처리 함수로 등록하며, 요청이 들어왔을 때 함수 본문을 실행한다. 실제 대화 API는 `APIRouter`에 등록하고 `/api/v1`과 `/chat` 접두어를 붙인다.

`Depends(get_current_user)`는 FastAPI가 인증 함수를 실행하고 그 결과를 인자로 제공하도록 선언한다. `get_current_user` 자체도 `Depends(get_db)`로 DB 세션을 받아 서명·만료 확인 뒤 사용자 존재·활성 상태를 조회한다. 정확한 의존성 순서는 의존 관계를 읽어 판단한다.

`yield`는 값을 하나 전달하고 실행을 이어갈 수 있게 하는 문법이다. `get_db`에서는 DB 세션을 제공하고 사용 뒤 닫는 데, AI 서비스에서는 답변 조각을 전달하는 데 쓴다. `async def`라고 선언했다고 함수 안의 동기 DB 작업까지 비동기가 되는 것은 아니다.

## 4. 한 질문의 처리 순서

읽을 코드: [chat.py](../app/api/v1/chat.py), [AI 서비스](../app/services/gemini_service.py), [인증 의존성](../app/api/deps.py). 화면의 요청·수신은 프런트 저장소 `js/chat.js`에 있다.

1. 브라우저가 Bearer 토큰, 질문, 선택적 session_id를 POST `/api/v1/chat/stream`으로 보낸다.
2. 인증·입력 검증 후 요청 횟수와 동시 처리 제한을 검사한다. 제한 거절은 HTTP 429이며 질문 저장·AI 호출을 하지 않는다.
3. 소유한 대화방을 찾거나 새로 만들고 질문을 저장한다. 새 대화방과 질문은 한 트랜잭션에서 commit하므로 초기 저장 실패 시 둘 다 rollback한다.
4. 현재 질문 ID를 제외한 이력을 읽어 스냅샷으로 준비한다. 질문 commit 후 스트리밍 응답을 시작한다.
5. 생성기에서 별도 `SessionLocal` DB 세션을 열고 meta 이벤트를 보낸다.
6. AI 서비스는 이전 메시지의 마지막 `MAX_HISTORY_MESSAGES`개와 현재 질문을 전달한다. 기본 10은 질문·답변 각각을 세는 메시지 수다. DB 이력 조회 자체는 전체를 읽는다.
7. 받은 답변 조각을 서비스의 `full_response`에 누적하면서 API에 전달한다. API는 SSE로 브라우저에 보내고, 화면도 받은 내용을 누적해서 표시한다.
8. AI 서비스의 최종 결과를 받은 뒤 답변을 별도 트랜잭션으로 저장한다. 그다음 done 이벤트를 보낸다.

현재 질문·답변은 별도 행·별도 commit이다. 답변을 조각마다 저장하지 않는다. 존재하지 않거나 다른 사용자 소유의 session_id를 전달하면 현재 스트림 코드는 새 대화방을 만든다. 조회·삭제 API의 404 처리와 구별한다.

## 5. 실패하면 무엇이 남는가?

| 조건 | 결과 |
|---|---|
| 초기 세션·질문 저장 실패 | HTTP 500 JSON. 자동 생성 세션과 질문 rollback, AI 호출 안 함 |
| AI 정상 종료 | 전체 답변을 status=success로 저장한 뒤 done |
| AI 시간 초과 | 부분 답변 + 오류 안내를 status=error, error_message=AI_TIMEOUT으로 저장하는 경로 |
| 일반 AI 호출 예외 | 부분 답변 + 오류 안내를 status=error, error_message=AI_SERVICE_ERROR로 저장하는 경로 |
| 저장 전 작업 취소·서버 종료 | 부분 답변 저장을 보장하지 못함. 이미 commit된 질문은 남음 |
| 답변 commit 실패 | 해당 답변 rollback, 질문은 남음. SSE error 안내 경로 |

AI 오류 결과도 후속 DB 저장이 성공해야 보존된다. 연결이 끊겼을 때 이미 답변 commit을 끝냈다면 답변은 남을 수 있다. 화면에 보였다는 사실과 DB에 저장됐다는 사실을 구분한다. 현재 취소 시 부분 답변 저장·주기적 체크포인트·이어받기는 구현하지 않았다.

연결 시작과 매 응답 읽기에 같은 deadline을 사용한다. 일반요청은 `AI_TIMEOUT_SECONDS` 기본60초, 검색요청은 `AI_SEARCH_TIMEOUT_SECONDS` 기본90초이며 SDK스트림정리는 별도로 최대1초다. 인증·DB저장·전송은 이 AI제한시간과 별개다. 취소는 호출자로 전파된다.

SSE를 시작한 뒤에는 HTTP 200인 상태에서도 AI 오류가 발생할 수 있다. 브라우저는 HTTP 상태뿐 아니라 done의 status/error와 error 이벤트도 읽어야 한다. 현재 FE는 fetch로 스트림을 직접 읽고 자동 재연결·재개 기능은 제공하지 않는다.

## 6. AI 모델·Mock·웹 검색

현재 기본 모델은 `gemma-4-26b-a4b-it`이다. 모델 학습 지식과 실시간 웹 검색은 별개다. 현재 로컬 코드에는 `GEMINI_SEARCH_ENABLED=True`일 때 `tools=[{'google_search': {}}]`를 전달하는 변경이 있다. False이면 도구를 제공하지 않는다. 도구 제공과 실제 검색 실행은 구별하며, 검색 여부는 모델이 판단한다.

검색연결은 [Gemma Google Search](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api#google-search)를 따른다. 실제실행은 grounding metadata의 검색어/출처로 구분한다. 출처는 답변본문에 붙여 DB에 저장하고 검색상태·검색제안은 SSE done으로 전달한다. 검색거절·옵션오류·사용량제한·빈답변을 분류하며 다른모델로 자동 전환하지 않는다.

키가 없으면 Demo 응답을 생성하고, 키가 있는데 SDK 초기화가 실패하면 AI_INIT_ERROR로 안내한다. Mock는 준비한 문자열을 나눠 보내는 연결 시험용이다. 실제 검색·실제 모델의 문맥 이해·응답 품질을 검증하지 않는다. SDK호출 오류는 공급자코드/고정원인분류로 추적하며 예외원문은 노출하지 않는다.

## 7. DB와 로그 읽기

```text
User id=7
  └─ ChatSession id=12, user_id=7
       ├─ ChatMessage id=31, role=user, content=질문, status=success
       └─ ChatMessage id=32, role=assistant, content=답변, status=success
```

숫자는 예시다. ChatSession은 DB에 저장하는 대화방이고, SQLAlchemy Session은 DB 작업 객체다. PK는 행의 식별자, FK는 다른 행의 참조, relationship은 파이썬 객체 사이의 접근 관계다. 현재 모델은 `Column`을 사용한다. `create_all()`은 기존 테이블 컬럼 변경을 수행하지 않는다.

DB 대화 기록은 다시 보여줄 데이터이고 `logs/server.log`는 운영 이벤트다. 저장 이벤트에는 request_id와 entity가 있으나 ChatMessage 행에는 request_id·turn_id 필드가 없다. 미들웨어는 요청 헤더의 X-Request-ID를 재사용하거나 UUID 앞 8자를 만들므로 매번 전체 UUID를 새로 발급하는 구조는 아니다. 미들웨어가 모든 요청에 request_received를 기록하지 않으며 이벤트는 호출 위치를 확인해야 한다.

AI latency_ms는 AI 서비스 시작부터 결과 생성까지의 시간이며 전체 요청 시간과 다르다. X-Process-Time-Ms도 call_next 반환까지 측정하므로 마지막 SSE 조각까지의 시간으로 해석하지 않는다. 생성기의 db_save_failed는 여러 종류의 예외를 잡는 위치여서 이름만으로 DB 원인이라고 단정하지 않는다.

| 집계 도구 | 평균 지연시간 대상 |
|---|---|
| `/logs/stats` | 성공 assistant 중 0·None을 제외 |
| `scripts/check_logs.py` | assistant의 성공·오류를 포함하고 0·None을 제외 |
| `scripts/check_logs.sql` 사용자별 통계 | 성공 assistant, 0 포함·NULL 제외 |

`/logs`의 total은 필터에 맞는 전체 메시지 수다. 일반 사용자는 자기 데이터만, 관리자는 필터 또는 전체 데이터를 조회한다. `/logs/stats` 성공률은 성공 답변 수 / 질문 수이며 질문이 없으면 100%다. 질문 행의 success는 질문 저장을 뜻하고 AI 성공을 뜻하지 않는다.

database.py에는 SQLite의 `check_same_thread=False`만 명시돼 있다. `timeout=30`, WAL, 외래키 PRAGMA 활성화는 코드에 선언돼 있지 않다. 스레드 검사 해제는 동시 쓰기·DB 잠금 해결을 보장하지 않는다. ORM cascade 삭제와 DB 외래키 강제는 다른 층위다.

## 8. 학습 순서와 확인 질문

| 회차 | 읽을 코드 | 설명할 수 있어야 할 것 |
|---|---|---|
| 1 | main.py, models/user.py, models/chat.py | 화면·서버·DB와 두 종류의 세션 |
| 2 | deps.py, schemas/auth.py, security.py | Depends, 입력 검사, 해시·JWT·사용자 조회 |
| 3 | database.py, chat.py 초기 저장 | add/flush/commit/rollback과 질문 저장 경계 |
| 4 | chat.py 생성기, gemini_service.py | SSE, 메모리 누적, 오류·취소·저장 결과 |
| 5 | logs.py, logging.py, middlewares.py | 사용자 격리, total, request_id, 측정 범위 |
| 6 | check_logs.py, check_logs.sql, 기존 테스트 | 모집단 차이와 코드·테스트·운영 근거 구분 |

이번 대화에서는 API/REST/FastAPI, SSE/SSR, 데코레이터, 스트림 저장과 검색 가능성을 소개했다. 소개받았다는 사실을 이해 완료로 간주하지 않는다. 다음에는 원하는 회차에서 실제 함수 한 개를 따라가며 설명해 본다.

확인 질문: AI 오류여도 왜 질문은 남을까? 받은 답변을 보내면서 동시에 누적할 수 있을까? 일반 예외와 취소는 어떻게 다를까? 도구 설정이 있는데도 검색했다고 확정할 수 없는 이유는 무엇일까? CLI와 API 평균이 달라지는 데이터는 무엇일까?

## 9. 담당자별 실습과 작업 원칙

- [인증 가이드](roles/auth_guide.md): 해시·JWT·의존성과 접근 제어.
- [DB·로그 가이드](roles/log_db_guide.md): 저장·조회·집계와 오류 증거.
- [AI·채팅 가이드](roles/chat_api_guide.md): 문맥·검색·스트림과 장애 처리.

설치·실행 명령은 README 한 곳에서 확인한다. 테스트 전에 프로세스 설정의 DATABASE_URL을 격리 DB로, GEMINI_API_KEY를 빈 값으로 설정한다. 앱 import도 init_db를 호출하며 모든 테스트가 동일하게 격리되는 것은 아니다. 신뢰성 테스트의 isolated_chat fixture는 의존성과 생성기 DB 세션을 따로 바꾼다.

실습은 담당 작업브랜치에서 코드읽기·재현·검증 순서로 진행한다. 기능변경은 목적과 테스트결과를 정리해 develop 대상PR로 제출한다.
