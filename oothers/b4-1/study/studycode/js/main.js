// ==========================================
// [JavaScript의 역할: 웹페이지에 동적 생명력(Behavior) 불어넣기]
// JS는 사용자의 조작(클릭, 스크롤, 키보드 입력 등)을 감지하고, 서버에서 데이터를 받아와
// 화면(DOM)을 실시간으로 다시 그리고 갱신하는 브라우저의 두뇌 역할을 담당합니다.
//
// * 실행 타이밍: 이 파일은 HTML에서 <script defer> 속성으로 연결되었습니다.
//   브라우저가 HTML 태그 파싱(DOM 빌드)을 완전히 끝내어 안전하게 요소를 조작할 수 있는 시점에 
//   브라우저 엔진에 의해 자동으로 호출되어 순차적으로 실행됩니다.
// ==========================================


// ==========================================
// 0. 중앙 집중식 상태(STATE) 관리 객체
// ==========================================
// [상태(State)란 무엇인가?]
// "지금 이 순간 웹 애플리케이션이 기억하고 있어야 하는 모든 정보(데이터)의 현재 값"입니다.
// 흩어진 변수들(theme, projects 데이터 등)을 하나의 거대한 객체에 모아 보관합니다.
//
// [STATE 기반 렌더링 (단방향 데이터 흐름의 시작)]
// 1. 사용자 행동 또는 API 이벤트 발생 -> 2. STATE 데이터 업데이트 -> 3. STATE를 토대로 화면을 새로 그리는 함수(render) 실행.
// 이 패턴은 화면의 상태 일관성을 철저하게 보장하며, 현대 프론트엔드 프레임워크(React, Vue 등)의 동작 핵심 원리입니다.
const STATE = {
  // 테마 상태: 로컬 스토리지에 저장된 값이 없다면, 사용자의 OS 다크모드 설정 여부를 감지해 초기값을 잡습니다.
  theme: localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),

  // 포트폴리오(프로젝트 목록) 관련 상태들
  portfolio: {
    allData: [],      // GitHub API를 통해 받아올 가공되지 않은 프로젝트 원본 데이터 배열
    filter: 'all',    // 사용자가 선택한 현재 언어 필터 ('all', 'JavaScript', 'Python' 등)
    status: 'idle',   // 현재 네트워크 통신 상태 ('idle': 대기, 'loading': 로딩중, 'success': 로딩성공, 'error': 로딩에러)
    errorMsg: ''      // 통신 에러 발생 시 사용자에게 노출할 에러 메시지 내용
  }
};


// ==========================================
// 1. 다크 모드 처리 (상태 기반 렌더링)
// ==========================================
// [DOM 선택(Querying)]
// document.getElementById() 또는 querySelector()를 사용해 HTML 뼈대에 새겨진 요소를 가져와 JS 객체로 다룰 수 있게 만듭니다.
const themeToggleBtn = document.getElementById('theme-toggle');
const themeIcon = themeToggleBtn.querySelector('.icon');
const htmlElement = document.documentElement; // <html> 태그를 가리킵니다.

// [렌더링 함수: STATE의 값만 바라보고 UI를 동기화하는 비주얼 가이드]
const renderTheme = () => {
  if (STATE.theme === 'dark') {
    // HTML 최상단 태그에 data-theme="dark" 속성을 심습니다. 
    // 그러면 CSS 파일 내의 [data-theme="dark"] 선택자가 활성화되어 색상 변수(Variables)들이 다크모드 색상으로 강제 덮어쓰기됩니다.
    htmlElement.setAttribute('data-theme', 'dark');
    themeIcon.textContent = '☀️'; // 토글 버튼의 아이콘을 태양으로 바꿉니다.
  } else {
    htmlElement.setAttribute('data-theme', 'light');
    themeIcon.textContent = '🌙'; // 토글 버튼의 아이콘을 달로 바꿉니다.
  }
};

// 초기 테마 실행: 사용자가 페이지에 진입하자마자 저장된 테마 값으로 화면을 먼저 세팅합니다.
renderTheme();

// [이벤트 리스너(Event Listener): 사용자의 행동 감시]
// themeToggleBtn 요소를 클릭(click)했을 때 전달한 함수가 실행되도록 브라우저 이벤트 루프에 등록합니다.
themeToggleBtn.addEventListener('click', () => {
  // 1. 데이터(STATE) 변경
  STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';

  // 로컬 스토리지(브라우저 내장 데이터베이스)에 저장하여 브라우저를 새로고침하거나 종료 후 재진입해도 다크모드가 유지되게 만듭니다.
  localStorage.setItem('theme', STATE.theme);

  // 2. 변경된 상태를 기반으로 즉시 화면 렌더링 업데이트
  renderTheme();
});


// ==========================================
// 2. 네비게이션 및 햄버거 메뉴 처리 (클래스 토글을 이용한 CSS 렌더링 제어)
// ==========================================
const navToggle = document.getElementById('nav-toggle');
const navMenu = document.getElementById('nav-menu');
const navLinks = document.querySelectorAll('.nav__link'); // 조건에 맞는 요소를 모두 긁어모아 유사 배열(NodeList)로 만듭니다.
const header = document.querySelector('.header');

// 모바일 햄버거 버튼 클릭 이벤트
navToggle.addEventListener('click', () => {
  // classList.toggle: active 클래스가 없다면 붙이고, 있다면 떼어냅니다.
  // CSS에 미리 정의된 '.nav__toggle.active'와 '.nav__menu.active' 스타일이 활성화/비활성화됩니다.
  navToggle.classList.toggle('active');
  navMenu.classList.toggle('active');
});

// 모바일 메뉴 안의 링크(Home, About 등) 클릭 시 메뉴바 닫기
navLinks.forEach(link => {
  link.addEventListener('click', () => {
    // 메뉴 링크를 눌러 해당 섹션으로 이동하고 나면 열려있던 메뉴 창을 닫아줍니다.
    navToggle.classList.remove('active');
    navMenu.classList.remove('active');
  });
});

// [스크롤 이벤트 최적화에 대한 이해]
// 브라우저는 사용자가 스크롤할 때 미세한 스크롤 단위마다 scroll 이벤트를 매우 빈번하게 발생시킵니다.
// 따라서 scroll 이벤트 핸들러 내부에서는 복잡한 계산이나 레이아웃 연산(Reflow)을 최소화해야 버벅임이 없습니다.
window.addEventListener('scroll', () => {
  // window.scrollY: 현재 사용자가 위에서부터 아래로 얼마나 스크롤했는지의 픽셀(px) 거리입니다.
  if (window.scrollY >= 60) {
    header.classList.add('scrolled'); // 헤더 아래에 그림자를 그리기 위해 scrolled 클래스 주입
  } else {
    header.classList.remove('scrolled');
  }
});


// ==========================================
// 3. 스크롤 탑 버튼 (Scroll Top Button)
// ==========================================
const scrollTopBtn = document.getElementById('scroll-top');

window.addEventListener('scroll', () => {
  if (window.scrollY >= 300) {
    scrollTopBtn.classList.add('show'); // 300px 이상 내려오면 버튼 노출
  } else {
    scrollTopBtn.classList.remove('show');
  }
});

scrollTopBtn.addEventListener('click', (e) => {
  // [e.preventDefault()의 원리]
  // HTML의 기본 앵커 링크 <a> 태그는 클릭 시 href="#" 경로로 화면을 강제로 홱 이동(새로고침 느낌)시키는 기본 특성이 있습니다.
  // e.preventDefault()는 이러한 브라우저의 내장 기본 동작을 멈추고, 우리가 JS로 정의한 동작만 일어나도록 차단해 줍니다.
  e.preventDefault();

  // 브라우저 화면의 스크롤 위치를 부드럽게(smooth) 최상단(top: 0)으로 이동시킵니다.
  window.scrollTo({ top: 0, behavior: 'smooth' });
});


// ==========================================
// 4. 스크롤 애니메이션 (Intersection Observer - 뷰포트 감지)
// ==========================================
// [Intersection Observer API: 웹 화면 최적화의 숨은 공신]
// 전통적인 scroll 이벤트 방식은 스크롤 할 때마다 요소의 위치 좌표를 매번 계산해야 해서 브라우저에 큰 부하를 줍니다.
// 반면, Intersection Observer는 "지정한 요소가 브라우저 화면(Viewport)에 일정 수준 이상 노출되었는지"를 
// 브라우저 자체의 효율적인 백그라운드 엔진이 감시하다가, 그 진입 시점에만 콜백 함수를 비동기로 호출해 줍니다. 성능이 대단히 우수합니다.

// threshold: 0.5 -> 타겟 요소가 50% 이상 화면에 노출되었을 때 콜백을 트리거하라는 설정입니다.
const observerOptions = { root: null, rootMargin: '0px', threshold: 0.5 };

const observer = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    // entry.isIntersecting: 감시 대상이 화면 안에 진입(교차)했는지 여부(true/false)
    if (entry.isIntersecting) {
      // 화면에 드러나면 CSS에서 opacity: 0; transform: translateY(30px);로 대기 중이던 요소에
      // 'appear' 클래스를 추가해 주어 서서히 투명해지며 위로 올라오는 CSS 트랜지션을 실행시킵니다.
      entry.target.classList.add('appear');

      // [리소스 관리: unobserve]
      // 한 번 애니메이션이 일어나서 그려진 요소는 더 이상 감시할 필요가 없으므로 관찰을 해제해 메모리와 연산 자원을 아낍니다.
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// 감시할 요소들을 전부 선택하여 관찰자(observer)에게 알려줍니다.
document.querySelectorAll('.section__title, .about__img-wrapper, .about__info, .skills__card, .project-card, .contact__container').forEach(el => {
  el.classList.add('fade-in'); // 초기 페이드인 대기 클래스 강제 부여
  observer.observe(el);        // 관찰 리스트에 등록
});


// ==========================================
// 5. 타이핑 효과 (Typewriter Effect)
// ==========================================
const typingElement = document.getElementById('typing-text');
const actualText = "안녕하세요, 저는 feelosophysics입니다.";
let charIndex = 0;

// [재귀적 setTimeout 타이핑 구현]
// 글자 한 자 한 자를 span 태그의 textContent에 더해주고(100ms 지연),
// 자기 자신(typeText)을 다시 호출하여 다음 글자를 타이핑하는 원리입니다.
const typeText = () => {
  if (charIndex < actualText.length) {
    typingElement.textContent += actualText.charAt(charIndex);
    charIndex++;
    // 100ms(0.1초) 뒤에 typeText 함수를 다시 실행시킵니다.
    setTimeout(typeText, 100);
  }
};
// 첫 화면 로드 완료 시 500ms(0.5초) 뒤 타이핑 애니메이션이 시작되도록 설정합니다.
setTimeout(typeText, 500);


// ==========================================
// 6. GitHub API 연동 및 필터링 (상태 기반 렌더링)
// ==========================================
const GITHUB_USERNAME = 'feelosophysics';
const projectsContainer = document.getElementById('projects-container');
const filterBtns = document.querySelectorAll('.filter-btn');

// [UI 렌더링 함수: 오직 STATE 데이터에만 종속되어 동작함]
// 이 함수는 호출되는 시점의 STATE.portfolio 정보를 100% 반영하여 HTML 문자열을 빌드하고 웹 브라우저 DOM을 변경합니다.
const renderProjectsUI = () => {
  const { status, allData, filter, errorMsg } = STATE.portfolio;

  // Case 1: 로딩 중 상태
  if (status === 'loading') {
    // innerHTML은 지정한 태그의 자식 태그들을 전달한 HTML 구조(문자열)로 완전히 통째로 덮어씁니다.
    projectsContainer.innerHTML = '<div class="projects__loading">프로젝트를 불러오는 중입니다...</div>';
    return;
  }

  // Case 2: API 통신 에러 발생 상태
  if (status === 'error') {
    projectsContainer.innerHTML = `
      <div class="projects__error">
        <p>${errorMsg}</p>
        <button class="btn btn--outline" id="retry-btn">다시 시도</button>
      </div>
    `;

    // [동적 이벤트 연결]
    // 렌더링 시점에 새로 생성된 '#retry-btn' 버튼 요소를 획득하여 다시 불러오는(fetchProjects) 이벤트를 연결합니다.
    const retryBtn = projectsContainer.querySelector('#retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', fetchProjects);
    }
    return;
  }

  // Case 3: 로딩 성공 상태 - 선택된 언어 필터에 따라 데이터 가공
  // filter === 'all' 이면 원본 데이터 전체를 사용하고, 
  // 그 외의 언어('Python' 등)면 repo.language 값이 선택한 언어와 일치하는 것만 걸러냅니다(filter).
  const filteredData = filter === 'all'
    ? allData
    : allData.filter(repo => repo.language === filter);

  // Case 3-1: 필터링 결과 표시할 카드가 없을 때
  if (status === 'success' && filteredData.length === 0) {
    projectsContainer.innerHTML = '<div class="projects__empty">표시할 프로젝트가 없습니다.</div>';
    return;
  }

  // Case 3-2: 필터링된 배열 데이터를 HTML 카드 목록으로 변환(Mapping)
  // 배열.map(): 각 요소를 받아 HTML 문자열 템플릿으로 변환한 뒤 새 배열로 만듭니다.
  // 배열.join(''): HTML 배열 요소들을 하나의 긴 텍스트로 합쳐 브라우저가 파싱할 수 있게 만듭니다.
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

  // 최종 카드로 컨테이너 내부 렌더링 교체
  projectsContainer.innerHTML = projectsHTML;
};

// [async/await와 fetch를 이용한 비동기 통신]
// async/await: 백그라운드에서 실행되는 비동기 작업(서버에서 데이터를 받아오는 통신)을 
// 마치 동기적인 코드(위에서 아래로 멈추었다 실행되는 형태)처럼 직관적으로 작성할 수 있도록 해주는 JS 최신 문법입니다.
const fetchProjects = async () => {
  // 1. 상태 변경: 로딩 중
  STATE.portfolio.status = 'loading';
  renderProjectsUI(); // 화면 렌더링 호출

  try {
    // 1. fetch가 지정된 주소로 HTTP GET 요청을 보내고 응답(Promise)을 반환할 때까지 await로 대기합니다.
    const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated`);

    // 응답코드가 200번대 성공이 아니면 에러 발생시킴
    if (!response.ok) {
      throw new Error(response.status === 403 ? 'API 호출 제한 초과' : '데이터를 불러올 수 없습니다.');
    }

    // 2. 서버가 넘겨준 스트림 데이터를 JSON 객체로 파싱할 때까지 다시 한 번 await로 대기합니다.
    const data = await response.json();

    // 2. 상태 변경: 성공
    // fork된 프로젝트(다른 사람 것을 복제해온 레포지토리)는 거르고 본인 레포지토리만 가져와 상태에 보관합니다.
    STATE.portfolio.allData = data.filter(repo => !repo.fork);
    STATE.portfolio.status = 'success';
    renderProjectsUI(); // 로딩이 완료된 최신 성공 상태로 화면 렌더링 호출

  } catch (error) {
    // 3. 상태 변경: 에러 발생
    STATE.portfolio.status = 'error';
    STATE.portfolio.errorMsg = error.message;
    renderProjectsUI(); // 에러 화면 렌더링 호출
  }
};

// [필터 버튼 클릭 이벤트 등록]
filterBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    // 1. UI 시각적 활성화 변경 (기존 액티브 버튼에서 클래스 뺏고 클릭된 버튼에 줌)
    filterBtns.forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');

    // 2. 상태 변경: 필터 값 갱신 후 화면을 다시 그립니다.
    // HTML에 작성해 둔 사용자 정의 데이터 속성 'data-filter' 값을 가져옵니다.
    STATE.portfolio.filter = e.target.getAttribute('data-filter');
    renderProjectsUI();
  });
});

// 포트폴리오 사이트가 로드되자마자 서버로부터 프로젝트를 받아오도록 함수를 최초 실행합니다.
fetchProjects();


// ==========================================
// 7. 폼 유효성 검사 및 전송 (Contact Form Validation)
// ==========================================
const contactForm = document.getElementById('contact-form');
const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const messageInput = document.getElementById('message');
const formSuccess = document.getElementById('form-success');

// 정규표현식(Regex)을 이용한 이메일 포맷 검사
const validateEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());
};

// [유효성 실패: 사용자 에러 표시]
const showError = (inputElement, errorElementId, message) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.add('invalid'); // 테두리를 빨갛게 하는 CSS 클래스('.invalid') 추가
  errorEl.textContent = message;          // 오류 설명 문구 주입
  errorEl.style.display = 'block';         // 기본 숨겨진 경고 메시지를 노출시킴
};

// [유효성 통과: 에러 리셋]
const clearError = (inputElement, errorElementId) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.remove('invalid');
  errorEl.style.display = 'none'; // 경고 메시지 숨김
};

// 폼 서브밋(Submit: 전송하기) 이벤트
contactForm.addEventListener('submit', async (e) => {
  e.preventDefault(); // Formspree 전송 시 브라우저가 화면을 다른 페이지로 새로고침해 버리는 기본동작 방지
  let isValid = true;

  // 이름 검사
  // .value.trim(): 입력창에 쓴 글자 양끝의 불필요한 공백을 깎아낸 알맹이 텍스트입니다.
  if (!nameInput.value.trim()) {
    showError(nameInput, 'name-error', '이름은 필수 항목입니다.');
    isValid = false;
  } else {
    clearError(nameInput, 'name-error');
  }

  // 이메일 검사
  if (!emailInput.value.trim()) {
    showError(emailInput, 'email-error', '이메일은 필수 항목입니다.');
    isValid = false;
  } else if (!validateEmail(emailInput.value)) {
    showError(emailInput, 'email-error', '유효한 이메일 형식이 아닙니다.');
    isValid = false;
  } else {
    clearError(emailInput, 'email-error');
  }

  // 메시지 검사
  if (!messageInput.value.trim()) {
    showError(messageInput, 'message-error', '메시지는 필수 항목입니다.');
    isValid = false;
  } else {
    clearError(messageInput, 'message-error');
  }

  // 모든 값들이 정상적으로 잘 들어있다면 전송 시도
  if (isValid) {
    try {
      // Formspree API 서버 주소로 폼 데이터를 POST 메서드로 백그라운드 전송합니다.
      const response = await fetch(contactForm.action, {
        method: 'POST',
        body: new FormData(contactForm), // 폼 내부의 name 속성이 달린 입력필드 데이터를 일괄 직렬화
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        contactForm.reset(); // 성공 시 입력 필드를 모두 깨끗하게 비웁니다.
        formSuccess.style.display = 'block'; // 성공 안내 문구를 화면에 띄웁니다.

        // 5초(5000ms) 후에 성공 문구가 화면에서 다시 스르륵 숨겨지도록 만듭니다.
        setTimeout(() => formSuccess.style.display = 'none', 5000);
      } else {
        alert('이메일 전송에 실패했습니다.');
      }
    } catch (error) {
      alert('네트워크 오류가 발생했습니다.');
    }
  }
});

// [실시간 피드백 유효성 검사 (input 이벤트)]
// 사용자가 타이핑(input)할 때마다 실시간으로 에러를 지워주는 사용자 편의 기능(UX)입니다.
// 매번 제출 버튼을 누르게 하지 않고, 입력이 올바르게 고쳐지는 즉시 빨간색 테두리와 메시지를 없앱니다.
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
