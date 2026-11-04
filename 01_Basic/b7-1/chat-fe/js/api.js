/**
 * 브라우저의 로그인 정보와 공통 API 호출을 맡습니다. localStorage는 브라우저에 남는 이름:값 저장소입니다.
 * fetch는 서버에 HTTP 요청을 보내고 Promise는 나중에 도착할 결과를 나타냅니다. await는 그 결과를
 * 기다립니다.
 * 화면 로그인 검사와 서버의 실제 인증 검사는 별개이며, 서버가 401을 보내면 저장된 로그인 정보를 지웁니다.
 */
const TOKEN_KEY = 'chat_access_token';
const USER_KEY = 'chat_user_info';
/**
 * 이전에 저장한 로그인 토큰을 읽습니다. 없으면 null입니다. 저장소의 문자열이 있다는 사실만으로 서버 인증 성공은
 * 아닙니다.
 */
function getToken() { return localStorage.getItem(TOKEN_KEY); }
/**
 * 로그인 응답의 토큰과 사용자 표시 정보를 저장합니다. 객체는 JSON 문자열로 바꾸어 localStorage에 넣습니다.
 */
function setToken(token, user) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}
/**
 * 토큰과 사용자 정보 두 값을 함께 지웁니다. 로그아웃과 만료 처리에서 같은 함수를 사용합니다.
 */
function removeToken() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); }
/**
 * 저장된 JSON 사용자 정보를 객체로 읽습니다. 잘못된 문자열이면 try/catch로 오류를 잡고 null을 반환합니다.
 */
function getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; }
}
/**
 * 주소·옵션을 받아 JSON 헤더와 Bearer 토큰을 붙여 요청합니다. ...는 객체의 속성을 펼쳐 기존 옵션에 합치는
 * 문법입니다.
 */
async function apiRequest(endpoint, options = {}) {
    // Content-Type은 보낼 데이터가 JSON이라는 표시입니다. 기존 옵션을 펼쳐 합치고 토큰이 있으면
    // Authorization 헤더에 붙입니다.
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    const token = getToken();
    if (token) headers.Authorization = 'Bearer ' + token;
    const response = await fetch(getApiUrl(endpoint), { ...options, headers });
    // 401은 서버가 인증을 인정하지 않았다는 뜻입니다. 브라우저에 남은 토큰도 지워 같은 오류를 반복하지 않게 합니다.
    if (response.status === 401) {
        removeToken();
        if (!/\/(login|register)\.html$/.test(window.location.pathname)) window.location.href = 'login.html';
        throw new Error('로그인이 만료되었습니다. 다시 로그인해 주세요.');
    }
    return response;
}
/**
 * 잠깐 나타났다가 사라지는 안내를 만듭니다. message를 HTML 특수문자로 바꿔 안내 내용이 코드로 해석되지 않게
 * 합니다.
 */
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div'); container.id = 'toast-container';
        container.className = 'toast-container'; container.setAttribute('role', 'status');
        container.setAttribute('aria-live', 'polite'); document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast ' + (['error','success'].includes(type) ? type : '');
    const icon = type === 'error' ? 'circle-exclamation' : type === 'success' ? 'circle-check' : 'circle-info';
    // innerHTML은 문자열을 HTML로 해석합니다. 안내 문구는 escapeHtml로 바꿔 사용자 글자가 태그로
    // 실행되지 않게 합니다.
    toast.innerHTML = '<i class="fa-solid fa-'+icon+'" aria-hidden="true"></i><span>'+escapeHtml(message)+'</span>';
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
/**
 * 로그인이 필요한 화면은 토큰이 없으면 로그인 화면으로 이동하고, 상단에는 닉네임과 로그아웃 버튼을 그립니다.
 */
function setupNavbar(requireAuth = true) {
    const token = getToken(), user = getUser();
    if (requireAuth && !token) { window.location.href = 'login.html'; return false; }
    const nav = document.getElementById('authNav');
    if (nav) {
        if (token && user) {
            const name = user.nickname || user.username || '사용자';
            nav.innerHTML = '<div class="user-info"><span class="user-avatar" aria-hidden="true">'+escapeHtml(Array.from(name)[0])+'</span><span>'+escapeHtml(name)+'</span></div><button class="logout-btn" onclick="handleLogout()" aria-label="로그아웃"><span>로그아웃</span><i class="fa-solid fa-arrow-right-from-bracket" aria-hidden="true" style="margin-left:7px"></i></button>';
        } else {
            nav.innerHTML = '<a href="login.html">로그인</a><a href="register.html" class="button button-small">회원가입</a>';
        }
    }
    return true;
}
/**
 * 서버 쿠키 삭제를 요청하고 성공/실패와 관계없이 브라우저의 로그인 정보도 지웁니다. finally는 항상 실행됩니다.
 */
async function handleLogout() {
    try { await apiRequest('/api/v1/auth/logout', { method: 'POST' }); }
    catch { /* 만료/요청 실패와 관계없이 브라우저의 로그인 정보를 지웁니다. */ }
    finally { removeToken(); window.location.href = 'login.html'; }
}
/**
 * HTML에서 특별한 뜻을 가진 &, <, >, 따옴표를 문자 표시용 표현으로 바꿉니다. 사용자 입력을 화면 텍스트로 넣을
 * 때 사용합니다.
 */
function escapeHtml(text) {
    return String(text ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}
