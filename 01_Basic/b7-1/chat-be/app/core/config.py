# 서버의 공통 설정을 한곳에서 읽습니다. 변수 옆의 str/int/bool은 글자/정수/참거짓이라는 자료형 표시입니다.
# BaseSettings는 같은 이름의 환경변수와 .env 파일을 읽고, 값이 없을 때 아래 기본값을 사용합니다.
# 실제 키는 .env 또는 서버 환경에만 두고 Git에 올리지 않습니다. .env.example은 비밀 없는 작성
# 예시입니다.
import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET_KEY = "feelosophysics-chatbot-super-secret-key-change-in-production"


class Settings(BaseSettings):
    """설정값들의 이름·타입·기본값을 모은 틀입니다. 환경의 문자열 값을 해당 자료형으로 읽는 일은
    BaseSettings가 맡습니다.
    """
    APP_NAME: str = "Construction Domain Knowledge Q&A Chatbot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    # .env에서는 JSON 배열로 지정합니다. 미설정 운영 서버는 실제 프론트 한 곳만 허용합니다.
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["https://b7-1-chat-fe.vercel.app"])

    # JWT 서명과 로그인 관련 설정입니다.
    # JWT 서명의 비밀키입니다. 키가 바뀌면 이전 키로 만든 토큰은 검증되지 않을 수 있어 자동 교체하지 않습니다.
    SECRET_KEY: str = DEVELOPMENT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 하루(분 단위 설정)입니다.
    COOKIE_NAME: str = "access_token"

    # DB 연결 위치 설정입니다.
    DATABASE_URL: str = "sqlite:///./chatbot.db"

    # AI 모델·검색·응답시간 설정입니다.
    # 브라우저가 아닌 서버만 보관하는 Google API 인증값입니다. 실제 키를 주석이나 Git에 적지 않습니다.
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL_NAME: str = "gemma-4-26b-a4b-it"  # AI Studio의 Gemma 4 26B 정식 식별자
    # True이면 AI 요청에 Google 검색 도구를 넣습니다. 실제 검색 여부는 모델이 판단합니다.
    # 검색 지원·무료 할당량은 모델과 Google 프로젝트에 따라 다르며, 이 값이 무료를 보장하지 않습니다.
    GEMINI_SEARCH_ENABLED: bool = True
    AI_TIMEOUT_SECONDS: int = Field(60, ge=1, le=300)
    # 검색에는 추가 대기가 생길 수 있어 별도 전체 제한을 둡니다. 조각마다 제한을 연장하지 않습니다.
    AI_SEARCH_TIMEOUT_SECONDS: int = Field(90, ge=1, le=300)
    # AI는 DB를 직접 기억하지 않습니다. 최근 이 개수의 메시지를 요청마다 함께 보내 문맥을 제공합니다.
    MAX_HISTORY_MESSAGES: int = 10

    # 기존 단일 worker의 메모리 제한값입니다. 여러 프로세스가 이 예산을 공유하지는 않습니다.
    REGISTER_REQUESTS_PER_MINUTE: int = Field(5, ge=1)
    LOGIN_REQUESTS_PER_MINUTE: int = Field(10, ge=1)
    CHAT_REQUESTS_PER_MINUTE: int = Field(6, ge=1)
    CHAT_GLOBAL_REQUESTS_PER_MINUTE: int = Field(20, ge=1)
    CHAT_USER_CONCURRENCY: int = Field(1, ge=1)
    CHAT_GLOBAL_CONCURRENCY: int = Field(3, ge=1)

    # AI의 역할과 답변 방향을 알려 주는 공통 안내입니다.
    # AI에게 역할과 답변 방향을 알려 주는 공통 문장입니다. 실제 모델 지원과 최신 사실의 정확성을 보장하는 설정은
    # 아닙니다.
    SYSTEM_INSTRUCTION: str = (
        "당신은 친절하고 전문적인 '건설 도메인 지식 & 상식 Q&A 전문 어시스턴트'입니다. "
        "사용자가 질문하는 시공/공정(골조, 마감, 방수, 조적, RC구조, 가설), "
        "인허가/행정 절차(건축허가, 착공신고, 사용승인, 준공검사), "
        "계약/비용(도급, 하도급, 평당 공사비, 공사대금 분할, 견적서), "
        "참여 주체(발주자, 시공사, 감리자, 건축사, 하도급업체), "
        "자재/구조(철근, 콘크리트, 단열재, 방수재, 구조 방식), "
        "개념 비교(신축 vs 리모델링 vs 재건축, 원도급 vs 하도급, 감리 vs 감독), "
        "플랜트/산업설비 건설(EPC, FEED, 화공/발전 플랜트, 턴키 계약)에 대해 "
        "일반인도 이해하기 쉽고 명확하게 설명하며, 핵심 개념을 친절한 마크다운 서식으로 답변하세요."
    )

    # 환경변수/파일의 문자열을 위 자료형으로 읽습니다. extra=ignore는 모르는 설정 이름을 무시한다는 뜻입니다.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() in {"production", "prod"}

    def validate_production_security(self) -> None:
        """운영 모드에서 공개 개발 키나 너무 짧은 키로 서버가 시작되지 않게 합니다. 오류에 실제 설정값을 넣지
        않습니다.
        """
        # 운영 조건일 때만 엄격하게 검사합니다. encode("utf-8")는 문자열을 바이트로 바꿔 글자 수가 아닌
        # 바이트 길이를 셉니다.
        if self.is_production:
            if self.SECRET_KEY.strip() == DEVELOPMENT_SECRET_KEY or len(self.SECRET_KEY.strip().encode("utf-8")) < 32:
                # 모델 검사 예외에 전체 설정 입력값이 포함될 수 있어 별도의 고정 오류를 사용합니다.
                # 실제 비밀값이 예외에 섞이지 않게 하는 처리입니다.
                raise RuntimeError("Production SECRET_KEY must be a unique random key of at least 32 bytes.")


# 같은 설정을 매 요청 다시 읽지 않도록 결과를 캐시합니다. .env를 고쳐도 기존 프로세스 메모리의 값이 즉시 바뀌지는
# 않습니다.
@lru_cache()
def get_settings() -> Settings:
    """설정을 읽고 운영 최소 조건을 검사합니다. lru_cache는 결과를 재사용하므로 환경 변경은 보통 프로세스 재시작
    후 반영됩니다.
    """
    settings = Settings()
    settings.validate_production_security()
    return settings
