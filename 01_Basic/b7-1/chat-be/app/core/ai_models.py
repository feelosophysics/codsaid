"""사용자가 고를 수 있는 모델만 명시합니다. 목록에 있다는 사실은 계정의 사용 권한이나 무료 한도를 보장하지 않습니다."""
from typing import Literal

# Literal은 아래 문자열 중 하나만 입력으로 받도록 제한하는 타입입니다.
ModelName = Literal[
    "gemma-4-26b-a4b-it", "gemini-3.8-flash",
    "gemini-3.5-flash-lite", "gemma-4-31b-it",
    "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
]
MODEL_CHOICES = [
    {"id": "gemma-4-26b-a4b-it", "label": "Gemma 4 26B"},
    {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash"},
    {"id": "gemini-3.7-flash", "label": "Gemini 3.7 Flash"},
    {"id": "gemini-3.6-flash", "label": "Gemini 3.6 Flash"},
    {"id": "gemini-3.5-flash", "label": "Gemini 3.5 Flash"},
    {"id": "gemini-3.5-flash-lite", "label": "Gemini 3.5 Flash-Lite"},
    {"id": "gemma-4-31b-it", "label": "Gemma 4 31B"},
]

# Gemma는 켜기/끄기에 해당하는 두 수준, Gemini는 모델마다 지원 수준이 다릅니다.
THINKING_LEVELS = {
    "gemma-4-26b-a4b-it": ["minimal", "high"],
    "gemma-4-31b-it": ["minimal", "high"],
    "gemini-3.8-flash": ["low", "medium", "high"],
    "gemini-3.7-flash": ["low", "medium", "high"],
    "gemini-3.6-flash": ["minimal", "low", "medium", "high"],
    "gemini-3.5-flash": ["minimal", "low", "medium", "high"],
    "gemini-3.5-flash-lite": ["minimal", "low", "medium", "high"],
}
for choice in MODEL_CHOICES:
    choice["thinking_levels"] = THINKING_LEVELS[choice["id"]]
    # 평소에는 낮은 추론으로 시작하고 필요한 질문에서 강도를 높입니다.
    choice["default_thinking"] = choice["thinking_levels"][0]

DEFAULT_THINKING = {choice["id"]: choice["default_thinking"] for choice in MODEL_CHOICES}
