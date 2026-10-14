"""검색근거·빈응답·SDK초기화·공급자진단·모델대기를 가짜SDK/임시DB로 검사합니다."""
import json
import time
from types import SimpleNamespace as Obj

import pytest
from sqlalchemy import select, func

from app.api.v1 import chat
from app.models.chat import ChatMessage
from app.services import gemini_service as gm
from app.services.ai_errors import classify_ai_error
from test_ai_options import service_with_fake_sdk


@pytest.mark.parametrize("message,expected", [
    ("429 quota RequestsPerDay private-key", "AI_RATE_LIMIT"),
    ("400 google_search unsupported private-key", "AI_SEARCH_UNSUPPORTED"),
    ("400 thinking_level not supported private-key", "AI_OPTION_UNSUPPORTED"),
    ("404 model not found private-key", "AI_MODEL_UNAVAILABLE"),
    ("403 permission denied private-key", "AI_AUTH_ERROR"),
    ("503 service unavailable private-key", "AI_UNAVAILABLE"),
])
def test_error_classification_drops_raw_details(message, expected):
    """모델/검색/옵션/인증/일시적 장애를 구분하고 원문을 반환하지 않습니다."""
    result = classify_ai_error(RuntimeError(message))
    assert result[0] == expected
    assert "private-key" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", [False, True])
async def test_empty_stream_is_never_success(monkeypatch, blocked):
    """빈답변과 안전필터로 중단된 답변을 성공으로 저장하지 않습니다."""
    async def chunks():
        """텍스트 없는 공급자 스트림을 흉내 냅니다."""
        yield Obj(text=None, candidates=[Obj(finish_reason="SAFETY" if blocked else "STOP")])
    async def connect(**kwargs):
        """네트워크 없이 준비한 응답을 반환합니다."""
        return chunks()
    service = service_with_fake_sdk(monkeypatch, connect)
    result = [chunk async for chunk in service.stream_chat_response(1, "empty", [], "test")]
    assert result[-1]["error"] == ("AI_RESPONSE_BLOCKED" if blocked else "AI_EMPTY_RESPONSE")


@pytest.mark.asyncio
async def test_grounding_survives_sse_and_db_save(isolated_chat, monkeypatch):
    """중복출처·검색제안이 SSE에 전달되고 출처본문이 기존DB에 저장되는지 검사합니다."""
    client, factory, _ = isolated_chat
    metadata = Obj(web_search_queries=["fixture search"],
        grounding_chunks=[Obj(web=Obj(uri="https://example.com/a(x)",title="출처")),Obj(web=Obj(uri="javascript:bad",title="bad"))],
        search_entry_point=Obj(rendered_content='<a href="https://google.com">Google</a>'))
    async def chunks():
        """같은출처가 두번오고 마지막조각에 텍스트가 없는 상황을 재현합니다."""
        yield Obj(text="가짜 답변", candidates=[Obj(grounding_metadata=metadata,finish_reason=None)])
        yield Obj(text=None, candidates=[Obj(grounding_metadata=metadata,finish_reason="STOP")])
    async def connect(**kwargs):
        """네트워크 없이 준비한 응답을 반환합니다."""
        return chunks()
    service = service_with_fake_sdk(monkeypatch, connect)
    monkeypatch.setattr(chat, "gemini_service", service)
    response = client.post('/api/v1/chat/stream',json={"message":"fixture","search_enabled":True})
    data=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert data[-1]['search'] == {"requested":True,"executed":True,"source_count":1}
    assert 'Google' in data[-1]['search_suggestions']
    with factory() as db:
        answer=db.scalar(select(ChatMessage).where(ChatMessage.role=='assistant'))
        assert answer.status=='success'
        assert '웹 검색 출처' in answer.content and 'a%28x%29' in answer.content
        assert 'javascript:' not in answer.content


def test_model_cooldown_rejects_before_saving(isolated_chat, monkeypatch):
    """최근한도거절 모델의 중복질문은 DB쓰기·AI호출 전에429로 거절합니다."""
    client,factory,_ = isolated_chat
    monkeypatch.setattr(chat.gemini_service, '_cooldowns', {'gemma-4-26b-a4b-it': time.monotonic()+60})
    response=client.post('/api/v1/chat/stream',json={"message":"fixture"})
    assert response.status_code==429 and int(response.headers['Retry-After'])>0
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id)))==0


@pytest.mark.asyncio
async def test_initialization_failure_cannot_fall_back_to_demo(monkeypatch):
    """SDK준비실패를 Demo성공으로 바꾸지 않습니다."""
    from google import genai
    def fail(**kwargs):
        """민감한예외원문이 밖으로 노출되지 않게 오류만 발생시킵니다."""
        raise RuntimeError('private-sdk-error')
    monkeypatch.setattr(gm.settings,'GEMINI_API_KEY','fake-only')
    monkeypatch.setattr(genai,'Client',fail)
    service=gm.GeminiService()
    result=[chunk async for chunk in service.stream_chat_response(1,'init',[],'test')]
    assert result[-1]['error']=='AI_INIT_ERROR'
    assert 'Demo' not in str(result) and 'private-sdk-error' not in str(result)


def test_error_history_removed_and_roles_merged(monkeypatch):
    """과거오류문구가 새질문의 문맥을오염시키지 않게 제외하고 역할을 정리합니다."""
    monkeypatch.setattr(gm.settings,'GEMINI_API_KEY','')
    service=gm.GeminiService()
    contents=service._build_context_messages([
        {"role":"assistant","content":"orphan","status":"success"},
        {"role":"user","content":"old","status":"success"},
        {"role":"assistant","content":"error notice","status":"error"},
    ],'new')
    assert [item['role'] for item in contents]==['user']
    assert [part['text'] for part in contents[0]['parts']]==['old','new']
