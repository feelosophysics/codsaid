# Google AI SDK(외부 API를 편하게 부르는 도구)를 감싸 질문·과거 문맥·검색 옵션을 보내고 답변을 조금씩
# 받습니다.
# 웹 검색 도구를 넣으면 모델이 필요할 때 검색할 수 있습니다. 옵션을 켠 것과 실제 검색 성공은 서로 다른 상태입니다.
# 전체 제한시간은 연결과 모든 조각 읽기에 함께 적용합니다. 키가 없으면 Demo, 초기화 실패는 오류로 처리합니다.
import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, List, Dict, Any, Optional
from app.core.config import get_settings
from app.core.ai_models import DEFAULT_THINKING
from app.services.ai_errors import classify_ai_error, error_message, EmptyResponseError
from app.services.grounding import collect_grounding, sources_markdown
from app.core.logging import (
    log_ai_call_start,
    log_ai_call_success,
    log_ai_call_failed,
    logger
)

settings = get_settings()


class GeminiService:
    """AI 설정과 클라이언트를 묶고 공통 호출 흐름을 제공합니다. 실제 호출과 Demo 호출이 아래에서 서로 다른 경로로
    실행됩니다.
    """

    def __init__(self):
        """설정을 복사하고 키가 있으면 SDK를 준비합니다. SDK 재시도는 앱의 전체 시간제한 안에서 관리합니다."""
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        self.search_enabled = settings.GEMINI_SEARCH_ENABLED
        self.timeout_seconds = settings.AI_TIMEOUT_SECONDS
        self.search_timeout_seconds = settings.AI_SEARCH_TIMEOUT_SECONDS
        self.system_instruction = settings.SYSTEM_INSTRUCTION
        self._client = None
        self._cooldowns = {}

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                # 한 요청을 SDK가 여러 번 재시도해 한도를 더 소모하거나 대기시간을 늘리지 않게 합니다.
                self._client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=1)
                ))
                self._types = types
            except Exception:
                self._client = None

    def cooldown_seconds(self, model_name):
        """공급자가 거절한 모델의 짧은 대기시간을 반환합니다. 다른 모델의 요청은 막지 않습니다."""
        return max(0, int(self._cooldowns.get(model_name, 0) - time.monotonic() + 0.999))

    def is_live_api(self) -> bool:
        """AI 키와 SDK 클라이언트가 준비됐는지 확인합니다. True라도 검색 권한·실제 API 호출 성공까지
        확인한 것은 아닙니다.
        """
        return bool(self._client and self.api_key)

    def _build_context_messages(self, history: List[Dict[str, str]], current_question: str) -> List[Any]:
        """최근 메시지를 user/model 역할로 바꾸고 마지막에 새 질문을 붙입니다. AI는 이 목록을 보고 같은
        대화의 앞 내용을 참고합니다.
        """
        contents = []
        
        # 최근 메시지만 골라 이번 질문의 문맥으로 보냅니다.
        # [-N:]은 목록의 뒤에서 최대 N개를 자르는 문법입니다. 과거 메시지가 너무 많아도 이번 요청의 문맥
        # 크기를 제한합니다.
        recent_history = history[-settings.MAX_HISTORY_MESSAGES:] if history else []
        for msg in recent_history:
            if msg.get("status", "success") != "success":
                continue
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        # 과거 문맥 뒤에 이번 질문을 추가합니다.
        contents.append({
            "role": "user",
            "parts": [{"text": current_question}]
        })
        # 실패한 답변을 제외하면 같은 역할이 연속할 수 있어 하나로 합칩니다.
        merged = []
        for item in contents:
            if merged and merged[-1]["role"] == item["role"]:
                merged[-1]["parts"].extend(item["parts"])
            else:
                merged.append(item)
        # 최근 기록을 자를 때 모델 답변이 첫 행이 된 경우, 질문으로 시작하도록 정리합니다.
        while merged and merged[0]["role"] == "model":
            merged.pop(0)
        return merged

    async def stream_chat_response(
        self,
        user_id: int,
        request_id: str,
        history: List[Dict[str, str]],
        current_question: str,
        model_name: Optional[str] = None,
        search_enabled: Optional[bool] = None,
        temperature: Optional[float] = None,
        thinking_level: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """질문과 과거 문맥을 보내고 AI 답변을 한 조각씩 전달합니다.

        async def와 yield를 함께 쓰면 비동기 생성기가 됩니다. 호출하는 쪽은 async for로 조각이
        도착할 때마다 처리합니다. 기다리는 동안 다른 요청도 진행할 수 있습니다.

        일반 조각은 text와 done=False를 담습니다. 마지막에는 done=True와 전체 답변·시간·오류를
        보내 API가 저장할 내용을 확정하게 합니다. 연결과 모든 조각 읽기는 같은 제한시간을 공유합니다.
        """
        start_time = time.perf_counter()
        # 요청별 지역 변수로 복사합니다. 공유 서비스의 속성을 바꾸면 다른 사용자 요청에 옵션이 섞입니다.
        selected_model = model_name or self.model_name
        use_search = self.search_enabled if search_enabled is None else search_enabled
        timeout_seconds = self.search_timeout_seconds if use_search else self.timeout_seconds
        log_ai_call_start(user_id=user_id, request_id=request_id, model=selected_model)
        
        full_response = ""
        sources, queries, search_suggestions = {}, set(), ""
        blocked = False

        if self.api_key and not self._client:
            friendly = error_message("AI_INIT_ERROR", "initialization")
            log_ai_call_failed(request_id, "AI_INIT_ERROR", 0)
            yield {"text": friendly, "done": False, "error": None}
            yield {"text": "", "done": True, "full_text": friendly, "latency_ms": 0, "error": "AI_INIT_ERROR"}
            return

        # 1. 키와 SDK가 준비된 실제 AI 호출 경로입니다.
        if self.is_live_api():
            try:
                contents = self._build_context_messages(history, current_question)
                # 도구를 제공하면 모델이 필요할 때 웹 검색을 사용할 수 있습니다.
                # 검색이 거절되더라도 자동으로 모델을 바꾸거나 검색 없는 요청을 재시도하지 않습니다.
                # AI 요청 설정을 사전(dict)에 모읍니다. SDK가 있으면 **config_options로
                # 이름별 인수를 펼쳐 설정 객체를 만듭니다.
                config_options = {
                    "system_instruction": self.system_instruction + "\n오늘 날짜(한국): " + datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
                    "temperature": temperature if temperature is not None else (1.0 if selected_model.startswith("gemini-3") else 0.7),
                }
                # 검색 도구를 제공하지만 검색을 매번 강제하지는 않습니다. 실제 검색 지원/무료 할당량은 별도로
                # 확인해야 합니다.
                effective_thinking = thinking_level or DEFAULT_THINKING.get(selected_model)
                if effective_thinking:
                    config_options["thinking_config"] = {"thinking_level": effective_thinking}
                if use_search:
                    config_options["tools"] = [{"google_search": {}}]
                    config_options["system_instruction"] += (
                        "\n사용자가 웹 검색을 켰습니다. 답변 전에 Google Search 도구로 관련 자료를 찾아 확인하세요. "
                        "기억만으로 최신 정보를 확인했다고 말하지 말고, 검색이 실행되지 않으면 그 한계를 밝혀 주세요."
                    )
                if hasattr(self, "_types") and self._types:
                    config = self._types.GenerateContentConfig(**config_options)
                else:
                    config = config_options

                # 연결과 모든 읽기에 한 종료 시각을 사용합니다. 조각이 계속 와도 전체 제한은 늘어나지 않습니다.
                # yield를 가로지르는 전체 취소 구역은 사용하지 않습니다.
                # 그렇게 하면 API가 받은 조각을 전송하는 동안 호출자까지 뜻밖에 취소될 수 있기 때문입니다.
                loop = asyncio.get_running_loop()
                # 종료 시각을 한 번만 계산합니다. 조각마다 새 제한을 주면 답변이 조금씩 올 때 전체
                # 제한이 계속 늘어납니다.
                deadline = loop.time() + timeout_seconds
                response_stream = None
                try:
                    # await는 기다리는 동안 다른 작업에 실행 기회를 줍니다. wait_for는 지정
                    # 시간이 지나면 기다리는 작업을 취소합니다.
                    response_stream = await asyncio.wait_for(
                        self._client.aio.models.generate_content_stream(
                            model=selected_model,
                            contents=contents,
                            config=config
                        ),
                        timeout=timeout_seconds
                    )
                    # 비동기 반복자를 얻습니다. anext는 다음 조각을 요청하며 더 없으면
                    # StopAsyncIteration이 발생합니다.
                    iterator = aiter(response_stream)
                    while True:
                        # 전체 종료 시각까지 남은 시간만 다음 읽기에 줍니다. 연결이 오래 걸렸다면
                        # 조각을 읽을 시간도 그만큼 줄어듭니다.
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            raise asyncio.TimeoutError
                        try:
                            chunk = await asyncio.wait_for(anext(iterator), timeout=remaining)
                        except StopAsyncIteration:
                            break
                        search_suggestions = collect_grounding(chunk, sources, queries) or search_suggestions
                        for candidate in getattr(chunk, "candidates", None) or []:
                            reason = str(getattr(candidate, "finish_reason", ""))
                            blocked = blocked or any(kind in reason for kind in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"))
                        if chunk.text:
                            full_response += chunk.text
                            # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을
                            # 요청하면 여기 뒤부터 이어서 실행합니다.
                            yield {
                                "text": chunk.text,
                                "done": False,
                                "error": None
                            }
                finally:
                    # 스트림이 aclose 정리 기능을 제공하는지 확인합니다. 자원을 정리하되 정리가 원래
                    # 결과를 덮어쓰지 않게 합니다.
                    close = getattr(response_stream, "aclose", None)
                    if close is not None:
                        try:
                            # 정리는 별도로 최대 1초만 기다립니다. SDK가 닫히지 않아도 원래 AI
                            # 타임아웃 결과를 계속 전달합니다.
                            await asyncio.wait_for(close(), timeout=1.0)
                        except Exception as close_error:
                            # 정리 실패는 원래 AI 결과를 덮거나 SDK 예외 원문을 노출하지 않게 처리합니다.
                            # 호출자 취소는 그대로 전달되어야 하므로 취소 예외를 성공으로 바꾸지 않습니다.
                            logger.warning(
                                "ai_stream_close_failed request_id=%s error_type=%s",
                                request_id, type(close_error).__name__
                            )

                if not full_response.strip():
                    raise EmptyResponseError(blocked)
                footer = sources_markdown(sources)
                if footer:
                    full_response += footer
                    yield {"text": footer, "done": False, "error": None}
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                log_ai_call_success(request_id=request_id, latency_ms=latency_ms)

                # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터
                # 이어서 실행합니다.
                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": None,
                    "search": {"requested": use_search, "executed": bool(queries or sources), "source_count": len(sources)},
                    "search_suggestions": search_suggestions
                }
                return

            # 제한시간 초과를 고정 오류 종류와 사용자 안내로 바꾸고, 이미 받은 답변 조각은 보존합니다.
            except asyncio.TimeoutError:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                error_msg = "AI_TIMEOUT"
                log_ai_call_failed(request_id=request_id, error=error_msg, latency_ms=latency_ms)
                friendly_err = f"\n\n⚠️ **응답 제한시간({timeout_seconds:g}초)을 넘겼어요. 검색을 끄거나 추론 수준을 낮춰 다시 시도해 주세요. (error: AI_TIMEOUT)**"
                full_response += friendly_err
                # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터
                # 이어서 실행합니다.
                yield {
                    "text": friendly_err,
                    "done": False,
                    "error": None
                }
                # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터
                # 이어서 실행합니다.
                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": "AI_TIMEOUT"
                }
                return
            except Exception as e:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                # SDK 예외 원문에는 요청값 등이 섞일 수 있어 고정 오류 코드만 밖으로 내보냅니다.
                error_code, reason, provider_code, retry_seconds = classify_ai_error(e)
                if error_code == "AI_RATE_LIMIT":
                    self._cooldowns[selected_model] = time.monotonic() + retry_seconds
                log_ai_call_failed(request_id=request_id, error=error_code, latency_ms=latency_ms)
                logger.warning("ai_diagnostic request_id=%s model=%s search=%s thinking=%s provider_code=%s reason=%s retry_seconds=%s",
                               request_id, selected_model, use_search, thinking_level or DEFAULT_THINKING.get(selected_model), provider_code, reason, retry_seconds)
                friendly_err = "\n\n⚠️ " + error_message(error_code, reason, retry_seconds)
                
                full_response += friendly_err
                # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터
                # 이어서 실행합니다.
                yield {
                    "text": friendly_err,
                    "done": False,
                    "error": None
                }
                # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터
                # 이어서 실행합니다.
                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": error_code
                }
                return

        # 2. 실제 AI 호출 없이 준비된 답변을 사용하는 Demo 경로입니다.
        # 이 아래는 실제 Google 검색/AI 없이 미리 준비한 답변을 쓰는 Demo 경로입니다. 실제 서비스 시험
        # 결과와 구분합니다.
        mock_reply = self._generate_mock_reply(current_question)
        chunks = self._chunk_text(mock_reply)

        for chunk in chunks:
            await asyncio.sleep(0.04)  # 실제 AI 대신 Demo 글자가 조금씩 나타나도록 기다립니다.
            full_response += chunk
            # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터 이어서
            # 실행합니다.
            yield {
                "text": chunk,
                "done": False,
                "error": None
            }

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_ai_call_success(request_id=request_id, latency_ms=latency_ms)

        # 이 자료를 호출한 API에 전달하고 잠시 멈춥니다. 호출자가 다음 조각을 요청하면 여기 뒤부터 이어서
        # 실행합니다.
        yield {
            "text": "",
            "done": True,
            "full_text": full_response,
            "latency_ms": latency_ms,
            "error": None
        }

    def _generate_mock_reply(self, question: str) -> str:
        """실제 AI를 호출하지 않고 질문의 특정 단어에 맞춘 Demo 답변을 만듭니다. 웹 검색이나 새 지식을 얻는
        동작은 없습니다.
        """
        q_lower = question.lower()

        if "안녕" in q_lower or "hi" in q_lower or "hello" in q_lower or "반가" in q_lower:
            return (
                "안녕하세요! 저는 **건설 도메인 지식 & 상식 Q&A 챗봇**입니다. 👷‍♂️🏗️\n\n"
                "시공/공정(골조·마감·방수·RC), 인허가 절차(건축허가·착공신고), 계약/비용(도급·하도급·평당 공사비), "
                "참여 주체(발주자·시공사·감리자), 자재/구조, 헷갈리는 개념(리모델링 vs 재건축), 플랜트 건설까지 "
                "건설 실무와 상식에 대해 무엇이든 편하게 물어보세요!"
            )
        elif "리모델링" in q_lower or "재건축" in q_lower:
            return (
                "### 🏗️ 리모델링 vs 재건축 핵심 차이점\n\n"
                "**1. 리모델링 (Remodeling)**\n"
                "- **개념**: 기존 건물의 뼈대(기둥, 보, 내력벽 등 기본 골조)를 유지한 채 노후 설비 교체, 평면 확장, 외관 개선을 수행하는 공사입니다.\n"
                "- **장점**: 공사 기간이 비교적 짧고 인허가 절차가 간소하며, 자원 낭비를 최소화합니다.\n\n"
                "**2. 재건축 (Reconstruction)**\n"
                "- **개념**: 노후·불량 건축물을 완전히 철거하고 그 대지 위에 새로 건물을 짓는 정비 사업입니다.\n"
                "- **특징**: 안전진단 통과, 정비구역 지정, 조합 설립 등 복잡한 법적 절차와 긴 사업 기간이 소요됩니다.\n\n"
                "> 💡 *[FAQ] 자세한 도메인 용어 및 FAQ는 `docs/domain_knowledge.md`를 참고하세요.*"
            )
        elif "원도급" in q_lower or "하도급" in q_lower:
            return (
                "### 💼 원도급 vs 하도급 핵심 개념\n\n"
                "- **원도급**: 공사를 발주한 건축주(발주자)와 직접 계약을 체결한 종합 시공사를 말합니다. 현장 전체의 시공·안전 책임을 집니다.\n"
                "- **하도급**: 원도급사로부터 공사의 일부(예: 창호, 방수, 철근 등)를 넘겨받아 전문적으로 수행하는 전문건설업체를 말합니다.\n\n"
                "> 💡 *[FAQ] 자세한 도메인 용어 및 FAQ는 `docs/domain_knowledge.md`를 참고하세요.*"
            )
        elif "콘크리트" in q_lower or "타설" in q_lower or "시공" in q_lower or "양생" in q_lower:
            return (
                "### 📐 콘크리트 타설 및 품질 관리 지침\n\n"
                "**1. 동절기/한중 콘크리트 (일평균 기온 4℃ 이하)**\n"
                "- **초기 동결 방지**: 압축강도 $5\\text{ MPa}$ 발현 시까지 온도를 $5^\\circ\\text{C}$ 이상 유지\n"
                "- **보온 양생**: 열풍기, 방풍막, 갈탄 지양(일산화탄소 질식 위험 $\\rightarrow$ 열풍기 권장)\n\n"
                "**2. 타설 시 주의사항**\n"
                "- 이어치기 시간 한도: 외기온 25℃ 이상 시 2시간, 25℃ 미만 시 2.5시간 이내\n"
                "- 진동기(Vibrator) 사용: 과다 진동 시 재료 분리 발생 $\\rightarrow$ 수직으로 5~15초간 삽입\n\n"
                "> 💡 *[Demo 모드] 실제 Google AI Studio(Gemma 4) 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "fastapi" in q_lower or "웹" in q_lower or "서버" in q_lower:
            return (
                "### 🚀 FastAPI의 핵심 특징과 파이프라인\n\n"
                "**FastAPI**는 현대적인 고성능 Python 웹 프레임워크입니다:\n\n"
                "1. **비동기 처리(Async/Await)**: `async def`를 통해 I/O 바운드 작업(AI API 호출, DB 쿼리)을 논블로킹으로 처리합니다.\n"
                "2. **Pydantic 데이터 검증**: 요청/응답 스키마를 타입 힌트 기반으로 자동 검증하고 직렬화합니다.\n"
                "3. **의존성 주입(Dependency Injection)**: `Depends(get_db)`, `Depends(get_current_user)`로 인증 및 DB 세션을 깔끔하게 분리합니다.\n\n"
                "```python\n"
                "@app.post('/api/v1/chat/stream')\n"
                "async def stream_chat(request: ChatMessageCreate, user: User = Depends(get_current_user)):\n"
                "    return StreamingResponse(gemini_service.stream_chat_response(...))\n"
                "```\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "db" in q_lower or "데이터베이스" in q_lower or "sqlite" in q_lower or "로그" in q_lower:
            return (
                "### 🗄️ 대화 로그 영속화 및 데이터 모델링 (Role 2)\n\n"
                "AI 챗봇 서비스에서 대화 로그 저장은 품질 관리와 사용자 경험에 필수적입니다:\n\n"
                "- **User (사용자)**: 계정 식별자 및 암호화된 비밀번호 관리 (`users`)\n"
                "- **ChatSession (대화방)**: 다중 대화 스레드 분리 (`chat_sessions`)\n"
                "- **ChatMessage (메시지/로그)**: 질문, AI 답변, 지연시간(latency_ms), 상태(status), 생성일시 저장 (`chat_messages`)\n\n"
                "상단 네비게이션의 **[대화 로그 확인]** 메뉴에서 현재 DB에 적재된 실시간 로그를 테이블로 직접 검증할 수 있습니다!"
            )
        else:
            return (
                f"질문해주신 **\"{question}\"**에 대한 건설 튜터 답변입니다.\n\n"
                "건설 실무 및 AI/SW 시스템 개발에서는 요청 수신 $\\rightarrow$ 도메인 분석/AI 추론 $\\rightarrow$ 결과 응답 $\\rightarrow$ DB 로깅의 전체 파이프라인이 "
                "안정적으로 유기 결합되어야 합니다.\n\n"
                "- **현장 안전 수칙 준수**: 법적 기준(산업안전보건법) 및 KCS 표준시방서 준수\n"
                "- **타임아웃 방어**: 외부 AI API 지연 시 시스템이 멈추지 않도록 예외 처리 필수\n"
                "- **대화 문맥 유지**: 이전 질의응답 내역을 프롬프트에 주입하여 연속성 있는 답변 생성\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )

    def _chunk_text(self, text: str, chunk_size: int = 4) -> List[str]:
        """Demo 문자열을 작은 조각으로 나눠 실제 스트리밍처럼 보여 줍니다. 기본 4글자 단위이며 AI의 실제
        토큰과 같은 단위는 아닙니다.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


# 앱에서 공통으로 사용할 AI 서비스 객체를 만듭니다. 설정은 생성 시 읽습니다.
gemini_service = GeminiService()
