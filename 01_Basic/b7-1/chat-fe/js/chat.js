/**
 * 대화 선택과 질문 전송, SSE 답변 표시를 맡습니다. DOM은 HTML을 JavaScript가 찾아 바꿀 수 있는 화면
 * 구조입니다.
 * currentSessionId는 서버와 연결하는 내부 ID이며 사용자용 순번이 아닙니다. 화면에는 대화 제목만 표시합니다.
 * SSE는 응답이 끝나기 전에도 여러 조각을 받는 방식입니다. 조각 경계와 문자 경계는 다를 수 있어
 * buffer/decoder로 이어 붙입니다.
 */
let currentSessionId = null, isStreaming = false, sessionRequestId = 0, selectionRequestId = 0;
let aiModelConfig = null;
// DOMContentLoaded는 HTML 요소가 준비됐다는 사건입니다. 화살표 함수 (() => ...)는 그때 실행할
// 작업을 전달합니다.
document.addEventListener('DOMContentLoaded', () => {
    if (!setupNavbar(true)) return;
    loadSessions();
    loadAIModels();
    document.getElementById('chatInput').focus();
});

/** 서버의 모델 목록·기본값을 읽습니다. 구버전 서버에서는 기존 기본 모델 전송 방식을 유지합니다. */
async function loadAIModels() {
    try {
        const response = await apiRequest('/api/v1/chat/models');
        if (!response.ok) return;
        const config = await response.json();
        if (!config.models?.some(model => model.id === config.default_model)) return;
        aiModelConfig = config;
        const select = document.getElementById('modelSelect');
        select.replaceChildren(...config.models.map(model => new Option(model.label, model.id)));
        select.value = config.default_model;
        document.getElementById('searchEnabled').checked = config.search_enabled;
        updateModelOptions();
        document.getElementById('aiSettings').hidden = false;
        setAISettingsDisabled(isStreaming);
    } catch { /* 목록을 받지 못해도 기존 채팅은 서버 기본값으로 사용할 수 있습니다. */ }
}

/** 모델 변경 시 지원하지 않는 이전 추론 선택은 기본값으로 되돌립니다. */
function updateModelOptions() {
    const model = aiModelConfig?.models.find(item => item.id === document.getElementById('modelSelect').value);
    const select = document.getElementById('thinkingSelect'), previous = select.value;
    const gemma = model?.id.startsWith('gemma');
    const labels = {minimal:gemma?'추론 끔':'최소',low:'낮음',medium:'중간',high:gemma?'추론 켬':'높음'};
    select.replaceChildren(...(model?.thinking_levels || []).map(level => new Option(labels[level], level)));
    select.value = model?.thinking_levels.includes(previous) ? previous : (model?.default_thinking || model?.thinking_levels[0] || '');
    document.getElementById('temperatureInput').value = '';
}

/** 사용자가 조정한 옵션을 비워 모델 기본값으로 돌아갑니다. 검색 선택은 별도로 유지합니다. */
function resetAIOptions() {
    document.getElementById('temperatureInput').value = '';
    const model = aiModelConfig?.models.find(item => item.id === document.getElementById('modelSelect').value);
    document.getElementById('thinkingSelect').value = model?.default_thinking || model?.thinking_levels[0] || '';
}

/** 입력값을 요청별 객체로 복사합니다. 숫자가 범위를 벗어나면 질문을 지우거나 전송하기 전에 알립니다. */
function getAIRequestOptions() {
    if (!aiModelConfig) return {};
    const input = document.getElementById('temperatureInput');
    if (!input.checkValidity()) throw new Error('Temperature는 0~2 사이의 숫자로 입력해 주세요.');
    const options = {
        model: document.getElementById('modelSelect').value,
        search_enabled: document.getElementById('searchEnabled').checked,
    };
    if (input.value !== '') options.temperature = Number(input.value);
    const thinking = document.getElementById('thinkingSelect').value;
    if (thinking) options.thinking_level = thinking;
    return options;
}

/** 답변 중 설정을 잠가 화면 선택과 이미 전송한 요청이 어긋나지 않게 합니다. */
function setAISettingsDisabled(disabled) {
    document.querySelectorAll('#aiSettings input,#aiSettings select,#aiSettings button').forEach(item => item.disabled = disabled);
}
/**
 * 입력 길이에 맞게 높이와 글자 수를 갱신합니다. scrollHeight는 내용 전체를 담는 데 필요한 높이입니다.
 */
function autoResizeTextarea(input) {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight,160)+'px';
    document.getElementById('charCounter').textContent = input.value.length+' / 2000';
}
/**
 * Enter는 전송하고 Shift+Enter는 줄을 바꿉니다. 한글 조합 중인 isComposing 상태에서는 전송하지
 * 않습니다.
 */
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault(); document.getElementById('chatForm').requestSubmit();
    }
}
/**
 * 주제 카드의 예시 질문을 입력칸에 넣고 실제 전송 폼을 호출합니다. 답변을 받는 중에는 중복 전송하지 않습니다.
 */
function sendQuickPrompt(text) {
    if (isStreaming) return;
    const input = document.getElementById('chatInput');
    input.value = text; autoResizeTextarea(input); document.getElementById('chatForm').requestSubmit();
}
/**
 * 내 대화 목록을 서버에서 읽어 제목과 삭제 버튼을 만듭니다. requestId로 오래된 요청 결과가 최신 목록을 덮지 않게
 * 합니다.
 */
async function loadSessions() {
    // 요청을 보낼 때마다 번호를 올립니다. 나중에 돌아온 오래된 결과를 비교해 버리므로 화면 선택이 뒤로 되돌아가지
    // 않습니다.
    const requestId = ++sessionRequestId;
    const list = document.getElementById('sessionsList');
    try {
        const response = await apiRequest('/api/v1/chat/sessions');
        if (!response.ok) throw new Error('대화 목록을 불러오지 못했습니다.');
        const sessions = await response.json();
        if (requestId !== sessionRequestId) return;
        list.innerHTML = '';
        if (!sessions.length) { list.innerHTML = '<p class="rail-empty">첫 질문을 남기면<br>여기에 대화가 모입니다.</p>'; return; }
        for (const session of sessions) {
            const item = document.createElement('div');
            item.className = 'session-item'+(currentSessionId===session.id?' active':'');
            const select = document.createElement('button');
            select.className = 'session-select'; select.disabled = isStreaming;
            select.setAttribute('aria-current',currentSessionId===session.id?'true':'false');
            select.innerHTML = '<i class="fa-regular fa-comment" aria-hidden="true"></i><span>'+escapeHtml(session.title)+'</span>';
            select.onclick = () => selectSession(session.id,session.title);
            const remove = document.createElement('button');
            remove.className = 'session-delete'; remove.disabled = isStreaming;
            remove.setAttribute('aria-label',session.title+' 대화 삭제');
            remove.innerHTML = '<i class="fa-regular fa-trash-can" aria-hidden="true"></i>';
            remove.onclick = () => deleteSession(session.id);
            item.append(select,remove); list.appendChild(item);
        }
    } catch (error) {
        if (requestId===sessionRequestId) list.innerHTML = '<p class="rail-empty">'+escapeHtml(error.message)+'</p>';
    }
}
/**
 * 새 대화 안내 template을 복사해 메시지 공간에 넣습니다. template 내용은 저장해 두었다가 필요할 때 화면에
 * 붙이는 HTML입니다.
 */
function renderWelcome() {
    const container = document.getElementById('messagesContainer');
    container.replaceChildren(document.getElementById('welcomeTemplate').content.cloneNode(true));
}
/**
 * 선택한 대화의 제목과 메시지를 읽습니다. 기다리는 동안 다른 대화를 선택했다면 이전 결과는 버립니다.
 */
async function selectSession(id,title) {
    if (isStreaming) return;
    // 요청을 보낼 때마다 번호를 올립니다. 나중에 돌아온 오래된 결과를 비교해 버리므로 화면 선택이 뒤로 되돌아가지
    // 않습니다.
    const requestId = ++selectionRequestId;
    currentSessionId = id;
    document.getElementById('currentSessionTitle').textContent = title || '대화';
    document.getElementById('messagesContainer').innerHTML = '<div class="loading-state">대화를 불러오는 중…</div>';
    toggleSidebar(false); loadSessions();
    try {
        const response = await apiRequest('/api/v1/chat/sessions/'+id+'/messages');
        if (!response.ok) throw new Error('대화를 불러오지 못했습니다.');
        const messages = await response.json();
        if (requestId!==selectionRequestId) return;
        document.getElementById('messagesContainer').replaceChildren();
        if (!messages.length) renderWelcome();
        messages.forEach(message => appendMessageBubble(message.role,message.content,message));
        scrollToBottom();
    } catch (error) {
        if (requestId===selectionRequestId) document.getElementById('messagesContainer').innerHTML = '<div class="empty-state">'+escapeHtml(error.message)+'</div>';
    }
}
/**
 * 현재 대화 ID를 비워 다음 첫 질문에서 서버가 새 대화를 만들게 합니다. 여기서는 DB에 빈 대화를 미리 만들지
 * 않습니다.
 */
function createNewSession() {
    if (isStreaming) return;
    ++selectionRequestId; currentSessionId = null;
    document.getElementById('currentSessionTitle').textContent = '새로운 질문을 시작하세요';
    document.getElementById('errorBanner').classList.add('hidden');
    renderWelcome(); loadSessions(); toggleSidebar(false); document.getElementById('chatInput').focus();
}
/**
 * 사용자 확인 후 대화 삭제 API를 호출합니다. 현재 대화를 삭제했다면 새 대화 안내로 돌아갑니다.
 */
async function deleteSession(id) {
    if (isStreaming || !confirm('이 대화와 질문·답변을 삭제할까요? 삭제한 기록은 복구할 수 없습니다.')) return;
    try {
        const response = await apiRequest('/api/v1/chat/sessions/'+id,{method:'DELETE'});
        if (!response.ok) throw new Error('삭제하지 못했습니다.');
        if (currentSessionId===id) createNewSession(); else loadSessions();
        showToast('대화를 삭제했습니다.');
    } catch (error) { showToast(error.message,'error'); }
}
/**
 * 질문/AI 답변을 서로 다른 모양으로 그립니다. 질문은 텍스트로, 답변은 정제한 Markdown으로 표시합니다.
 */
function appendMessageBubble(role,content,meta={}) {
    const element = document.createElement('article');
    element.className = 'message'+(role==='user'?' message-user':'');
    if (role==='user') {
        element.innerHTML = '<div class="user-bubble">'+escapeHtml(content)+'</div>';
    } else {
        element.innerHTML = '<div class="message-avatar" aria-hidden="true"><i class="fa-solid fa-leaf"></i></div><div class="message-content"><div class="message-label">현장노트 · AI 답변</div><div class="markdown-body">'+renderMarkdown(content)+'</div><div class="message-meta"><span>'+(meta.latency_ms?formatDuration(meta.latency_ms):'')+'</span><button class="copy-btn" onclick="copyMessageText(this)" aria-label="답변 텍스트 복사"><i class="fa-regular fa-copy" aria-hidden="true"></i> 복사</button></div></div>';
        element.dataset.content = content;
    }
    document.getElementById('messagesContainer').appendChild(element);
    return element;
}
/**
 * 답변이 오기 전에 대기 표시와 빈 말풍선을 만듭니다. 나중에 같은 element를 찾아 조각을 채웁니다.
 */
function appendAssistantStreamingBubble(id) {
    const element = appendMessageBubble('assistant','');
    element.id = id;
    const content = element.querySelector('.markdown-body');
    content.classList.add('content-area','typing-cursor');
    content.innerHTML = '<span class="thinking-label">질문을 살펴보고 있어요…</span>';
    element.querySelector('.message-meta').classList.add('hidden');
    return element;
}
/**
 * 지금까지 모인 전체 답변으로 말풍선을 갱신합니다. dataset.content에는 복사용 원문을 따로 보관합니다.
 */
function updateStreamingBubbleText(id,text) {
    const element = document.getElementById(id);
    if (!element) return;
    element.dataset.content = text;
    element.querySelector('.content-area').innerHTML = renderMarkdown(text);
}
/**
 * 스트림 커서를 없애고 완료/오류 상태와 시간을 표시합니다. 실제 완료 여부는 서버의 done 사건으로 구분합니다.
 */
function finishStreamingBubble(id,text,latency,status) {
    const element = document.getElementById(id);
    if (!element) return;
    updateStreamingBubbleText(id,text);
    element.querySelector('.content-area').classList.remove('typing-cursor');
    element.querySelector('.message-meta').classList.remove('hidden');
    element.querySelector('.message-meta span').textContent = (latency?formatDuration(latency)+' · ':'')+(status==='success'?'답변 완료':'답변 확인 필요');
}
/**
 * 답변 수신 중 입력·대화 변경·삭제 버튼을 잠급니다. 같은 연결 중 대화를 바꾸어 답변이 섞이는 것을 막습니다.
 */
function setStreamingState(streaming) {
    setAISettingsDisabled(streaming);
    isStreaming = streaming;
    const button = document.getElementById('sendBtn');
    button.disabled = streaming;
    button.setAttribute('aria-label',streaming?'답변을 받는 중':'질문 보내기');
    button.innerHTML = '<i class="fa-solid '+(streaming?'fa-spinner fa-spin':'fa-arrow-up')+'" aria-hidden="true"></i>';
    document.getElementById('chatInput').readOnly = streaming;
    document.getElementById('chatForm').setAttribute('aria-busy',String(streaming));
    document.querySelectorAll('.new-chat,.session-select,.session-delete,.topic-card').forEach(item => item.disabled = streaming);
}
/**
 * 질문을 POST로 보내고 응답 스트림을 읽습니다. meta로 대화를 연결하고 text로 화면을 갱신하며 done으로 완료를
 * 확인합니다.
 */
async function handleChatSubmit(event) {
    event.preventDefault();
    if (isStreaming) return;
    const input = document.getElementById('chatInput'), message = input.value.trim();
    if (!message) return;
    let aiOptions;
    try { aiOptions = getAIRequestOptions(); }
    catch (error) { showErrorBanner(error.message); return; }
    ++selectionRequestId;
    input.value = ''; autoResizeTextarea(input);
    document.getElementById('welcomeHero')?.remove();
    document.getElementById('errorBanner').classList.add('hidden');
    appendMessageBubble('user',message);
    const bubbleId = 'ai-stream-'+Date.now();
    appendAssistantStreamingBubble(bubbleId); setStreamingState(true); scrollToBottom();
    let fullText = '', finished = false;
    try {
        const headers = {'Content-Type':'application/json'}, token = getToken();
        if (token) headers.Authorization = 'Bearer '+token;
        const response = await fetch(getApiUrl('/api/v1/chat/stream'),{
            method:'POST',headers,body:JSON.stringify({message,session_id:currentSessionId,...aiOptions})
        });
        if (response.status===401) { removeToken(); window.location.href='login.html'; throw new Error('다시 로그인해 주세요.'); }
        if (response.status===429) {
            const retryAfter = Number(response.headers.get('Retry-After'));
            const errorData = await response.json().catch(()=>({}));
            const detail = typeof errorData.detail === 'string' ? errorData.detail : '요청이 많습니다.';
            throw new Error(detail + (retryAfter > 0 ? ' 약 '+Math.ceil(retryAfter)+'초 뒤 다시 시도할 수 있어요.' : ' 잠시 후 다시 시도해 주세요.'));
        }
        if (!response.ok) throw new Error('요청을 처리하지 못했습니다. (HTTP '+response.status+')');
        // body는 아직 내려오는 응답의 통로입니다. reader는 조각을 읽고 TextDecoder는 나뉘어 도착한
        // UTF-8 바이트를 글자로 이어 줍니다.
        const reader = response.body.getReader(), decoder = new TextDecoder();
        let buffer = '';
        /**
         * 빈 줄로 구분된 SSE 한 사건에서 event 이름과 data JSON을 읽습니다. 한 네트워크 조각에 여러
         * 사건이 있어도 각각 처리합니다.
         */
        function processEvent(block) {
            let type = 'message';
            const data = [];
            for (const line of block.split('\n')) {
                if (line.startsWith('event:')) type = line.slice(6).trim();
                if (line.startsWith('data:')) data.push(line.slice(5).trim());
            }
            if (!data.length) return;
            const value = JSON.parse(data.join('\n'));
            if (type==='meta' && !currentSessionId) {
                currentSessionId = value.session_id;
                document.getElementById('currentSessionTitle').textContent = value.session_title;
                loadSessions();
            } else if (type==='done') {
                finished = true; finishStreamingBubble(bubbleId,fullText,value.latency_ms,value.status);
                renderSearchResult(bubbleId,value.search,value.search_suggestions);
            } else if (type==='error') { showErrorBanner(value.message || '답변 중 오류가 발생했습니다.'); }
            else if (value.text) { fullText += value.text; updateStreamingBubbleText(bubbleId,fullText); scrollToBottom(); }
        }
        while (true) {
            const {done,value} = await reader.read();
            // 한 조각이 사건/한글 문자 중간에서 끝날 수 있어 남은 내용을 버리지 않고 다음 조각과 합칩니다.
            buffer = (buffer + decoder.decode(value || new Uint8Array(),{stream:!done})).replace(/\r\n/g,'\n');
            let boundary;
            // SSE의 빈 줄 두 개가 사건 끝입니다. 한 읽기에 여러 사건이 들어와도 모두 차례로 처리합니다.
            while ((boundary=buffer.indexOf('\n\n'))>=0) {
                const block = buffer.slice(0,boundary); buffer = buffer.slice(boundary+2);
                if (block.trim()) processEvent(block);
            }
            if (done) break;
        }
        if (buffer.trim()) processEvent(buffer);
        // 연결이 끊겼다고 정상 완료는 아닙니다. 서버의 done 사건을 받아야 답변 저장까지 완료됐다고 판단합니다.
        if (!finished) throw new Error('답변 연결이 종료되었습니다. 잠시 후 다시 질문해 주세요.');
    } catch (error) {
        showErrorBanner(error.message || '서버 연결을 확인해 주세요.');
        finishStreamingBubble(bubbleId,fullText || '답변을 받지 못했습니다. 잠시 후 다시 질문해 주세요.',null,'error');
    // 성공/오류와 관계없이 입력 잠금을 풀어 다음 질문을 보낼 수 있게 합니다.
    } finally { setStreamingState(false); input.focus(); loadSessions(); }
}

/** 검색 설정과 실제 반환된 근거를 구분해 표시합니다. 출처 본문은 DB에 함께 저장됩니다. */
function renderSearchResult(bubbleId, search, suggestions) {
    const bubble = document.getElementById(bubbleId);
    if (!bubble || !search?.requested) return;
    const content = bubble.querySelector('.message-content') || bubble;
    const status = document.createElement('div');
    status.className = 'search-result-status';
    status.textContent = search.executed ? '웹 검색 확인 · 출처 '+search.source_count+'개' : '이 답변에서 검색 근거가 반환되지 않았어요';
    content.append(status);
    if (suggestions) {
        // 공급자 HTML은 본문 DOM에 넣지 않고 스크립트/동일출처 접근이 막힌 프레임에서 표시합니다.
        const frame = document.createElement('iframe');
        frame.className = 'search-suggestions';
        frame.title = 'Google 검색 제안';
        frame.setAttribute('sandbox','allow-popups allow-popups-to-escape-sandbox');
        frame.srcdoc = suggestions;
        content.append(frame);
    }
}
/**
 * 채팅 화면에 오류 문장을 텍스트로 표시합니다. 서버나 연결 오류를 사용자가 볼 수 있게 합니다.
 */
function showErrorBanner(message) {
    document.getElementById('errorBannerText').textContent = message;
    document.getElementById('errorBanner').classList.remove('hidden');
}
/**
 * 메시지 영역의 스크롤을 맨 아래로 옮겨 새 답변을 보이게 합니다. 문서 전체 스크롤과는 별개입니다.
 */
function scrollToBottom() { const container=document.getElementById('messagesContainer'); container.scrollTop=container.scrollHeight; }
/**
 * 말풍선의 원문을 클립보드로 복사합니다. 브라우저 권한 때문에 실패하면 직접 선택해 복사하도록 안내합니다.
 */
async function copyMessageText(button) {
    const content = button.closest('.message')?.dataset.content;
    try { await navigator.clipboard.writeText(content || ''); showToast('답변을 복사했습니다.','success'); }
    catch { showToast('복사하지 못했습니다. 답변을 직접 선택해 복사해 주세요.','error'); }
}
