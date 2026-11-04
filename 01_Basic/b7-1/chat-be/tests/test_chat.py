# 세션 생성 → 질문 → SSE 답변 → 메시지 조회로 이어지는 API 흐름을 확인합니다.
# Mock는 실제 Google 대신 정해진 답변을 내는 대역입니다. Mock 성공은 실제 Google 호출 성공의 증거가
# 아닙니다.
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app


def test_chat_pipeline():
    """새 대화의 질문·SSE 완료·DB 메시지 조회가 이어지는지 검사합니다. Mock 응답으로 API 연결 흐름을
    확인합니다.
    """
    client = TestClient(app)
    # 1. 시험용 계정을 만들고 로그인합니다.
    username = f"chatuser_{int(time.time())}"
    password = "chatPassword123"

    client.post("/api/v1/auth/register", json={"username": username, "nickname": "채팅테스터", "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200

    # 2. 시험용 대화를 만듭니다.
    session_res = client.post("/api/v1/chat/sessions", json={"title": "FastAPI 질문 세션"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 3. 시험용 SSE 채팅 요청을 보냅니다.
    stream_res = client.post(
        "/api/v1/chat/stream",
        json={"message": "FastAPI의 장점은 무엇인가요?", "session_id": session_id}
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    assert "event: meta" in stream_res.text
    assert "event: done" in stream_res.text

    # 4. 저장된 대화 메시지를 다시 조회합니다.
    msg_res = client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert msg_res.status_code == 200
    messages = msg_res.json()
    assert len(messages) >= 2  # 질문과 답변을 합한 개수입니다.

    # 5. 기록 조회 API를 확인합니다.
    logs_res = client.get("/api/v1/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()["items"]
    assert len(logs) >= 2
