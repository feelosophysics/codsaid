# b4-1 학습 가이드: Vanilla Portfolio 구현 기록

이 문서는 `b4-1.md` 미션을 수행하기 위해 세운 로드맵과 실제 구현 내용을 함께 정리한 학습 가이드입니다. 단순히 결과물을 보는 데서 끝나지 않고, 왜 이런 구조로 만들었는지와 어떤 코드 흐름을 봐야 하는지를 따라갈 수 있도록 작성했습니다.

## 1. 로드맵

### 1단계: 요구사항을 기능 단위로 나누기

미션은 크게 네 덩어리로 나눌 수 있습니다.

- HTML: `header`, `nav`, `main`, `section`, `article`, `footer`를 사용한 시맨틱 구조
- CSS: 변수, Flexbox, Grid, 모바일 우선 반응형, 다크 모드
- JavaScript: 이벤트 처리, 상태 변경, DOM 업데이트
- 비동기: GitHub API 호출과 로딩, 성공, 에러, 빈 데이터 UI

이렇게 나누면 “페이지를 예쁘게 만드는 작업”과 “브라우저 동작 원리를 익히는 작업”을 동시에 놓치지 않을 수 있습니다.

### 2단계: 파일 구조 만들기

미션 요구사항에 맞춰 다음 구조를 만들었습니다.

```text
b4-1/
  index.html
  css/
    style.css
  js/
    main.js
  images/
    profile.svg
  README.md
  b4-1-guide.md
```

각 파일의 책임은 분리했습니다.

- `index.html`: 문서 구조와 콘텐츠
- `css/style.css`: 모든 스타일과 반응형 레이아웃
- `js/main.js`: 이벤트, 상태, 렌더링, API 호출
- `images/profile.svg`: About 섹션의 프로필 이미지 에셋
- `README.md`: 실행, 배포, 제출 안내
- `b4-1-guide.md`: 학습용 구현 해설

### 3단계: 정적 구조를 먼저 완성하기

먼저 JavaScript 없이도 읽을 수 있는 HTML 구조를 만들었습니다.

- `Hero`: 인사말, CTA 버튼
- `About`: 자기소개, 프로필 이미지
- `Skills`: 기술 스택 목록
- `Projects`: GitHub API 결과가 들어갈 영역
- `Contact`: 폼과 검증 메시지 영역
- `Footer`: 저작권, 소셜 링크

이 순서가 중요한 이유는 JavaScript는 이미 존재하는 DOM을 찾아 조작하기 때문입니다. HTML 구조가 안정적이어야 `querySelector`도 안정적으로 동작합니다.

### 4단계: CSS로 레이아웃과 테마 만들기

CSS는 모바일 우선으로 작성했습니다. 기본 스타일은 작은 화면 기준이고, `768px`, `1024px` 이상에서 확장합니다.

핵심 구현:

- `:root`에 색상, 간격, 그림자, 폰트 변수 정의
- `[data-theme="dark"]`에 다크 모드 변수 재정의
- 네비게이션은 Flexbox로 정렬
- 프로젝트 카드는 Grid의 `repeat(auto-fit, minmax(...))` 패턴 사용
- 버튼과 카드에 hover transition, box-shadow 적용

Flexbox와 Grid의 구분도 명확히 했습니다.

- Flexbox: 한 줄 또는 한 방향의 배치에 적합합니다. 네비게이션처럼 로고, 메뉴, 버튼을 가로로 정렬할 때 사용했습니다.
- Grid: 행과 열이 함께 생기는 카드 목록에 적합합니다. Projects와 Skills처럼 화면 너비에 따라 카드 개수가 바뀌는 곳에 사용했습니다.

### 5단계: JavaScript 상태 설계하기

`main.js`에는 다음 상태 객체를 두었습니다.

```js
const state = {
  theme: getInitialTheme(),
  menuOpen: false,
  projects: {
    status: "idle",
    items: [],
    error: "",
    filter: "All",
  },
  form: {
    errors: {},
    submitted: false,
  },
};
```

이 구조의 핵심은 DOM을 직접 기준으로 삼지 않고, “현재 앱이 어떤 상태인가”를 먼저 기록한다는 점입니다. 그런 다음 상태에 맞게 화면을 다시 그립니다.

## 2. 핵심 구현 해설

### 다크 모드

흐름:

```text
테마 버튼 클릭 -> state.theme 변경 -> html[data-theme] 변경 -> CSS 변수 값 변경
```

`setTheme()` 함수가 이 흐름을 담당합니다.

- `state.theme`을 갱신합니다.
- `<html data-theme="dark">` 또는 `<html data-theme="light">`를 설정합니다.
- `localStorage`에 저장해 새로고침 후에도 유지합니다.
- 버튼의 `aria-pressed`와 라벨을 함께 갱신합니다.

이 방식의 장점은 색상 값을 JavaScript가 직접 바꾸지 않는다는 것입니다. JavaScript는 상태만 바꾸고, 실제 시각 변화는 CSS 변수가 처리합니다.

### 모바일 햄버거 메뉴

흐름:

```text
메뉴 버튼 클릭 -> state.menuOpen 변경 -> nav-list active 클래스 토글
```

`toggleMenu()`는 메뉴 상태를 바꾸고, `classList.toggle()`로 화면을 업데이트합니다. 메뉴 링크를 클릭하면 `closeMenu()`가 실행되어 모바일 메뉴가 닫힙니다.

### 스크롤 UI

흐름:

```text
scroll 이벤트 발생 -> window.scrollY 확인 -> 헤더/Top 버튼 클래스 갱신
```

`updateScrollUi()`는 두 기준을 사용합니다.

- 60px 이상 스크롤: 헤더에 `is-scrolled` 클래스 추가
- 300px 이상 스크롤: Top 버튼에 `visible` 클래스 추가

CSS가 클래스에 따라 그림자, 테두리, 투명도를 처리합니다.

### Intersection Observer 애니메이션

스크롤 이벤트로 모든 섹션 위치를 계속 계산하지 않고, 브라우저가 제공하는 `IntersectionObserver`를 사용했습니다.

흐름:

```text
섹션이 화면에 20% 이상 진입 -> is-visible 클래스 추가 -> CSS transition 실행
```

`threshold: 0.2`는 미션 권장값을 따랐습니다.

### GitHub API 연동

흐름:

```text
fetchProjects 실행 -> loading 상태 -> fetch 요청 -> success/error 상태 -> Projects DOM 업데이트
```

`fetchProjects()`는 `async/await`와 `try/catch`를 사용합니다.

- 요청 시작 전: `status: "loading"`
- 응답 성공: `status: "success"`, `items`에 저장소 배열 저장
- 응답 실패 또는 예외: `status: "error"`, `error` 메시지 저장

화면 출력은 `renderProjects()`가 담당합니다. 상태별 UI는 다음 네 가지입니다.

- 로딩: 스피너와 로딩 메시지
- 성공: 저장소 카드 목록
- 에러: 에러 메시지와 재시도 버튼
- 빈 데이터: 표시할 프로젝트가 없다는 메시지

저장소 카드는 `map()`으로 HTML 문자열 배열을 만들고 `join("")`으로 합쳐 출력합니다. 포크 저장소는 `filter()`로 제외했습니다.

### 프로젝트 필터링

보너스 기능으로 언어별 필터를 추가했습니다.

흐름:

```text
필터 버튼 클릭 -> state.projects.filter 변경 -> renderProjects 재실행 -> 필터링된 카드 출력
```

여기서 `filter()`는 선택된 언어와 일치하는 저장소만 남기는 데 사용됩니다.

### Contact 폼 검증

흐름:

```text
submit 이벤트 발생 -> preventDefault -> 입력값 검증 -> state.form.errors 변경 -> 에러 메시지 DOM 업데이트
```

`validateForm()`은 세 가지를 검사합니다.

- 이름 필수값
- 이메일 필수값과 형식
- 메시지 필수값

폼 제출에 성공해도 실제 이메일 전송은 하지 않습니다. 미션의 필수 요구는 “새로고침 방지 후 성공 또는 에러 메시지 UI 노출”이므로, 현재 구현은 성공 메시지를 보여주는 수준입니다.

## 3. 코드에서 꼭 봐야 할 부분

### `querySelector`와 `addEventListener`

`elements` 객체에 DOM 요소를 한 번에 모아두었습니다.

```js
const elements = {
  menuButton: document.querySelector("[data-menu-button]"),
  navList: document.querySelector("[data-nav-list]"),
  themeButton: document.querySelector("[data-theme-button]"),
};
```

이후 `bindEvents()`에서 이벤트를 연결합니다.

```js
elements.themeButton.addEventListener("click", () => {
  setTheme(state.theme === "dark" ? "light" : "dark");
});
```

HTML에 `onclick`을 쓰지 않고 JavaScript에서 이벤트를 연결했기 때문에 구조와 동작이 분리됩니다.

### 구조분해 할당

GitHub 저장소 데이터를 필요한 이름으로 꺼낼 때 구조분해 할당을 사용했습니다.

```js
.map(({ name, description, html_url: url, language, stargazers_count: stars, updated_at: updatedAt }) => ({
  name,
  description,
  url,
  language: language || "Other",
  stars,
  updatedAt,
}));
```

API 응답의 긴 속성명을 화면에서 쓰기 좋은 이름으로 바꾸는 효과가 있습니다.

### 상태 기반 렌더링

`setProjectState()`는 상태를 바꾼 뒤 반드시 `renderProjects()`를 호출합니다.

```js
function setProjectState(nextState) {
  state.projects = {
    ...state.projects,
    ...nextState,
  };

  renderProjects();
}
```

이 패턴을 익히면 React나 Vue에서 상태가 바뀔 때 화면이 갱신되는 방식을 더 쉽게 이해할 수 있습니다.

## 4. 직접 바꿔보면 좋은 연습

1. `GITHUB_USERNAME`을 본인의 GitHub 아이디로 바꾸기
2. Hero 문구와 About 소개를 본인 내용으로 수정하기
3. Skills 목록을 본인이 배우는 기술로 교체하기
4. Contact 폼 성공 메시지를 더 자연스럽게 바꾸기
5. GitHub API 결과를 별점순으로 정렬해보기
6. 저장소 카드에 topics 또는 homepage 링크를 추가해보기

## 5. 제출 전 체크리스트

- `index.html`이 `css/style.css`, `js/main.js`를 올바르게 연결하는가
- 모바일에서 햄버거 메뉴가 열리고 닫히는가
- 다크 모드가 새로고침 후에도 유지되는가
- GitHub API 로딩, 성공, 에러, 빈 데이터 상태가 코드에 구현되어 있는가
- Contact 폼에서 빈 값과 잘못된 이메일이 막히는가
- 모든 이미지에 `alt`가 있는가
- 모든 폼 입력이 `label`과 연결되어 있는가
- README에 배포 URL과 스크린샷을 추가했는가

