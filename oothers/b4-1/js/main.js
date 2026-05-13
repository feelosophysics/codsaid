const GITHUB_USERNAME = "octocat";
const API_URL = `https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=9`;

const elements = {
  root: document.documentElement,
  body: document.body,
  header: document.querySelector("[data-header]"),
  menuButton: document.querySelector("[data-menu-button]"),
  navList: document.querySelector("[data-nav-list]"),
  navLinks: document.querySelectorAll("[data-nav-list] a"),
  themeButton: document.querySelector("[data-theme-button]"),
  themeLabel: document.querySelector("[data-theme-label]"),
  scrollTop: document.querySelector("[data-scroll-top]"),
  animatedSections: document.querySelectorAll("[data-animate]"),
  typingText: document.querySelector("[data-typing-text]"),
  filterGroup: document.querySelector("[data-filter-group]"),
  projectStatus: document.querySelector("[data-project-status]"),
  projectGrid: document.querySelector("[data-project-grid]"),
  retryButton: document.querySelector("[data-retry-button]"),
  contactForm: document.querySelector("[data-contact-form]"),
  formMessage: document.querySelector("[data-form-message]"),
};

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

function getInitialTheme() {
  const savedTheme = localStorage.getItem("portfolio-theme");

  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function setTheme(nextTheme) {
  state.theme = nextTheme;
  elements.root.dataset.theme = state.theme;
  elements.themeButton.setAttribute("aria-pressed", String(state.theme === "dark"));
  elements.themeLabel.textContent = state.theme === "dark" ? "Light" : "Dark";
  localStorage.setItem("portfolio-theme", state.theme);
}

function toggleMenu() {
  state.menuOpen = !state.menuOpen;
  elements.navList.classList.toggle("active", state.menuOpen);
  elements.body.classList.toggle("menu-open", state.menuOpen);
  elements.menuButton.setAttribute("aria-expanded", String(state.menuOpen));
}

function closeMenu() {
  state.menuOpen = false;
  elements.navList.classList.remove("active");
  elements.body.classList.remove("menu-open");
  elements.menuButton.setAttribute("aria-expanded", "false");
}

function updateScrollUi() {
  const isPastHeader = window.scrollY > 60;
  const canScrollTop = window.scrollY > 300;

  elements.header.classList.toggle("is-scrolled", isPastHeader);
  elements.scrollTop.classList.toggle("visible", canScrollTop);
}

function observeSections() {
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

  elements.animatedSections.forEach((section) => observer.observe(section));
}

function startTypingEffect() {
  const text = "이벤트 → 상태 변경 → DOM 업데이트의 흐름을 직접 구현합니다.";
  let index = 0;

  const typeNextCharacter = () => {
    elements.typingText.textContent = text.slice(0, index);
    index += 1;

    if (index <= text.length) {
      window.setTimeout(typeNextCharacter, 58);
    }
  };

  typeNextCharacter();
}

function setProjectState(nextState) {
  state.projects = {
    ...state.projects,
    ...nextState,
  };

  renderProjects();
}

async function fetchProjects() {
  setProjectState({ status: "loading", error: "", items: [] });

  try {
    const response = await fetch(API_URL);

    if (!response.ok) {
      throw new Error(`GitHub API 요청 실패: ${response.status}`);
    }

    const repos = await response.json();
    const visibleRepos = repos
      .filter(({ fork }) => !fork)
      .map(({ name, description, html_url: url, language, stargazers_count: stars, updated_at: updatedAt }) => ({
        name,
        description,
        url,
        language: language || "Other",
        stars,
        updatedAt,
      }));

    setProjectState({ status: "success", items: visibleRepos, filter: "All" });
  } catch (error) {
    setProjectState({
      status: "error",
      error: error.message || "프로젝트를 불러올 수 없습니다.",
      items: [],
    });
  }
}

function renderProjects() {
  const { status, items, error, filter } = state.projects;
  elements.projectGrid.innerHTML = "";
  elements.projectStatus.innerHTML = "";
  renderFilters(items, filter);

  if (status === "loading") {
    elements.projectStatus.innerHTML = `
      <div class="state-panel">
        <div class="spinner" aria-hidden="true"></div>
        <p>프로젝트를 불러오는 중입니다...</p>
      </div>
    `;
    return;
  }

  if (status === "error") {
    elements.projectStatus.innerHTML = `
      <div class="state-panel">
        <p>프로젝트를 불러올 수 없습니다.</p>
        <p>${escapeHtml(error)}</p>
        <button class="button button--small" type="button" data-inline-retry>재시도</button>
      </div>
    `;
    document.querySelector("[data-inline-retry]").addEventListener("click", fetchProjects);
    return;
  }

  if (status !== "success") {
    return;
  }

  if (items.length === 0) {
    elements.projectStatus.innerHTML = `
      <div class="state-panel">
        <p>표시할 프로젝트가 없습니다.</p>
      </div>
    `;
    return;
  }

  const filteredItems = filter === "All" ? items : items.filter((project) => project.language === filter);

  if (filteredItems.length === 0) {
    elements.projectStatus.innerHTML = `
      <div class="state-panel">
        <p>${escapeHtml(filter)} 프로젝트가 아직 없습니다.</p>
      </div>
    `;
    return;
  }

  elements.projectGrid.innerHTML = filteredItems.map(createProjectCard).join("");
}

function renderFilters(items, activeFilter) {
  const languages = ["All", ...new Set(items.map(({ language }) => language))];

  if (items.length === 0) {
    elements.filterGroup.innerHTML = "";
    return;
  }

  elements.filterGroup.innerHTML = languages
    .map(
      (language) => `
        <button
          class="filter-button ${language === activeFilter ? "active" : ""}"
          type="button"
          data-filter="${escapeHtml(language)}"
        >
          ${escapeHtml(language)}
        </button>
      `
    )
    .join("");
}

function createProjectCard({ name, description, url, language, stars, updatedAt }) {
  const updatedDate = new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(updatedAt));

  return `
    <article class="project-card">
      <h3><a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${escapeHtml(name)}</a></h3>
      <p>${escapeHtml(description || "설명이 등록되지 않은 저장소입니다.")}</p>
      <div class="project-card__meta" aria-label="${escapeAttribute(name)} 저장소 정보">
        <span>${escapeHtml(language)}</span>
        <span>Stars ${Number(stars)}</span>
        <span>${updatedDate}</span>
      </div>
    </article>
  `;
}

function handleFilterClick(event) {
  const filterButton = event.target.closest("[data-filter]");

  if (!filterButton) {
    return;
  }

  setProjectState({ filter: filterButton.dataset.filter });
}

function validateForm(formData) {
  const errors = {};
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!formData.name.trim()) {
    errors.name = "이름을 입력해 주세요.";
  }

  if (!formData.email.trim()) {
    errors.email = "이메일을 입력해 주세요.";
  } else if (!emailPattern.test(formData.email)) {
    errors.email = "올바른 이메일 형식으로 입력해 주세요.";
  }

  if (!formData.message.trim()) {
    errors.message = "메시지를 입력해 주세요.";
  }

  return errors;
}

function renderFormState() {
  const { errors, submitted } = state.form;

  document.querySelectorAll("[data-error-for]").forEach((errorElement) => {
    const fieldName = errorElement.dataset.errorFor;
    errorElement.textContent = errors[fieldName] || "";
  });

  if (Object.keys(errors).length > 0) {
    elements.formMessage.textContent = "입력값을 다시 확인해 주세요.";
    return;
  }

  elements.formMessage.textContent = submitted ? "문의가 접수된 것으로 처리했습니다." : "";
}

function handleContactSubmit(event) {
  event.preventDefault();

  const formData = Object.fromEntries(new FormData(elements.contactForm).entries());
  const errors = validateForm(formData);

  state.form = {
    errors,
    submitted: Object.keys(errors).length === 0,
  };

  renderFormState();

  if (state.form.submitted) {
    elements.contactForm.reset();
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function bindEvents() {
  elements.themeButton.addEventListener("click", () => {
    setTheme(state.theme === "dark" ? "light" : "dark");
  });

  elements.menuButton.addEventListener("click", toggleMenu);
  elements.navLinks.forEach((link) => link.addEventListener("click", closeMenu));
  elements.scrollTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  elements.retryButton.addEventListener("click", fetchProjects);
  elements.filterGroup.addEventListener("click", handleFilterClick);
  elements.contactForm.addEventListener("submit", handleContactSubmit);
  window.addEventListener("scroll", updateScrollUi, { passive: true });
}

function init() {
  setTheme(state.theme);
  bindEvents();
  observeSections();
  startTypingEffect();
  updateScrollUi();
  fetchProjects();
}

init();
