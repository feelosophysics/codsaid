# b4-1 상세 학습 가이드: 순수 HTML/CSS/JS 반응형 포트폴리오

이 문서는 `b4-1.md` 미션을 처음 접하는 사람을 위한 아주 자세한 학습 가이드입니다.

목표는 단순히 "완성된 코드를 복사해서 제출하기"가 아닙니다. 이 프로젝트를 통해 브라우저가 HTML, CSS, JavaScript를 어떻게 읽고, 사용자의 행동에 따라 화면이 어떻게 바뀌는지 이해하는 것이 목표입니다.

이 프로젝트의 핵심 문장은 다음과 같습니다.

```text
사용자 이벤트 -> 상태 변경 -> DOM 업데이트 -> 화면 변화
```

예를 들어 다크 모드 버튼을 누르면 다음 순서로 일이 일어납니다.

```text
버튼 클릭 이벤트 발생
-> JavaScript가 현재 테마 상태를 light에서 dark로 변경
-> html 태그의 data-theme 속성이 dark로 변경
-> CSS 변수가 다크 모드 값으로 바뀜
-> 화면 색상이 바뀜
```

React를 배우기 전 이 흐름을 직접 경험하는 것이 매우 중요합니다. React도 결국 "상태가 바뀌면 화면을 다시 그린다"는 생각을 더 편리하게 만든 도구이기 때문입니다.

---

## 1. 프로젝트 전체 구조 이해하기

이번 미션의 결과물은 다음 구조를 가집니다.

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
  b4-1.md
  b4-1_Detailed_Study_Guide.md
```

각 파일의 역할은 다음과 같습니다.

| 파일 | 역할 |
| --- | --- |
| `index.html` | 웹페이지의 구조와 내용을 담당합니다. 제목, 섹션, 버튼, 폼, 이미지 같은 뼈대를 만듭니다. |
| `css/style.css` | 화면의 색상, 간격, 크기, 배치, 반응형 레이아웃, 다크 모드를 담당합니다. |
| `js/main.js` | 버튼 클릭, 스크롤, 폼 제출, GitHub API 호출처럼 움직이는 기능을 담당합니다. |
| `images/profile.svg` | About/Hero 영역에 표시되는 프로필 일러스트 이미지입니다. |
| `README.md` | 실행 방법, 배포 방법, 프로젝트 설명을 정리한 제출용 문서입니다. |
| `b4-1_Detailed_Study_Guide.md` | 지금 읽고 있는 학습용 상세 해설 문서입니다. |

처음 웹을 배울 때 가장 중요한 습관은 "역할을 나누어 생각하기"입니다.

HTML, CSS, JavaScript를 한 문장으로 나누면 다음과 같습니다.

```text
HTML: 무엇이 있는가?
CSS: 어떻게 보이는가?
JavaScript: 어떻게 반응하는가?
```

이 프로젝트에서도 그 원칙을 지킵니다.

---

## 2. 브라우저는 HTML, CSS, JavaScript를 어떻게 처리할까?

웹페이지를 열면 브라우저는 대략 다음 순서로 일을 합니다.

1. `index.html`을 읽습니다.
2. HTML 안에 연결된 `css/style.css`를 다운로드하고 적용합니다.
3. HTML 안에 연결된 `js/main.js`를 다운로드하고 실행합니다.
4. HTML 구조와 CSS 스타일을 합쳐 화면을 그립니다.
5. 사용자가 클릭, 입력, 스크롤 같은 행동을 하면 JavaScript 이벤트 코드가 실행됩니다.

`index.html`의 `<head>`에는 이런 코드가 있습니다.

```html
<link rel="stylesheet" href="css/style.css" />
<script defer src="js/main.js"></script>
```

`link`는 CSS 파일을 연결합니다.

`script`는 JavaScript 파일을 연결합니다.

여기서 `defer`가 중요합니다.

```html
<script defer src="js/main.js"></script>
```

`defer`는 "HTML 문서를 끝까지 읽은 뒤 JavaScript를 실행해 주세요"라는 뜻입니다. JavaScript는 HTML 요소를 찾아서 조작해야 합니다. 그런데 HTML이 아직 만들어지기 전에 JavaScript가 먼저 실행되면, 찾으려는 버튼이나 폼이 아직 존재하지 않을 수 있습니다.

그래서 이 프로젝트에서는 `defer`를 사용합니다.

---

## 3. HTML 기본 개념

HTML은 HyperText Markup Language의 약자입니다.

쉽게 말해 HTML은 웹페이지의 구조를 설명하는 언어입니다.

HTML은 태그로 이루어져 있습니다.

```html
<p>안녕하세요.</p>
```

여기서 `<p>`는 문단을 의미합니다. 브라우저는 `<p>`를 보고 "이 부분은 문단이구나"라고 이해합니다.

### 3-1. 태그, 속성, 콘텐츠

HTML 요소는 보통 세 부분으로 나눌 수 있습니다.

```html
<a href="#projects">프로젝트 보기</a>
```

| 부분 | 예시 | 의미 |
| --- | --- | --- |
| 태그 | `a` | 링크를 만드는 요소 |
| 속성 | `href="#projects"` | 클릭했을 때 이동할 위치 |
| 콘텐츠 | `프로젝트 보기` | 화면에 보이는 글자 |

속성은 태그에 추가 정보를 줍니다.

`href="#projects"`는 "이 링크를 누르면 id가 projects인 위치로 이동한다"는 뜻입니다.

---

## 4. 시맨틱 HTML이란?

시맨틱은 "의미가 있는"이라는 뜻입니다.

시맨틱 HTML은 단순히 화면을 나누기 위해 아무 태그나 쓰는 것이 아니라, 각 영역의 의미에 맞는 태그를 사용하는 방식입니다.

나쁜 예시는 다음과 같습니다.

```html
<div>
  <div>메뉴</div>
  <div>본문</div>
  <div>푸터</div>
</div>
```

브라우저와 검색 엔진, 스크린 리더는 이 구조만 보고 각 영역이 무엇을 의미하는지 알기 어렵습니다.

더 좋은 예시는 다음과 같습니다.

```html
<header>
  <nav>메뉴</nav>
</header>
<main>본문</main>
<footer>푸터</footer>
```

이제 각 영역의 의미가 분명합니다.

이번 프로젝트는 다음 시맨틱 태그를 사용합니다.

| 태그 | 의미 |
| --- | --- |
| `<header>` | 페이지 상단 영역 |
| `<nav>` | 내비게이션, 즉 메뉴 영역 |
| `<main>` | 페이지의 핵심 본문 |
| `<section>` | 주제별 구역 |
| `<article>` | 독립적으로 읽을 수 있는 콘텐츠 카드 |
| `<footer>` | 페이지 하단 정보 |
| `<figure>` | 이미지와 설명을 묶는 영역 |
| `<figcaption>` | 이미지 설명 |

시맨틱 태그를 쓰면 다음 장점이 있습니다.

1. 코드를 읽는 사람이 구조를 빠르게 이해합니다.
2. 검색 엔진이 페이지 구조를 더 잘 이해합니다.
3. 스크린 리더 같은 보조 기술이 사용자에게 더 정확한 정보를 전달합니다.
4. CSS와 JavaScript를 연결할 때도 구조가 명확해집니다.

---

## 5. 이번 페이지의 HTML 구조

`index.html`의 큰 구조는 다음과 같습니다.

```text
body
  skip link
  header
    nav
      brand
      hamburger button
      nav list
      dark mode button
  main
    hero section
    about section
    skills section
    projects section
    contact section
  footer
  scroll top button
```

이 구조를 화면으로 보면 다음과 같습니다.

```text
+--------------------------------------------------+
| Header: 로고, 메뉴, 다크모드 버튼                |
+--------------------------------------------------+
| Hero: 큰 제목, 소개, CTA 버튼, 이미지            |
+--------------------------------------------------+
| About: 프로젝트 소개                             |
+--------------------------------------------------+
| Skills: HTML/CSS/JS/API 기술 카드                |
+--------------------------------------------------+
| Projects: GitHub API 저장소 카드                 |
+--------------------------------------------------+
| Contact: 이름, 이메일, 메시지 폼                 |
+--------------------------------------------------+
| Footer: 저작권, 소셜 링크                        |
+--------------------------------------------------+
```

---

## 6. id, class, data 속성의 차이

HTML을 보면 `id`, `class`, `data-*` 속성이 많이 나옵니다.

각각의 역할이 다릅니다.

### 6-1. id

`id`는 문서 안에서 하나만 존재해야 하는 고유 이름입니다.

```html
<section id="projects"></section>
```

메뉴 링크에서 다음처럼 이동할 수 있습니다.

```html
<a href="#projects">Projects</a>
```

이 링크를 클릭하면 브라우저는 `id="projects"`인 요소로 이동합니다.

### 6-2. class

`class`는 스타일을 적용하거나 여러 요소를 같은 그룹으로 묶을 때 사용합니다.

```html
<button class="button button-primary">프로젝트 보기</button>
```

CSS에서는 다음처럼 사용합니다.

```css
.button {
  border-radius: 8px;
}
```

`class`는 여러 개를 함께 줄 수 있습니다.

```html
class="button button-primary"
```

이 뜻은 "button 스타일도 적용하고, button-primary 스타일도 적용한다"입니다.

### 6-3. data-* 속성

`data-*` 속성은 JavaScript가 요소를 찾기 쉽게 하기 위해 사용합니다.

```html
<button data-theme-button>Dark</button>
```

JavaScript에서는 다음처럼 찾습니다.

```js
document.querySelector("[data-theme-button]");
```

이 프로젝트에서는 JavaScript 연결용으로 `data-*` 속성을 많이 사용합니다. 이렇게 하면 CSS용 클래스와 JavaScript용 선택자를 분리할 수 있어서 유지보수가 쉬워집니다.

---

## 7. 접근성 기초: alt, label, aria

웹사이트는 마우스와 눈으로만 사용하는 것이 아닙니다. 키보드로 이동하는 사람, 스크린 리더로 듣는 사람도 있습니다.

### 7-1. 이미지 alt

이미지는 반드시 `alt` 속성을 가져야 합니다.

```html
<img
  src="images/profile.svg"
  alt="노트북으로 웹 포트폴리오를 제작하는 개발자 일러스트"
/>
```

`alt`는 이미지를 볼 수 없는 환경에서 대신 읽히는 설명입니다. 의미 있는 이미지라면 설명을 적고, 장식용 이미지라면 빈 `alt=""`를 사용할 수 있습니다.

이번 프로젝트의 이미지는 포트폴리오 소개에 의미가 있으므로 설명을 넣었습니다.

### 7-2. label과 input 연결

폼에서는 `label`과 `input`을 연결해야 합니다.

```html
<label for="email">이메일</label>
<input id="email" name="email" type="email" />
```

`label`의 `for="email"`과 `input`의 `id="email"`이 연결됩니다.

이렇게 하면 사용자가 "이메일" 글자를 클릭해도 입력칸에 커서가 들어갑니다. 스크린 리더도 이 입력칸이 이메일 입력칸이라는 것을 알 수 있습니다.

### 7-3. aria-live

GitHub API 상태나 폼 메시지처럼 나중에 바뀌는 메시지는 다음 속성을 사용합니다.

```html
<div role="status" aria-live="polite" data-project-status></div>
```

`aria-live="polite"`는 화면 내용이 바뀌었을 때 보조 기술이 사용자에게 자연스럽게 알려줄 수 있게 합니다.

---

## 8. CSS 기본 개념

CSS는 Cascading Style Sheets의 약자입니다.

HTML이 구조라면 CSS는 디자인과 배치입니다.

CSS는 다음 형태로 작성합니다.

```css
선택자 {
  속성: 값;
}
```

예를 들어 다음 코드는 모든 `body`의 기본 글꼴과 배경색을 정합니다.

```css
body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-base);
}
```

여기서 `body`는 선택자입니다.

`margin`, `background`, `color`, `font-family`는 속성입니다.

`0`, `var(--color-bg)` 같은 것들이 값입니다.

---

## 9. CSS 변수 이해하기

이번 프로젝트는 CSS 변수를 적극적으로 사용합니다.

CSS 변수는 `--`로 시작합니다.

```css
:root {
  --color-bg: #f6f7f3;
  --color-text: #171b1a;
  --space-4: 1rem;
}
```

사용할 때는 `var()`를 씁니다.

```css
body {
  background: var(--color-bg);
  color: var(--color-text);
}
```

CSS 변수를 쓰면 좋은 점이 있습니다.

1. 같은 색상과 간격을 여러 곳에서 재사용할 수 있습니다.
2. 색을 바꾸고 싶을 때 한 곳만 수정하면 됩니다.
3. 다크 모드를 구현하기 쉬워집니다.

---

## 10. 다크 모드 CSS 원리

다크 모드는 CSS 변수 값을 바꿔서 구현합니다.

밝은 모드 변수:

```css
:root {
  --color-bg: #f6f7f3;
  --color-text: #171b1a;
}
```

어두운 모드 변수:

```css
[data-theme="dark"] {
  --color-bg: #101413;
  --color-text: #eef5f2;
}
```

HTML 태그가 다음 상태면 밝은 모드입니다.

```html
<html lang="ko" data-theme="light">
```

JavaScript가 버튼 클릭 후 다음처럼 바꾸면 어두운 모드가 됩니다.

```html
<html lang="ko" data-theme="dark">
```

CSS는 `[data-theme="dark"]` 조건에 맞는 변수 값을 사용합니다.

중요한 점은 JavaScript가 모든 요소의 색상을 직접 바꾸지 않는다는 것입니다.

JavaScript는 `data-theme`만 바꿉니다.

CSS가 실제 색상 변경을 처리합니다.

이렇게 역할을 나누면 코드가 훨씬 깔끔해집니다.

---

## 11. 모바일 퍼스트 반응형 디자인

반응형 웹은 화면 크기에 따라 레이아웃이 자연스럽게 바뀌는 웹사이트입니다.

이번 프로젝트는 모바일 퍼스트 방식으로 작성합니다.

모바일 퍼스트란 기본 CSS를 작은 화면 기준으로 작성하고, 화면이 넓어질 때 미디어 쿼리로 확장하는 방식입니다.

기본 상태:

```css
.hero-layout {
  display: grid;
  gap: 2rem;
}
```

768px 이상:

```css
@media (min-width: 768px) {
  .hero-layout {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.82fr);
  }
}
```

이 뜻은 다음과 같습니다.

```text
작은 화면: 한 줄에 하나씩 세로 배치
768px 이상: 두 열로 가로 배치
```

이번 프로젝트의 브레이크포인트는 미션 요구사항에 맞춰 다음을 사용합니다.

| 너비 | 의미 |
| --- | --- |
| 기본 | 모바일 |
| `768px` 이상 | 태블릿 이상 |
| `1024px` 이상 | 데스크톱 이상 |

---

## 12. Flexbox 이해하기

Flexbox는 한 방향 배치에 강합니다.

예를 들어 헤더의 내비게이션은 다음 요소들을 가로로 배치해야 합니다.

```text
로고 | 메뉴 | 다크 모드 버튼
```

CSS는 다음처럼 작성합니다.

```css
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
```

여기서 중요한 속성은 세 가지입니다.

| 속성 | 의미 |
| --- | --- |
| `display: flex` | 자식 요소를 Flexbox 방식으로 배치 |
| `align-items: center` | 세로축 가운데 정렬 |
| `justify-content: space-between` | 가로축에서 양끝으로 벌리기 |

Flexbox는 메뉴, 버튼 묶음, footer 링크처럼 한 줄 또는 한 방향의 정렬에 적합합니다.

---

## 13. Grid 이해하기

Grid는 행과 열이 있는 2차원 배치에 강합니다.

Projects 카드처럼 화면 너비에 따라 카드 개수가 바뀌는 곳에 적합합니다.

```css
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}
```

처음 보면 어렵지만 나눠보면 이해할 수 있습니다.

`display: grid`는 Grid 레이아웃을 사용한다는 뜻입니다.

`grid-template-columns`는 열의 구조를 정합니다.

`repeat(auto-fit, minmax(240px, 1fr))`는 다음 의미입니다.

```text
가능한 만큼(auto-fit) 열을 반복해서 만들되,
각 열은 최소 240px,
공간이 남으면 1fr만큼 늘어난다.
```

그래서 모바일에서는 카드가 한 줄에 하나씩 보이고, 화면이 넓어지면 두 개, 세 개 이상으로 자연스럽게 늘어납니다.

Flexbox와 Grid를 구분하는 쉬운 기준은 다음과 같습니다.

| 상황 | 추천 |
| --- | --- |
| 가로 또는 세로 한 방향 정렬 | Flexbox |
| 카드 목록처럼 행과 열이 함께 필요함 | Grid |

---

## 14. JavaScript는 무엇을 담당할까?

JavaScript는 사용자의 행동에 반응하는 역할을 합니다.

이번 프로젝트에서 JavaScript가 담당하는 기능은 다음과 같습니다.

1. 다크 모드 버튼 클릭 처리
2. 모바일 햄버거 메뉴 열기/닫기
3. 메뉴 클릭 시 부드러운 스크롤
4. 스크롤 위치에 따른 헤더 스타일 변경
5. 스크롤 Top 버튼 표시와 클릭 이동
6. Intersection Observer 스크롤 애니메이션
7. GitHub API 호출
8. Projects 로딩/성공/에러/빈 상태 렌더링
9. 언어별 프로젝트 필터링
10. Contact 폼 입력값 검증
11. Hero 타이핑 효과

이 기능들이 많아 보이지만, 대부분 같은 패턴을 따릅니다.

```text
요소 찾기
-> 이벤트 연결
-> 상태 변경
-> 화면 업데이트
```

---

## 15. DOM이란?

DOM은 Document Object Model의 약자입니다.

브라우저는 HTML을 읽고, 그 HTML을 JavaScript가 다룰 수 있는 객체 구조로 바꿉니다. 이것이 DOM입니다.

예를 들어 HTML에 다음 버튼이 있다고 합시다.

```html
<button data-theme-button>Dark</button>
```

JavaScript는 이 버튼을 다음처럼 찾을 수 있습니다.

```js
const button = document.querySelector("[data-theme-button]");
```

이제 `button` 변수에는 HTML 버튼 요소가 들어 있습니다.

그리고 다음처럼 이벤트를 연결할 수 있습니다.

```js
button.addEventListener("click", () => {
  console.log("버튼을 클릭했습니다.");
});
```

이것이 DOM 조작의 시작입니다.

---

## 16. querySelector와 querySelectorAll

`querySelector`는 조건에 맞는 첫 번째 요소를 찾습니다.

```js
document.querySelector("[data-theme-button]");
```

`querySelectorAll`은 조건에 맞는 모든 요소를 찾습니다.

```js
document.querySelectorAll("[data-nav-list] a");
```

이번 프로젝트는 `elements` 객체에 DOM 요소를 모아둡니다.

```js
const elements = {
  root: document.documentElement,
  body: document.body,
  header: document.querySelector("[data-header]"),
  menuButton: document.querySelector("[data-menu-button]"),
  navLinks: document.querySelectorAll("[data-nav-list] a"),
};
```

이렇게 모아두면 장점이 있습니다.

1. 어떤 DOM 요소를 사용하는지 한눈에 볼 수 있습니다.
2. 같은 요소를 여러 함수에서 다시 찾지 않아도 됩니다.
3. 함수 내부가 조금 더 짧아집니다.

---

## 17. 이벤트와 addEventListener

이벤트는 사용자의 행동 또는 브라우저에서 일어나는 사건입니다.

예시는 다음과 같습니다.

| 이벤트 | 발생 시점 |
| --- | --- |
| `click` | 클릭했을 때 |
| `submit` | 폼을 제출했을 때 |
| `scroll` | 페이지를 스크롤했을 때 |
| `input` | 입력칸의 값이 바뀌었을 때 |

이벤트를 연결할 때는 `addEventListener`를 사용합니다.

```js
elements.menuButton.addEventListener("click", toggleMenu);
```

이 뜻은 다음과 같습니다.

```text
menuButton이 클릭되면 toggleMenu 함수를 실행한다.
```

HTML에 다음처럼 `onclick`을 직접 쓰는 방식은 사용하지 않습니다.

```html
<button onclick="toggleMenu()">메뉴</button>
```

이 프로젝트에서는 HTML은 구조만 담당하고, JavaScript는 동작을 담당하도록 분리합니다.

---

## 18. 상태란 무엇인가?

상태는 "현재 화면이 어떤 상황인지 나타내는 데이터"입니다.

이 프로젝트의 상태 객체는 다음과 같습니다.

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
    touched: false,
  },
};
```

각 상태는 다음을 의미합니다.

| 상태 | 의미 |
| --- | --- |
| `theme` | 현재 테마가 light인지 dark인지 |
| `menuOpen` | 모바일 메뉴가 열려 있는지 |
| `projects.status` | GitHub API 상태가 idle/loading/success/error 중 무엇인지 |
| `projects.items` | 화면에 보여줄 저장소 목록 |
| `projects.error` | API 실패 시 에러 메시지 |
| `projects.filter` | 현재 선택된 언어 필터 |
| `form.errors` | 폼 입력값 오류 메시지 |
| `form.submitted` | 폼 제출 성공 여부 |
| `form.touched` | 사용자가 폼 제출을 시도했는지 |

상태를 따로 두는 이유는 화면을 직접 기준으로 삼지 않기 위해서입니다.

좋은 흐름:

```text
상태를 바꾼다 -> 상태에 맞게 화면을 그린다
```

나쁜 흐름:

```text
화면 여기저기를 직접 바꾸다 보니 현재 상태를 알기 어렵다
```

상태 객체를 두면 코드가 커져도 흐름이 덜 복잡해집니다.

---

## 19. 다크 모드 JavaScript 흐름

다크 모드의 핵심 함수는 `setTheme`입니다.

```js
function setTheme(nextTheme) {
  state.theme = nextTheme;
  elements.root.dataset.theme = state.theme;
  elements.themeButton.setAttribute("aria-pressed", String(state.theme === "dark"));
  elements.themeIcon.textContent = state.theme === "dark" ? "☀" : "☾";
  elements.themeLabel.textContent = state.theme === "dark" ? "Light" : "Dark";
  localStorage.setItem(THEME_STORAGE_KEY, state.theme);
}
```

한 줄씩 보면 다음과 같습니다.

```js
state.theme = nextTheme;
```

현재 테마 상태를 바꿉니다.

```js
elements.root.dataset.theme = state.theme;
```

`document.documentElement`는 HTML 문서의 `<html>` 요소입니다. 즉 이 코드는 다음 HTML을 바꿉니다.

```html
<html data-theme="dark">
```

```js
localStorage.setItem(THEME_STORAGE_KEY, state.theme);
```

브라우저 저장소에 테마 값을 저장합니다.

이 덕분에 새로고침 후에도 다크 모드가 유지됩니다.

---

## 20. localStorage 이해하기

`localStorage`는 브라우저에 작은 문자열 데이터를 저장하는 기능입니다.

저장:

```js
localStorage.setItem("theme", "dark");
```

읽기:

```js
const theme = localStorage.getItem("theme");
```

삭제:

```js
localStorage.removeItem("theme");
```

이번 프로젝트는 다음 키를 사용합니다.

```js
const THEME_STORAGE_KEY = "b4-1-theme";
```

다크 모드를 저장할 때:

```js
localStorage.setItem(THEME_STORAGE_KEY, state.theme);
```

처음 페이지가 열릴 때:

```js
const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
```

이미 저장된 값이 있으면 그 값을 사용하고, 없으면 시스템 다크 모드 설정을 확인합니다.

```js
window.matchMedia("(prefers-color-scheme: dark)").matches
```

이 코드는 사용자의 운영체제나 브라우저가 다크 모드를 선호하는지 확인합니다.

---

## 21. 햄버거 메뉴 흐름

모바일에서는 메뉴가 숨겨지고 햄버거 버튼이 보입니다.

버튼을 클릭하면 `toggleMenu`가 실행됩니다.

```js
function toggleMenu() {
  state.menuOpen = !state.menuOpen;
  elements.navList.classList.toggle("active", state.menuOpen);
  elements.menuButton.classList.toggle("is-open", state.menuOpen);
  elements.body.classList.toggle("menu-open", state.menuOpen);
  elements.menuButton.setAttribute("aria-expanded", String(state.menuOpen));
}
```

핵심은 이 줄입니다.

```js
state.menuOpen = !state.menuOpen;
```

`!`는 반대로 바꾸는 연산자입니다.

```text
false -> true
true -> false
```

즉 메뉴가 닫혀 있으면 열고, 열려 있으면 닫습니다.

그 다음 `classList.toggle`을 사용합니다.

```js
elements.navList.classList.toggle("active", state.menuOpen);
```

`state.menuOpen`이 `true`이면 `active` 클래스를 추가합니다.

`false`이면 `active` 클래스를 제거합니다.

CSS에서는 다음처럼 동작합니다.

```css
.nav-list {
  display: none;
}

.nav-list.active {
  display: grid;
}
```

즉 JavaScript는 클래스를 바꾸고, CSS는 그 클래스에 따라 보이거나 숨깁니다.

---

## 22. 부드러운 스크롤 흐름

메뉴 링크는 `href="#about"`처럼 섹션 id를 가리킵니다.

JavaScript는 메뉴 링크 클릭을 가로채서 직접 스크롤합니다.

```js
function handleNavClick(event) {
  const link = event.currentTarget;
  const targetId = link.getAttribute("href");
  const target = document.querySelector(targetId);

  event.preventDefault();
  closeMenu();
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}
```

중요한 부분은 다음입니다.

```js
event.preventDefault();
```

브라우저의 기본 링크 이동을 막습니다.

그리고 직접 실행합니다.

```js
target.scrollIntoView({ behavior: "smooth", block: "start" });
```

이 코드는 대상 섹션으로 부드럽게 이동합니다.

---

## 23. 스크롤 이벤트와 UI 변경

스크롤하면 헤더와 Top 버튼 상태가 바뀝니다.

```js
function updateScrollUi() {
  const isPastHeader = window.scrollY > 60;
  const canScrollTop = window.scrollY > 300;

  elements.header.classList.toggle("is-scrolled", isPastHeader);
  elements.scrollTopButton.classList.toggle("visible", canScrollTop);
}
```

`window.scrollY`는 현재 페이지가 위에서 얼마나 내려왔는지를 픽셀 단위로 알려줍니다.

```text
window.scrollY > 60
```

60px보다 많이 스크롤했으면 헤더에 `is-scrolled` 클래스를 붙입니다.

```text
window.scrollY > 300
```

300px보다 많이 스크롤했으면 Top 버튼에 `visible` 클래스를 붙입니다.

CSS는 클래스에 따라 그림자, 테두리, 투명도를 바꿉니다.

---

## 24. Intersection Observer 이해하기

스크롤 애니메이션은 `IntersectionObserver`로 구현합니다.

이 API는 어떤 요소가 화면 안에 들어왔는지 감지합니다.

```js
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.2 }
);
```

`threshold: 0.2`는 요소의 20% 이상이 화면에 보이면 감지하겠다는 뜻입니다.

HTML에는 애니메이션 대상 섹션에 `data-animate`가 있습니다.

```html
<section class="section about" id="about" data-animate>
```

CSS 초기 상태:

```css
[data-animate] {
  opacity: 0;
  transform: translateY(28px);
}
```

보이는 상태:

```css
[data-animate].is-visible {
  opacity: 1;
  transform: translateY(0);
}
```

즉 처음에는 약간 아래에 있고 투명하다가, 화면에 들어오면 제자리로 올라오며 나타납니다.

---

## 25. GitHub API란?

API는 Application Programming Interface의 약자입니다.

쉽게 말해 "다른 프로그램이 사용할 수 있도록 열어둔 데이터 창구"입니다.

GitHub는 사용자 저장소 목록을 가져올 수 있는 API를 제공합니다.

이번 프로젝트는 다음 주소를 사용합니다.

```text
https://api.github.com/users/feelosophysics/repos?sort=updated&per_page=12
```

이 주소에서 `feelosophysics` 부분이 GitHub 사용자명입니다.

본인 계정으로 바꾸고 싶다면 `js/main.js`의 맨 위를 수정합니다.

```js
const GITHUB_USERNAME = "feelosophysics";
```

예를 들어 GitHub 아이디가 `octocat`이면 다음처럼 바꿉니다.

```js
const GITHUB_USERNAME = "octocat";
```

---

## 26. fetch와 async/await

GitHub API처럼 외부 데이터를 가져올 때는 시간이 걸립니다.

이런 작업을 비동기 작업이라고 합니다.

JavaScript에서는 `fetch`로 네트워크 요청을 보낼 수 있습니다.

```js
const response = await fetch(API_URL);
```

`await`는 "결과가 올 때까지 기다린다"는 뜻입니다.

`await`를 쓰려면 함수 앞에 `async`가 필요합니다.

```js
async function fetchProjects() {
  const response = await fetch(API_URL);
}
```

전체 흐름은 다음과 같습니다.

```js
async function fetchProjects() {
  setProjectState({ status: "loading" });

  try {
    const response = await fetch(API_URL);
    const repos = await response.json();
    setProjectState({ status: "success", items: repos });
  } catch (error) {
    setProjectState({ status: "error", error: error.message });
  }
}
```

핵심은 요청 시작, 성공, 실패를 상태로 구분한다는 점입니다.

---

## 27. try/catch로 에러 처리하기

네트워크 요청은 항상 성공하지 않습니다.

가능한 실패 상황은 다음과 같습니다.

1. 인터넷 연결이 끊김
2. GitHub API 제한에 걸림
3. 사용자명을 잘못 입력함
4. GitHub 서버가 일시적으로 응답하지 않음

그래서 `try/catch`를 사용합니다.

```js
try {
  const response = await fetch(API_URL);

  if (!response.ok) {
    throw new Error(`GitHub API 응답 코드: ${response.status}`);
  }

  const repos = await response.json();
} catch (error) {
  setProjectState({
    status: "error",
    error: error.message,
  });
}
```

`response.ok`는 HTTP 응답이 성공 범위인지 알려줍니다.

대략 200번대 응답이면 성공입니다.

403, 404, 500 같은 응답은 실패로 처리합니다.

`throw new Error(...)`는 일부러 에러를 발생시켜 `catch`로 이동하게 합니다.

---

## 28. 배열 메서드: filter, map, forEach

이번 미션은 배열 메서드 학습도 포함합니다.

GitHub API는 저장소 목록을 배열로 줍니다.

### 28-1. filter

`filter`는 조건에 맞는 항목만 남깁니다.

```js
const projects = repos.filter(({ fork }) => !fork);
```

GitHub 저장소에는 `fork`라는 값이 있습니다.

`fork`가 `true`이면 다른 사람의 저장소를 복사한 것입니다.

`!fork`는 fork가 아닌 저장소만 남기겠다는 뜻입니다.

언어 필터에도 `filter`가 사용됩니다.

```js
items.filter((project) => project.language === filter);
```

### 28-2. map

`map`은 배열의 각 항목을 다른 형태로 바꿉니다.

```js
const names = repos.map((repo) => repo.name);
```

이번 프로젝트에서는 GitHub API 데이터를 화면에 쓰기 좋은 객체로 바꿉니다.

```js
.map(({ name, description, html_url: url, language }) => ({
  name,
  description,
  url,
  language: language || "Other",
}))
```

그리고 프로젝트 카드를 만들 때도 사용합니다.

```js
elements.projectGrid.innerHTML = filteredItems.map(createProjectCard).join("");
```

각 프로젝트 객체를 HTML 문자열로 바꾼 뒤, `join("")`으로 하나의 문자열로 합칩니다.

### 28-3. forEach

`forEach`는 배열을 하나씩 순회하면서 작업할 때 사용합니다.

```js
elements.navLinks.forEach((link) => {
  link.addEventListener("click", handleNavClick);
});
```

여기서는 모든 메뉴 링크에 클릭 이벤트를 연결합니다.

---

## 29. 구조분해 할당 이해하기

구조분해 할당은 객체나 배열에서 필요한 값을 꺼내는 문법입니다.

일반적인 방식:

```js
const name = repo.name;
const description = repo.description;
```

구조분해 방식:

```js
const { name, description } = repo;
```

이번 프로젝트에서는 다음처럼 사용합니다.

```js
.map(
  ({
    name,
    description,
    html_url: url,
    language,
    stargazers_count: stars,
    updated_at: updatedAt,
  }) => ({
    name,
    description,
    url,
    language: language || "Other",
    stars,
    updatedAt,
  })
)
```

여기서 `html_url: url`은 GitHub API의 `html_url`이라는 이름을 코드에서 `url`이라는 이름으로 쓰겠다는 뜻입니다.

`stargazers_count: stars`도 마찬가지입니다.

긴 API 속성명을 화면 코드에서 짧고 이해하기 쉬운 이름으로 바꾸는 효과가 있습니다.

---

## 30. 템플릿 리터럴 이해하기

템플릿 리터럴은 백틱으로 문자열을 만드는 문법입니다.

```js
const message = `안녕하세요, ${name}님`;
```

`${}` 안에는 JavaScript 표현식을 넣을 수 있습니다.

이번 프로젝트에서는 프로젝트 카드 HTML을 만들 때 사용합니다.

```js
return `
  <article class="project-card">
    <h3>
      <a href="${escapeAttribute(url)}">${escapeHtml(name)}</a>
    </h3>
    <p>${escapeHtml(description || "설명이 등록되지 않은 저장소입니다.")}</p>
  </article>
`;
```

여러 줄 HTML 문자열을 만들 때 매우 편리합니다.

주의할 점은 API에서 받은 데이터가 그대로 HTML에 들어가면 위험할 수 있다는 것입니다.

그래서 이 프로젝트는 `escapeHtml`, `escapeAttribute` 함수를 사용합니다.

---

## 31. innerHTML과 보안

`innerHTML`은 요소 안의 HTML을 문자열로 바꾸는 기능입니다.

```js
elements.projectGrid.innerHTML = "<p>Hello</p>";
```

하지만 외부 데이터가 들어갈 때는 조심해야 합니다.

예를 들어 누군가 저장소 설명에 HTML 태그나 스크립트 같은 문자열을 넣어둘 수도 있습니다.

그래서 이번 프로젝트는 다음 함수를 사용해 특수 문자를 안전한 형태로 바꿉니다.

```js
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
```

이 함수는 `<`를 `&lt;`로 바꿉니다.

그러면 브라우저는 그것을 HTML 태그로 해석하지 않고 글자로 표시합니다.

---

## 32. Projects 상태별 렌더링

Projects 섹션은 상태에 따라 다른 화면을 보여줍니다.

상태는 다음 네 가지가 중요합니다.

| 상태 | 의미 | 화면 |
| --- | --- | --- |
| `loading` | 데이터를 요청 중 | 스피너와 로딩 문구 |
| `success` | 데이터를 성공적으로 받음 | 프로젝트 카드 목록 |
| `error` | 요청 실패 | 에러 메시지와 재시도 버튼 |
| 빈 배열 | 성공했지만 보여줄 항목 없음 | 빈 상태 메시지 |

상태 변경은 `setProjectState`에서 처리합니다.

```js
function setProjectState(nextState) {
  state.projects = {
    ...state.projects,
    ...nextState,
  };

  renderProjects();
}
```

여기서 중요한 흐름:

```text
상태를 바꾼다
-> renderProjects를 호출한다
-> 상태에 맞는 HTML을 만든다
```

React를 배우면 이 흐름이 더 자동화됩니다. 지금은 직접 구현하면서 원리를 익히는 단계입니다.

---

## 33. 프로젝트 언어 필터링

GitHub 저장소에는 `language` 값이 있습니다.

예를 들어 JavaScript, HTML, CSS 등이 들어올 수 있습니다.

프로젝트 목록을 받으면 언어 목록을 만듭니다.

```js
const languages = ["All", ...new Set(items.map(({ language }) => language))];
```

이 코드는 세 가지 개념을 사용합니다.

1. `map`으로 언어만 뽑습니다.
2. `Set`으로 중복을 제거합니다.
3. 스프레드 문법 `...`으로 다시 배열로 펼칩니다.

필터 버튼을 클릭하면 다음 함수가 실행됩니다.

```js
function handleFilterClick(event) {
  const filterButton = event.target.closest("[data-filter]");

  if (!filterButton) {
    return;
  }

  setProjectState({ filter: filterButton.dataset.filter });
}
```

여기서 `event.target`은 실제 클릭된 요소입니다.

`closest("[data-filter]")`는 클릭된 요소 자신 또는 부모 중에서 `data-filter`가 있는 가장 가까운 요소를 찾습니다.

필터 상태가 바뀌면 `renderProjects`가 다시 실행되고, 선택한 언어에 맞는 프로젝트만 보여줍니다.

---

## 34. 폼 검증 흐름

Contact 폼에는 세 입력이 있습니다.

1. 이름
2. 이메일
3. 메시지

폼 제출 이벤트는 다음처럼 연결됩니다.

```js
elements.contactForm.addEventListener("submit", handleContactSubmit);
```

제출 함수:

```js
function handleContactSubmit(event) {
  event.preventDefault();

  const errors = validateForm(getFormData());
  const isValid = Object.keys(errors).length === 0;

  setFormState({
    errors,
    touched: true,
    submitted: isValid,
  });

  if (isValid) {
    elements.contactForm.reset();
  }
}
```

`event.preventDefault()`는 폼의 기본 제출 동작을 막습니다.

기본 제출 동작이 실행되면 페이지가 새로고침될 수 있습니다. 이번 프로젝트에서는 실제 서버 전송을 하지 않고 JavaScript로 검증만 하므로 기본 동작을 막습니다.

---

## 35. FormData와 Object.fromEntries

폼 값을 읽을 때 다음 코드를 사용합니다.

```js
function getFormData() {
  return Object.fromEntries(new FormData(elements.contactForm).entries());
}
```

`FormData`는 폼 안의 입력값을 모아주는 브라우저 기능입니다.

입력값이 다음과 같다면:

```text
name: 홍길동
email: hello@example.com
message: 안녕하세요
```

`Object.fromEntries`를 거치면 다음 객체가 됩니다.

```js
{
  name: "홍길동",
  email: "hello@example.com",
  message: "안녕하세요"
}
```

객체 형태가 되면 `formData.name`, `formData.email`처럼 쉽게 사용할 수 있습니다.

---

## 36. 이메일 정규식

이메일 형식은 다음 정규식으로 검사합니다.

```js
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
```

정규식이 처음이면 무섭게 보일 수 있습니다. 아주 간단히 해석하면 다음 뜻입니다.

```text
공백과 @가 아닌 글자가 앞에 하나 이상 있고
@가 있고
공백과 @가 아닌 글자가 하나 이상 있고
.이 있고
공백과 @가 아닌 글자가 하나 이상 있어야 한다
```

즉 다음은 통과합니다.

```text
hello@example.com
```

다음은 실패합니다.

```text
hello
hello@
hello@example
```

완벽한 이메일 검증은 매우 복잡하지만, 학습용 폼에서는 이 정도면 충분합니다.

---

## 37. input 이벤트로 실시간 오류 갱신하기

미션에는 `input` 이벤트도 다루라고 되어 있습니다.

이번 프로젝트는 폼 제출을 한 번 시도한 뒤에는 사용자가 입력을 수정할 때 오류 메시지를 다시 계산합니다.

```js
elements.fields.forEach((field) => field.addEventListener("input", handleFormInput));
```

```js
function handleFormInput() {
  if (!state.form.touched) {
    return;
  }

  setFormState({
    errors: validateForm(getFormData()),
    submitted: false,
  });
}
```

처음부터 입력할 때마다 오류를 보여주면 사용자가 부담스러울 수 있습니다. 그래서 제출을 한 번 시도한 뒤부터 실시간으로 오류를 갱신합니다.

---

## 38. classList.add, remove, toggle

DOM 요소의 클래스를 조작할 때 `classList`를 사용합니다.

클래스 추가:

```js
element.classList.add("active");
```

클래스 제거:

```js
element.classList.remove("active");
```

클래스 토글:

```js
element.classList.toggle("active");
```

조건에 따라 토글:

```js
element.classList.toggle("active", true);
```

두 번째 인자가 `true`이면 클래스를 추가하고, `false`이면 제거합니다.

이번 프로젝트는 조건식이 명확한 경우 두 번째 인자를 사용합니다.

```js
elements.navList.classList.toggle("active", state.menuOpen);
```

---

## 39. textContent와 innerHTML의 차이

`textContent`는 텍스트만 바꿉니다.

```js
elements.themeLabel.textContent = "Dark";
```

`innerHTML`은 HTML 구조를 바꿉니다.

```js
elements.projectStatus.innerHTML = `
  <div class="state-panel">
    <p>프로젝트를 불러오는 중입니다...</p>
  </div>
`;
```

기준은 다음과 같습니다.

| 상황 | 추천 |
| --- | --- |
| 단순 글자만 바꿀 때 | `textContent` |
| 여러 태그를 동적으로 만들 때 | `innerHTML` |

외부 데이터가 들어가는 `innerHTML`에는 반드시 escape 처리를 하는 습관이 좋습니다.

---

## 40. Hero 타이핑 효과

타이핑 효과는 문자열을 앞에서부터 조금씩 잘라 보여주는 방식입니다.

```js
function startTypingEffect() {
  const text = "이벤트가 상태를 바꾸고, 상태가 화면을 다시 그립니다.";
  let index = 0;

  const typeNextCharacter = () => {
    elements.typingText.textContent = text.slice(0, index);
    index += 1;

    if (index <= text.length) {
      window.setTimeout(typeNextCharacter, 55);
    }
  };

  typeNextCharacter();
}
```

`slice(0, index)`는 문자열의 0번째부터 index 전까지 잘라냅니다.

`setTimeout`은 일정 시간이 지난 뒤 함수를 실행합니다.

즉 한 글자 보여주고, 55ms 뒤 다음 글자를 보여주는 방식입니다.

---

## 41. 초기화 함수 init

JavaScript 파일의 마지막에는 `init()`이 있습니다.

```js
function init() {
  setTheme(state.theme);
  bindEvents();
  observeSections();
  startTypingEffect();
  updateScrollUi();
  fetchProjects();
}

init();
```

초기화 함수는 페이지가 처음 열릴 때 필요한 일을 한 번에 실행합니다.

순서는 다음과 같습니다.

1. 저장된 테마를 화면에 적용합니다.
2. 버튼, 폼, 스크롤 이벤트를 연결합니다.
3. 섹션 등장 애니메이션 감지를 시작합니다.
4. Hero 타이핑 효과를 시작합니다.
5. 현재 스크롤 위치에 맞게 헤더와 Top 버튼을 갱신합니다.
6. GitHub API에서 프로젝트 목록을 불러옵니다.

프로젝트가 커질수록 초기화 함수는 중요합니다. "앱이 시작될 때 무슨 일이 일어나는가"를 한 곳에서 볼 수 있기 때문입니다.

---

## 42. README는 왜 필요한가?

`README.md`는 프로젝트를 처음 보는 사람에게 설명하는 문서입니다.

README에는 다음 내용을 넣었습니다.

1. 프로젝트 소개
2. 사용 기술
3. 주요 기능
4. 실행 방법
5. GitHub API 사용자 변경 방법
6. GitHub Pages 배포 절차
7. 스크린샷 체크리스트
8. 제출물 링크

개발자에게 README는 매우 중요합니다. 아무리 코드가 좋아도 실행 방법을 모르면 다른 사람이 확인하기 어렵습니다.

---

## 43. 로컬에서 실행하는 방법

`b4-1` 폴더에서 다음 명령을 실행합니다.

```bash
python3 -m http.server 5500
```

그 다음 브라우저에서 다음 주소를 엽니다.

```text
http://localhost:5500
```

VS Code를 사용한다면 Live Server 확장으로 실행해도 됩니다.

단순히 `index.html`을 더블 클릭해도 어느 정도 보일 수 있지만, API 요청이나 경로 문제를 줄이기 위해 정적 서버로 실행하는 습관이 좋습니다.

---

## 44. GitHub Pages 배포 이해하기

GitHub Pages는 GitHub 저장소의 정적 파일을 웹사이트로 배포해주는 기능입니다.

현재 계획의 배포 대상 URL은 다음입니다.

```text
https://feelosophysics.github.io/codsaid/oothers/b4-1/
```

이 URL 구조를 나누면 다음과 같습니다.

```text
https://feelosophysics.github.io
```

GitHub 사용자 Pages 도메인입니다.

```text
/codsaid/
```

저장소 이름입니다.

```text
/oothers/b4-1/
```

저장소 안에서 이번 프로젝트가 들어 있는 하위 경로입니다.

배포 절차는 README에 정리되어 있습니다.

주의할 점은 GitHub Pages 설정과 push 권한이 필요하다는 것입니다. 로컬 파일을 만드는 것만으로는 인터넷에 자동 공개되지 않습니다. 변경사항을 GitHub에 push하고 Pages 설정이 켜져 있어야 합니다.

---

## 45. 직접 바꿔야 하는 개인화 위치

현재 콘텐츠는 학습용 샘플입니다.

본인 포트폴리오로 바꾸려면 다음을 수정하면 됩니다.

### 45-1. GitHub 사용자명

파일:

```text
js/main.js
```

수정할 부분:

```js
const GITHUB_USERNAME = "feelosophysics";
```

본인의 GitHub 아이디로 바꿉니다.

### 45-2. Hero 문구

파일:

```text
index.html
```

수정할 부분:

```html
<h1>브라우저의 기본기로 완성한 포트폴리오</h1>
```

본인의 소개 문장으로 바꿉니다.

### 45-3. About 내용

파일:

```text
index.html
```

About 섹션의 문단을 본인의 학습 과정, 관심 분야, 목표로 바꿉니다.

### 45-4. Footer와 소셜 링크

파일:

```text
index.html
```

수정할 부분:

```html
<a href="https://github.com/feelosophysics" target="_blank" rel="noreferrer">
```

본인의 GitHub 주소로 바꿉니다.

---

## 46. 제출 전 체크리스트

아래 항목을 하나씩 확인하세요.

### HTML

- `header`, `nav`, `main`, `section`, `article`, `footer`가 사용되었는가?
- Hero, About, Skills, Projects, Contact, Footer가 모두 있는가?
- 메뉴 링크가 각 섹션 id로 이동하는가?
- 이미지에 의미 있는 `alt`가 있는가?
- 폼의 `label for`와 입력 요소의 `id`가 연결되어 있는가?

### CSS

- `css/style.css`가 외부 파일로 연결되었는가?
- `:root`에 CSS 변수가 있는가?
- `[data-theme="dark"]` 다크 모드 변수가 있는가?
- 네비게이션에 Flexbox가 사용되었는가?
- Projects 카드에 Grid와 `auto-fit`, `minmax`가 사용되었는가?
- 모바일 퍼스트로 작성되었는가?
- `768px`, `1024px` 브레이크포인트가 있는가?
- 버튼과 카드에 hover, transition, shadow가 있는가?

### JavaScript

- `defer`로 JavaScript가 연결되었는가?
- `var` 없이 `const`, `let`만 사용하는가?
- HTML에 `onclick`을 쓰지 않는가?
- `querySelector`, `querySelectorAll`을 사용하는가?
- `addEventListener`를 사용하는가?
- `click`, `submit`, `scroll`, `input` 이벤트가 있는가?
- `event.preventDefault()`가 폼 제출과 링크 스크롤 처리에 사용되는가?
- `classList.add`, `remove`, `toggle`이 사용되는가?
- `textContent`, `innerHTML`이 적절히 사용되는가?

### API와 상태

- `fetch`와 `async/await`를 사용하는가?
- `try/catch`로 에러를 처리하는가?
- 로딩 상태 UI가 있는가?
- 성공 상태 카드 렌더링이 있는가?
- 에러 상태 메시지와 재시도 버튼이 있는가?
- 빈 상태 메시지가 있는가?
- 다크 모드 상태가 localStorage에 저장되는가?
- 폼 오류 상태가 화면에 반영되는가?
- 프로젝트 필터 상태가 카드 목록에 반영되는가?

### 배포

- GitHub Pages 설정이 켜져 있는가?
- 배포 URL에서 페이지가 열리는가?
- 배포 URL에서 API, 다크 모드, 폼 검증, 메뉴가 동작하는가?
- README에 저장소 URL과 배포 URL이 있는가?
- 데스크톱, 모바일, 다크 모드 스크린샷을 준비했는가?

---

## 47. 이 미션과 React의 연결

이 미션에서 직접 구현한 흐름은 React의 핵심 개념과 연결됩니다.

| 이번 미션 | React에서의 대응 개념 |
| --- | --- |
| `state` 객체 | `useState` |
| `addEventListener` | `onClick`, `onSubmit` 같은 이벤트 prop |
| `renderProjects()` | 상태에 따른 JSX 렌더링 |
| `fetchProjects()` | API 호출 후 상태 업데이트 |
| `classList.toggle()` | 상태에 따라 className 변경 |
| `innerHTML`로 카드 생성 | 배열 `map()`으로 컴포넌트 렌더링 |

React를 배우면 DOM을 직접 자주 만지지 않습니다. 하지만 React가 대신 해주는 일을 이해하려면, 먼저 DOM을 직접 다뤄보는 경험이 필요합니다.

이번 미션은 그 기초를 만드는 작업입니다.

---

## 48. 추천 학습 순서

처음부터 모든 코드를 완벽히 이해하려고 하면 어렵습니다.

다음 순서로 공부하는 것을 추천합니다.

1. `index.html`을 열고 페이지 섹션 구조를 먼저 읽습니다.
2. `css/style.css`에서 `:root`, `.navbar`, `.project-grid`, 미디어 쿼리를 확인합니다.
3. `js/main.js`에서 `elements`와 `state` 객체만 먼저 읽습니다.
4. 다크 모드 흐름인 `setTheme`을 이해합니다.
5. 햄버거 메뉴 흐름인 `toggleMenu`, `closeMenu`를 이해합니다.
6. 폼 흐름인 `handleContactSubmit`, `validateForm`, `renderFormState`를 이해합니다.
7. 마지막으로 가장 긴 GitHub API 흐름인 `fetchProjects`, `renderProjects`를 읽습니다.

한 번에 외우지 않아도 됩니다. "이 버튼을 누르면 어떤 함수가 실행되지?"를 따라가는 습관이 가장 중요합니다.

---

## 49. 연습 과제

프로젝트를 더 잘 이해하려면 직접 조금씩 바꿔보세요.

1. `GITHUB_USERNAME`을 본인 아이디로 바꿔보세요.
2. Projects 카드에 `fork` 저장소도 보이도록 `filter` 조건을 바꿔보세요.
3. 프로젝트를 별 개수 순으로 정렬해보세요.
4. 폼 메시지 최소 길이를 10자로 제한해보세요.
5. 다크 모드 버튼 라벨을 한국어로 바꿔보세요.
6. Skills 카드에 본인이 배우는 기술을 추가해보세요.
7. Top 버튼이 300px이 아니라 500px 이후 보이게 바꿔보세요.
8. Intersection Observer의 `threshold`를 0.5로 바꿔 차이를 확인해보세요.

---

## 50. 마지막 정리

이번 미션에서 가장 중요한 것은 멋진 디자인보다 흐름을 이해하는 것입니다.

반드시 기억해야 할 핵심은 다음입니다.

```text
HTML은 구조를 만든다.
CSS는 화면을 꾸미고 배치한다.
JavaScript는 이벤트를 듣고 상태를 바꾸고 화면을 업데이트한다.
API는 외부 데이터를 가져온다.
상태별 UI는 사용자가 지금 무슨 일이 일어나는지 이해하게 해준다.
```

이 프로젝트를 끝까지 따라오면 다음을 설명할 수 있어야 합니다.

1. 시맨틱 태그를 왜 사용하는지
2. Flexbox와 Grid를 언제 쓰는지
3. `querySelector`로 요소를 찾고 `addEventListener`로 이벤트를 연결하는 방법
4. 화살표 함수, 구조분해 할당, `map`, `filter`, `forEach`의 기본 사용법
5. `fetch`와 `async/await`로 API 데이터를 가져오는 방법
6. 로딩, 성공, 에러, 빈 상태를 UI로 나누는 이유
7. 다크 모드, API, 폼 검증에서 "상태 -> 렌더링" 흐름이 어떻게 동작하는지

이제 `index.html`, `css/style.css`, `js/main.js`를 함께 보면서 버튼 하나, 상태 하나, 화면 변화 하나씩 따라가면 됩니다.
