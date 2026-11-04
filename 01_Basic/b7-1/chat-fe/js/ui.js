/**
 * 여러 화면이 함께 쓰는 메뉴·시간·Markdown 표시 도구입니다. Markdown은 별표/샵 같은 문자로 서식을 표현하는
 * 방식입니다.
 * HTML 변환 결과는 DOMPurify로 정제합니다. 사용자나 AI가 쓴 글을 검증 없이 HTML로 넣으면 스크립트가
 * 실행될 수 있습니다.
 * aria 속성은 스크린리더에 버튼 의미/상태를 알려 주며 inert는 닫힌 모바일 메뉴에 키보드가 들어가지 않게 합니다.
 */
/**
 * 모바일 메뉴의 열림 상태를 바꾸고 키보드 초점을 메뉴/열기 버튼으로 옮깁니다. ?.는 요소가 있을 때만 동작시키는
 * 문법입니다.
 */
function toggleSidebar(open) {
    const expanded = typeof open === 'boolean' ? open : !document.body.classList.contains('sidebar-open');
    document.body.classList.toggle('sidebar-open', expanded);
    syncSidebarAccess();
    document.querySelector('.mobile-menu')?.setAttribute('aria-expanded', String(expanded));
    if (expanded) document.querySelector('.sidebar .rail-link')?.focus();
    else document.querySelector('.mobile-menu')?.focus();
}
/**
 * 모바일에서 닫힌 메뉴를 inert로 만들어 화면 밖의 버튼에 Tab 초점이 들어가지 않게 합니다.
 */
function syncSidebarAccess() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.inert = window.matchMedia('(max-width: 760px)').matches && !document.body.classList.contains('sidebar-open');
}
document.addEventListener('DOMContentLoaded', syncSidebarAccess);
window.matchMedia('(max-width: 760px)').addEventListener('change', syncSidebarAccess);
/**
 * 입력칸의 password/text 종류를 바꿔 비밀번호 표시/숨김을 전환합니다. 서버에 보낼 비밀번호 문자열은 바꾸지
 * 않습니다.
 */
function togglePassword(id, button) {
    const input = document.getElementById(id);
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', visible ? '비밀번호 숨기기' : '비밀번호 표시');
    button.innerHTML = '<i class="fa-regular '+(visible?'fa-eye-slash':'fa-eye')+'" aria-hidden="true"></i>';
}
/**
 * 서식 문자열을 HTML로 바꾸고 위험한 태그/속성을 정제합니다. 라이브러리가 없으면 일반 텍스트로 안전하게 표시합니다.
 */
function renderMarkdown(text) {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        // Markdown을 HTML로 바꾼 뒤 정제합니다. 변환만 하면 AI/사용자 입력 속 HTML도 실행될 수
        // 있어 두 단계가 필요합니다.
        return DOMPurify.sanitize(marked.parse(String(text || ''), { breaks: true, gfm: true }), {
            USE_PROFILES: { html: true }, FORBID_TAGS: ['img', 'style'], FORBID_ATTR: ['style']
        });
    }
    return '<p>' + escapeHtml(text).replace(/\n/g, '<br>') + '</p>';
}
/**
 * 밀리초를 초로 바꾸고 한국어 숫자로 표시합니다. 유효한 숫자가 아니면 대시를 반환합니다.
 */
function formatDuration(milliseconds) {
    if (milliseconds === null || milliseconds === undefined || !Number.isFinite(Number(milliseconds))) return '—';
    return (Number(milliseconds)/1000).toLocaleString('ko-KR', { maximumFractionDigits: 1 }) + '초';
}
/**
 * 시간대 표시 없는 DB 시각을 UTC로 해석한 뒤 한국 시간으로 표시합니다. 잘못된 날짜는 표시하지 않습니다.
 */
function formatRecordDate(value) {
    if (!value) return '—';
    // DB 시각은 UTC이며 문자열에 시간대 접미사가 없는 경우가 있습니다.
    // DB의 시간대 없는 날짜는 UTC로 해석하기 위해 Z를 붙입니다. 이미 시간대 표시가 있으면 중복으로 붙이지
    // 않습니다.
    const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value + 'Z';
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('ko-KR', {
        timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false
    }).format(date);
}
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('sidebar-open')) toggleSidebar(false);
    // 모바일 메뉴가 열린 동안 Tab 이동이 메뉴 안에 머물게 합니다. Shift+Tab은 반대 방향 이동입니다.
    if (event.key === 'Tab' && document.body.classList.contains('sidebar-open')) {
        const items = Array.from(document.querySelectorAll('.sidebar a,.sidebar button:not(:disabled)'));
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
});
