


// ==========================================
// 0. 중앙 집중식 상태(STATE) 관리 객체
// ==========================================
const STATE = {
  // 테마 상태 초기화
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
const themeToggleBtn = document.getElementById('theme-toggle');
const themeIcon = themeToggleBtn.querySelector('.icon');
const htmlElement = document.documentElement; // <html> 태그를 가리킵니다.

// 테마 렌더링 함수
const renderTheme = () => {
  if (STATE.theme === 'dark') {
    // HTML에 data-theme="dark" 설정
    htmlElement.setAttribute('data-theme', 'dark');
    themeIcon.textContent = '☀️'; // 토글 버튼의 아이콘을 태양으로 바꿉니다.
  } else {
    htmlElement.setAttribute('data-theme', 'light');
    themeIcon.textContent = '🌙'; // 토글 버튼의 아이콘을 달로 바꿉니다.
  }
};

// 초기 테마 적용
renderTheme();

themeToggleBtn.addEventListener('click', () => {
  STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';
  // 로컬 스토리지에 테마 저장
  localStorage.setItem('theme', STATE.theme);
  renderTheme();
});


// ==========================================
// 2. 네비게이션 및 햄버거 메뉴 처리 (클래스 토글을 이용한 CSS 렌더링 제어)
// ==========================================
const navToggle = document.getElementById('nav-toggle');
const navMenu = document.getElementById('nav-menu');
const navLinks = document.querySelectorAll('.nav__link');
const header = document.querySelector('.header');

// 모바일 햄버거 버튼 클릭 이벤트
navToggle.addEventListener('click', () => {
  // active 클래스 토글
  navToggle.classList.toggle('active');
  navMenu.classList.toggle('active');
});

// 모바일 메뉴 안의 링크 클릭 시 메뉴바 닫기
navLinks.forEach(link => {
  link.addEventListener('click', () => {
    navToggle.classList.remove('active');
    navMenu.classList.remove('active');
  });
});

window.addEventListener('scroll', () => {
  if (window.scrollY >= 60) {
    header.classList.add('scrolled');
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
    scrollTopBtn.classList.add('show');
  } else {
    scrollTopBtn.classList.remove('show');
  }
});

scrollTopBtn.addEventListener('click', (e) => {
  e.preventDefault();
  // 최상단으로 부드럽게 스크롤
  window.scrollTo({ top: 0, behavior: 'smooth' });
});


// ==========================================
// 4. 스크롤 애니메이션 (Intersection Observer - 뷰포트 감지)
// ==========================================
// [Intersection Observer API: 웹 화면 최적화의 숨은 공신]
// 전통적인 scroll 이벤트 방식은 스크롤 할 때마다 요소의 위치 좌표를 매번 계산해야 해서 브라우저에 큰 부하를 줍니다.
// 반면, Intersection Observer는 "지정한 요소가 브라우저 화면(Viewport)에 일정 수준 이상 노출되었는지"를 
// 브라우저 자체의 효율적인 백그라운드 엔진이 감시하다가, 그 진입 시점에만 콜백 함수를 비동기로 호출해 줍니다. 성능이 대단히 우수합니다.

// 요소가 50% 노출 시 콜백 트리거
const observerOptions = { root: null, rootMargin: '0px', threshold: 0.5 };

const observer = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // 화면 진입 시 appear 클래스 추가
      entry.target.classList.add('appear');
      // 애니메이션 실행 후 관찰 해제
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// 감시할 요소들 관찰 시작
document.querySelectorAll('.section__title, .about__img-wrapper, .about__info, .skills__card, .project-card, .contact__container').forEach(el => {
  el.classList.add('fade-in');
  observer.observe(el);
});


// ==========================================
// 5. 타이핑 효과 (Typewriter Effect)
// ==========================================
const typingElement = document.getElementById('typing-text');
const actualText = "안녕하세요, 저는 feelosophysics입니다.";
let charIndex = 0;

// 타이핑 재귀 함수
const typeText = () => {
  if (charIndex < actualText.length) {
    typingElement.textContent += actualText.charAt(charIndex);
    charIndex++;
    setTimeout(typeText, 100);
  }
};
// 0.5초 후 타이핑 시작
setTimeout(typeText, 500);


// ==========================================
// 6. GitHub API 연동 및 필터링 (상태 기반 렌더링)
// ==========================================
const GITHUB_USERNAME = 'feelosophysics';
const projectsContainer = document.getElementById('projects-container');
const filterBtns = document.querySelectorAll('.filter-btn');

// 프로젝트 UI 렌더링 함수 (STATE 기반)
const renderProjectsUI = () => {
  const { status, allData, filter, errorMsg } = STATE.portfolio;

  // Case 1: 로딩 중 상태
  if (status === 'loading') {
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

    // 다시 시도 버튼 이벤트 연결
    const retryBtn = projectsContainer.querySelector('#retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', fetchProjects);
    }
    return;
  }

  // Case 3: 로딩 성공 상태 - 필터링 적용
  const filteredData = filter === 'all'
    ? allData
    : allData.filter(repo => repo.language === filter);

  // Case 3-1: 필터링 결과 표시할 카드가 없을 때
  if (status === 'success' && filteredData.length === 0) {
    projectsContainer.innerHTML = '<div class="projects__empty">표시할 프로젝트가 없습니다.</div>';
    return;
  }

  // Case 3-2: 프로젝트 카드 생성 및 삽입
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

// GitHub Repository API 호출
const fetchProjects = async () => {
  STATE.portfolio.status = 'loading';
  renderProjectsUI();

  try {
    const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated`);

    if (!response.ok) {
      throw new Error(response.status === 403 ? 'API 호출 제한 초과' : '데이터를 불러올 수 없습니다.');
    }

    const data = await response.json();

    // 본인 레포지토리만 필터링
    STATE.portfolio.allData = data.filter(repo => !repo.fork);
    STATE.portfolio.status = 'success';
    renderProjectsUI();

  } catch (error) {
    STATE.portfolio.status = 'error';
    STATE.portfolio.errorMsg = error.message;
    renderProjectsUI();
  }
};

// 필터 버튼 클릭 이벤트 등록
filterBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    filterBtns.forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');

    // 상태 필터 갱신 및 UI 렌더링
    STATE.portfolio.filter = e.target.getAttribute('data-filter');
    renderProjectsUI();
  });
});

// 초기 프로젝트 로드
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

// 에러 메시지 표시
const showError = (inputElement, errorElementId, message) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.add('invalid');
  errorEl.textContent = message;
  errorEl.style.display = 'block';
};

// 에러 메시지 초기화
const clearError = (inputElement, errorElementId) => {
  const errorEl = document.getElementById(errorElementId);
  inputElement.classList.remove('invalid');
  errorEl.style.display = 'none';
};

// 폼 서브밋(Submit: 전송하기) 이벤트
contactForm.addEventListener('submit', async (e) => {
  e.preventDefault(); // 기본 전송 동작 차단
  let isValid = true;

  // 이름 유효성 검사
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
      // Formspree API 전송
      const response = await fetch(contactForm.action, {
        method: 'POST',
        body: new FormData(contactForm),
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        contactForm.reset();
        formSuccess.style.display = 'block';

        // 5초 후 성공 메시지 숨김
        setTimeout(() => formSuccess.style.display = 'none', 5000);
      } else {
        alert('이메일 전송에 실패했습니다.');
      }
    } catch (error) {
      alert('네트워크 오류가 발생했습니다.');
    }
  }
});

// 실시간 입력 유효성 검사 이벤트
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
