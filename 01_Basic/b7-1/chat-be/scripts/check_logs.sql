-- SQL은 데이터베이스에 읽을 표와 조건을 요청하는 언어입니다. 아래 SELECT 문들은 데이터를 조회합니다.
-- 사용자와 대화 내용이 출력될 수 있으므로 운영 DB에 자동 실행하지 않습니다.
-- FROM은 읽을 표, JOIN은 연결, WHERE는 조건, GROUP BY는 묶음, ORDER BY는 정렬, LIMIT은
-- 최대 개수입니다.
-- ==========================================================
-- AI 챗봇 서비스 SQLite 실무 분석 & 감사 쿼리 스크립트 (check_logs.sql)
-- 평가자 또는 개발자가 SQLite CLI / DBeaver 등에서 직접 실행 가능
-- ==========================================================

-- 1. 등록된 모든 사용자 조회
SELECT 
    id, 
    username, 
    is_active, 
    is_admin,
    created_at 
FROM users 
ORDER BY id ASC;

-- 2. 사용자별 대화 세션 목록 조회
SELECT 
    s.id AS session_id, 
    u.username, 
    s.title, 
    s.created_at, 
    s.updated_at
FROM chat_sessions s
-- 같은 내부 번호를 기준으로 두 표를 연결합니다. 연결되는 행이 없는 항목은 JOIN 결과에서 빠집니다.
JOIN users u ON s.user_id = u.id
ORDER BY s.updated_at DESC;

-- 3. 최근 20개 대화 로그(질문/응답/지연시간/상태) 상세 조회
SELECT 
    m.id AS log_id,
    u.username,
    m.session_id,
    m.role,
    m.latency_ms,
    m.status,
    m.content,
    m.created_at
FROM chat_messages m
-- 같은 내부 번호를 기준으로 두 표를 연결합니다. 연결되는 행이 없는 항목은 JOIN 결과에서 빠집니다.
JOIN users u ON m.user_id = u.id
ORDER BY m.created_at DESC
LIMIT 20;

-- 4. 사용자별 질문/응답 통계 및 평균 AI 지연시간
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(CASE WHEN m.role = 'user' THEN 1 END) AS question_count,
    COUNT(CASE WHEN m.role = 'assistant' THEN 1 END) AS answer_count,
    ROUND(AVG(CASE WHEN m.role = 'assistant' AND m.status = 'success' THEN m.latency_ms ELSE NULL END), 1) AS avg_ai_latency_ms,
    COUNT(CASE WHEN m.status = 'error' THEN 1 END) AS error_count
FROM users u
-- 연결된 메시지가 없어도 왼쪽 표의 사용자/대화는 남겨 0건인 항목도 조회할 수 있게 합니다.
LEFT JOIN chat_messages m ON u.id = m.user_id
-- 같은 사용자/시간/세션별로 묶습니다. COUNT는 개수, AVG는 평균, MIN/MAX는 가장 이른/늦은 값을 구합니다.
GROUP BY u.id, u.username
ORDER BY question_count DESC;

-- 5. [심화] 가장 질문을 많이 한 상위 사용자 TOP 5 (Power Users)
SELECT 
    u.username,
    COUNT(m.id) AS total_user_questions,
    COUNT(DISTINCT m.session_id) AS total_sessions_used,
    MAX(m.created_at) AS last_active_at
FROM users u
-- 같은 내부 번호를 기준으로 두 표를 연결합니다. 연결되는 행이 없는 항목은 JOIN 결과에서 빠집니다.
JOIN chat_messages m ON u.id = m.user_id
WHERE m.role = 'user'
-- 같은 사용자/시간/세션별로 묶습니다. COUNT는 개수, AVG는 평균, MIN/MAX는 가장 이른/늦은 값을 구합니다.
GROUP BY u.id, u.username
ORDER BY total_user_questions DESC
LIMIT 5;

-- 6. [심화] 시간대별(Hour) AI 챗봇 호출 트래픽 및 부하 분포
SELECT 
    strftime('%H', created_at) AS hour_of_day,
    COUNT(*) AS total_requests,
    COUNT(CASE WHEN role = 'user' THEN 1 END) AS user_questions,
    ROUND(AVG(CASE WHEN role = 'assistant' THEN latency_ms END), 1) AS avg_latency_ms
FROM chat_messages
-- 같은 사용자/시간/세션별로 묶습니다. COUNT는 개수, AVG는 평균, MIN/MAX는 가장 이른/늦은 값을 구합니다.
GROUP BY hour_of_day
ORDER BY hour_of_day ASC;

-- 7. [심화] AI 응답 속도 SLA 및 지연시간 구간별 분포 (Performance Distribution)
SELECT 
    COUNT(CASE WHEN latency_ms < 3000 AND role = 'assistant' THEN 1 END) AS fast_responses_under_3s,
    COUNT(CASE WHEN latency_ms >= 3000 AND latency_ms < 7000 AND role = 'assistant' THEN 1 END) AS normal_responses_3_to_7s,
    COUNT(CASE WHEN latency_ms >= 7000 AND role = 'assistant' THEN 1 END) AS slow_responses_over_7s,
    COUNT(CASE WHEN status = 'error' THEN 1 END) AS total_errors,
    COUNT(CASE WHEN role = 'assistant' THEN 1 END) AS total_ai_responses
FROM chat_messages;

-- 8. [심화] 세션별 대화 턴 수(Turn Count) 및 활성도 요약
SELECT 
    s.id AS session_id,
    u.username,
    s.title,
    COUNT(m.id) AS turn_count,
    MIN(m.created_at) AS first_message_at,
    MAX(m.created_at) AS last_message_at
FROM chat_sessions s
-- 같은 내부 번호를 기준으로 두 표를 연결합니다. 연결되는 행이 없는 항목은 JOIN 결과에서 빠집니다.
JOIN users u ON s.user_id = u.id
-- 연결된 메시지가 없어도 왼쪽 표의 사용자/대화는 남겨 0건인 항목도 조회할 수 있게 합니다.
LEFT JOIN chat_messages m ON s.id = m.session_id
-- 같은 사용자/시간/세션별로 묶습니다. COUNT는 개수, AVG는 평균, MIN/MAX는 가장 이른/늦은 값을 구합니다.
GROUP BY s.id, u.username, s.title
ORDER BY turn_count DESC;

