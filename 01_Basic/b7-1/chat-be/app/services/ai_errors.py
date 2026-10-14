"""공급자 오류에서 공개해도 되는 코드·원인 분류·대기시간만 추출합니다."""
import re


class EmptyResponseError(Exception):
    """텍스트 없이 끝난 응답을 정상 성공과 구분합니다."""
    def __init__(self, blocked=False):
        self.blocked = blocked


def classify_ai_error(error):
    """원문은 메모리에서만 검사하고 로그·응답에는 고정 분류를 반환합니다."""
    if isinstance(error, EmptyResponseError):
        return ("AI_RESPONSE_BLOCKED" if error.blocked else "AI_EMPTY_RESPONSE"), "empty_output", 0, 0
    raw = str(error).lower()
    code = getattr(error, "code", None)
    if not isinstance(code, int):
        match = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", raw)
        code = int(match.group(1)) if match else 0
    retry_seconds = 0
    # SDK 구조화 details가 있으면 RetryInfo 숫자만 추출합니다. 프로젝트/키/메시지는 반환하지 않습니다.
    response = getattr(error, "response_json", None) or {}
    body = response.get("error", response) if isinstance(response, dict) else {}
    details = body.get("details", []) if isinstance(body, dict) else []
    if not isinstance(details, list):
        details = []
    for detail in details:
        delay = detail.get("retryDelay", "") if isinstance(detail, dict) else ""
        match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(delay))
        if match:
            retry_seconds = min(300, max(1, int(float(match.group(1))) + 1))
        # 공급자가 세부 한도를 구조화해서 주면 분류에만 사용합니다. 값/프로젝트 정보는 공개하지 않습니다.
        for violation in detail.get('violations', []) if isinstance(detail, dict) else []:
            if isinstance(violation, dict):
                raw += ' ' + str(violation.get('quotaId', '')).lower()
    if code == 429 or "resource_exhausted" in raw:
        if "perday" in raw or "per_day" in raw or "daily" in raw:
            reason = "quota_daily"
        elif "token" in raw:
            reason = "quota_tokens"
        else:
            reason = "quota_requests"
        return "AI_RATE_LIMIT", reason, code or 429, retry_seconds or 60
    if code == 404:
        return "AI_MODEL_UNAVAILABLE", "model_unavailable", code, 0
    if code in {401, 403}:
        return "AI_AUTH_ERROR", "authentication", code, 0
    if code == 400:
        if any(word in raw for word in ("google_search", "google search", "grounding")):
            return "AI_SEARCH_UNSUPPORTED", "search_configuration", code, 0
        if "thinking" in raw:
            return "AI_OPTION_UNSUPPORTED", "thinking_configuration", code, 0
        return "AI_OPTION_UNSUPPORTED", "parameter_invalid", code, 0
    if code >= 500:
        return "AI_UNAVAILABLE", "provider_unavailable", code, 0
    return "AI_SERVICE_ERROR", "unknown", code, 0


def error_message(code, reason, retry_seconds=0):
    """오류별 다음 행동을 짧게 알려 줍니다. 공급자 예외 문장은 그대로 보여주지 않습니다."""
    if code == "AI_RATE_LIMIT":
        if reason == "quota_daily":
            return "이 모델의 오늘 사용량을 모두 썼어요. 다른 모델을 선택하거나 일일 한도 초기화 후 이용해 주세요."
        return f"이 모델의 요청·토큰 한도에 도달했어요. 약 {retry_seconds}초 뒤 다시 시도하거나 다른 모델을 선택해 주세요."
    return {
        "AI_MODEL_UNAVAILABLE": "현재 계정에서 이 모델을 사용할 수 없어요. 다른 모델을 선택해 주세요.",
        "AI_AUTH_ERROR": "AI 서비스 인증을 확인해야 합니다. 관리자에게 문의해 주세요.",
        "AI_SEARCH_UNSUPPORTED": "이 모델의 검색 요청이 거절됐어요. 검색을 끄거나 다른 모델로 검색해 주세요.",
        "AI_OPTION_UNSUPPORTED": "선택한 추론·생성 옵션이 거절됐어요. 옵션을 기본값으로 돌리거나 다른 모델을 선택해 주세요.",
        "AI_UNAVAILABLE": "AI 제공 서비스가 일시적으로 응답하지 않아요. 잠시 후 다시 시도해 주세요.",
        "AI_EMPTY_RESPONSE": "모델이 답변을 반환하지 않았어요. 질문을 짧게 바꾸거나 다른 모델을 선택해 주세요.",
        "AI_RESPONSE_BLOCKED": "모델이 이 답변 생성을 중단했어요. 질문 표현을 바꾸어 주세요.",
        "AI_INIT_ERROR": "AI 연결을 초기화하지 못했어요. 관리자에게 문의해 주세요.",
    }.get(code, "AI 응답을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.")
