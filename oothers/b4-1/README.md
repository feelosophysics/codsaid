# Vanilla Web Portfolio

순수 HTML, CSS, JavaScript만 사용해 만든 반응형 포트폴리오 웹사이트입니다. 핵심 목표는 `사용자 이벤트 -> 상태 변경 -> DOM 업데이트` 흐름을 직접 구현하며 웹의 기본 동작 원리를 익히는 것입니다.

## 사용 기술

- HTML5 semantic markup
- CSS custom properties, Flexbox, Grid, responsive layout
- Vanilla JavaScript DOM API, event handling, localStorage
- Fetch API, async/await, try/catch
- Intersection Observer API

## 주요 기능

- 모바일 햄버거 메뉴 토글
- 메뉴 클릭 시 부드러운 섹션 이동
- 스크롤 60px 이상에서 헤더 스타일 변경
- 스크롤 300px 이상에서 Top 버튼 표시
- 다크 모드 전환과 localStorage 저장
- Intersection Observer 기반 스크롤 등장 애니메이션
- Contact 폼 필수값 및 이메일 형식 검증
- GitHub API 저장소 목록 연동
- 로딩, 성공, 에러, 빈 데이터 상태 UI
- 언어별 프로젝트 필터링
- Hero 타이핑 효과

## 실행 방법

VS Code Live Server를 사용하거나, 이 디렉토리에서 정적 서버를 실행합니다.

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
const GITHUB_USERNAME = "feelosophysics";
```

GitHub API는 인증 없이 시간당 60회 제한이 있으므로, 제한에 걸리면 에러 상태 UI와 재시도 버튼이 표시됩니다.

## 배포

현재 저장소 기준 GitHub Pages 목표 URL:

```text
https://feelosophysics.github.io/codsaid/oothers/b4-1/
```

GitHub Pages 배포 절차:

1. `b4-1/` 변경사항을 커밋하고 `main` 브랜치에 push합니다.
2. GitHub 저장소 `Settings -> Pages`로 이동합니다.
3. `Deploy from a branch`를 선택합니다.
4. `main` 브랜치와 루트 폴더를 선택한 뒤 저장합니다.
5. 위 목표 URL에서 배포 결과를 확인합니다.

## 스크린샷 체크리스트

| 화면 | 상태 |
| --- | --- |
| 데스크톱 | 준비 중 |
| 모바일 | 준비 중 |
| 다크 모드 | 준비 중 |

## 제출물

- GitHub 저장소 URL: `https://github.com/feelosophysics/codsaid`
- 배포된 사이트 URL: `https://feelosophysics.github.io/codsaid/oothers/b4-1/`
