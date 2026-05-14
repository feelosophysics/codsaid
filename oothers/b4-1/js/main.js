const GITHUB_USERNAME = "feelosophysics";
const API_URL = `https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=12`;
const THEME_STORAGE_KEY = "b4-1-theme";

const elements = {
  root: document.documentElement,
  body: document.body,
  header: document.querySelector("[data-header]"),
  menuButton: document.querySelector("[data-menu-button]"),
  navList: document.querySelector("[data-nav-list]"),
  navLinks: document.querySelectorAll("[data-nav-list] a"),
  themeButton: document.querySelector("[data-theme-button]"),
  themeIcon: document.querySelector("[data-theme-icon]"),
  themeLabel: document.querySelector("[data-theme-label]"),
  typingText: document.querySelector("[data-typing-text]"),
  scrollTopButton: document.querySelector("[data-scroll-top]"),
  animatedSections: document.querySelectorAll("[data-animate]"),
  retryButton: document.querySelector("[data-retry-button]"),
  filterGroup: document.querySelector("[data-filter-group]"),
  projectStatus: document.querySelector("[data-project-status]"),
  projectGrid: document.querySelector("[data-project-grid]"),
  contactForm: document.querySelector("[data-contact-form]"),
  formMessage: document.querySelector("[data-form-message]"),
  fields: document.querySelectorAll("[data-field]"),
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
    touched: false,
  },
};

function getInitialTheme() {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);

  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function setTheme(nextTheme) {
  state.theme = nextTheme;
  elements.root.dataset.theme = state.theme;
  elements.themeButton.setAttribute("aria-pressed", String(state.theme === "dark"));
  elements.themeIcon.textContent = state.theme === "dark" ? "☀" : "☾";
  elements.themeLabel.textContent = state.theme === "dark" ? "Light" : "Dark";
  localStorage.setItem(THEME_STORAGE_KEY, state.theme);
}

function toggleMenu() {
  state.menuOpen = !state.menuOpen;
  elements.navList.classList.toggle("active", state.menuOpen);
  elements.menuButton.classList.toggle("is-open", state.menuOpen);
  elements.body.classList.toggle("menu-open", state.menuOpen);
  elements.menuButton.setAttribute("aria-expanded", String(state.menuOpen));
  elements.menuButton.setAttribute("aria-label", state.menuOpen ? "메뉴 닫기" : "메뉴 열기");
}

function closeMenu() {
  state.menuOpen = false;
  elements.navList.classList.remove("active");
  elements.menuButton.classList.remove("is-open");
  elements.body.classList.remove("menu-open");
  elements.menuButton.setAttribute("aria-expanded", "false");
  elements.menuButton.setAttribute("aria-label", "메뉴 열기");
}

function handleNavClick(event) {
  const link = event.currentTarget;
  const targetId = link.getAttribute("href");

  if (!targetId || !targetId.startsWith("#")) {
    return;
  }

  const target = document.querySelector(targetId);

  if (!target) {
    return;
  }

  event.preventDefault();
  closeMenu();
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateScrollUi() {
  const isPastHeader = window.scrollY > 60;
  const canScrollTop = window.scrollY > 300;

  elements.header.classList.toggle("is-scrolled", isPastHeader);
  elements.scrollTopButton.classList.toggle("visible", canScrollTop);
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

function setProjectState(nextState) {
  state.projects = {
    ...state.projects,
    ...nextState,
  };

  renderProjects();
}

async function fetchProjects() {
  setProjectState({
    status: "loading",
    items: [],
    error: "",
    filter: "All",
  });

  try {
    const response = await fetch(API_URL);

    if (!response.ok) {
      throw new Error(`GitHub API 응답 코드: ${response.status}`);
    }

    const repos = await response.json();
    const projects = repos
      .filter(({ fork }) => !fork)
      .map(
        ({
          name,
          description,
          html_url: url,
          homepage,
          language,
          stargazers_count: stars,
          updated_at: updatedAt,
        }) => ({
          name,
          description,
          url,
          homepage,
          language: language || "Other",
          stars,
          updatedAt,
        })
      );

    setProjectState({
      status: "success",
      items: projects,
      error: "",
      filter: "All",
    });
  } catch (error) {
    setProjectState({
      status: "error",
      items: [],
      error: error.message || "프로젝트를 불러올 수 없습니다.",
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
        <button class="button button-small" type="button" data-inline-retry>재시도</button>
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

  const filteredItems =
    filter === "All" ? items : items.filter((project) => project.language === filter);

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
  if (items.length === 0) {
    elements.filterGroup.innerHTML = "";
    return;
  }

  const languages = ["All", ...new Set(items.map(({ language }) => language))];
  elements.filterGroup.innerHTML = languages
    .map(
      (language) => `
        <button
          class="filter-button ${language === activeFilter ? "active" : ""}"
          type="button"
          data-filter="${escapeAttribute(language)}"
        >
          ${escapeHtml(language)}
        </button>
      `
    )
    .join("");
}

function createProjectCard({ name, description, url, homepage, language, stars, updatedAt }) {
  const updatedDate = new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(updatedAt));

  const homepageLink = homepage
    ? `<a href="${escapeAttribute(homepage)}" target="_blank" rel="noreferrer">Demo</a>`
    : "";

  return `
    <article class="project-card">
      <h3>
        <a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">
          ${escapeHtml(name)}
        </a>
      </h3>
      <p>${escapeHtml(description || "설명이 등록되지 않은 저장소입니다.")}</p>
      <div class="project-card-meta" aria-label="${escapeAttribute(name)} 저장소 정보">
        <span>${escapeHtml(language)}</span>
        <span>Stars ${Number(stars)}</span>
        <span>${updatedDate}</span>
        ${homepageLink ? `<span>${homepageLink}</span>` : ""}
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

function getFormData() {
  return Object.fromEntries(new FormData(elements.contactForm).entries());
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

function setFormState(nextState) {
  state.form = {
    ...state.form,
    ...nextState,
  };

  renderFormState();
}

function renderFormState() {
  const { errors, submitted } = state.form;

  document.querySelectorAll("[data-error-for]").forEach((errorElement) => {
    const fieldName = errorElement.dataset.errorFor;
    const field = document.querySelector(`[data-field="${fieldName}"]`);
    const message = errors[fieldName] || "";

    errorElement.textContent = message;
    field.classList.toggle("has-error", Boolean(message));
    field.setAttribute("aria-invalid", String(Boolean(message)));
  });

  if (Object.keys(errors).length > 0) {
    elements.formMessage.textContent = "입력값을 다시 확인해 주세요.";
    return;
  }

  elements.formMessage.textContent = submitted
    ? "문의가 접수된 것으로 처리했습니다. 실제 전송은 연결하지 않았습니다."
    : "";
}

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

function handleFormInput() {
  if (!state.form.touched) {
    return;
  }

  setFormState({
    errors: validateForm(getFormData()),
    submitted: false,
  });
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
  elements.navLinks.forEach((link) => link.addEventListener("click", handleNavClick));
  elements.scrollTopButton.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  elements.retryButton.addEventListener("click", fetchProjects);
  elements.filterGroup.addEventListener("click", handleFilterClick);
  elements.contactForm.addEventListener("submit", handleContactSubmit);
  elements.fields.forEach((field) => field.addEventListener("input", handleFormInput));
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
