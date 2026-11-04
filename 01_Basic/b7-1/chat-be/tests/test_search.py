"""실제 검색 요청 대신 가짜 SDK가 받은 설정을 검사합니다. 기본 켜짐·명시적 꺼짐·SDK 객체 변환과 오류 처리 경계를
확인합니다.
이 시험은 Gemma 프로젝트의 검색 지원이나 무료 요금제를 확인하지 않습니다. 실제 API에는 연결하지 않습니다.
"""
from types import SimpleNamespace

import pytest
from google.genai import types

from app.core.config import Settings
from app.services import gemini_service as gm


def test_search_defaults_to_enabled_without_changing_gemma(monkeypatch):
    """환경변수와 .env가 덮어쓰지 않는 기본 설정에서 검색이 켜지고 Gemma 모델이 유지되는지 확인합니다.
    """
    monkeypatch.delenv('GEMINI_SEARCH_ENABLED', raising=False)
    monkeypatch.delenv('GEMINI_MODEL_NAME', raising=False)
    settings = Settings(_env_file=None, GEMINI_API_KEY='')
    assert settings.GEMINI_SEARCH_ENABLED is True
    assert settings.GEMINI_MODEL_NAME == 'gemma-4-26b-a4b-it'


@pytest.mark.asyncio
# True/False와 SDK 객체/사전 경로를 조합합니다. 검색 옵션이 실제 호출 인수까지 전달되는지 확인합니다.
@pytest.mark.parametrize('enabled', [True, False])
@pytest.mark.parametrize('sdk_config', [True, False])
async def test_stream_sends_search_choice_to_sdk(monkeypatch, enabled, sdk_config):
    """검색 켜기/끄기가 실제 SDK 설정 객체와 사전 두 경로에서 호출 인수까지 올바르게 전달되는지 검사합니다.
    """
    monkeypatch.setattr(gm.settings, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(gm.settings, 'GEMINI_SEARCH_ENABLED', enabled)
    service = gm.GeminiService()
    service.api_key = 'fake-sdk-only'
    requests = []

    async def chunks():
        """검색 시험의 가짜 답변을 한 조각 반환합니다. 실제 검색·Google API·운영 DB에는 접근하지
        않습니다.
        """
        yield SimpleNamespace(text='가짜 검색 답변')

    async def connect(**kwargs):
        """실제 네트워크 연결 대신 시험이 준비한 응답 스트림을 반환합니다. 일부 시험에서는 전달된 질문/설정도
        수집합니다.
        """
        requests.append(kwargs)
        return chunks()

    # 네트워크 클라이언트를 가짜로 대체합니다. 이 시험에서 답변이 나와도 실제 Google 검색 성공을 뜻하지 않습니다.
    service._client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=connect))
    )
    if sdk_config:
        service._types = types
    result = [item async for item in service.stream_chat_response(1, 'search-config-test', [], '밈 설명')]

    assert len(requests) == 1
    assert requests[0]['model'] == service.model_name
    config = requests[0]['config']
    # 검색을 켠 요청은 도구 사용을 명시적으로 요구하고 현재 날짜를 제공합니다.
    instruction = config.system_instruction if sdk_config else config['system_instruction']
    assert '오늘 날짜(한국)' in instruction
    assert ('Google Search 도구로 관련 자료' in instruction) is enabled
    if sdk_config:
        assert isinstance(config, types.GenerateContentConfig)
        assert bool(config.tools) is enabled
        if enabled:
            assert config.tools[0].google_search is not None
    else:
        assert ('tools' in config) is enabled
        if enabled:
            assert config['tools'] == [{'google_search': {}}]
    assert result[-1]['error'] is None
    assert result[-1]['full_text'] == '가짜 검색 답변'


@pytest.mark.asyncio
async def test_search_rejection_is_error_without_retry_or_mock(monkeypatch):
    """검색 거절을 오류로 전달하고, 검색 없는 재시도나 Demo 성공으로 바꾸지 않는지 확인합니다.
    """
    monkeypatch.setattr(gm.settings, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(gm.settings, 'GEMINI_SEARCH_ENABLED', True)
    service = gm.GeminiService()
    service.api_key = 'fake-sdk-only'
    requests = []

    async def connect(**kwargs):
        """호출 횟수를 기록한 뒤 검색이 허용되지 않는 프로젝트의 오류를 재현합니다. 실제 API는 호출하지 않습니다.
        """
        requests.append(kwargs)
        raise RuntimeError('search unavailable in fake project')

    # 네트워크 클라이언트를 가짜로 대체합니다. 이 시험에서 답변이 나와도 실제 Google 검색 성공을 뜻하지 않습니다.
    service._client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=connect))
    )
    result = [item async for item in service.stream_chat_response(1, 'search-rejection-test', [], '밈 설명')]
    assert len(requests) == 1
    assert result[-1]['error'] == 'AI_SERVICE_ERROR'
    assert '[Demo 모드]' not in result[-1]['full_text']
