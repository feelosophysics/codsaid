/**
 * 가입/로그인 폼 입력을 검사하고 서버로 보냅니다. JSON.stringify는 객체를 전송할 문자열로 바꿉니다.
 * preventDefault는 폼의 기본 페이지 이동을 막고, response.ok는 HTTP 요청 성공 여부를 나타냅니다.
 * 프론트 입력 검사는 빠른 안내를 위한 것이며 서버가 같은 조건을 다시 검사해야 합니다.
 */
document.addEventListener('DOMContentLoaded', () => setupNavbar(false));
/**
 * 로그인/가입을 기다리는 동안 버튼을 비활성화하고 진행 표시를 바꿉니다. 연속 클릭으로 같은 요청이 중복되는 것을 줄입니다.
 */
function setAuthBusy(busy, registering = false) {
    const button = document.getElementById('submitBtn');
    button.disabled = busy;
    button.innerHTML = busy
        ? '<span>'+(registering?'계정을 만드는 중…':'로그인하는 중…')+'</span><i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>'
        : '<span>'+(registering?'계정 만들기':'로그인')+'</span><i class="fa-solid fa-arrow-right" aria-hidden="true"></i>';
}
/**
 * 폼 오류 안내에 문자열만 넣고 숨김 상태를 풉니다. textContent는 HTML로 해석하지 않고 그대로 글자를
 * 표시합니다.
 */
function showAuthError(message) {
    document.getElementById('errorText').textContent = typeof message === 'string' ? message : '입력 내용을 확인해 주세요.';
    document.getElementById('errorMessage').classList.remove('hidden');
}
/**
 * 아이디/비밀번호 전송 → 응답 읽기 → 토큰 저장 → 허용된 화면 이동 순서입니다. 임의 외부 URL로 redirect하지
 * 않습니다.
 */
async function handleLogin(event) {
    // 폼의 기본 동작은 페이지 이동입니다. 이를 막고 아래 fetch 요청으로 데이터를 보내 결과를 화면에서 처리합니다.
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    document.getElementById('errorMessage').classList.add('hidden');
    setAuthBusy(true);
    try {
        const response = await fetch(getApiUrl('/api/v1/auth/login'), {
            method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})
        });
        // 서버의 JSON 문자열을 JavaScript 객체로 읽습니다. 이 뒤에도 response.ok를 검사해야
        // 오류 응답을 성공으로 처리하지 않습니다.
        const data = await response.json();
        if (!response.ok) { showAuthError(data.detail || '아이디와 비밀번호를 확인해 주세요.'); setAuthBusy(false); return; }
        setToken(data.access_token, data.user);
        // 주소의 redirect는 사용자가 바꿀 수 있으므로 허용한 내부 화면만 선택합니다.
        const redirect = new URLSearchParams(window.location.search).get('redirect');
        window.location.href = ['index.html','logs.html'].includes(redirect) ? redirect : 'index.html';
    } catch {
        showAuthError(CONFIG.API_BASE_URL ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.' : '서비스 연결을 준비 중입니다. 잠시 후 다시 시도해 주세요.');
        setAuthBusy(false);
    }
}
/**
 * 아이디·닉네임·비밀번호 길이와 확인 입력을 먼저 검사합니다. 서버 가입 성공 후에는 별도 로그인 화면으로 안내합니다.
 */
async function handleRegister(event) {
    // 폼의 기본 동작은 페이지 이동입니다. 이를 막고 아래 fetch 요청으로 데이터를 보내 결과를 화면에서 처리합니다.
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const nickname = document.getElementById('nickname').value.trim();
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('passwordConfirm').value;
    if (username.length < 3 || username.length > 30) return showAuthError('아이디는 3~30자로 입력해 주세요.');
    if (!nickname || nickname.length > 30) return showAuthError('닉네임은 공백을 제외하고 1~30자로 입력해 주세요.');
    if (password.trim().length < 8 || password.length > 100) return showAuthError('비밀번호는 8~100자로 입력해 주세요.');
    if (password !== confirm) return showAuthError('비밀번호와 비밀번호 확인이 일치하지 않습니다.');
    document.getElementById('errorMessage').classList.add('hidden');
    setAuthBusy(true,true);
    try {
        const response = await fetch(getApiUrl('/api/v1/auth/register'), {
            method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,nickname,password})
        });
        // 서버의 JSON 문자열을 JavaScript 객체로 읽습니다. 이 뒤에도 response.ok를 검사해야
        // 오류 응답을 성공으로 처리하지 않습니다.
        const data = await response.json();
        if (!response.ok) { showAuthError(data.detail || '계정을 만들지 못했습니다. 입력 내용을 확인해 주세요.'); setAuthBusy(false,true); return; }
        showToast('회원가입이 완료되었습니다. 로그인해 주세요.','success');
        setTimeout(() => { window.location.href = 'login.html'; },600);
    } catch {
        showAuthError(CONFIG.API_BASE_URL ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.' : '서비스 연결을 준비 중입니다. 잠시 후 다시 시도해 주세요.');
        setAuthBusy(false,true);
    }
}
