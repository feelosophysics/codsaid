# 요청 제한과 JWT 최소 조건을 검증합니다. 일부러 시간을 움직이거나 많은 동시 요청을 만들어 경계를 검사합니다.
# parametrize는 같은 시험을 여러 입력 조합으로 반복하고, 가짜 시계/AI는 실제 대기·API 비용 없이 조건을
# 재현합니다.
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.v1 import auth, chat
from app.core import abuse, config
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User


# 입력 조합별로 같은 검사를 반복합니다. 실제 운영 키 대신 시험용 값으로 경계 조건을 확인합니다.
@pytest.mark.parametrize("environment", ["production", "prod"])
# 입력 조합별로 같은 검사를 반복합니다. 실제 운영 키 대신 시험용 값으로 경계 조건을 확인합니다.
@pytest.mark.parametrize("key", [config.DEVELOPMENT_SECRET_KEY, "", "audit-short"])
def test_production_rejects_default_empty_or_short_key(environment, key):
    """운영 환경 이름과 잘못된 키 조합별로 서버 설정의 시작 검사가 실패해야 하는지 확인합니다.
    """
    settings = config.Settings(_env_file=None, APP_ENV=environment, SECRET_KEY=key)
    with pytest.raises(RuntimeError) as error:
        settings.validate_production_security()
    assert str(error.value) == "Production SECRET_KEY must be a unique random key of at least 32 bytes."


def test_get_settings_enforces_security_without_echoing_key(monkeypatch):
    """설정 로딩의 보안 검사가 작동하고 실패 예외에 키 원문이 섞이지 않는지 확인합니다.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "audit-private-short-sentinel")
    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as error:
            config.get_settings()
        assert "audit-private-short-sentinel" not in str(error.value)
    finally:
        config.get_settings.cache_clear()


def test_random_length_key_and_development_settings_still_work():
    """충분한 길이의 시험 키와 개발 설정이 허용되는지 검사합니다. 시험 값의 실제 랜덤성까지 증명하는 것은 아닙니다.
    """
    config.Settings(_env_file=None, APP_ENV="production", SECRET_KEY="audit-only-long-key-for-isolated-settings-check").validate_production_security()
    config.Settings(_env_file=None, APP_ENV="development").validate_production_security()


# 입력 조합별로 같은 검사를 반복합니다. 실제 운영 키 대신 시험용 값으로 경계 조건을 확인합니다.
@pytest.mark.parametrize("key,passed", [
    ("audit-only-long-key-for-isolated-settings-check", True),
    (config.DEVELOPMENT_SECRET_KEY, False),
    ("audit-private-short-sentinel", False),
])
def test_security_check_script_reports_booleans_without_secret_or_db(tmp_path, key, passed):
    """별도 프로세스로 점검 CLI를 실행해 boolean만 출력하고 키/DB를 노출하거나 만들지 않는지 검사합니다.
    """
    repo = Path(__file__).resolve().parents[1]
    environment = dict(os.environ, APP_ENV="production", SECRET_KEY=key,
                       GEMINI_API_KEY="audit-only-private-ai-sentinel",
                       DATABASE_URL="sqlite:///" + (tmp_path / "must-not-exist.db").as_posix())
    result = subprocess.run([sys.executable, str(repo / "scripts/check_security_config.py")],
                            cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == (0 if passed else 1)
    assert json.loads(result.stdout)["baseline_passed"] is passed
    assert key not in result.stdout + result.stderr
    assert "audit-only-private-ai-sentinel" not in result.stdout + result.stderr
    assert result.stderr == "" and not (tmp_path / "must-not-exist.db").exists()


def limits(**changes):
    """시험에 필요한 기본 제한값을 만들고 특정 조건만 바꿉니다. 운영 설정을 수정하는 함수가 아닙니다.
    """
    values = dict(CHAT_USER_CONCURRENCY=1, CHAT_GLOBAL_CONCURRENCY=3,
                  CHAT_REQUESTS_PER_MINUTE=6, CHAT_GLOBAL_REQUESTS_PER_MINUTE=20)
    values.update(changes)
    return SimpleNamespace(**values)


def test_sliding_window_retry_and_expiration():
    """가짜 시계를 움직여 제한 초과의 대기시간과 60초 뒤 요청 허용을 확인합니다.
    """
    now = [100.0]
    guard = abuse.RequestGuard(clock=lambda: now[0])
    guard.admit_auth("login", "peer", 2)
    now[0] = 101.2
    guard.admit_auth("login", "peer", 2)
    with pytest.raises(abuse.LimitExceeded) as error:
        guard.admit_auth("login", "peer", 2)
    assert error.value.retry_after == 59
    now[0] = 160.0
    guard.admit_auth("login", "peer", 2)
    assert len(guard.windows[("login", "peer")]) == 2


def test_identity_storage_is_bounded_and_expired_peers_are_removed():
    """추적할 접속자 수의 상한을 넘기면 거절하고, 만료된 접속자 정보는 메모리에서 제거하는지 검사합니다.
    """
    now = [0.0]
    guard = abuse.RequestGuard(clock=lambda: now[0], max_buckets=2)
    guard.admit_auth("login", "a", 1)
    guard.admit_auth("login", "b", 1)
    with pytest.raises(abuse.LimitExceeded) as error:
        guard.admit_auth("login", "c", 1)
    assert error.value.reason == "limiter_capacity" and len(guard.windows) == 2
    now[0] = 60.0
    guard.admit_auth("login", "c", 1)
    assert list(guard.windows) == [("login", "c")]


def test_failed_global_admission_does_not_consume_user_budget_or_slot():
    """전체 한도로 거절된 요청이 개인 예산이나 동시 슬롯까지 소비하지 않는지 검사합니다.
    """
    guard = abuse.RequestGuard()
    settings = limits(CHAT_GLOBAL_REQUESTS_PER_MINUTE=1)
    guard.admit_chat(1, settings).release()
    with pytest.raises(abuse.LimitExceeded):
        guard.admit_chat(2, settings)
    assert ("chat_user", 2) not in guard.windows
    assert guard.active_total == 0 and guard.active_users == {}


def test_parallel_admission_obeys_global_capacity_and_idempotent_release():
    """동시 스레드 경쟁에서도 전체 용량을 넘지 않고, 슬롯을 두 번 반환해도 수가 잘못 줄지 않는지 검사합니다.
    """
    guard = abuse.RequestGuard()
    def acquire(user_id):
        """여러 스레드가 동시에 슬롯을 얻도록 시도합니다. ThreadPoolExecutor에서 호출해 경쟁 상황의
        제한 동작을 확인합니다.
        """
        try:
            return guard.admit_chat(user_id, limits())
        except abuse.LimitExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        leases = [lease for lease in pool.map(acquire, range(8)) if lease is not None]
    assert len(leases) == guard.active_total == 3
    for lease in leases:
        lease.release()
        lease.release()
    assert guard.active_total == 0 and guard.active_users == {}


def successful_ai(monkeypatch):
    """항상 성공하는 가짜 AI를 연결합니다. 제한 거절 시 이 함수가 호출되지 않았는지 검사할 때 사용합니다.
    """
    calls = []
    async def respond(**kwargs):
        """가짜 답변 한 조각과 완료 상태를 만들어 줍니다. 실제 Google 요청 없이 API의 저장·제한 처리를
        시험합니다.
        """
        calls.append(kwargs)
        yield {"text": "", "done": True, "full_text": "audit answer", "latency_ms": 1, "error": None}
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", respond)
    return calls


def test_register_rate_limit_precedes_password_hash_and_user_insert(isolated_chat, monkeypatch):
    """가입 제한 초과 시 비용이 큰 비밀번호 해시와 DB 저장이 실행되지 않는지 검사합니다.
    """
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "REGISTER_REQUESTS_PER_MINUTE", 1)
    abuse.guard = abuse.RequestGuard()
    hashing = Mock(wraps=auth.get_password_hash)
    monkeypatch.setattr(auth, "get_password_hash", hashing)
    first = client.post("/api/v1/auth/register", json={"username": "new_a", "nickname": "A", "password": "auditPassword123"})
    second = client.post("/api/v1/auth/register", json={"username": "new_b", "nickname": "B", "password": "auditPassword123"})
    assert first.status_code == 201 and second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1 and hashing.call_count == 1
    with factory() as db:
        assert db.scalar(select(func.count(User.id))) == 2


def test_login_failures_count_and_forwarded_header_cannot_reset_budget(isolated_chat, monkeypatch):
    """실패 로그인도 횟수에 들어가고 임의 전달 헤더로 접속 IP 제한을 우회할 수 없는지 검사합니다.
    """
    client, _, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "LOGIN_REQUESTS_PER_MINUTE", 1)
    abuse.guard = abuse.RequestGuard()
    verifying = Mock(wraps=auth.verify_password)
    monkeypatch.setattr(auth, "verify_password", verifying)
    first = client.post("/api/v1/auth/login", json={"username": "reliability_user", "password": "wrong-audit-password"}, headers={"X-Forwarded-For": "192.0.2.1"})
    second = client.post("/api/v1/auth/login", json={"username": "reliability_user", "password": "auditPassword123"}, headers={"X-Forwarded-For": "192.0.2.2"})
    assert first.status_code == 401 and second.status_code == 429
    assert verifying.call_count == 1
    # 비밀번호 변경도 로그인과 같은 IP별 인증 예산을 쓰는지 확인합니다.
    assert client.put("/api/v1/auth/password", json={"current_password": "auditPassword123", "new_password": "auditPassword456"}).status_code == 429


def test_chat_rate_rejection_does_not_save_question_or_call_ai(isolated_chat, monkeypatch, caplog):
    """채팅 제한 초과 시 429·거절 로그가 오고 질문 저장이나 AI 호출은 발생하지 않는지 검사합니다.
    """
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "CHAT_REQUESTS_PER_MINUTE", 1)
    calls = successful_ai(monkeypatch)
    assert client.post("/api/v1/chat/stream", json={"message": "first"}).status_code == 200
    caplog.clear()
    denied = client.post("/api/v1/chat/stream", json={"message": "denied"}, headers={"Origin": "https://b7-1-chat-fe.vercel.app", "X-Request-ID": "rate-denied"})
    assert denied.status_code == 429 and "요청이 너무 많습니다" in denied.json()["detail"]
    assert int(denied.headers["Retry-After"]) >= 1
    assert "Retry-After" in denied.headers["Access-Control-Expose-Headers"]
    assert len(calls) == 1 and abuse.guard.active_total == 0
    assert "request_rejected" in caplog.text and "request_id=rate-denied" in caplog.text
    assert "db_save_success" not in caplog.text
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 2
        assert db.scalar(select(func.count(ChatSession.id))) == 1


def test_global_chat_rate_applies_across_users(isolated_chat, monkeypatch):
    """여러 사용자로 요청해도 전체 횟수 예산이 하나로 적용되는지 검사합니다.
    """
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "CHAT_GLOBAL_REQUESTS_PER_MINUTE", 1)
    calls = successful_ai(monkeypatch)
    assert client.post("/api/v1/chat/stream", json={"message": "first"}).status_code == 200
    with TestClient(app) as other:
        assert other.post("/api/v1/auth/register", json={"username": "other_audit", "nickname": "B", "password": "auditPassword123"}).status_code == 201
        assert other.post("/api/v1/auth/login", json={"username": "other_audit", "password": "auditPassword123"}).status_code == 200
        assert other.post("/api/v1/chat/stream", json={"message": "denied"}).status_code == 429
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 2
    assert len(calls) == 1 and abuse.guard.active_total == 0


@pytest.mark.asyncio
# 입력 조합별로 같은 검사를 반복합니다. 실제 운영 키 대신 시험용 값으로 경계 조건을 확인합니다.
@pytest.mark.parametrize("cancel", [False, True])
async def test_active_stream_blocks_same_user_and_releases_after_completion_or_cancel(
    isolated_chat, monkeypatch, cancel
):
    """스트림 진행 중 같은 사용자의 새 요청이 거절되고 완료/취소 뒤에는 슬롯을 다시 쓸 수 있는지 검사합니다.
    """
    client, factory, _ = isolated_chat
    started, finish = asyncio.Event(), asyncio.Event()
    async def slow_ai(**kwargs):
        """가짜 AI 답변을 잠시 멈춰 진행 중인 연결을 만듭니다. 같은 사용자의 두 번째 요청이 거절되는지 확인하는
        조건입니다.
        """
        started.set()
        await finish.wait()
        yield {"text": "", "done": True, "full_text": "audit answer", "latency_ms": 1, "error": None}
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", slow_ai)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", cookies=client.cookies) as browser:
        first = asyncio.create_task(browser.post("/api/v1/chat/stream", json={"message": "first"}))
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            assert abuse.guard.active_total == 1
            denied = await browser.post("/api/v1/chat/stream", json={"message": "denied"})
            assert denied.status_code == 429 and denied.headers["Retry-After"] == "1"
            with factory() as db:
                assert db.scalar(select(func.count(ChatMessage.id))) == 1
            if cancel:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            else:
                finish.set()
                assert (await first).status_code == 200
            assert abuse.guard.active_total == 0
            finish.set()
            assert (await browser.post("/api/v1/chat/stream", json={"message": "after"})).status_code == 200
            assert abuse.guard.active_total == 0
        finally:
            finish.set()
            if not first.done():
                first.cancel()
            await asyncio.gather(first, return_exceptions=True)


@pytest.mark.asyncio
async def test_capacity_is_held_until_asgi_send_finishes_or_is_cancelled():
    """응답 객체를 만든 시점이 아닌 실제 전송 완료/취소 시점까지 동시 슬롯이 유지되는지 검사합니다.
    """
    guard = abuse.RequestGuard()
    started = asyncio.Event()
    async def send_blocked(scope, receive, send):
        """응답 전송이 끝나지 않은 상황을 흉내 냅니다. API 함수가 끝나도 네트워크 전송이 남으면 슬롯을 유지해야
        합니다.
        """
        scope["state"]["chat_lease"] = guard.admit_chat(1, limits())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        started.set()
        await asyncio.Event().wait()
    async def send(message):
        """시험용 ASGI 전송 함수를 대체합니다. 준비한 신호를 기다려 전송이 멈추거나 취소되는 경계를 만듭니다.
        """
        pass
    task = asyncio.create_task(abuse.ChatLeaseMiddleware(send_blocked)({"type": "http", "state": {}}, None, send))
    await asyncio.wait_for(started.wait(), timeout=1)
    assert guard.active_total == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert guard.active_total == 0
