# B7-1 제출 점검표

기준은 [미션 요구사항 원문](mission_requirements.md)입니다. 구현 상태와 평가 전 확인할 항목을 구분합니다.

| 요구사항 | 구현 / 확인 방법 |
|---|---|
| 로그인 후 같은 화면에서 질문·답변 | FE index.html, 모델/추론/검색 도구 모음, SSE말풍선 |
| 회원가입·로그인·접근 제어 | auth API, JWT 의존성, 비로그인401, 소유자별 대화/기록 조회 |
| 서버 AI 호출·문맥 유지 | GeminiService, 최근10개 메시지, 실패답변 제외, 서버 전용 API키 |
| 질문·답변·사용자·시각 누적 저장 | users/chat_sessions/chat_messages, 질문·답변 별도commit |
| 사용자 기준 기록 조회 | logs.html, /logs 및 /logs/stats, check_logs.py / check_logs.sql |
| 요청/AI/DB 성공·실패 이벤트 | logging.py, request_id, ai_diagnostic 원인 분류 |
| AI 실패·시간초과 안내 | 전체deadline60/90초, 오류분류, 429모델대기, 질문/부분답변 보존 |
| 입력 검사 | 질문1~2,000자·공백차단, 가입조건, 모델별지원옵션검사 |
| 외부 접속과 실행 문서 | Vercel/EC2 HTTPS, README, deployment.md |
| 팀 역할·개인 작업 요약 | README 역할표, 담당자별 Git 이력 대조 |
| 브랜치·PR 협업과 개인10커밋 | 개인 작업브랜치/develop PR, 팀원별 유의미한커밋 점검 |
| 민감정보 관리 | 서버.env, .env.example, .gitignore, 비밀없는 진단로그 |

## 평가 전 확인

- [ ] 운영 서비스에서 가입·로그인·질문·후속문맥·새로고침 후 기록 확인
- [ ] 실제 AI 성공·후속 문맥 확인, 할당량 부족 모델 구분 (검색 실행/출처는 선택 기능)
- [x] 실제 Git 이력에 따른 구현 작성자와 개인별 작업 요약 정리
- [ ] 팀원별 유의미한10회 이상 커밋과 PR 병합 기록 확인
- [ ] develop/main PR 통합·운영 버전 일치 확인 (감독 리뷰 상태는 PR에서 별도 확인)

코드 시험은 tests/에서 임시DB·가짜SDK로 실행합니다. 실제 AI 품질·외부서비스 접근은 별도 확인 항목입니다.
