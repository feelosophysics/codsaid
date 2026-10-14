# DB·로그 담당자 학습·실습 가이드

공통 흐름은 [통합 학습 가이드](../deep_dive_study_guide.md), 실행/API는 [README](../../README.md)를 참고합니다.

## 읽을 코드

| 파일 | 살펴볼 내용 |
|---|---|
| [models/chat.py](../../app/models/chat.py) | 대화방·메시지·FK·relationship |
| [core/database.py](../../app/core/database.py) | engine·SessionLocal·get_db |
| [api/v1/chat.py](../../app/api/v1/chat.py) | 질문과 답변의 별도 commit·rollback |
| [api/v1/logs.py](../../app/api/v1/logs.py) | 소유권·필터·count·통계 |
| [core/logging.py](../../app/core/logging.py) / [middlewares.py](../../app/core/middlewares.py) | 이벤트·request_id와 측정 범위 |
| [check_logs.py](../../scripts/check_logs.py) / [check_logs.sql](../../scripts/check_logs.sql) | CLI·SQL 집계 |
| [test_db.py](../../tests/test_db.py) / [test_chat_reliability.py](../../tests/test_chat_reliability.py) | 모델·초기 저장·답변 저장 장애 검증 |

## 현재 기능과 남은 한계

세션 필터, 페이지네이션 전체 count, `/logs/stats`, CLI 색상 표시, SQL TOP 5·시간대 집계는 이미 구현돼 있다. 각 쿼리의 집계범위와 소유권조건을 살펴본다.

세션·질문 저장 이벤트에는 request_id와 entity가 있다. ChatMessage 행에는 request_id·turn_id가 없다. 이벤트 로그와 DB 대화 기록의 연결 범위를 구별한다. db_save_failed가 발생했다고 예외 원인이 항상 DB인 것은 아니다.

SQLite 연결에는 check_same_thread=False만 명시돼 있다. timeout=30·WAL·외래키 PRAGMA 활성화가 설정돼 있다고 설명하지 않는다. DB 잠금은 쓰기 트랜잭션의 길이·경합·연결 설정을 확인해서 판단한다. ORM cascade와 직접 SQL 삭제에서의 FK 강제는 따로 검증한다.

## 읽기·검증 실습

1. User → ChatSession → ChatMessage 예시를 그리고 대화방과 SQLAlchemy Session을 구분한다.
2. 초기 질문 저장 실패와 답변 저장 실패의 commit 경계를 따라간다. 질문만 남는 경우를 설명한다.
3. 두 사용자의 격리 데이터로 일반 사용자·관리자 조회 범위를 예측한다. limit보다 많은 데이터를 만들고 total과 items 길이가 다른지 확인한다.
4. 지연시간 0·NULL·정상·오류 답변을 섞어서 API·CLI·SQL의 평균 대상 차이를 설명한다. SQL 파일도 쿼리별 모집단이 다를 수 있다.
5. 신뢰성 테스트에서 DB 오류를 주입하는 방법을 읽고 SSE error·DB 행·저장 이벤트가 어떻게 대응하는지 확인한다.
6. 필요하면 격리 DB에서 PRAGMA foreign_keys를 조회하고 ORM 삭제와 직접 SQL 삭제를 비교한다. 모델 선언만으로 실험 결과를 미리 확정하지 않는다.

테스트와 CLI는 설정된 DB에 접근한다. 통합 가이드의 격리 준비 후 사용한다. 기존 앱 import의 init_db와 생성기 별도 SessionLocal까지 확인한다.

## 설명 확인과 후속 개선 후보

질문 success는 왜 AI 성공이 아닐까? 평균값을 비교하기 전에 무엇을 맞춰야 할까? 요청 ID만으로 DB 행까지 추적 가능한가?

후속 후보는 부분 답변 보존 정책, DB 행의 요청 연결, 이력 조회량 제한, 집계 정의 통일이다. 코드 읽기·재현 뒤 하나를 정하고 필요한 수정과 검증만 수행한다. 변경의 목적과 재현결과를 PR에 함께 작성한다.
