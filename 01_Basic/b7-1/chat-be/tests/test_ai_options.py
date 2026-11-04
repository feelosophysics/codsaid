"""모델별 옵션 검사·동시 요청 격리·검색 제한을 가짜 SDK와 임시 DB로 검사합니다."""
import asyncio
from types import SimpleNamespace

import pytest
from google.genai import types
from sqlalchemy import func, select

from app.core.ai_models import MODEL_CHOICES
from app.models.chat import ChatMessage
from app.services import gemini_service as gm


def service_with_fake_sdk(monkeypatch, connect):
    """네트워크 대신 전달 인수를 관찰할 수 있는 가짜 SDK를 연결합니다."""
    monkeypatch.setattr(gm.settings, "GEMINI_API_KEY", "")
    service = gm.GeminiService()
    service.api_key = "fake-only"
    service._types = types
    service._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=connect)))
    return service


@pytest.mark.asyncio
async def test_concurrent_options_do_not_change_shared_defaults(monkeypatch):
    """두 요청이 서로 다른 모델·검색·추론·temperature를 사용해도 공유 기본값은 바뀌지 않습니다."""
    requests = []

    async def chunks():
        """조각 사이에 실행 기회를 양보해 두 요청이 실제로 겹치도록 합니다."""
        await asyncio.sleep(0)
        yield SimpleNamespace(text="answer")

    async def connect(**kwargs):
        """SDK에 전달한 요청 설정을 수집합니다."""
        requests.append(kwargs)
        return chunks()

    service = service_with_fake_sdk(monkeypatch, connect)
    baseline = service.model_name, service.search_enabled

    async def collect(model, search, temperature, thinking):
        """요청별 옵션으로 스트림을 끝까지 소비합니다."""
        return [chunk async for chunk in service.stream_chat_response(
            1, model, [], "test", model_name=model, search_enabled=search,
            temperature=temperature, thinking_level=thinking
        )]

    results = await asyncio.gather(
        collect("gemma-4-31b-it", False, 0, "minimal"),
        collect("gemini-3.8-flash", True, 1.2, "low"),
    )
    assert all(result[-1]["error"] is None for result in results)
    by_model = {request["model"]: request["config"] for request in requests}
    assert by_model["gemma-4-31b-it"].temperature == 0
    assert not by_model["gemma-4-31b-it"].tools
    assert by_model["gemma-4-31b-it"].thinking_config.thinking_level.value.lower() == "minimal"
    assert by_model["gemini-3.8-flash"].temperature == 1.2
    assert by_model["gemini-3.8-flash"].tools[0].google_search is not None
    assert (service.model_name, service.search_enabled) == baseline


@pytest.mark.asyncio
@pytest.mark.parametrize("search", [False, True])
async def test_search_uses_separate_total_deadline(monkeypatch, search):
    """같은 지연에도 검색 시간 안에는 성공하고 일반 요청은 제한시간을 넘기는지 검사합니다."""
    async def chunks():
        """일반 제한보다 길고 검색 제한보다 짧은 지연을 재현합니다."""
        await asyncio.sleep(0.06)
        yield SimpleNamespace(text="answer")

    async def connect(**kwargs):
        """준비한 지연 스트림을 반환합니다."""
        return chunks()

    service = service_with_fake_sdk(monkeypatch, connect)
    service.timeout_seconds = 0.02
    service.search_timeout_seconds = 0.3
    result = [chunk async for chunk in service.stream_chat_response(1, "deadline", [], "test", search_enabled=search)]
    assert result[-1]["error"] == (None if search else "AI_TIMEOUT")


@pytest.mark.parametrize("options", [
    {"model": "arbitrary-model"}, {"temperature": -0.1}, {"temperature": 2.1},
    {"model": "gemma-4-26b-a4b-it", "thinking_level": "low"},
    {"model": "gemini-3.8-flash", "thinking_level": "minimal"},
])
def test_invalid_options_rejected_before_db_write(isolated_chat, options):
    """지원하지 않는 모델·옵션은 질문 저장이나 AI 호출 전에 422로 거절합니다."""
    client, factory, _ = isolated_chat
    response = client.post("/api/v1/chat/stream", json={"message": "test", **options})
    assert response.status_code == 422
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 0


def test_models_endpoint_requires_login(isolated_chat):
    """로그인한 사용자는 비밀 없는 모델 목록을 받고, 로그아웃 상태는 거절됩니다."""
    client, _, _ = isolated_chat
    response = client.get("/api/v1/chat/models")
    assert response.status_code == 200
    assert response.json()["models"] == MODEL_CHOICES
    client.cookies.clear()
    assert client.get("/api/v1/chat/models").status_code == 401


@pytest.mark.asyncio
async def test_provider_quota_error_does_not_leak_or_retry(monkeypatch, caplog):
    """429 원문을 노출하지 않고 고정 코드와 모델 변경 안내를 전달하며 재시도하지 않습니다."""
    calls = []

    async def connect(**kwargs):
        """개인정보가 섞인 공급자 오류를 인위적으로 발생시킵니다."""
        calls.append(kwargs)
        raise RuntimeError("429 RESOURCE_EXHAUSTED private-provider-payload")

    service = service_with_fake_sdk(monkeypatch, connect)
    result = [chunk async for chunk in service.stream_chat_response(1, "quota", [], "test")]
    assert len(calls) == 1
    assert result[-1]["error"] == "AI_RATE_LIMIT"
    assert "private-provider-payload" not in str(result) + caplog.text
