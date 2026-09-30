# 극한 상세 학습 가이드: 바닐라 JS 포트폴리오 (현미경 해부 버전 v2)

초심자의 시선에 맞춰, 단 하나의 속성이나 태그도 건너뛰지 않고 "이 코드가 왜 여기 있어야 하는가"를 완전히 파헤칩니다. 전체 코드를 기능(섹션) 단위로 묶어 HTML(뼈대) → CSS(옷) → JS(동작) 순으로 하나하나 뜯어봅니다.

---

## 🗺️ 전체 학습 로드맵 (기능/섹션 중심)

*모든 챕터는 해당 기능과 관련된 HTML, CSS, JS 코드를 한 호흡에 묶어서 분석합니다.*

| 챕터 | 주제 | 핵심 개념 |
|------|------|-----------|
| **0** | 이 미션의 배경과 학습 지도 | 왜 이걸 배우는가, React 징검다리, 6가지 학습 목표 매핑 |
| **1** | 웹의 기반 다지기 (사전 준비와 전역 설정) | DOCTYPE, `<head>`, 구글 폰트, `defer`, `:root` 변수, Reset CSS |
| **2** | 길잡이 만들기 (헤더 · 네비게이션 · 스크롤 인터랙션) | 시맨틱 태그, Flexbox, 햄버거 메뉴, 스크롤 탑, 네비 배경 변경 |
| **3** | 첫인상과 테마 변경 (STATE 패턴 · 다크 모드 · 타이핑) | STATE 중앙 관리, localStorage, `data-theme`, `prefers-color-scheme`, setTimeout |
| **4** | 나를 소개하다 (About & Skills 섹션) | `<img>` alt, CSS Grid, `auto-fit`/`minmax`, 반응형 카드 |
| **5** | 내 작업물 자랑하기 (Projects · GitHub API · 상태별 렌더링) | `fetch`, `async/await`, `try/catch`, `map`/`filter`, 구조분해 할당, 4가지 상태 UI, `addEventListener` vs `onclick` |
| **6** | 문의 받기 (Contact Form · 유효성 검사 · 실시간 피드백) | `<form>`, `<label>`, `submit`/`input` 이벤트, 정규식, `showError`/`clearError`, Formspree |
| **7** | 반응형 설계와 모바일 퍼스트 | `max-width` vs `min-width`, 브레이크포인트, 왜 모바일 퍼스트인가 |
| **8** | 배포와 자기 점검 | GitHub Pages, 체크리스트, "다른 초심자에게 설명하기" 연습 |

---

## 📖 Chapter 0: 이 미션의 배경과 학습 지도

### 0-1. 왜 이 미션을 하는가?

이 미션의 한 줄 요약: **"React를 배우기 전에, React가 대신 해주는 일을 맨손으로 직접 해보기"**

React, Vue, Angular 같은 모던 프론트엔드 프레임워크는 결국 내부적으로 HTML, CSS, JavaScript를 만들어냅니다. 자동차를 타기 전에 자전거를 탈 줄 알아야 하듯, 프레임워크가 "자동화"해주는 것들을 먼저 "수동으로" 겪어봐야 나중에 왜 그 자동화가 편리한지 뼈저리게 느낄 수 있습니다.

특히 이 미션이 강조하는 핵심 흐름은:

```
사용자 이벤트 → 상태(STATE) 변경 → 화면(DOM) 업데이트
```

이것은 React의 `useState` → `re-render` 흐름과 **정확히** 같은 구조입니다. 우리는 이 흐름을 자바스크립트로 직접 구현함으로써, 나중에 React를 배울 때 "아, 이것을 자동으로 해주는 거구나!" 하고 단번에 이해할 수 있는 근육 기억을 만듭니다.

### 0-2. 6가지 학습 목표와 챕터 매핑

미션 문서(3장)에서 "이 과제를 마친 후, 학습자는 아래를 스스로 설명할 수 있어야 한다"라고 제시한 6가지 목표와, 이 학습 가이드에서 그 목표를 다루는 챕터를 매핑합니다.

| # | 학습 목표 | 관련 챕터 | 대응하는 실제 코드 |
|---|-----------|-----------|-------------------|
| 1 | HTML **시맨틱 태그**를 왜 사용하는지, 어떤 기준으로 구조를 설계했는지 | Ch.1, Ch.2 | `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>` |
| 2 | CSS **Flexbox와 Grid의 차이**, 언제 각각을 선택하는지 | Ch.2, Ch.4 | `.nav`(Flex), `.skills__container`(Grid), `.projects__container`(Grid) |
| 3 | `querySelector`로 DOM 선택, `addEventListener`로 이벤트 연결 흐름 | Ch.2, Ch.5, Ch.6 | `document.getElementById(...)`, `.addEventListener('click', ...)` |
| 4 | **화살표 함수, 구조분해 할당, 배열 메서드**(map/filter) | Ch.3, Ch.5 | `const renderTheme = () => {...}`, `const { status, allData } = STATE.portfolio`, `.map()`, `.filter()` |
| 5 | `fetch`와 `async/await`로 비동기 데이터를 가져오고, **로딩/성공/실패 상태**를 UI로 표현 | Ch.5 | `fetchProjects()`, `renderProjectsUI()`, loading/success/error/empty 분기 |
| 6 | **이벤트 → 상태 변경 → DOM 업데이트** 연결 | Ch.3, Ch.5, Ch.6 | 다크 모드 토글, API 상태 변경, 폼 유효성 검사, 필터 변경 |

### 0-3. 프로젝트에서 구현한 "상태 → 렌더링" 흐름 4가지

미션은 최소 3가지 이상의 "상태 → 렌더링" 흐름을 요구합니다. 우리 포트폴리오에는 **4가지**가 구현되어 있습니다:

```
흐름 1: 다크 모드 토글 클릭 → STATE.theme 변경 → renderTheme() → 전체 화면 색상 전환
흐름 2: GitHub API 호출 → STATE.portfolio.status 변경 → renderProjectsUI() → 로딩/카드/에러/빈 화면
흐름 3: 필터 버튼 클릭 → STATE.portfolio.filter 변경 → renderProjectsUI() → 프로젝트 목록 필터링
흐름 4: 폼 입력/제출 → 각 필드 유효성 상태 변경 → showError()/clearError() → 에러 메시지 표시/숨김
```

---

## 📖 Chapter 1: 웹의 기반 다지기 (사전 준비와 전역 설정)

이 웹사이트를 열자마자 보이지 않는 곳에서 브라우저가 무슨 일을 하는지, `index.html` 최상단 코드를 모두 해부합니다.

### 1-1. 문서의 시작과 신분증 (`index.html`)

```html
<!DOCTYPE html>
<html lang="ko">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio - feelosophysics</title>
  <meta name="description" content="Backend Developer Portfolio">
```

#### 🔬 현미경 분석 (한 줄도 빠짐없이)
- `<!DOCTYPE html>`: 브라우저(크롬 등)에게 "이 문서는 10년 전 옛날 문법이 아니라, 최신 규격인 **HTML5**로 작성되었어. 최신 방식으로 읽어줘!"라고 알려주는 선언문입니다. 이 태그가 없으면 브라우저가 화면을 이상하게 그릴 수 있습니다(호환성 모드).
- `<html lang="ko">`: HTML 문서의 진짜 시작점입니다. `lang="ko"`는 Language(언어)가 Korean(한국어)이라는 뜻입니다. 시각장애인용 화면 낭독기가 이 문서를 읽을 때 "아, 한국어 발음 엔진으로 읽어야겠구나" 하고 판단하게 돕습니다.
- `<head>`: 브라우저 탭 이름, 폰트, 검색 엔진 설정 등 **화면에는 안 보이지만 페이지에 꼭 필요한 설정**들을 담는 그릇입니다.
- `<meta charset="UTF-8">`: `meta`는 문서의 정보(데이터)를 의미합니다. `charset`은 Character Set(문자 집합)의 약자입니다. `UTF-8`은 전 세계 모든 언어와 이모티콘(😊)을 깨지지 않고 보여주는 만능 번역기 규칙입니다. 이걸 안 쓰면 한글이 "웗꿳"하고 깨집니다.
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">`: **반응형 웹을 위한 절대 반지**입니다.
  - `viewport`: 스마트폰 화면에서 보이는 영역을 뜻합니다.
  - `width=device-width`: "웹사이트의 가로 너비를 네가 지금 보고 있는 기기(스마트폰, 태블릿)의 가로 너비와 똑같이 맞춰라"라는 뜻입니다.
  - `initial-scale=1.0`: "처음 들어왔을 때 화면 확대/축소 비율을 무조건 1배율(기본)로 해라."
- `<title>`: 브라우저 탭 맨 위에 뜨는 이름이자, 즐겨찾기를 할 때 저장되는 이름입니다.
- `<meta name="description" content="Backend Developer Portfolio">`: 검색 엔진(구글)이 검색 결과 페이지에서 이 사이트의 설명을 보여줄 때 쓰는 한 줄 요약입니다. SEO(검색 엔진 최적화)의 기본입니다.

### 1-2. 외부 자원 끌어오기 (폰트와 파일 연결)

```html
  <!-- 폰트 추가: 구글 폰트 (Inter) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/style.css">
  <script src="js/main.js" defer></script>
</head>
```

#### 🔬 현미경 분석
이 부분은 내 컴퓨터 밖(구글 서버)에서 무언가를 가져오는 마법의 통로입니다.

- `<link>` 태그: 현재 HTML 문서와 외부 문서(폰트 파일, CSS 파일 등)를 **연결(Link)**해주는 태그입니다.
- `<link rel="preconnect" href="https://fonts.googleapis.com">`
  - `rel="preconnect"`: relation(관계)가 preconnect(미리 연결)라는 뜻입니다. 
  - `href`: Hypertext Reference의 약자로, 연결할 주소입니다.
  - **해석**: 브라우저야, 이따가 내가 구글 서버(`https://fonts.googleapis.com`)에서 폰트를 다운받을 건데, 시간 아까우니까 **미리 서버랑 몰래 연결선부터 꽂아놔!** (로딩 속도 최적화 기술입니다).
- `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>`
  - `fonts.gstatic.com`은 구글이 실제 폰트 파일을 쟁여두는 진짜 창고 주소입니다.
  - `crossorigin`: 내 웹사이트 도메인(예: naver.com)과 구글 서버의 도메인이 서로 다르지만(Cross Origin), 폰트를 가져오는 걸 허락해달라는 보안 통과 암호입니다.
- `<link href="...Inter:wght@400;500..." rel="stylesheet">`
  - 이제 미리 선을 꽂아둔 구글 창고에서 진짜로 `Inter`라는 이름의 폰트를 굵기별(400, 500, 600, 700)로 다운로드해 옵니다. `rel="stylesheet"`는 가져오는 이 파일이 디자인을 담당하는 스타일시트 파일임을 알립니다.
- `<link rel="stylesheet" href="css/style.css">`: 내가 직접 만든 CSS 파일에 연결합니다.
- `<script src="js/main.js" defer></script>`: 내가 만든 자바스크립트 파일(`src`: Source)을 불러옵니다. **`defer`**는 "HTML 뼈대 그림을 끝까지 다 그리고 나서 이 자바스크립트를 실행해!"라는 아주 중요한 지시어입니다.

> **💡 `defer`는 왜 중요한가?** JS 파일이 HTML보다 먼저 실행되면, `document.getElementById('nav-toggle')`처럼 HTML 요소를 찾는 코드가 "그런 거 아직 없는데?"라고 `null`을 뱉어 에러가 납니다. `defer`를 달아주면 HTML 파싱이 모두 끝난 뒤에야 JS가 실행되므로, 이 문제가 원천 차단됩니다.

### 1-3. 초기화와 변수 세팅 (`style.css` 도입부)

CSS 파일의 첫 부분에서는 모든 브라우저가 멋대로 가진 기본 여백을 청소하고, 프로젝트 전체에서 쓸 색상 변수를 만듭니다.

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  /* 따뜻한 파스텔톤 컬러 팔레트 */
  --color-bg: #fffbf7;
  --color-bg-alt: #fceceb;
  --color-text: #4a403d;
  --color-text-muted: #8c827f;
  --color-primary: #f2a6a6;
  --color-primary-hover: #e08b8b;
  --color-border: #f0dedd;
  --color-error: #e57373;
  --color-success: #81c784;
  --color-card-bg: #ffffff;
  --color-card-shadow: rgba(0, 0, 0, 0.627);

  --font-main: 'Inter', sans-serif;
  --nav-height: 70px;
  --container-width: 1100px;
}

/* Dark Mode Variables */
[data-theme="dark"] {
  --color-bg: #2d2a2a;
  --color-bg-alt: #383434;
  --color-text: #f5f0f0;
  /* ...이하 다크 모드 색상들... */
}
```

#### 🔬 현미경 분석
- `*` (별표): "HTML 문서 안에 있는 **모~든 태그**야 내 말 들어라"라는 뜻입니다.
- `margin: 0; padding: 0;`: 크롬, 사파리 등은 기본적으로 태그마다 약간의 띄어쓰기(여백)를 몰래 가지고 있습니다. 이걸 0으로 싹 다 청소(초기화)해야 우리가 원하는 대로 정확히 디자인을 얹을 수 있습니다.
- `box-sizing: border-box;`: 매우 중요한 공식입니다! 가로 너비를 100px로 줬는데 테두리(border)를 5px 주면 전체 크기가 110px로 뚱뚱해지는 현상을 막아줍니다. "테두리를 포함해서 무조건 전체 너비를 100px로 꽉 맞춰라"라는 마법의 코드입니다.
- `:root`: 이 웹사이트의 최상위 뿌리를 말합니다.
- `--color-bg: #fffbf7;`: 이름 앞에 `--`를 붙이면 CSS 안에서 언제든 재사용할 수 있는 **변수**가 됩니다. 나중에 배경색을 바꿀 때, 수백 줄의 CSS를 다 고칠 필요 없이 여기서 `#fffbf7` 하나만 고치면 사이트 전체의 배경색이 싹 바뀝니다.
- `var(--color-bg)`: 나중에 CSS 파일 아래쪽에서 변수 값을 쓸 때 이렇게 꺼내 씁니다.
- `--nav-height: 70px;`: 네비게이션 바의 높이입니다. 이걸 변수로 만든 이유는, Hero 섹션의 `padding-top`에서도, 모바일 메뉴의 `top` 위치에서도 같은 값을 쓰기 때문입니다. 한 곳만 수정하면 전부 연쇄적으로 바뀝니다.
- `[data-theme="dark"]`: **이것이 다크 모드의 핵심 톱니바퀴입니다!** 나중에 JavaScript가 `<html>` 태그에 `data-theme="dark"` 속성을 붙이면, CSS가 이걸 감지하고 여기 적힌 어두운 색상 변수들로 싹 갈아치워버립니다. 같은 `var(--color-bg)`인데 자동으로 `#fffbf7`(밝은 베이지) → `#2d2a2a`(따뜻한 다크)로 바뀌는 마법!

---

## 📖 Chapter 2: 길잡이 만들기 (헤더 · 네비게이션 · 스크롤 인터랙션)

이제 본격적으로 화면 상단에 찰싹 붙어있는 메뉴바(네비게이션)와 스크롤 관련 인터랙션이 어떻게 구조를 잡고 동작하는지 파헤칩니다.

### 2-1. 네비게이션 바의 HTML 구조 (`index.html`)

```html
<header class="header">
  <nav class="nav container">
    <a href="#" class="nav__logo">Dev.feel</a>

    <div class="nav__menu" id="nav-menu">
      <ul class="nav__list">
        <li class="nav__item"><a href="#home" class="nav__link">Home</a></li>
        <li class="nav__item"><a href="#about" class="nav__link">About</a></li>
        <li class="nav__item"><a href="#skills" class="nav__link">Skills</a></li>
        <li class="nav__item"><a href="#projects" class="nav__link">Projects</a></li>
        <li class="nav__item"><a href="#contact" class="nav__link">Contact</a></li>
      </ul>
    </div>

    <div class="nav__actions">
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle Dark Mode">
        <span class="icon">🌙</span>
      </button>
      <div class="nav__toggle" id="nav-toggle">
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </div>
    </div>
  </nav>
</header>
```

#### 🔬 현미경 분석
- `<header>`: 머리말을 뜻하는 시맨틱 태그입니다. 로봇(검색 엔진)이 "아, 여기가 사이트의 간판 메뉴 영역이구나"라고 인식합니다. `class="header"`를 달아서 나중에 CSS로 디자인할 이름표를 붙여줬습니다.
- `<nav>`: Navigation(조종/탐색)의 약자입니다. 다른 페이지나 섹션으로 이동하는 링크들의 묶음을 감쌀 때 쓰는 태그입니다. `container`라는 클래스를 하나 더 달았는데, 이는 콘텐츠가 화면 양옆 끝에 너무 딱 달라붙지 않게 가운데로 모아주는 상자 역할을 합니다.
- `<a href="#" class="nav__logo">`: `<a>`는 닻(Anchor)을 의미하며 링크를 만듭니다. `href="#"`는 "클릭해도 다른 페이지로 가지 말고 지금 페이지의 맨 위로 가라"는 뜻입니다. 로고를 누르면 보통 화면 맨 위로 가니까요.
- `<ul>`과 `<li>`: 메뉴 항목들을 만들 때 쓰는 세트 메뉴입니다.
  - `<ul>`: Unordered List (순서가 없는 목록). 메뉴 1, 메뉴 2를 묶는 큰 포장지입니다.
  - `<li>`: List Item (목록 항목). 포장지 안의 알맹이(Home, About 등) 하나하나입니다. 왜 굳이 이렇게 쓰냐면, 메뉴라는 것이 본질적으로 '항목들의 목록'이기 때문입니다. 로봇이 이 코드를 보면 "아, 이 사이트는 메뉴가 5개인 목록이구나" 하고 정확히 파악합니다.
- `<a href="#home">Home</a>`: 이 버튼을 클릭하면, 페이지에서 `<section id="home">`이라는 이름표가 붙은 곳으로 화면이 스크롤되어 내려갑니다! `id`를 찾아가는 앵커 링크의 마법입니다.
- `aria-label="Toggle Dark Mode"`: 시각장애인용 스크린 리더가 이 버튼을 만났을 때 "다크 모드 토글"이라고 읽어줍니다. 이모지(🌙)만으로는 뭔 버튼인지 알 수 없기 때문입니다. 웹 접근성(Accessibility)의 기본!
- `nav__toggle`과 3개의 `<span class="bar">`: 모바일에서 보이는 **햄버거 메뉴 아이콘(☰)**의 정체입니다. 가로 막대 3개를 CSS로 세로로 쌓으면 ☰ 모양이 됩니다.

### 2-2. 네비게이션 바를 양옆으로 찢는 CSS 마법 (`style.css`)

HTML만 적어두면 메뉴가 아래로 한 줄씩 못생기게 나열됩니다. 이를 멋지게 가로로 배치하는 것이 CSS Flexbox입니다.

```css
.header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: var(--nav-height);
  background-color: var(--color-bg);
  z-index: 100;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
}

.header.scrolled {
  box-shadow: 0 4px 20px var(--color-card-shadow);
}

.nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.nav__list {
  display: flex;
  gap: 2rem;
}
```

#### 🔬 현미경 분석
- `position: fixed;`: **화면을 아무리 스크롤해도 헤더가 상단에 찰싹 붙어서 따라옵니다.** 스크롤해도 사라지지 않는 끈적이 메뉴바입니다.
- `top: 0; left: 0; width: 100%;`: 화면의 꼭대기(top: 0), 왼쪽 끝(left: 0)에서 시작해서 가로 전체(width: 100%)를 차지하라는 뜻입니다.
- `z-index: 100;`: 화면에 여러 요소가 겹칠 때 "나는 맨 앞에 있어야 해!"라는 우선순위 숫자입니다. 100이면 다른 모든 요소 위에 그려집니다. (기본값은 0)
- `transition: background-color 0.3s ease, box-shadow 0.3s ease;`: 배경색이나 그림자가 바뀔 때 0.3초에 걸쳐 부드럽게 전환됩니다. 이것 없이는 뚝뚝 끊기듯 변합니다.
- `.header.scrolled`: 스크롤 시 JS가 `header`에 `scrolled` 클래스를 붙이면, `box-shadow`가 생겨서 헤더가 둥실 떠있는 것처럼 보입니다.
- `.nav`: CSS에서 쩜(`.`)은 클래스(이름표)를 부르는 말입니다. 즉, HTML의 `<nav class="nav">`를 부릅니다.
- `display: flex;`: **"네 안에 있는 자식 요소들을 가로 1차원으로 쫙 배열하겠다!"**라는 뜻입니다. 이 순간 묶여있던 로고, 메뉴 뭉치, 다크모드 버튼 뭉치가 가로로 정렬됩니다.
- `justify-content: space-between;`: Flexbox의 핵심입니다. 가로축 정렬을 결정하는데, `space-between`은 요소들 사이(between)에 공간(space)을 줘서 **자석의 같은 극처럼 양쪽 끝으로 쫘아악 밀어버립니다.** (왼쪽 끝엔 로고, 오른쪽 끝엔 메뉴).
- `align-items: center;`: 세로축 정렬입니다. 로고 글씨와 메뉴 글씨의 높낮이가 약간 달라도, 정확히 한가운데에 꼬치처럼 중심을 꽂아서 맞춰줍니다.
- `.nav__list`: 메뉴 알맹이(`<li>`들)를 묶고 있는 `<ul>` 태그입니다. 이 녀석에게도 `display: flex;`를 주면 세로로 나오던 Home, About 글씨들이 가로로 배치됩니다.
- `gap: 2rem;`: 메뉴 사이사이의 간격을 띄워줍니다. (`margin`을 일일이 안 줘도 알아서 사이를 띄우는 꿀 기능입니다).

### 2-3. 햄버거 메뉴 토글 (JS: `classList.toggle`)

```javascript
const navToggle = document.getElementById('nav-toggle');
const navMenu = document.getElementById('nav-menu');
const navLinks = document.querySelectorAll('.nav__link');

navToggle.addEventListener('click', () => {
  navToggle.classList.toggle('active');
  navMenu.classList.toggle('active');
});

navLinks.forEach(link => {
  link.addEventListener('click', () => {
    navToggle.classList.remove('active');
    navMenu.classList.remove('active');
  });
});
```

#### 🔬 현미경 분석
- `document.getElementById('nav-toggle')`: HTML 문서(document) 전체에서 `id="nav-toggle"`이라는 고유 이름표가 붙은 딱 하나의 요소를 찾아서 자바스크립트 변수에 담아둡니다. 이제 이 변수를 통해 그 요소를 마음대로 조종할 수 있습니다.
- `document.querySelectorAll('.nav__link')`: CSS 선택자(`.클래스명`)로 일치하는 **모든** 요소를 찾아 배열과 비슷한 NodeList로 돌려줍니다. (querySelector는 첫 번째 하나만, querySelectorAll은 전부)
- `classList.toggle('active')`: 가장 영리한 클래스 조작 메서드입니다. `active` 클래스가 **없으면 붙이고, 있으면 떼어냅니다**. 한 번 누르면 메뉴가 열리고(active 붙음), 한 번 더 누르면 닫히는(active 떼짐) 토글 동작이 이 한 줄로 완성됩니다!
- `navLinks.forEach(...)`: 메뉴 링크 하나하나에 "클릭하면 메뉴를 닫아라"라는 경비원을 붙여줍니다. 모바일에서 메뉴 항목을 탭하면 해당 섹션으로 스크롤되면서 동시에 메뉴 패널이 닫히는 자연스러운 UX를 만들어줍니다.

### 2-4. 네비게이션 배경 변경 (스크롤 60px 이상)

```javascript
window.addEventListener('scroll', () => {
  if (window.scrollY >= 60) {
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }
});
```

#### 🔬 현미경 분석
- `window.addEventListener('scroll', ...)`: 사용자가 마우스 휠을 굴리거나 화면을 쓸어올릴 때마다 발동하는 이벤트입니다. `window`는 브라우저 창 자체를 뜻합니다.
- `window.scrollY`: 현재 페이지가 위에서부터 몇 픽셀만큼 아래로 스크롤되었는지 알려주는 숫자입니다. 맨 꼭대기이면 0, 아래로 60px 내려가면 60입니다.
- **60px 기준값의 의미**: 네비게이션 바 높이(`--nav-height`)가 70px이므로, 사용자가 약 한 줄 정도 스크롤했을 때 "아, 이 사람은 콘텐츠를 읽기 시작했구나"라고 판단하는 지점입니다. 이때 `box-shadow`를 추가해서 헤더가 콘텐츠 위에 살짝 떠있는 느낌을 줍니다.
- `classList.add('scrolled')` / `classList.remove('scrolled')`: CSS에 미리 정의해둔 `.header.scrolled { box-shadow: ... }` 규칙이 활성화/비활성화됩니다.

### 2-5. 스크롤 탑 버튼 (스크롤 300px 이상)

```html
<!-- HTML -->
<a href="#" class="scroll-top" id="scroll-top" aria-label="Scroll to top">↑</a>
```

```css
/* CSS */
.scroll-top {
  position: fixed;
  bottom: -50px;  /* 처음에는 화면 아래에 숨겨둠 */
  right: 20px;
  opacity: 0;     /* 투명하게 */
  transition: all 0.3s ease;
}

.scroll-top.show {
  bottom: 20px;   /* 화면 오른쪽 하단에 나타남 */
  opacity: 1;     /* 보이게 */
}
```

```javascript
// JS
const scrollTopBtn = document.getElementById('scroll-top');

window.addEventListener('scroll', () => {
  if (window.scrollY >= 300) {
    scrollTopBtn.classList.add('show');
  } else {
    scrollTopBtn.classList.remove('show');
  }
});

scrollTopBtn.addEventListener('click', (e) => {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
```

#### 🔬 현미경 분석
- **처음 상태**: `bottom: -50px`과 `opacity: 0` 덕분에 버튼이 화면 아래에 숨겨져 보이지 않습니다.
- **300px 기준값의 의미**: 사용자가 충분히 스크롤했을 때만 "맨 위로" 버튼이 나타납니다. 맨 위에 있을 때 이 버튼이 보이면 의미가 없으니까요.
- `e.preventDefault()`: `<a href="#">`를 클릭하면 브라우저가 기본적으로 URL에 `#`를 추가하고 페이지 맨 위로 순간이동합니다. 이걸 막고(prevent), 대신 우리가 직접 `window.scrollTo()`로 **부드럽게** 올라가게 만듭니다.
- `window.scrollTo({ top: 0, behavior: 'smooth' })`: 페이지 최상단(top: 0)으로, 부드럽게(smooth) 스크롤합니다. `behavior: 'smooth'`가 없으면 순간이동처럼 뚝 올라갑니다.

---

## 📖 Chapter 3: 첫인상과 테마 변경 및 상태 관리 (STATE 패턴)

이 챕터에서는 화면의 첫인상을 결정하는 히어로 섹션과 다크 모드, 그리고 피드백 평가에서 가장 중요한 **상태(STATE) 관리 기법**을 현미경 분석합니다.

### 3-1. 왜 상태(STATE) 객체를 따로 만들어야 할까요?

자바스크립트 파일(`main.js`)의 맨 위를 보면 다음과 같은 코드가 있습니다.

```javascript
const STATE = {
  theme: localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
  portfolio: {
    allData: [],      // GitHub에서 가져온 원본 데이터
    filter: 'all',    // 현재 선택된 언어 필터
    status: 'idle',   // 'loading', 'success', 'error', 'empty'
    errorMsg: ''
  }
};
```

#### 🔬 현미경 분석
- **변수 남발의 문제점**: 원래 다크 모드 따로(`let currentTheme = 'light'`), 프로젝트 목록 따로(`let projects = []`) 그냥 흩어져 있는 변수를 만들어도 웹사이트는 당장 잘 돌아갑니다. 하지만 규모가 커지면 "현재 이 웹사이트가 어떤 상태지?"를 파악하기 위해 수십 개의 변수를 일일이 추적해야 합니다.
- **`STATE` 객체로 묶는 이유**: 모든 핵심 데이터를 `STATE`라는 하나의 객체(주머니)에 몰아넣으면 놀라운 장점이 생깁니다.
  1. **중앙 통제실 역할**: `console.log(STATE)` 딱 한 줄만 쳐보면, 지금 웹사이트가 다크 모드인지, 아니면 프로젝트를 불러오는 중인지 스냅샷처럼 한눈에 파악할 수 있습니다.
  2. **단방향 데이터 흐름 구축**: 사용자가 어떤 버튼을 누르면 → 화면 요소를 직접 주물러서 바꾸는 것이 아니라 → `STATE` 객체의 값만 조용히 바꾸고 → `render()` 함수가 오직 `STATE`만을 쳐다보며 화면을 일괄적으로 다시 그립니다. 화면 꼬임 현상이 원천 차단됩니다.
  3. **리액트(React)로 가는 징검다리**: 이것이 바로 모던 프론트엔드 프레임워크인 리액트(`useState`)가 일하는 핵심 패러다임입니다. 이를 바닐라 자바스크립트로 직접 구현해보며 그 철학을 미리 체득한 것입니다!

#### 🔬 `theme` 초기값의 3단계 판단 로직
```javascript
localStorage.getItem('theme')                                     // 1단계: 이전에 저장한 테마가 있나?
  || (window.matchMedia('(prefers-color-scheme: dark)').matches    // 2단계: 없으면 → 운영체제가 다크모드인가?
      ? 'dark'                                                    // 2-1: 맞으면 'dark'
      : 'light')                                                  // 2-2: 아니면 'light'
```

- `localStorage.getItem('theme')`: 브라우저의 영구 메모장에서 `theme`이라는 키로 저장된 값을 꺼냅니다. 처음 방문이면 `null`이 나옵니다.
- `||` (OR 연산자): 앞의 값이 `null`이면(falsy), 뒤의 값으로 넘어갑니다.
- `window.matchMedia('(prefers-color-scheme: dark)')`: **보너스 과제 5-4의 핵심 코드!** 운영체제(macOS, Windows, iOS 등)의 시스템 설정에서 다크 모드가 켜져있는지를 물어봅니다. `.matches`가 `true`이면 시스템이 다크 모드입니다.
- 결론: "사용자가 예전에 선택한 테마 → 없으면 시스템 설정 → 그것도 없으면 라이트" 순서로 가장 현명한 초기값을 결정합니다.

### 3-2. 다크 모드는 어떻게 기억되고 적용되는가?

```javascript
const themeToggleBtn = document.getElementById('theme-toggle');
const themeIcon = themeToggleBtn.querySelector('.icon');
const htmlElement = document.documentElement;

const renderTheme = () => {
  if (STATE.theme === 'dark') {
    htmlElement.setAttribute('data-theme', 'dark');
    themeIcon.textContent = '☀️';
  } else {
    htmlElement.setAttribute('data-theme', 'light');
    themeIcon.textContent = '🌙';
  }
};

// 초기 테마 렌더링
renderTheme();

// 토글 버튼 클릭 시 '상태 변경' 후 '렌더링' 호출 (단방향 데이터 흐름)
themeToggleBtn.addEventListener('click', () => {
  // 1. 상태 변경 (데이터만 먼저 바꿈)
  STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', STATE.theme);

  // 2. 화면 업데이트 지시
  renderTheme();
});
```

#### 🔬 현미경 분석
- `document.documentElement`: HTML 문서의 가장 꼭대기 태그인 `<html>`을 가리킵니다. 여기에 `data-theme` 속성을 붙여야 CSS가 전역으로 감지합니다.
- `themeToggleBtn.querySelector('.icon')`: `themeToggleBtn` **안에서만** `.icon` 클래스를 찾습니다. 문서 전체를 뒤지는 것이 아니라 범위를 좁혀서 찾는 것입니다.
- `addEventListener('click', ...)`: 사용자가 달 모양 버튼을 '클릭'할 때까지 귀를 쫑긋 세우고 기다리는 경비원입니다.
- `STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';`: 삼항 연산자입니다. "만약 지금 테마가 다크면 라이트로, 아니면 다크로 `STATE.theme` 값을 바꿔라!" 라는 뜻입니다. **여기서 화면은 아직 안 변했습니다.** 데이터만 바뀐 것입니다.
- `localStorage.setItem('theme', STATE.theme);`: 웹 브라우저가 가진 영구 메모장(`localStorage`)에 현재 테마를 펜으로 꾹꾹 눌러 적어둡니다. 그래야 컴퓨터를 끄고 내일 다시 접속해도 브라우저가 메모장을 보고 다크 모드를 유지해줍니다.
- `htmlElement.setAttribute('data-theme', 'dark');`: `renderTheme()`이 호출되면 HTML 제일 꼭대기(`<html>` 태그)에 `data-theme="dark"`라는 암호표를 억지로 붙여버립니다. 그러면 CSS 파일의 `[data-theme="dark"]` 선택자가 이걸 목격하고 득달같이 달려와서 전역 변수 색상을 검정으로 덮어씌워버립니다.
- **단방향 흐름 정리**: `클릭 → STATE.theme 변경 → renderTheme() → 화면 업데이트`. 화면을 직접 건드리는 코드는 오직 `renderTheme()` 함수 하나뿐입니다. 이것이 단방향 데이터 흐름의 정수입니다.

### 3-3. 타이핑 효과의 비밀: `setTimeout`

```html
<!-- HTML -->
<h1 class="hero__title">
  <span class="typing-text" id="typing-text"></span><span class="cursor">|</span>
</h1>
```

```css
/* CSS */
.cursor {
  display: inline-block;
  width: 3px;
  animation: blink 1s infinite;
  color: var(--color-primary);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
```

```javascript
// JS
const typingElement = document.getElementById('typing-text');
const actualText = "안녕하세요, 저는 feelosophysics입니다.";
let charIndex = 0;

const typeText = () => {
  if (charIndex < actualText.length) {
    typingElement.textContent += actualText.charAt(charIndex);
    charIndex++;
    setTimeout(typeText, 100);
  }
};
setTimeout(typeText, 500);
```

#### 🔬 현미경 분석
- `<span id="typing-text"></span>`: 처음 화면이 켜지면 텅 빈 투명 상자입니다.
- `<span class="cursor">|</span>`: 깜빡거리는 커서(`|`)입니다.
- `@keyframes blink`: CSS 애니메이션을 정의합니다. 0%(시작)에는 보이고, 50%(중간)에 투명해지고, 100%(끝)에 다시 보입니다. `animation: blink 1s infinite;`로 이걸 1초마다 무한 반복하게 걸어두었습니다.
- `actualText.charAt(charIndex)`: `charAt`은 글자들이 연결된 기차에서 `charIndex` 번째 칸의 글자 하나만 똑 떼오는 기능입니다. 0번이면 '안', 1번이면 '녕'을 가져옵니다.
- `textContent +=`: 기존 화면 내용 뒤에 새로 가져온 글자를 찰싹 붙여줍니다. (안 → 안녕 → 안녕하)
- `let charIndex = 0;`: `const`가 아니라 `let`인 이유! 이 값은 0에서 시작해서 1, 2, 3... 계속 바뀌어야 하기 때문입니다. `const`는 한 번 정하면 못 바꾸고, `let`은 바꿀 수 있습니다.
- `setTimeout(typeText, 100);`: 이 마술의 핵심 뼈대입니다! 브라우저에게 **"100ms(0.1초) 뒤에 이 `typeText` 함수를 한 번 더 실행해!"**라고 예약 문자를 보냅니다. 
  즉, 0.1초마다 자기 자신을 꼬리에 꼬리를 물고 무한 호출하면서 한 글자씩 붙이니까, 우리 눈에는 마치 타자기로 치는 것처럼 스르륵 나타나게 되는 것입니다. (이런 패턴을 "재귀 타이머"라고 합니다.)
- `setTimeout(typeText, 500);` (마지막 줄): 페이지가 열리고 0.5초 뒤에 타이핑을 시작합니다. 즉시 시작하지 않고 잠시 기다려주는 연출입니다.

---

## 📖 Chapter 4: 나를 소개하다 (About & Skills 섹션)

자기소개와 기술 스택을 보여주는 영역입니다. 여기서는 이미지를 다루는 방식과 반응형 레이아웃의 마법인 **CSS Grid**를 집중적으로 파헤칩니다.

### 4-1. 시각 자료의 접근성 (`<img>` 태그)

```html
<img src="images/profile.jpg" alt="feelosophysics 프로필 이미지" class="about__img" id="profile-img">
```

#### 🔬 현미경 분석
- `src="images/profile.jpg"`: Source의 약자로, 이미지 파일이 어디에 있는지 경로를 알려줍니다.
- `alt="feelosophysics 프로필 이미지"`: Alternative Text(대체 텍스트)의 약자입니다. 정말 중요한 속성입니다! 
  만약 인터넷이 느려서 이미지가 안 뜨거나 이미지 파일이 삭제되었을 때, 이 텍스트가 대신 화면에 뜹니다. 또한 시각 장애인의 스크린 리더는 이 `alt` 속성을 소리 내어 읽어줍니다. 이것이 없으면 웹 접근성 점수가 크게 깎입니다.

### 4-2. Flexbox vs Grid: 언제 어떤 것을 쓰는가?

미션 목표 2번에서 "Flexbox와 Grid의 차이, 언제 각각을 선택해야 하는지"를 설명할 수 있어야 한다고 했습니다. 우리 포트폴리오에서 두 가지를 모두 사용하고 있으니, 실제 사례로 비교합니다.

| 특성 | Flexbox | Grid |
|------|---------|------|
| **차원** | 1차원 (가로 한 줄 또는 세로 한 줄) | 2차원 (가로 + 세로 격자) |
| **비유** | 빨래줄에 빨래를 매다는 것 | 바둑판에 돌을 놓는 것 |
| **우리 코드에서** | `.nav` (로고↔메뉴 양끝 정렬), `.hero__buttons` (버튼 나란히) | `.skills__container` (스킬 카드 격자), `.projects__container` (프로젝트 카드 격자) |
| **선택 기준** | 한 줄에 요소를 나열하고, 간격·정렬만 조절하면 될 때 | 행과 열이 모두 필요하거나, 화면 너비에 따라 열 수가 바뀌어야 할 때 |

### 4-3. 반응형의 마법, CSS Grid (`style.css`)

스킬 카드(`skills__card`)들이 모바일에서는 1줄, 태블릿에서는 2줄, 데스크톱에서는 3줄로 알아서 정렬되는 마법의 코드입니다.

```css
.skills__container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}
```

#### 🔬 현미경 분석
- `display: grid;`: Flexbox가 1차원(한 줄) 정렬이라면, Grid는 2차원(바둑판) 정렬의 끝판왕입니다. 카드들을 표처럼 격자로 묶어줍니다.
- `grid-template-columns`: 세로 기둥(열, Column)을 어떻게 세울 것인지 규칙을 정합니다.
- `repeat(auto-fit, ...)`: 괄호 안의 규칙을 화면이 허락하는 한 무한히 반복(repeat)하라는 뜻입니다. `auto-fit`은 화면 공간이 남으면 알아서 열의 개수를 늘려 맞추는 스마트한 옵션입니다.
- `minmax(250px, 1fr)`: "카드 너비는 절대 **최소 250px** 아래로 찌그러지지 않게 해라. 하지만 공간이 남으면 **1fr**(fraction, 비율)씩 공평하게 나눠 가져서 늘어나라!"는 뜻입니다.
  - **💡 왜 이게 대단한가요?** 이 단 한 줄 덕분에 우리는 미디어 쿼리 없이도 모바일(너비가 250px 겨우 나옴)에서는 1줄이 되고, 데스크톱에서는 여러 줄이 되는 완벽한 반응형 웹을 뚝딱 만들 수 있습니다.

프로젝트 카드도 동일한 원리이지만 최소 너비만 다릅니다:

```css
.projects__container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}
```

프로젝트 카드는 설명 텍스트가 더 길기 때문에, 최소 너비를 300px로 더 넓게 잡았습니다.

### 4-4. 카드의 시각 효과와 호버 (CSS)

```css
.skills__card {
  background-color: var(--color-card-bg);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 5px 15px var(--color-card-shadow);
  transition: transform 0.3s ease;
}

.skills__card:hover {
  transform: translateY(-5px);
}
```

#### 🔬 현미경 분석
- `border-radius: 12px;`: 카드의 네 모서리를 12px만큼 둥글게 깎아줍니다.
- `box-shadow: 0 5px 15px var(--color-card-shadow);`: 카드 아래에 그림자를 드리워서 종이가 살짝 떠있는 것처럼 보이게 합니다. `0 5px 15px`은 가로 0, 세로 5px 아래, 흐림 반경 15px입니다.
- `transition: transform 0.3s ease;`: `transform` 속성이 변할 때 0.3초에 걸쳐 부드럽게 전환합니다.
- `:hover`: 마우스를 올렸을 때 적용되는 가상 클래스입니다.
- `transform: translateY(-5px);`: Y축(세로)으로 -5px, 즉 위로 5px 이동시킵니다. 마우스를 올리면 카드가 살짝 뜨는 효과!

---

## 📖 Chapter 5: 내 작업물 자랑하기 (Projects 섹션 & GitHub API)

내 컴퓨터(로컬)를 벗어나 인터넷 세상(GitHub 서버)과 통신하는 **비동기 프로그래밍**의 정수입니다. 이 챕터가 미션에서 가장 무거운 비중을 차지합니다.

### 5-1. `fetch`와 `async/await` (비동기 통신의 원리)

```javascript
const GITHUB_USERNAME = 'feelosophysics';
const projectsContainer = document.getElementById('projects-container');

const fetchProjects = async () => {
  // 1. 상태 변경: 로딩 중
  STATE.portfolio.status = 'loading';
  renderProjectsUI();

  try {
    const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated`);
    if (!response.ok) {
      throw new Error(response.status === 403 ? 'API 호출 제한 초과' : '데이터를 불러올 수 없습니다.');
    }
    const data = await response.json();

    // 2. 상태 변경: 성공
    STATE.portfolio.allData = data.filter(repo => !repo.fork);
    STATE.portfolio.status = 'success';
    renderProjectsUI();

  } catch (error) {
    // 3. 상태 변경: 에러
    STATE.portfolio.status = 'error';
    STATE.portfolio.errorMsg = error.message;
    renderProjectsUI();
  }
};

// 앱 시작 시 데이터 로드
fetchProjects();
```

#### 🔬 현미경 분석
- **비동기(Asynchronous)란?**: 커피숍에서 커피를 주문(API 요청)하고, 커피가 나올 때까지 아무것도 못하고 서서 기다리는 것(동기)이 아니라, 진동벨을 받고 다른 일을 하다가 벨이 울리면 커피를 받아오는 것(비동기)입니다.
- `async`: 이 함수는 "비동기로 작동할 거야(커피를 주문할 거야)"라고 브라우저에게 미리 알려주는 키워드입니다.
- `` `https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated` ``: **템플릿 리터럴**입니다. 작은따옴표(`'`)나 큰따옴표(`"`)가 아닌 백틱(`` ` ``)으로 감싸면, `${변수명}` 자리에 변수 값이 자동으로 끼워집니다. 결과: `https://api.github.com/users/feelosophysics/repos?sort=updated`
- `await fetch(...)`: `fetch`는 브라우저가 외부에 심부름을 가는 함수입니다. `await`는 "저기요, GitHub 서버까지 갔다 오려면 시간이 꽤 걸리니까, 결과가 도착할 때까지 여기서 잠시만 기다려줄게!"라는 뜻입니다.
- `response.ok`: HTTP 응답 코드가 200번대(성공)이면 `true`, 아니면 `false`입니다.
- `response.status === 403`: GitHub API는 인증 없이 시간당 60회만 호출할 수 있습니다. 초과하면 403(Forbidden) 코드를 보냅니다.
- `throw new Error(...)`: 직접 에러 객체를 만들어서 던집니다. 던져진 에러는 `catch` 블록이 받아서 처리합니다.
- `response.json()`: 서버가 보내준 텍스트 뭉치를 자바스크립트 객체/배열로 파싱(해석)합니다.
- `try ... catch`: 데이터를 가져오다 보면 인터넷이 끊기거나 GitHub 서버가 터지는 등 별의별 일이 다 생깁니다. `try` 안의 코드를 실행해 보다가 실패하면, 스크립트가 뻗어버리는 대신 `catch` 영역으로 쏙 빠져나가서 안전하게 에러 화면을 띄워줍니다.

### 5-2. 구조분해 할당 — 실제 사용 사례

```javascript
const renderProjectsUI = () => {
  const { status, allData, filter, errorMsg } = STATE.portfolio;
  // ...
};
```

#### 🔬 현미경 분석
- 원래 이렇게 써야 합니다:
  ```javascript
  const status = STATE.portfolio.status;
  const allData = STATE.portfolio.allData;
  const filter = STATE.portfolio.filter;
  const errorMsg = STATE.portfolio.errorMsg;
  ```
- 구조분해 할당을 쓰면 한 줄로 줄어듭니다:
  ```javascript
  const { status, allData, filter, errorMsg } = STATE.portfolio;
  ```
- **왜 필요한가?**: 코드가 짧아지는 것도 좋지만, 진짜 이유는 **"이 함수가 STATE.portfolio에서 정확히 어떤 데이터를 사용하는지"를 첫 줄에서 한눈에 선언하는 것**입니다. 함수를 읽는 사람이 아래를 읽기 전에 "아, 이 함수는 status, allData, filter, errorMsg 이 4개를 쓰는구나" 하고 즉시 파악할 수 있습니다.

### 5-3. 4가지 상태별 UI 렌더링 (`renderProjectsUI` 전체 해부)

미션이 요구하는 **로딩/성공/에러/빈 상태**가 모두 이 함수 하나에서 처리됩니다.

```javascript
const renderProjectsUI = () => {
  const { status, allData, filter, errorMsg } = STATE.portfolio;

  // ---- 상태 1: 로딩 ----
  if (status === 'loading') {
    projectsContainer.innerHTML = '<div class="projects__loading">프로젝트를 불러오는 중입니다...</div>';
    return;
  }

  // ---- 상태 2: 에러 ----
  if (status === 'error') {
    projectsContainer.innerHTML = `
      <div class="projects__error">
        <p>${errorMsg}</p>
        <button class="btn btn--outline" id="retry-btn">다시 시도</button>
      </div>
    `;
    // onclick 대신 addEventListener로 이벤트 연결 (미션 제약사항 준수)
    const retryBtn = projectsContainer.querySelector('#retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', fetchProjects);
    }
    return;
  }

  // ---- 필터 적용 ----
  const filteredData = filter === 'all'
    ? allData
    : allData.filter(repo => repo.language === filter);

  // ---- 상태 3: 빈 데이터 ----
  if (status === 'success' && filteredData.length === 0) {
    projectsContainer.innerHTML = '<div class="projects__empty">표시할 프로젝트가 없습니다.</div>';
    return;
  }

  // ---- 상태 4: 성공 (카드 렌더링) ----
  const projectsHTML = filteredData.map(repo => {
    const description = repo.description || '프로젝트에 대한 설명이 없습니다.';
    const language = repo.language || 'Others';

    return `
      <article class="project-card fade-in appear">
        <h3><a href="${repo.html_url}" target="_blank" rel="noopener noreferrer">${repo.name}</a></h3>
        <p>${description}</p>
        <div class="project-meta">
          <span>${language}</span>
          <span>⭐ ${repo.stargazers_count}</span>
        </div>
      </article>
    `;
  }).join('');

  projectsContainer.innerHTML = projectsHTML;
};
```

#### 🔬 현미경 분석 (상태별)

**로딩 상태**:
- `innerHTML`로 "프로젝트를 불러오는 중입니다..." 텍스트를 박아넣습니다.
- `return;`으로 함수를 즉시 종료합니다. 아래의 카드 렌더링 코드까지 갈 필요가 없으니까요.

**에러 상태와 `onclick` 금지 원칙**:
- 에러 메시지와 "다시 시도" 버튼을 `innerHTML`로 만듭니다.
- ⚠️ **미션 제약사항 (4-4, 7장)**: `onclick="fetchProjects()"` 같은 인라인 이벤트 핸들러는 사용 금지입니다. 왜냐하면:
  1. HTML과 JavaScript가 뒤섞여 유지보수가 어려워집니다.
  2. 보안 위험(CSP 정책 위반 가능)이 있습니다.
  3. React 같은 현대 프레임워크에서는 아예 사용할 수 없는 패턴입니다.
- **해결법**: `innerHTML`로 HTML을 먼저 그린 다음 → `querySelector`로 방금 만든 버튼을 찾아 → `addEventListener`로 이벤트를 연결합니다. 이것이 **"관심사의 분리"** (HTML은 구조만, JS는 동작만) 원칙입니다.
- `if (retryBtn)`: 혹시 버튼을 못 찾았을 때 에러가 나지 않도록 안전장치입니다.

**빈 상태**:
- 성공적으로 데이터를 가져왔지만(`status === 'success'`), 필터링 결과 보여줄 프로젝트가 0개인 경우입니다.
- 예: "Java" 필터를 눌렀는데 Java 프로젝트가 없을 때.

**성공 상태**:
- `map()`으로 데이터 배열을 HTML 문자열 배열로 변환합니다.
- `.join('')`으로 배열을 하나의 문자열로 합칩니다.
- `target="_blank"`: 새 탭에서 링크를 엽니다.
- `rel="noopener noreferrer"`: `target="_blank"`의 보안 구멍을 막아줍니다. 새 탭에서 열린 페이지가 원래 페이지를 조종하는 것을 방지합니다.

### 5-4. Array 메서드의 쌍두마차: `filter`와 `map`

가져온 방대한 GitHub 데이터를 우리가 원하는 형태로 요리해 화면에 뿌려야 합니다.

```javascript
// 1. 포크한 저장소 걸러내기 (filter)
STATE.portfolio.allData = data.filter(repo => !repo.fork);

// 2. 언어별 필터링 (filter)
const filteredData = filter === 'all'
  ? allData
  : allData.filter(repo => repo.language === filter);

// 3. 카드 UI 만들기 (map)
const projectsHTML = filteredData.map(repo => {
  return `<article class="project-card">...</article>`;
}).join('');
```

#### 🔬 현미경 분석
- `filter()`: 거름망입니다. GitHub에서 가져온 수십 개의 프로젝트 배열 중, 내가 남의 코드를 복사해온 것(`fork`)이 **아닌(`!`)** 순수 내 프로젝트만 쏙쏙 걸러내어 새로운 배열을 만듭니다. **원본 배열은 건드리지 않습니다!**
- `map()`: 변신 터널입니다. 자바스크립트의 딱딱한 데이터 객체(`{name: 'my-project'}`)가 `map` 터널을 통과하면 화려한 HTML 코드 문자열로 찍혀 나옵니다.
- `.join('')`: `map`을 통과하고 나면 `[ "<article>..", "<article>.." ]` 처럼 쉼표(`,`)로 묶인 배열 형태입니다. `join('')`을 쓰면 이 쉼표들을 싹 없애고 하나의 거대한 덩어리 텍스트로 합쳐줍니다.
- `innerHTML`: 텅 비어있던 HTML 박스 안에, 방금 우리가 만들어낸 거대한 HTML 덩어리를 콱 쑤셔 넣어서 화면에 짠! 하고 나타나게 만듭니다.

### 5-5. 필터 버튼 이벤트

```html
<!-- HTML -->
<div class="projects__filter">
  <button class="filter-btn active" data-filter="all">All</button>
  <button class="filter-btn" data-filter="JavaScript">JavaScript</button>
  <button class="filter-btn" data-filter="Python">Python</button>
  <button class="filter-btn" data-filter="Java">Java</button>
</div>
```

```javascript
// JS
const filterBtns = document.querySelectorAll('.filter-btn');

filterBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    // UI 활성화 변경
    filterBtns.forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');

    // 상태 변경: 필터 값 갱신 후 렌더링
    STATE.portfolio.filter = e.target.getAttribute('data-filter');
    renderProjectsUI();
  });
});
```

#### 🔬 현미경 분석
- `data-filter="JavaScript"`: HTML의 `data-*` 속성은 개발자가 자유롭게 커스텀 데이터를 태그에 저장해두는 주머니입니다. `data-filter`에 필터링에 쓸 언어 이름을 넣어뒀습니다.
- `e.target`: 이벤트가 발생한 **바로 그 요소**를 가리킵니다. 즉, 사용자가 클릭한 그 버튼!
- `getAttribute('data-filter')`: 해당 버튼의 `data-filter` 주머니에서 값을 꺼냅니다.
- **상태 → 렌더링 흐름**: 버튼 클릭 → `STATE.portfolio.filter` 변경 → `renderProjectsUI()` 호출 → 화면이 알아서 업데이트. 또다시 단방향 흐름!

### 5-6. Intersection Observer (스크롤 애니메이션)

우리가 마우스를 스크롤할 때마다 요소들이 아래에서 위로 스르륵 나타나는 마법입니다.

```css
/* CSS */
.fade-in {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.fade-in.appear {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
// JS
const observerOptions = { root: null, rootMargin: '0px', threshold: 0.5 };
const observer = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('appear');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

document.querySelectorAll('.section__title, .about__img-wrapper, .about__info, .skills__card, .project-card, .contact__container').forEach(el => {
  el.classList.add('fade-in');
  observer.observe(el);
});
```

#### 🔬 현미경 분석
- **CSS 트릭**: `.fade-in` 클래스로 요소를 투명(opacity: 0)하게 만들고 30px 아래로 밀어놓습니다. `.appear` 클래스가 추가되면 원래 위치로 올라오면서 보이게 됩니다.
- 과거에는 스크롤 애니메이션을 위해 픽셀 단위로 스크롤 위치를 감시(`window.addEventListener('scroll')`)해야 했고, 이는 컴퓨터 자원을 엄청나게 갉아먹었습니다.
- `Intersection Observer`(교차 관찰자)는 최신 기술입니다. 브라우저가 직접 나서서 "이 요소가 사용자의 화면(뷰포트)에 들어왔어!"라고 알려주는 스마트한 망원경입니다.
- `threshold: 0.5`: **임계값**입니다. 요소의 50%가 화면에 보여야 발동합니다. 0이면 1px만 보여도 발동, 1.0이면 100% 다 보여야 발동합니다.
- `root: null`: 관찰 기준이 브라우저 뷰포트(화면 전체)임을 뜻합니다.
- `isIntersecting`: 망원경으로 보던 요소가 드디어 화면에 겹쳐서(교차해서) 보이기 시작했는지 묻는 속성입니다.
- `classList.add('appear')`: 화면에 보이면 `appear`라는 클래스를 딱 붙여줍니다. CSS에 미리 작성해둔 애니메이션 규칙에 의해 이 요소가 투명도 0에서 1로 변하며 나타납니다.
- `unobserve`: "한 번 나타났으면 이제 망원경 치워!"라는 뜻입니다. 스크롤을 위아래로 내릴 때마다 계속 애니메이션이 발동하면 정신 사납기 때문에, 단 한 번만 실행하도록 감시를 끕니다.

---

## 📖 Chapter 6: 문의 받기 (Contact Form · 유효성 검사 · 실시간 피드백)

사용자의 입력을 받고 폼 유효성을 검사하여 실제 서버로 날려 보내는 과정입니다. 이 챕터에서는 **`submit` 이벤트와 `input` 이벤트**를 모두 다룹니다.

### 6-1. `<form>`과 짝꿍 태그들 (`index.html`)

```html
<form id="contact-form" class="contact__form" action="https://formspree.io/f/xpqejrwb" method="POST">
  <div class="form__group">
    <label for="name" class="form__label">Name</label>
    <input type="text" id="name" name="name" class="form__input" placeholder="이름을 입력하세요">
    <span class="form__error" id="name-error">이름은 필수 항목입니다.</span>
  </div>

  <div class="form__group">
    <label for="email" class="form__label">Email</label>
    <input type="email" id="email" name="email" class="form__input" placeholder="이메일을 입력하세요">
    <span class="form__error" id="email-error">유효한 이메일을 입력해주세요.</span>
  </div>

  <div class="form__group">
    <label for="message" class="form__label">Message</label>
    <textarea id="message" name="message" class="form__input" rows="5" placeholder="메시지를 남겨주세요"></textarea>
    <span class="form__error" id="message-error">메시지는 필수 항목입니다.</span>
  </div>

  <button type="submit" class="btn btn--primary form__submit">Send Message</button>
  <div id="form-success" class="form__success">메시지가 성공적으로 전송되었습니다!</div>
</form>
```

#### 🔬 현미경 분석
- `<form>`: 사용자가 입력한 데이터를 어딘가로 전송하기 위한 봉투 역할을 합니다.
- `action`: 데이터를 받을 서버의 주소입니다. (여기서는 무료 메일 발송 서비스인 Formspree 서버 주소를 적습니다).
- `method="POST"`: 전송 방식입니다. 남들이 내 메일 내용이나 비밀번호를 주소창에서 쉽게 보지 못하게 편지봉투 안에 꽁꽁 숨겨서 보내라는(POST) 뜻입니다.
- `<label for="name">`과 `<input id="name">`: 이 둘은 영혼의 단짝입니다. `for`의 이름과 `id`의 이름이 똑같으면, 사용자가 좁은 텍스트 상자(`input`)를 힘들게 클릭하지 않고 글자(`label`, 'Name')만 눌러도 텍스트 상자에 깜빡이는 커서가 생깁니다. 모바일 환경에서 클릭하기 훨씬 편해지는 꿀팁입니다.
- `<span class="form__error">`: 에러 메시지를 담는 상자입니다. CSS에서 `display: none;`으로 숨겨두었다가, JS가 에러를 발견하면 `display: block;`으로 보이게 만듭니다.
- `<textarea>`: `<input>`과 달리 여러 줄의 텍스트를 입력할 수 있는 큰 상자입니다. `rows="5"`는 기본 높이를 5줄로 설정합니다.
- `placeholder="이름을 입력하세요"`: 아직 아무것도 입력하지 않았을 때 연하게 보이는 안내 텍스트입니다. 입력을 시작하면 사라집니다.

### 6-2. `showError`와 `clearError` — 에러 표시/숨김 함수

```javascript
const validateEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());
};

const showError = (inputElement, errorElementId, message) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.add('invalid');
  errorEl.textContent = message;
  errorEl.style.display = 'block';
};

const clearError = (inputElement, errorElementId) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.remove('invalid');
  errorEl.style.display = 'none';
};
```

#### 🔬 현미경 분석

**`validateEmail` — 이메일 정규식 해부**:
```
/^[^\s@]+@[^\s@]+\.[^\s@]+$/
```
정규식(Regular Expression)은 문자열 패턴을 검사하는 마법의 주문입니다. 한 토막씩 해부하면:

| 토막 | 의미 |
|------|------|
| `^` | 문자열의 시작 |
| `[^\s@]+` | 공백(`\s`)과 `@`가 **아닌** 문자가 1개 이상 |
| `@` | @ 기호가 반드시 있어야 함 |
| `[^\s@]+` | @ 뒤에 다시 공백과 @가 아닌 문자 1개 이상 (도메인명) |
| `\.` | 점(`.`)이 반드시 있어야 함 (`.`을 `\.`로 이스케이프) |
| `[^\s@]+` | 점 뒤에 다시 문자 1개 이상 (com, kr 등 최상위 도메인) |
| `$` | 문자열의 끝 |

즉, `abc@def.ghi` 형태만 통과시킵니다. `abc`, `@abc`, `abc@`, `abc@def` 같은 것은 모두 실패합니다.

**`showError` 함수**: 
1. 입력 필드에 `invalid` 클래스를 추가합니다 → CSS의 `.form__input.invalid { border-color: red; }`가 발동해서 테두리가 빨갛게 변합니다.
2. 에러 메시지 텍스트를 설정합니다.
3. `display: block`으로 에러 메시지를 보이게 합니다.

**`clearError` 함수**: `showError`의 정확한 반대 동작입니다. `invalid` 클래스를 제거하고 에러 메시지를 숨깁니다.

### 6-3. 폼 제출 시 유효성 검사 (`submit` 이벤트)

```javascript
contactForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  let isValid = true;

  if (!nameInput.value.trim()) {
    showError(nameInput, 'name-error', '이름은 필수 항목입니다.');
    isValid = false;
  } else { clearError(nameInput, 'name-error'); }

  if (!emailInput.value.trim()) {
    showError(emailInput, 'email-error', '이메일은 필수 항목입니다.');
    isValid = false;
  } else if (!validateEmail(emailInput.value)) {
    showError(emailInput, 'email-error', '유효한 이메일 형식이 아닙니다.');
    isValid = false;
  } else { clearError(emailInput, 'email-error'); }

  if (!messageInput.value.trim()) {
    showError(messageInput, 'message-error', '메시지는 필수 항목입니다.');
    isValid = false;
  } else { clearError(messageInput, 'message-error'); }

  if (isValid) {
    try {
      const response = await fetch(contactForm.action, {
        method: 'POST',
        body: new FormData(contactForm),
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        contactForm.reset();
        formSuccess.style.display = 'block';
        setTimeout(() => formSuccess.style.display = 'none', 5000);
      } else {
        alert('이메일 전송에 실패했습니다.');
      }
    } catch (error) {
      alert('네트워크 오류가 발생했습니다.');
    }
  }
});
```

#### 🔬 현미경 분석
- `submit` 이벤트: `click`이 아닙니다. 폼 안에서 엔터를 치거나 전송 버튼을 누르는 모든 '제출' 행위를 포착합니다.
- **`e.preventDefault()` (초핵심)**: `<form>`은 원래 전송되는 순간 **페이지를 새로고침** 해버리는 기본 성질을 가지고 있습니다. 요즘 유행하는 싱글 페이지 애플리케이션(SPA)이나 깔끔한 사이트에서는 화면 깜빡임이 생기면 촌스럽기 때문에, 자바스크립트가 개입해서 "원래 네가 하려던 새로고침 행동, 멈춰!"라고 제지하는 것입니다.
- `let isValid = true;`: 문지기 통과 카드입니다. 하나라도 검사에 걸리면 `false`로 바뀝니다.
- `.value.trim()`: `value`는 사용자가 텍스트 상자에 친 글자입니다. `trim()`은 사용자가 장난친다고 스페이스바만 쳐서 여백을 만든 것을 가위로 싹둑 잘라냅니다. 자르고 났더니 빈칸(`!`)이라면? 이름을 안 썼다고 에러를 띄웁니다.
- **이메일 검사의 2단 구조**: 먼저 빈칸인지 확인 → 빈칸이 아니면 형식이 맞는지 확인. 순서가 중요합니다!
- `new FormData(contactForm)`: 폼에 입력된 모든 데이터를 한 방에 수거해서 택배 박스(FormData 객체)에 담습니다.
- `contactForm.reset()`: 전송 성공 후 모든 입력 필드를 초기화(비우기)합니다.
- `setTimeout(() => formSuccess.style.display = 'none', 5000)`: 성공 메시지를 5초 후에 자동으로 숨깁니다.

### 6-4. 실시간 유효성 검사 (`input` 이벤트)

미션 요구사항 4-4에서 `click`, `submit`, `scroll`, **`input`** 이벤트를 모두 다뤄야 합니다. `input` 이벤트는 사용자가 **글자를 치는 매 순간** 발동합니다.

```javascript
// 실시간 유효성 검사 (input 이벤트 처리 — 미션 4-4 요구사항)
nameInput.addEventListener('input', () => {
  if (nameInput.value.trim()) {
    clearError(nameInput, 'name-error');
  }
});

emailInput.addEventListener('input', () => {
  if (emailInput.value.trim() && validateEmail(emailInput.value)) {
    clearError(emailInput, 'email-error');
  }
});

messageInput.addEventListener('input', () => {
  if (messageInput.value.trim()) {
    clearError(messageInput, 'message-error');
  }
});
```

#### 🔬 현미경 분석
- **`input` 이벤트 vs `submit` 이벤트**: `submit`은 "전송" 버튼을 눌러야 발동하지만, `input`은 사용자가 **한 글자를 칠 때마다** 발동합니다.
- **UX 개선 효과**: 사용자가 폼을 제출해서 "이름이 비어있습니다!" 에러를 받았다고 가정합시다. 이름을 타이핑하기 시작하면, `input` 이벤트가 즉시 감지해서 빨간 에러 메시지를 실시간으로 사라지게 만듭니다. "내가 올바르게 입력하고 있구나"라는 즉각적인 피드백을 줌으로써 사용자 경험(UX)이 크게 개선됩니다.
- **왜 `clearError`만 하고 `showError`는 안 하는가?**: 타이핑하는 매 순간 "아직 이메일 형식이 안 맞아!"라고 경고를 띄우면 오히려 성가시기 때문입니다. 에러 표시는 제출(`submit`) 시점에만, 에러 해제는 실시간(`input`)으로 하는 것이 가장 친절한 UX 패턴입니다.
- **상태 → 렌더링 흐름 3번의 실체**: `input 이벤트 발생 → 유효성 상태 판단 → clearError()로 에러 UI 업데이트`. 이것이 미션이 요구하는 "이벤트 → 상태 변경 → DOM 업데이트" 패턴의 세 번째 사례입니다.

---

## 📖 Chapter 7: 반응형 설계와 모바일 퍼스트

### 7-1. 모바일 퍼스트란? (왜 `min-width`인가?)

웹 디자인에서 반응형을 구현하는 두 가지 철학이 있습니다:

| 접근법 | 미디어 쿼리 | 기본 스타일 대상 | 확장 방향 |
|--------|-------------|-----------------|-----------|
| **데스크톱 퍼스트** | `max-width` | 데스크톱 (넓은 화면) | 좁은 쪽으로 줄여나감 |
| **모바일 퍼스트** ✅ | `min-width` | 모바일 (좁은 화면) | 넓은 쪽으로 늘려나감 |

**왜 모바일 퍼스트를 써야 하는가?**

1. **전 세계 웹 트래픽의 60% 이상이 모바일**입니다. 가장 많은 사용자가 보는 화면을 기본으로 잡는 것이 합리적입니다.
2. **"추가"가 "삭제"보다 쉽습니다**. 모바일에서 기본 레이아웃을 잡고, 화면이 넓어지면 기능을 "추가"하는 것이, 데스크톱에서 복잡하게 만든 후 모바일로 "삭제/축소"하는 것보다 훨씬 깔끔합니다.
3. **미션 요구사항(4-3)**에서 명시적으로 "모바일 퍼스트로 작성한다"고 되어있습니다.

### 7-2. 실제 CSS 코드 해부

우리 CSS의 구조를 큰 그림으로 보면:

```
[기본 스타일 = 모바일]     ← 미디어 쿼리 없이 바로 작성
        ↓
@media (min-width: 768px)  ← 태블릿 이상에서 "추가"되는 스타일
        ↓
@media (min-width: 1024px) ← 데스크톱 이상에서 "추가"되는 스타일
```

#### 모바일 기본 스타일 (미디어 쿼리 바깥)

```css
/* 햄버거 메뉴: 모바일에서는 슬라이드 메뉴로 동작 */
.nav__menu {
  position: fixed;
  top: var(--nav-height);
  right: -100%;       /* 화면 오른쪽 밖에 숨김 */
  width: 70%;
  height: calc(100vh - var(--nav-height));
  transition: right 0.3s ease;
}

.nav__menu.active {
  right: 0;           /* JS가 active 붙이면 화면 안으로 슬라이드 */
}

.nav__toggle {
  display: flex;       /* 모바일에서 햄버거 아이콘 보임 */
}

.hero__title {
  font-size: 2.2rem;   /* 모바일에서는 작은 글씨 */
}

.hero__buttons {
  flex-direction: column;  /* 모바일에서 버튼 세로 배치 */
}

.section {
  padding: 60px 0;     /* 모바일에서는 여백 줄임 */
}
```

#### 🔬 현미경 분석
- `right: -100%;`: 화면 오른쪽 밖으로 100% 밀어서 완전히 숨깁니다. `active` 클래스가 붙으면 `right: 0`으로 되돌아와 화면에 나타납니다. `transition`이 있으므로 슬라이드 효과!
- `calc(100vh - var(--nav-height))`: 전체 화면 높이(100vh)에서 네비바 높이를 뺀 나머지만큼 메뉴 높이를 잡습니다. `calc()`은 CSS 안에서 수학 계산을 할 수 있는 함수입니다.
- `display: flex;` (nav__toggle): 모바일에서 햄버거 아이콘이 보입니다. (위쪽 기본 정의에서 `display: none;`이지만, 여기서 `display: flex;`로 덮어씁니다.)

#### 태블릿 이상 (768px 이상)

```css
@media screen and (min-width: 768px) {
  .nav__menu {
    position: static;          /* 고정 위치 해제 → 문서 흐름에 따라 배치 */
    width: auto;
    height: auto;
    background-color: transparent;
    flex-direction: row;
    padding: 0;
    box-shadow: none;
  }

  .nav__list {
    flex-direction: row;        /* 메뉴 항목 가로 배치 */
    gap: 2rem;
  }

  .nav__toggle {
    display: none;              /* 햄버거 아이콘 숨김 */
  }

  .hero__title {
    font-size: 3rem;            /* 큰 화면에서는 큰 글씨 */
  }

  .hero__buttons {
    flex-direction: row;        /* 버튼 가로 배치 */
  }

  .section {
    padding: 100px 0;           /* 넓은 화면에서는 여백 증가 */
  }
}
```

#### 🔬 현미경 분석
- `@media screen and (min-width: 768px)`: "화면(screen) 너비가 **최소 768px 이상**일 때, 이 안의 스타일을 적용하라"는 뜻입니다. 모바일(768px 미만)에서는 이 블록이 완전히 무시됩니다.
- `position: static;`: 모바일에서 `fixed`(화면에 고정)였던 메뉴를 원래의 문서 흐름으로 돌려놓습니다. 태블릿 이상에서는 메뉴가 헤더 안에 자연스럽게 자리잡습니다.
- `display: none;` (nav__toggle): 태블릿 이상에서는 햄버거 아이콘이 필요 없으므로 숨깁니다.

#### 햄버거 → X 버튼 변신 애니메이션

```css
.nav__toggle.active .bar:nth-child(1) {
  transform: translateY(8px) rotate(45deg);
}

.nav__toggle.active .bar:nth-child(2) {
  opacity: 0;
}

.nav__toggle.active .bar:nth-child(3) {
  transform: translateY(-8px) rotate(-45deg);
}
```

#### 🔬 현미경 분석
- `nth-child(1)`: 첫 번째 막대입니다. 아래로 8px 이동 + 45도 회전 → `╲` 모양이 됩니다.
- `nth-child(2)`: 가운데 막대입니다. 투명하게 사라집니다.
- `nth-child(3)`: 세 번째 막대입니다. 위로 8px 이동 + -45도 회전 → `╱` 모양이 됩니다.
- 결과: ☰ (삼선) → ✕ (X자) 변신! `transition: all 0.3s ease;`가 걸려있으므로 부드럽게 변합니다.

---

## 📖 Chapter 8: 배포와 자기 점검

### 8-1. GitHub Pages 배포

GitHub Pages는 GitHub 저장소에 올린 HTML/CSS/JS 파일을 무료로 웹사이트로 호스팅(공개)해주는 서비스입니다.

배포 과정:
1. GitHub에 저장소를 만들고 코드를 push합니다.
2. 저장소의 **Settings → Pages** 메뉴로 이동합니다.
3. Branch를 `main`으로 설정하고 저장합니다.
4. 몇 분 후 `https://사용자이름.github.io/저장소이름/portfolio/` 형태의 URL이 생성됩니다.

### 8-2. 전체 미션 체크리스트

**프로젝트 구성 (4-1)**
- [x] `index.html`, `css/`, `js/`, `images/` 폴더 구조 분리
- [x] 외부 스타일시트와 JavaScript 파일을 HTML에 올바르게 연결
- [x] `defer` 속성으로 JS 연결

**HTML 구조 (4-2)**
- [x] `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>` 시맨틱 태그 사용
- [x] Hero / About / Skills / Projects / Contact / Footer 섹션 모두 포함
- [x] 앵커 링크로 각 섹션 이동 가능
- [x] 모든 이미지에 `alt` 속성
- [x] 폼 `<label>` - `<input>` 의 `for`-`id` 매칭

**CSS 스타일링 (4-3)**
- [x] CSS 변수(`:root`)로 색상, 폰트, 간격 정의
- [x] 다크 모드용 변수 별도 정의 (`[data-theme="dark"]`)
- [x] 네비게이션: Flexbox 사용
- [x] Projects/Skills 카드: Grid 사용 (`auto-fit`, `minmax`)
- [x] **모바일 퍼스트** (`min-width`) 미디어 쿼리
- [x] 브레이크포인트: 768px (태블릿), 1024px (데스크톱)
- [x] hover 효과 + transition + box-shadow

**JavaScript (4-4)**
- [x] `defer`로 스크립트 연결
- [x] `const`, `let`만 사용 (`var` 금지)
- [x] `onclick` 미사용 → `addEventListener`로 이벤트 연결
- [x] `querySelector`, `querySelectorAll`로 요소 선택
- [x] `textContent`, `innerHTML`로 내용 변경
- [x] `classList.add/remove/toggle`로 클래스 조작
- [x] `click`, `submit`, `scroll`, `input` 이벤트 모두 다룸
- [x] `event.preventDefault()`로 기본 동작 방지

**인터랙션 (4-5)**
- [x] 햄버거 메뉴 토글 (`classList.toggle('active')`)
- [x] 부드러운 스크롤 (`scroll-behavior: smooth`)
- [x] 스크롤 탑 버튼 (기준: **300px**)
- [x] 네비게이션 스타일 변경 (기준: **60px**)
- [x] 다크 모드 (localStorage 저장, 새로고침 유지)
- [x] 스크롤 애니메이션 (Intersection Observer, threshold: **0.5**)

**폼 UX (4-6)**
- [x] 이름, 이메일, 메시지 필수값 검증
- [x] 이메일 형식 검증 (정규식)
- [x] 에러 메시지가 입력 필드 근처에 표시
- [x] `e.preventDefault()` + 성공 메시지 표시

**ES6+ (4-7)**
- [x] 화살표 함수 (`const renderTheme = () => {...}`)
- [x] 템플릿 리터럴 (`` `${repo.name}` ``)
- [x] 구조분해 할당 (`const { status, allData, filter, errorMsg } = STATE.portfolio`)
- [x] `map()`, `filter()`, `forEach()`

**비동기 처리 (4-8)**
- [x] `fetch` + `async/await`로 GitHub API 호출
- [x] 4가지 상태 UI: 로딩/성공/에러/빈 데이터
- [x] `try/catch` 에러 처리
- [x] 레이트 리밋(403) 에러 처리

**상태 관리 (4-9)**
- [x] STATE 중앙 관리 객체
- [x] "이벤트 → 상태 변경 → 화면 업데이트" 흐름 4가지 구현

**보너스 과제 (5장)**
- [x] 5-1. 프로젝트 언어별 필터링 (`array.filter()`)
- [x] 5-2. 타이핑 효과 (`setTimeout` 재귀)
- [x] 5-3. Formspree 연동 (⚠️ action URL 교체 필요)
- [x] 5-4. 시스템 다크 모드 감지 (`prefers-color-scheme`)

### 8-3. "다른 초심자에게 설명하기" 연습 문제

미션의 궁극적 목표는 **스스로 설명할 수 있는 것**입니다. 아래 질문에 자신의 말로 답해보세요:

1. **시맨틱 태그**: 왜 `<div>`만으로 전체를 감싸면 안 되나요? `<header>`, `<nav>`, `<section>`을 쓰면 누가 어떤 이점을 얻나요?
2. **Flexbox vs Grid**: 네비게이션 메뉴에는 Flexbox를, Projects 카드에는 Grid를 쓴 이유는 무엇인가요?
3. **DOM 조작 흐름**: 다크 모드 토글 버튼을 누르면, JavaScript 코드에서 어떤 순서로 일이 벌어지나요? (이벤트 → 상태 → DOM)
4. **`onclick` 금지**: 왜 HTML에 `onclick="..."` 대신 JS에서 `addEventListener`를 써야 하나요?
5. **비동기 처리**: `fetch`로 GitHub 데이터를 가져올 때, 왜 `async/await`가 필요하고, `try/catch`를 왜 감싸야 하나요?
6. **4가지 상태 UI**: 사용자가 Projects 섹션을 볼 때, 어떤 4가지 화면이 보일 수 있나요? 각각 언제 나타나나요?
7. **모바일 퍼스트**: `max-width`와 `min-width` 미디어 쿼리의 차이는 무엇이고, 왜 `min-width`를 써야 하나요?
8. **`input` 이벤트**: 폼에서 `submit`만으로도 유효성 검사가 가능한데, 왜 `input` 이벤트를 추가했나요? 사용자 경험에 어떤 차이가 있나요?
9. **STATE 패턴**: `STATE` 객체 없이 변수를 따로따로 만들어도 동작은 합니다. 그런데 왜 굳이 하나로 묶었을까요? React와 어떤 관계가 있나요?
10. **구조분해 할당**: `const { status, allData, filter, errorMsg } = STATE.portfolio;` 이 한 줄이 없으면 코드가 어떻게 바뀌나요?

---

> 🎉 **마무리**
> 
> 고생하셨습니다! `index.html`의 뼈대부터 `main.js`의 심장 박동, `style.css`의 모바일 퍼스트 설계까지, 한 줄도 건너뛰지 않고 모든 코드의 존재 이유를 현미경으로 뜯어보았습니다. 
> 
> 이 문서의 흐름을 본인의 언어로 말할 수 있게 된다면, 바닐라 자바스크립트 포트폴리오를 넘어 리액트 등 어떤 모던 프론트엔드 환경에서도 자신 있게 코드를 짜고 설명하실 수 있을 것입니다!
