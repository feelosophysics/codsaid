/**
 * 저장된 내 질문/답변을 조회하고 검색·필터·상세 보기를 제공합니다. 새 AI 요청은 보내지 않습니다.
 * 서버는 페이지별 자료를 주고 프론트 검색은 받은 현재 페이지에만 적용됩니다. 통계는 별도 API의 전체 값입니다.
 * 내부 메시지 ID는 상세 항목을 찾는 데만 사용하며 화면에 사용자용 번호로 출력하지 않습니다.
 */
let logItems = [], logTotal = 0, logOffset = 0, logRole = '', logsRequestId = 0;
const LOG_PAGE_SIZE = 50;
document.addEventListener('DOMContentLoaded', () => {
    if (!setupNavbar(true)) return;
    refreshLogs();
    document.getElementById('logDetail').addEventListener('click', event => {
        if (event.target === event.currentTarget) {
            const bounds = event.currentTarget.getBoundingClientRect();
            if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.currentTarget.close();
        }
    });
});
/**
 * 목록과 통계를 동시에 읽습니다. allSettled는 한 요청이 실패해도 다른 요청의 결과 처리가 계속되게 합니다.
 */
async function refreshLogs() { await Promise.allSettled([fetchLogs(), fetchLogStats()]); }
/**
 * 서버 전체 통계를 네 카드에 넣습니다. 자료가 없거나 요청이 실패하면 의미 없는 0 대신 대시를 표시합니다.
 */
async function fetchLogStats() {
    const ids = ['statTotalLogs','statSessions','statAvgLatency','statSuccessRate'];
    try {
        const response = await apiRequest('/api/v1/logs/stats');
        if (!response.ok) throw new Error('통계 조회 실패');
        const stats = await response.json();
        document.getElementById('statTotalLogs').textContent = Number(stats.total_questions || 0).toLocaleString('ko-KR');
        document.getElementById('statSessions').textContent = Number(stats.total_sessions || 0).toLocaleString('ko-KR');
        document.getElementById('statAvgLatency').textContent = stats.total_answers ? formatDuration(stats.avg_latency_ms) : '—';
        document.getElementById('statSuccessRate').textContent = stats.total_questions ? Number(stats.success_rate_percent).toLocaleString('ko-KR') + '%' : '—';
    } catch {
        ids.forEach(id => document.getElementById(id).textContent = '—');
        showToast('대화 통계를 불러오지 못했습니다. 새로고침해 주세요.', 'error');
    }
}
/**
 * 필터·페이지 조건으로 기록을 읽습니다. 삭제 등으로 현재 페이지가 범위를 벗어나면 마지막 유효 페이지로 옮깁니다.
 */
async function fetchLogs() {
    const requestId = ++logsRequestId;
    const body = document.getElementById('logsTableBody');
    const refresh = document.getElementById('refreshLogs');
    refresh.disabled = true;
    document.getElementById('prevPage').disabled = true;
    document.getElementById('nextPage').disabled = true;
    body.innerHTML = '<tr><td colspan="5" class="loading-state"><i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> 기록을 불러오는 중…</td></tr>';
    const status = document.getElementById('statusFilter').value;
    let endpoint = '/api/v1/logs?limit='+LOG_PAGE_SIZE+'&offset='+logOffset;
    if (status) endpoint += '&status='+encodeURIComponent(status);
    try {
        const response = await apiRequest(endpoint);
        if (!response.ok) throw new Error('기록을 불러올 수 없습니다.');
        const data = await response.json();
        if (requestId !== logsRequestId) return;
        logItems = data.items || []; logTotal = Number(data.total || 0);
        if (!logItems.length && logOffset > 0 && logTotal <= logOffset) {
            logOffset = Math.max(0, Math.ceil(logTotal/LOG_PAGE_SIZE)-1)*LOG_PAGE_SIZE;
            return await fetchLogs();
        }
        renderLogs();
        document.getElementById('lastUpdated').textContent = '최근 확인 '+new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Seoul'}).format(new Date());
    } catch (error) {
        if (requestId !== logsRequestId) return;
        logItems = [];
        body.innerHTML = '<tr><td colspan="5" class="empty-state">'+escapeHtml(error.message)+'<br>잠시 후 새로고침해 주세요.</td></tr>';
        document.getElementById('logCountLabel').textContent = '기록 조회 실패';
        document.getElementById('pageLabel').textContent = '—';
    } finally { if (requestId === logsRequestId) refresh.disabled = false; }
}
/**
 * 받은 페이지에서 검색어/역할에 맞는 기록을 그립니다. 실제 내용을 열 때는 화면에 숨긴 내부 ID로 원래 항목을 찾습니다.
 */
function renderLogs() {
    const query = document.getElementById('logSearch').value.trim().toLocaleLowerCase();
    // filter는 조건에 맞는 항목만 새 목록으로 만듭니다. 원래 페이지 자료는 유지하며 화면 검색은 이 페이지
    // 안에서만 동작합니다.
    const items = logItems.filter(item => (!logRole || item.role === logRole) &&
        (!query || String(item.content || '').toLocaleLowerCase().includes(query)));
    const body = document.getElementById('logsTableBody');
    if (!items.length) {
        const filtered = query || logRole || document.getElementById('statusFilter').value;
        body.innerHTML = '<tr><td colspan="5" class="empty-state"><i class="fa-regular fa-folder-open" aria-hidden="true"></i>'+ (filtered?'조건에 맞는 기록이 없어요. 검색어나 필터를 바꿔보세요.':'아직 기록이 없어요. 지식 채팅에서 첫 질문을 남겨보세요.')+'</td></tr>';
    } else {
        // map은 각 기록을 HTML 행으로 바꾸고 join은 하나의 문자열로 합칩니다. ID는 상세 연결에만 쓰며
        // 화면 번호로 출력하지 않습니다.
        body.innerHTML = items.map(item => {
            const assistant = item.role === 'assistant', success = item.status === 'success';
            const status = success ? '성공' : item.status === 'timeout' ? '시간 초과' : '오류';
            const date = formatRecordDate(item.created_at);
            // 표/서식 기호를 줄여 미리보기 문자열을 만듭니다. 이것만으로 안전해지는 것은 아니므로 표시 직전
            // escapeHtml도 사용합니다.
            const preview = String(item.content || '').split('\n').filter(line => line.trim() && !/^\s*\|/.test(line)).join(' ').replace(/[#*_>]/g,'').replaceAll(String.fromCharCode(96),'');
            return '<tr><td><span class="role-label '+(assistant?'assistant':'')+'"><i class="fa-'+(assistant?'solid fa-leaf':'regular fa-comment')+'" aria-hidden="true"></i>'+(assistant?'AI 답변':'나의 질문')+'</span></td><td class="content-cell"><button class="record-preview" onclick="openLogDetail('+Number(item.id)+')" aria-label="'+(assistant?'답변':'질문')+' 전체 내용 보기">'+escapeHtml(preview)+'</button></td><td class="record-date">'+escapeHtml(date)+'</td><td class="muted-cell desktop-column">'+(assistant?formatDuration(item.latency_ms):'—')+'</td><td><span class="status-pill '+(success?'':'error')+'">'+status+'</span></td></tr>';
        }).join('');
    }
    const pages = Math.max(1, Math.ceil(logTotal/LOG_PAGE_SIZE)), page = Math.floor(logOffset/LOG_PAGE_SIZE)+1;
    document.getElementById('pageLabel').textContent = page+' / '+pages;
    document.getElementById('prevPage').disabled = logOffset === 0;
    document.getElementById('nextPage').disabled = logOffset + LOG_PAGE_SIZE >= logTotal;
    document.getElementById('logCountLabel').textContent = (logTotal ? (logOffset+1)+'–'+Math.min(logOffset+LOG_PAGE_SIZE,logTotal)+' / 전체 '+logTotal+'개 메시지' : '0개 메시지') + ((query||logRole)?' · 현재 페이지 '+items.length+'개 표시':'');
}
/**
 * 전체/질문/답변 탭을 바꾸고 현재 페이지를 다시 그립니다. 서버에서 추가 페이지를 모두 가져오는 검색은 아닙니다.
 */
function setLogRole(role, button) {
    logRole = role;
    document.querySelectorAll('.record-tab').forEach(tab => {
        tab.classList.toggle('active',tab===button); tab.setAttribute('aria-pressed',String(tab===button));
    });
    renderLogs();
}
/**
 * 상태 필터가 바뀌면 첫 페이지로 돌아가 서버에서 다시 읽습니다. 기존 offset을 쓰면 빈 페이지가 될 수 있습니다.
 */
function changeLogStatus() { logOffset = 0; fetchLogs(); }
/**
 * 한 페이지 크기만큼 offset을 움직이고 다시 조회합니다. Math.max로 음수 시작 위치를 막습니다.
 */
function changeLogPage(direction) { logOffset = Math.max(0,logOffset+direction*LOG_PAGE_SIZE); fetchLogs(); }
/**
 * 현재 페이지의 메시지 전체 내용을 대화상자에 표시합니다. 날짜와 응답시간을 보여주고 DB 번호는 숨깁니다.
 */
function openLogDetail(id) {
    const item = logItems.find(item => item.id === id);
    if (!item) return;
    document.getElementById('detailTitle').textContent = item.role === 'assistant' ? 'AI 답변' : '나의 질문';
    document.getElementById('detailMeta').textContent = formatRecordDate(item.created_at)+(item.role==='assistant'?' · '+formatDuration(item.latency_ms):'');
    document.getElementById('detailContent').innerHTML = item.role === 'assistant' ? renderMarkdown(item.content) : '<p style="white-space:pre-wrap">'+escapeHtml(item.content)+'</p>';
    document.getElementById('logDetail').showModal();
}
