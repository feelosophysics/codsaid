# Vanilla Portfolio

외부 프레임워크 없이 HTML, CSS, JavaScript만으로 만든 반응형 포트폴리오 웹사이트입니다.  
핵심 목표는 `사용자 이벤트 -> 상태 변경 -> DOM 업데이트` 흐름을 직접 구현하며 웹의 기본 동작 원리를 익히는 것입니다.

## 사용 기술

- HTML5 semantic markup
- CSS3 custom properties, Flexbox, Grid, responsive layout
- Vanilla JavaScript DOM API, event handling, localStorage
- Fetch API, async/await, try/catch
- Intersection Observer API

## 주요 기능

- 모바일 햄버거 메뉴 토글
- 섹션 앵커 이동과 부드러운 스크롤
- 스크롤 위치에 따른 헤더 스타일 변경
- 300px 이상 스크롤 시 Top 버튼 노출
- 다크 모드 전환과 localStorage 저장
- Intersection Observer 기반 스크롤 등장 애니메이션
- Contact 폼 필수값 및 이메일 형식 검증
- GitHub API 저장소 목록 연동
- 로딩, 성공, 에러, 빈 데이터 상태 UI
- 언어별 프로젝트 필터링
- Hero 타이핑 효과

## 실행 방법

VS Code Live Server를 사용하거나, 이 디렉토리에서 간단한 정적 서버를 실행합니다.

```bash
python3 -m http.server 5500
```

브라우저에서 다음 주소를 엽니다.

```text
http://localhost:5500
```

## GitHub API 사용자 변경

[js/main.js](js/main.js) 상단의 `GITHUB_USERNAME` 값을 본인의 GitHub 아이디로 변경하면 Projects 섹션이 본인 저장소를 불러옵니다.

```js
const GITHUB_USERNAME = "octocat";
```

GitHub API는 인증 없이 시간당 60회 제한이 있으므로, 제한에 걸리면 에러 상태 UI와 재시도 버튼이 표시됩니다.

## 배포

GitHub Pages 배포 절차:

1. 이 프로젝트를 GitHub 저장소에 push합니다.
2. 저장소의 `Settings -> Pages`로 이동합니다.
3. `Deploy from a branch`를 선택합니다.
4. `main` 브랜치와 루트 폴더를 선택한 뒤 저장합니다.
5. 발급된 Pages URL을 아래에 기록합니다.

배포 URL:

```text
배포 후 여기에 URL을 입력하세요.
```

## 스크린샷

배포 또는 로컬 실행 후 아래 항목을 캡처해 README에 추가합니다.

| 화면 | 이미지 |
| --- | --- |
| 데스크톱 | 준비 중 |
| 모바일 | 준비 중 |
| 다크 모드 | 준비 중 |

## 제출물

- GitHub 저장소 URL: 배포 전 입력
- 배포된 사이트 URL: 배포 전 입력

