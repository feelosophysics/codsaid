# 현장노트 — 건설 지식 AI 어시스턴트

건설 용어·시공 원리를 질문하고 이전 대화를 조회하는 정적 웹 프론트입니다. 회원가입·로그인, 채팅·실시간답변, 개인 기록 조회를 FastAPI와 연결합니다.

- [서비스](https://b7-1-chat-fe.vercel.app) · [백엔드 저장소](https://github.com/cocoa7-1/chat-be) · [API 문서](https://b71chatbe.ddns.net/docs)

## 실행과 설정

```bash
python -m http.server 3000
```

http://localhost:3000 에 접속합니다. 로컬 BE는 http://localhost:8000 입니다. 별도 빌드/설치는 필요 없습니다.

js/config.js는 localhost와 배포주소를 구분합니다. DEPLOYED_API_BASE_URL은 백엔드HTTPS주소이며 /api/v1은 포함하지 않습니다. 정적 파일이므로 Vercel환경변수가 아닌 코드설정에 반영합니다. AI키·DB연결정보는 백엔드에서 관리합니다.

## 화면과 파일

| 화면 / 파일 | 역할 |
|---|---|
| index.html / js/chat.js | 대화목록·질문·SSE말풍선·복사, 입력창 모델/추론선택·검색스위치·생성옵션 |
| logs.html / js/logs.js | 내 기록·전체통계·현재페이지 검색·필터·페이지네이션·상세 |
| login.html / register.html | 로그인·닉네임가입·비밀번호조건/확인 |
| js/api.js / js/auth.js | JWT 저장과 Bearer 인증 요청 |
| js/ui.js | Markdown정제·공통UI·시간표시 |
| css/style.css | 데스크톱/모바일·초점·모션 설정 |

모델을 선택하면 지원하는 추론 수준이 동적으로 바뀝니다. 답변 중에는 설정을 잠그고 다음 질문부터 적용합니다. 검색 출처는 답변에, 검색 실행 상태와 제안은 말풍선 하단에 표시합니다. 요청·모델할당량 오류는 대기시간과 함께 안내합니다.

Markdown은 Marked/DOMPurify로 정제합니다. 관련 CDN을 사용할 수 없으면 일반 텍스트로 표시합니다. 인증토큰은 주소별 localStorage에 저장되며 서버가 실제 인증을 검사합니다.

## 배포와 검증

Vercel에서 Framework Other, 빌드 없음, Output루트(.)로 배포합니다. 최종 Production 기준은 main입니다. 개인 작업을 develop 대상 PR로 취합한 뒤 develop → main PR을 merge commit으로 병합하고, main의 Production 배포 성공과 서비스 도메인의 파일 일치를 확인합니다. 모델·추론·생성 옵션 패널의 모바일 폭 제한과 도구 모음 기준 배치를 포함합니다.

검증: 로그인/가입입력, 모델별옵션전환, SSE완료/오류, 기록필터·상세·페이지이동, 390px모바일 가로넘침/키보드접근을 확인합니다. [UI 안내](docs/ui-review.md)와 [백엔드 미션 점검표](https://github.com/cocoa7-1/chat-be/blob/main/docs/mission-checklist.md)를 참고하세요. 실제 AI·후속 문맥·저장된 기록은 운영 시연에서 별도로 확인합니다.

## 팀 역할과 개인별 작업 요약

| 작성자 / 역할 | 작업 요약 |
|---|---|
| feelosophysics (alzznd) / FE 구현·통합 | 초기 정적 클라이언트, 인증·API 연동, 현장노트 UI, 모델·추론·검색·Temperature 옵션, 오류/출처 표시, 모바일 팝오버와 배포 문서 |
| dolphin1404 (Kyumin Lee) / 감독 | PR 템플릿 작성, 리뷰·통합 관리 담당 |
| bwmin / BE 인증 | 닉네임·비밀번호 정책과 변경 API 및 테스트. FE는 해당 API와 연결 |
| heeyoung35 / BE AI·채팅 | AI 연동·응답 스트리밍(SSE)·대화 문맥 유지 영역 담당. FE는 해당 채팅 API와 연결 |

alzznd와 feelosophysics는 같은 작성자입니다. BE 인증·DB·AI의 구현과 실행 환경 변수는 [BE README](https://github.com/cocoa7-1/chat-be/blob/main/README.md), DB 확인은 [로그 가이드](https://github.com/cocoa7-1/chat-be/blob/main/docs/roles/log_db_guide.md)를 참고하세요.
