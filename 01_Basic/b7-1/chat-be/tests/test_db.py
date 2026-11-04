# DB 표의 관계와 삭제, 기록 페이지 나누기/필터, 통계를 확인합니다.
# 시험용 DB에서도 사용자·대화·메시지의 연결 규칙이 실제 API와 같아야 하므로 저장 후 다시 조회해 검사합니다.
import pytest
import time
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.core.security import get_password_hash


def test_database_models_and_relationships():
    """사용자·대화·메시지를 연결해 저장하고 관계로 다시 읽습니다. 대화 삭제가 메시지 정리에 이어지는지도 검사합니다.
    """
    init_db()
    db = SessionLocal()
    try:
        # 시험용 사용자를 만듭니다.
        username = f"dbuser_{int(time.time())}"
        user = User(username=username, nickname="DB테스트", password_hash=get_password_hash("pass123"))
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None

        # 시험용 대화 묶음을 만듭니다.
        session = ChatSession(user_id=user.id, title="DB 테스트 대화방")
        db.add(session)
        db.commit()
        db.refresh(session)
        assert session.id is not None

        # 한 대화에 질문과 답변을 각각 저장합니다.
        msg1 = ChatMessage(session_id=session.id, user_id=user.id, role="user", content="테스트 질문")
        msg2 = ChatMessage(session_id=session.id, user_id=user.id, role="assistant", content="테스트 답변", latency_ms=120)
        db.add_all([msg1, msg2])
        db.commit()

        # 객체 관계를 따라 저장된 행을 다시 읽을 수 있는지 확인합니다.
        retrieved_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert len(retrieved_session.messages) == 2
        assert retrieved_session.user.username == username

        # 대화 삭제 시 연결된 메시지도 함께 삭제되는지 확인합니다.
        db.delete(user)
        db.commit()

        deleted_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert deleted_session is None
    finally:
        db.close()


def test_log_pagination_and_session_filtering():
    """대화별 필터와 limit/offset 페이지 조건이 함께 작동하는지 검사합니다. 전체 개수와 페이지 내용은 구분해야
    합니다.
    """
    client = TestClient(app)
    username = f"loguser_{int(time.time())}"
    password = "LogPassword123"

    # 시험용 계정을 가입한 뒤 로그인합니다.
    client.post("/api/v1/auth/register", json={"username": username, "nickname": "로그테스터", "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200

    # 필터 비교를 위해 서로 다른 대화 두 개를 만듭니다.
    s1 = client.post("/api/v1/chat/sessions", json={"title": "세션 A"}).json()["id"]
    s2 = client.post("/api/v1/chat/sessions", json={"title": "세션 B"}).json()["id"]

    # 첫 번째 대화에 여러 질문을 저장합니다.
    client.post("/api/v1/chat/stream", json={"message": "질문 A-1", "session_id": s1})
    client.post("/api/v1/chat/stream", json={"message": "질문 A-2", "session_id": s1})

    # 두 번째 대화에 별도 질문을 저장해 필터 결과를 구분합니다.
    client.post("/api/v1/chat/stream", json={"message": "질문 B-1", "session_id": s2})

    # 첫 번째 대화의 기록만 반환하는지 확인합니다.
    res_s1 = client.get(f"/api/v1/logs?session_id={s1}")
    assert res_s1.status_code == 200
    data_s1 = res_s1.json()
    assert data_s1["total"] == 4  # 질문 2건과 답변 2건입니다.
    for item in data_s1["items"]:
        assert item["session_id"] == s1

    # 두 번째 대화의 기록만 반환하는지 확인합니다.
    res_s2 = client.get(f"/api/v1/logs?session_id={s2}")
    assert res_s2.status_code == 200
    data_s2 = res_s2.json()
    assert data_s2["total"] == 2  # 질문 1건과 답변 1건입니다.

    # 첫 항목부터 최대 두 개만 반환하는 페이지 조건을 확인합니다.
    page_res = client.get(f"/api/v1/logs?limit=2&offset=0")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["total"] >= 6
    assert len(page_data["items"]) == 2


def test_log_statistics_endpoint():
    """질문/답변/세션 수와 응답시간 통계를 생성한 시험 데이터와 대조합니다.
    """
    client = TestClient(app)
    username = f"statsuser_{int(time.time())}"
    password = "StatsPassword123"

    # 시험용 계정을 가입한 뒤 로그인합니다.
    client.post("/api/v1/auth/register", json={"username": username, "nickname": "통계테스터", "password": password})
    client.post("/api/v1/auth/login", json={"username": username, "password": password})

    # 대화를 만들고 가짜 AI 채팅을 실행해 통계용 기록을 저장합니다.
    sess_id = client.post("/api/v1/chat/sessions", json={"title": "통계 검증 세션"}).json()["id"]
    client.post("/api/v1/chat/stream", json={"message": "건설 안전 질문입니다.", "session_id": sess_id})

    # 통계 API의 결과를 준비한 시험 데이터와 대조합니다.
    stats_res = client.get("/api/v1/logs/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["total_messages"] >= 2
    assert stats["total_questions"] >= 1
    assert stats["total_answers"] >= 1
    assert stats["total_sessions"] >= 1
    assert stats["avg_latency_ms"] >= 0
    assert stats["success_rate_percent"] == 100.0


def test_statistics_aggregate_without_loading_bodies_and_preserve_user_scope(isolated_chat):
    """성공/실패·0/빈 소요시간·관리자 조회 범위를 비교하고 본문을 읽지 않는지도 확인합니다."""
    from sqlalchemy import event

    client, factory, engine = isolated_chat
    with factory() as db:
        owner = db.scalar(select(User).where(User.username == "reliability_user"))
        other = User(username="other_stats", nickname="Other", password_hash="unused")
        db.add(other)
        db.flush()
        other_id, owner_id = other.id, owner.id
        sessions = [ChatSession(user_id=owner_id, title="Owner"), ChatSession(user_id=other_id, title="Other")]
        db.add_all(sessions)
        db.flush()
        for _ in range(4):
            db.add(ChatMessage(user_id=owner_id, session_id=sessions[0].id, role="user", content="fixture"))
        for status, latency in [("success", 100), ("success", 101), ("success", 0), ("success", None), ("error", 900), ("timeout", 120)]:
            db.add(ChatMessage(user_id=owner_id, session_id=sessions[0].id, role="assistant", content="fixture", status=status, latency_ms=latency))
        db.add_all([
            ChatMessage(user_id=other_id, session_id=sessions[1].id, role="user", content="fixture"),
            ChatMessage(user_id=other_id, session_id=sessions[1].id, role="assistant", content="fixture", status="success", latency_ms=3000),
        ])
        db.commit()

    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        own = client.get(f"/api/v1/logs/stats?user_id={other_id}").json()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert own == dict(total_messages=10, total_questions=4, total_answers=6, total_sessions=1, avg_latency_ms=100, success_rate_percent=100.0)
    assert all("chat_messages.content" not in statement.lower() for statement in statements)
    with factory() as db:
        db.get(User, owner_id).is_admin = True
        db.commit()
    all_users = client.get("/api/v1/logs/stats").json()
    assert all_users == dict(total_messages=12, total_questions=5, total_answers=7, total_sessions=2, avg_latency_ms=1067, success_rate_percent=100.0)
    other_stats = client.get(f"/api/v1/logs/stats?user_id={other_id}").json()
    assert other_stats == dict(total_messages=2, total_questions=1, total_answers=1, total_sessions=1, avg_latency_ms=3000, success_rate_percent=100.0)
    empty = client.get("/api/v1/logs/stats?user_id=999999").json()
    assert empty == dict(total_messages=0, total_questions=0, total_answers=0, total_sessions=0, avg_latency_ms=0, success_rate_percent=100.0)

