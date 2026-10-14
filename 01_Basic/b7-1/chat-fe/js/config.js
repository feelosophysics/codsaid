/**
 * 프론트가 접속할 백엔드 주소를 정합니다. localhost는 지금 브라우저가 실행되는 컴퓨터를 뜻합니다.
 * 배포 사이트에서는 EC2 HTTPS 주소를 사용합니다. 브라우저에 AI 키를 넣지 않고 질문을 백엔드로 보냅니다.
 */
// 배포 백엔드의 HTTPS 주소입니다. /api/v1 경로는 붙이지 않습니다.
const DEPLOYED_API_BASE_URL = 'https://b71chatbe.ddns.net';
// 배포 페이지의 localhost는 EC2가 아니라 접속자의 컴퓨터입니다. 개발 호스트일 때만 로컬 API를 선택합니다.
const isLocal = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(window.location.hostname);

const CONFIG = {
    API_BASE_URL: isLocal ? 'http://localhost:8000' : DEPLOYED_API_BASE_URL.replace(/\/+$/, ''),
    APP_NAME: '현장노트 · 건설 지식 AI 어시스턴트',
    VERSION: '1.1.0'
};

/**
 * 공통 백엔드 주소와 API 경로를 합칩니다. 배포 주소가 없거나 HTTPS가 아니면 요청 전에 안내 오류를 냅니다.
 */
function getApiUrl(endpoint) {
    if (!CONFIG.API_BASE_URL || (!isLocal && !CONFIG.API_BASE_URL.startsWith('https://'))) {
        throw new Error('서비스 연결을 준비 중입니다. 잠시 후 다시 시도해 주세요.');
    }
    return `${CONFIG.API_BASE_URL}${endpoint}`;
}
