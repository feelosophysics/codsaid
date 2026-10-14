"""AI 스트림 지연·취소와 DB 실패를 인위적으로 만들어 복구 동작을 확인합니다.
FakeStream은 Google 대신 조각을 보내거나 멈추는 대역이고, 실패 주입은 실제 DB 장애 없이 오류 경로를
시험하는 방법입니다.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from app.api.v1 import chat
from app.core import abuse
from app.core.database import get_db
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.services import gemini_service as gm


class FakeStream:
    """시험용 AI 스트림입니다. 조각별 지연·무한 대기·정리 지연을 재현해 타임아웃과 취소 동작을 검사합니다.
    """
    def __init__(self, steps, close_delay=0):
        """시험이 지정한 지연/문자열 목록과 정리 상태를 준비합니다. Event는 다른 비동기 실행과 시작/완료 신호를
        주고받는 도구입니다.
        """
        self.steps = iter(steps)
        self.close_delay = close_delay
        self.read_started = asyncio.Event()
        self.closed = False
        self.close_cancelled = False

    def __aiter__(self):
        """객체가 비동기 반복자로 사용될 때 자신을 반환합니다. async for가 이 객체를 따라 답변 조각을 받게
        합니다.
        """
        return self

    async def __anext__(self):
        """다음 가짜 조각을 기다렸다가 반환합니다. 더 없으면 StopAsyncIteration으로 반복 종료를
        알립니다.
        """
        try:
            delay, text = next(self.steps)
        except StopIteration:
            raise StopAsyncIteration
        self.read_started.set()
        # None은 값 없음입니다. 여기서는 끝나지 않는 가짜 대기를 뜻해 스트림이 멈춘 상황을 재현합니다.
        if delay is None:
            await asyncio.Event().wait()
        else:
            await asyncio.sleep(delay)
        return SimpleNamespace(text=text)

    async def aclose(self):
        """스트림 정리 과정을 흉내 내고 완료/취소 여부를 기록합니다. 정리가 너무 느려도 전체 처리가 무한히 멈추지
        않는지 검사합니다.
        """
        self.closed = True
        try:
            await asyncio.sleep(self.close_delay)
        except asyncio.CancelledError:
            self.close_cancelled = True
            raise


def fake_service(monkeypatch, stream, connection_delay=0, timeout=0.12):
    """키 없는 서비스를 만든 뒤 가짜 SDK를 넣습니다. 연결 지연·응답 지연·제한시간을 실제 API 없이 조절합니다.
    """
    monkeypatch.setattr(gm.settings, "GEMINI_API_KEY", "")
    service = gm.GeminiService()
    service.api_key = "fake-sdk-only"
    service.timeout_seconds = timeout
    service.search_timeout_seconds = timeout

    async def connect(**kwargs):
        """실제 네트워크 연결 대신 시험이 준비한 응답 스트림을 반환합니다. 일부 시험에서는 전달된 질문/설정도
        수집합니다.
        """
        await asyncio.sleep(connection_delay)
        return stream

    service._client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=connect))
    )
    return service


async def collect(service):
    """비동기 스트림의 조각을 끝까지 모읍니다. async for는 기다리며 하나씩 오는 데이터를 순회하는 문법입니다.
    """
    return [chunk async for chunk in service.stream_chat_response(1, "timeout-test", [], "test")]


@pytest.mark.asyncio
# 같은 시험을 여러 지연/오류 조건으로 반복합니다. 각 조합은 독립적인 시험 결과로 집계됩니다.
@pytest.mark.parametrize("connection_delay,steps,partial", [
    (0.5, [(0, "first")], ""),
    (0, [(None, "first")], ""),
    (0, [(0, "first"), (None, "second")], "first"),
    (0, [(0.03, "token")] * 20, "token"),
    (0.08, [(0.08, "first")], ""),
])
async def test_shared_timeout_covers_connection_and_all_reads(
    monkeypatch, caplog, connection_delay, steps, partial
):
    """연결 지연·첫 조각 전후 정지·계속 오는 조각 모두 하나의 전체 제한시간을 지키는지 검사합니다.
    """
    stream = FakeStream(steps)
    service = fake_service(monkeypatch, stream, connection_delay)
    chunks = await asyncio.wait_for(collect(service), timeout=0.8)
    final = chunks[-1]
    assert final["done"] and final["error"] == "AI_TIMEOUT"
    assert "AI_TIMEOUT" in final["full_text"]
    assert final["full_text"].startswith(partial)
    if connection_delay == 0:
        assert stream.closed
    assert "ai_call_failed" in caplog.text and "error=\"AI_TIMEOUT\"" in caplog.text
    assert "ai_call_success" not in caplog.text


@pytest.mark.asyncio
async def test_normal_stream_completes_and_closes(monkeypatch, caplog):
    """정상 스트림이 전체 답변과 성공 사건을 남기고 자원을 닫는지 검사합니다.
    """
    stream = FakeStream([(0.01, "one"), (0.01, "two")])
    chunks = await collect(fake_service(monkeypatch, stream))
    assert [chunk["text"] for chunk in chunks[:-1]] == ["one", "two"]
    assert chunks[-1]["full_text"] == "onetwo" and chunks[-1]["error"] is None
    assert stream.closed
    assert "ai_call_success" in caplog.text and "ai_call_failed" not in caplog.text


@pytest.mark.asyncio
async def test_timeout_does_not_cancel_consumer_between_chunks(monkeypatch):
    """조각을 받은 호출자가 처리하는 동안 서비스의 타임아웃이 호출자까지 뜻밖에 취소하지 않는지 검사합니다.
    """
    stream = FakeStream([(0, "first"), (0, "second")])
    service = fake_service(monkeypatch, stream, timeout=0.04)
    response = service.stream_chat_response(1, "consumer-delay", [], "test")
    assert (await anext(response))["text"] == "first"
    await asyncio.sleep(0.08)
    rest = [chunk async for chunk in response]
    assert rest[-1]["error"] == "AI_TIMEOUT"
    assert not any(chunk["text"] == "second" for chunk in rest)
    assert stream.closed


@pytest.mark.asyncio
async def test_caller_cancellation_propagates_and_closes(monkeypatch, caplog):
    """사용자 연결 취소가 서비스에도 전달되고 스트림은 닫히며 가짜 성공으로 기록되지 않는지 검사합니다.
    """
    stream = FakeStream([(None, "first")])
    service = fake_service(monkeypatch, stream, timeout=5)
    task = asyncio.create_task(collect(service))
    await asyncio.wait_for(stream.read_started.wait(), timeout=0.8)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stream.closed
    assert "ai_call_failed" not in caplog.text and "ai_call_success" not in caplog.text


@pytest.mark.asyncio
async def test_slow_cleanup_is_bounded_and_keeps_timeout_result(monkeypatch, caplog):
    """정리가 오래 걸려도 최대 정리시간 뒤 끝나고 원래 타임아웃 오류가 유지되는지 검사합니다.
    """
    stream = FakeStream([(None, "first")], close_delay=5)
    service = fake_service(monkeypatch, stream, timeout=0.04)
    chunks = await asyncio.wait_for(collect(service), timeout=1.8)
    assert chunks[-1]["error"] == "AI_TIMEOUT"
    assert stream.closed and stream.close_cancelled
    assert "ai_stream_close_failed" in caplog.text


# 같은 시험을 여러 지연/오류 조건으로 반복합니다. 각 조합은 독립적인 시험 결과로 집계됩니다.
@pytest.mark.parametrize("failure,existing_session,endpoint", [
    ("session_insert", False, "/api/v1/chat/stream"),
    ("question_insert", False, "/api/v1/chat/stream"),
    ("commit", False, "/api/v1/chat/stream"),
    ("question_insert", True, "/api/v1/chat/stream"),
    ("commit", True, "/api/v1/chat/stream"),
    ("session_insert", False, "/api/v1/chat/sessions"),
    ("commit", False, "/api/v1/chat/sessions"),
])
def test_initial_db_failure_rolls_back_and_returns_json(
    isolated_chat, monkeypatch, caplog, failure, existing_session, endpoint
):
    """세션/질문 저장 실패를 주입해 rollback·JSON 500·실패 로그·AI 미호출을 확인합니다.
    """
    client, factory, engine = isolated_chat
    payload = {"message": "private question"} if endpoint.endswith("stream") else {"title": "private title"}
    if existing_session:
        payload["session_id"] = client.post("/api/v1/chat/sessions", json={"title": "existing"}).json()["id"]
    with factory() as check:
        baseline_sessions = check.scalar(select(func.count(ChatSession.id)))
        original_updated = check.scalar(select(ChatSession.updated_at))

    db = factory()
    rollback = Mock(wraps=db.rollback)
    monkeypatch.setattr(db, "rollback", rollback)
    ai = Mock(side_effect=AssertionError("AI must not run after initial DB failure"))
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", ai)

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        """특정 DB INSERT 시 오류를 일으켜 저장 실패를 재현합니다. 실제 운영 DB를 고장 내는 방식은
        아닙니다.
        """
        table = "chat_sessions" if failure == "session_insert" else "chat_messages"
        if statement.startswith("INSERT INTO " + table):
            raise OperationalError("private SQL", {"question": "private question"}, RuntimeError("injected"))

    if failure == "commit":
        monkeypatch.setattr(db, "commit", Mock(side_effect=OperationalError("private SQL", None, RuntimeError("injected"))))
    else:
        event.listen(engine, "before_cursor_execute", fail_insert)

    def db_dependency():
        """시험용 DB 작업 공간을 API에 제공하고 사용 후 닫습니다. 운영 get_db 대신 시험 동안만
        연결됩니다.
        """
        yield db

    app.dependency_overrides[get_db] = db_dependency
    caplog.clear()
    try:
        response = client.post(endpoint, json=payload, headers={"X-Request-ID": "db-failure-test"})
        assert response.status_code == 500
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": chat.DB_SAVE_ERROR_DETAIL}
        assert response.headers["X-Request-ID"] == "db-failure-test"
        assert rollback.called and not ai.called
        assert abuse.guard.active_total == 0
        assert "db_save_failed" in caplog.text and "request_id=db-failure-test" in caplog.text
        assert "db_save_success" not in caplog.text
        assert "private SQL" not in caplog.text and "private question" not in caplog.text
        with factory() as check:
            assert check.scalar(select(func.count(ChatSession.id))) == baseline_sessions
            assert check.scalar(select(func.count(ChatMessage.id))) == 0
            assert check.scalar(select(ChatSession.updated_at)) == original_updated
        # rollback 뒤에도 같은 작업 공간을 다시 사용할 수 있는지 확인합니다.
        assert db.scalar(select(func.count(ChatMessage.id))) == 0
    finally:
        if failure != "commit":
            event.remove(engine, "before_cursor_execute", fail_insert)
        db.close()


# 같은 시험을 여러 지연/오류 조건으로 반복합니다. 각 조합은 독립적인 시험 결과로 집계됩니다.
@pytest.mark.parametrize("timeout", [False, True])
def test_sse_result_and_save_events_survive_transaction_changes(
    isolated_chat, monkeypatch, caplog, timeout
):
    """정상/실패/타임아웃 AI 결과가 질문 보존·답변 저장·SSE 계약·성공/실패 로그에 올바르게 이어지는지 검사합니다.
    """
    client, factory, _ = isolated_chat
    stream = FakeStream([(0, "first"), (None, "second")] if timeout else [(0, "answer")])
    service = fake_service(monkeypatch, stream, timeout=0.05 if timeout else 0.5)
    monkeypatch.setattr(chat, "gemini_service", service)
    caplog.clear()
    response = client.post(
        "/api/v1/chat/stream", json={"message": "question"},
        headers={"X-Request-ID": "sse-save-test"}
    )
    assert response.status_code == 200
    assert "event: meta" in response.text and "event: done" in response.text
    data = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert data[-1]["error"] == ("AI_TIMEOUT" if timeout else None)
    assert data[-1]["status"] == ("error" if timeout else "success")
    with factory() as db:
        messages = db.scalars(select(ChatMessage).order_by(ChatMessage.id)).all()
        assert len(messages) == 2 and [m.role for m in messages] == ["user", "assistant"]
        assert messages[1].status == data[-1]["status"]
        assert messages[1].error_message == data[-1]["error"]
        assert messages[1].id == data[-1]["message_id"]
        assert messages[0].id == data[0]["user_message_id"]
        assert messages[0].session_id == data[0]["session_id"]
        assert messages[1].content.startswith("first" if timeout else "answer")
        assert messages[1].latency_ms is not None
    events = [record.getMessage() for record in caplog.records if "db_save_success" in record.getMessage()]
    assert len(events) == 3
    assert all("request_id=sse-save-test" in entry for entry in events)
    assert any("entity=session" in entry for entry in events)
    assert any("entity=user_message" in entry for entry in events)
    assert any("entity=assistant_message" in entry for entry in events)
    assert stream.closed
    assert abuse.guard.active_total == 0


def test_explicit_session_success_event(isolated_chat, caplog):
    """별도 세션 생성 API도 저장 확정 뒤 세션 성공 사건을 남기는지 검사합니다.
    """
    client, _, _ = isolated_chat
    caplog.clear()
    response = client.post("/api/v1/chat/sessions", json={"title": "new"}, headers={"X-Request-ID": "session-save-test"})
    assert response.status_code == 201 and response.json()["title"] == "new"
    assert response.json()["messages"] == []
    assert "db_save_success" in caplog.text
    assert "entity=session" in caplog.text and "request_id=session-save-test" in caplog.text


def test_followup_context_and_foreign_session_stay_isolated(isolated_chat, monkeypatch):
    """같은 대화의 후속 질문은 앞 문맥을 받고 다른 사용자 대화 번호는 가져오거나 삭제할 수 없는지 검사합니다.
    """
    client, _, _ = isolated_chat
    service = fake_service(monkeypatch, FakeStream([]), timeout=0.5)
    calls = []

    async def connect(**kwargs):
        """실제 네트워크 연결 대신 시험이 준비한 응답 스트림을 반환합니다. 일부 시험에서는 전달된 질문/설정도
        수집합니다.
        """
        calls.append(kwargs["contents"])
        return FakeStream([(0, "answer" + str(len(calls)))])

    service._client.aio.models.generate_content_stream = connect
    monkeypatch.setattr(chat, "gemini_service", service)

    def metadata(response):
        """SSE 문자열에서 meta 사건의 JSON을 꺼냅니다. 새 대화 번호와 제목이 이전 문맥/소유권 조건에
        맞는지 검사합니다.
        """
        assert response.status_code == 200 and "event: done" in response.text
        return json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith("data: ")))

    first = metadata(client.post("/api/v1/chat/stream", json={"message": "first question"}))
    session_id = first["session_id"]
    second = metadata(client.post("/api/v1/chat/stream", json={"message": "followup", "session_id": session_id}))
    assert second["session_id"] == session_id and second["session_title"] == "first question"
    assert [(m["role"], m["parts"][0]["text"]) for m in calls[1]] == [
        ("user", "first question"), ("model", "answer1"), ("user", "followup")
    ]

    with TestClient(app) as other:
        assert other.post("/api/v1/auth/register", json={
            "username": "other_user", "nickname": "Other", "password": "auditPassword123"
        }).status_code == 201
        assert other.post("/api/v1/auth/login", json={
            "username": "other_user", "password": "auditPassword123"
        }).status_code == 200
        assert other.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 404
        assert other.delete(f"/api/v1/chat/sessions/{session_id}").status_code == 404
        third = metadata(other.post("/api/v1/chat/stream", json={"message": "other question", "session_id": session_id}))
        # 존재하지 않거나 남의 대화 번호이면 내 소유의 새 대화를 만드는 기존 동작을 확인합니다.
        # 다른 사용자의 메시지를 내 AI 문맥으로 재사용하지 않아야 합니다.
        assert third["session_id"] != session_id
        assert calls[2] == [{"role": "user", "parts": [{"text": "other question"}]}]
        assert other.get(f"/api/v1/logs?session_id={session_id}").json()["total"] == 0
        assert other.get("/api/v1/logs").json()["total"] == 2
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 200
    assert len(client.get(f"/api/v1/chat/sessions/{session_id}/messages").json()) == 4
