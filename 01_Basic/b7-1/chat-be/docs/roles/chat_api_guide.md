# AI·채팅 담당자 학습·실습 가이드

공통 흐름은 [통합 학습 가이드](../deep_dive_study_guide.md), 실행/API는 [README](../../README.md)를 참고합니다.

## 읽을 코드

| 파일 | 살펴볼 내용 |
|---|---|
| [api/v1/chat.py](../../app/api/v1/chat.py) | 세션 관리·SSE·저장 경계 |
| [services/gemini_service.py](../../app/services/gemini_service.py) | SDK·이력 절단·검색 도구·공유 deadline·Mock |
| [schemas/chat.py](../../app/schemas/chat.py) | ChatStreamRequest와 질문 검증 |
| [core/config.py](../../app/core/config.py) | 모델·검색·시간 제한·이력 설정 |
| [core/abuse.py](../../app/core/abuse.py) | 요청 횟수·동시 슬롯 |
| [test_chat.py](../../tests/test_chat.py) / [test_chat_reliability.py](../../tests/test_chat_reliability.py) | 스트림·시간 초과·취소·DB 실패 |
| [test_search.py](../../tests/test_search.py) | 검색 도구 on/off·오류 처리의 로컬 검증 |

## 현재 구현에서 구분할 것

빈 질문 차단, 2,000자 제한, 세션 삭제, AI 오류 안내와 전체 AI 스트림 시간 제한은 이미 있다. 기본 이력은 이전 메시지 10개이며 질문·답변 10쌍이 아니다. DB는 현재 질문을 제외한 전체 이력을 읽고 서비스에서 마지막 N개를 선택한다.

SSE는 REST의 반대말이 아니다. 세션 API 설계와 답변 스트리밍은 함께 사용한다. 조각을 full_response에 누적하면서 화면으로 전송하고, 최종 결과 뒤 답변을 저장한다. 일반 AI 예외와 작업 취소는 다르게 처리된다. 정확한 결과는 통합 가이드의 실패 표를 읽는다.

현재 기본 모델은 gemma-4-26b-a4b-it이다. GEMINI_SEARCH_ENABLED 기본 True로 Google Search 도구를 제공한다. False로 끌 수 있으며 모델이 실제 검색 여부를 판단한다. 검색 metadata로 실행여부를 구분하고 출처를 답변본문에 저장하며 SSE로 검색제안을 전달한다. 실제 검색 지원·계정 조건은 공식 문서와 실호출로 확인하며 모델을 임의로 바꾸지 않는다.

Mock는 연결 시험용 문자열을 나눠 보낸다. 시스템 지시문 변화·실제 문맥 이해·검색·품질을 Mock 답변으로 평가하지 않는다. SDK초기화실패는 AI_INIT_ERROR, 빈답변은 AI_EMPTY_RESPONSE로 처리한다.

## 읽기·검증 실습

1. 격리 DB·Mock 환경에서 meta → data → done을 읽고 어떤 시점에 질문·답변이 저장되는지 설명한다.
2. 가짜 AI 스트림으로 연결 지연·중간 조각 지연을 각각 재현하는 기존 신뢰성 테스트를 읽는다. 같은 deadline의 의미를 확인한다.
3. 일반 AI 예외·타임아웃·호출자 취소를 비교한다. 부분 답변을 어디서 보유하며 어떤 경로에서 잃을 수 있는지 설명한다.
4. 이력 메시지 12개를 가정하고 마지막 10개와 새 질문이 어떻게 조립되는지 예측한다.
5. test_search.py에서 tools 유무를 확인한다. 이 테스트가 실제 Google 검색 실행을 증명하지 않는 이유를 설명한다.
6. 실호출을 수행할 때는 검색이 필요한 구체적 최신 질문과 반환 근거를 함께 확인한다. SDK 초기화 성공·AI 생성 성공·검색 실행·화면 출처 표시를 각각 구분한다.

운영 .env의 시간 제한이나 프롬프트를 학습 실험으로 변경하지 않는다. 통합 가이드의 테스트 격리 원칙을 따른다. scripts/test_api.py는 TestClient 기반 보조 검증이며 배포 서버 검증이 아니다.

## 후속 개선 후보

다음개선 후보는 취소시 부분답변보존과 이력조회량 제한이다. 검색실행/출처전달·할당량대기·SDK초기화오류의 기존테스트를 먼저 확인한다.
