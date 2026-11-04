# 채팅·대화·기록·통계 API가 주고받는 데이터의 규격입니다. BaseModel이 타입과 길이를 검사합니다.
# List는 여러 항목의 목록이고 Optional은 값이 없을 수도 있다는 표시입니다. Field(...)의 점 세 개는
# 필수값이라는 뜻입니다.
# 내부 id는 서버가 데이터를 연결할 때 쓰며 사용자 화면의 대화 순서를 뜻하지 않습니다.
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.core.ai_models import ModelName


class ChatStreamRequest(BaseModel):
    """새 질문 입력입니다. session_id가 없거나 내 소유 대화를 찾지 못하면 새 대화를 만들고, 내 대화이면
    이어서 사용합니다.
    """
    message: str = Field(..., min_length=1, max_length=2000, description="사용자 질문 (1~2000자)")
    session_id: Optional[int] = Field(None, description="대화 세션 ID (없을 경우 새 세션 자동 생성)")
    # 생략하면 서버 기본 모델/검색 설정을 사용하므로 기존 클라이언트도 계속 동작합니다.
    model: Optional[ModelName] = None
    search_enabled: Optional[bool] = None
    temperature: Optional[float] = Field(None, ge=0, le=2, allow_inf_nan=False)
    thinking_level: Optional[Literal["minimal", "low", "medium", "high"]] = None

    # 필드 길이 검사에 더해 공백만 있는 질문을 거절하는 사용자 정의 검사입니다.
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """질문 양끝 공백을 제거하고 빈 질문·2,000자 초과를 거절합니다. 정리한 질문만 DB와 AI에 전달합니다.
        """
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("질문 내용을 입력해주세요.")
        if len(cleaned) > 2000:
            raise ValueError("질문은 최대 2,000자까지 입력 가능합니다.")
        return cleaned


class ChatSessionCreate(BaseModel):
    """빈 대화를 만들 때 보낼 제목의 규격입니다. 제목을 생략하면 기본 새 대화 이름을 사용합니다.
    """
    title: Optional[str] = Field("새 대화", max_length=100)


class ChatMessageResponse(BaseModel):
    """메시지 조회 응답의 규격입니다. 본문 외에 역할·시간·상태를 담아 화면이 질문과 답변을 다르게 표시하게 합니다.
    """
    id: int
    session_id: int
    user_id: int
    role: str
    content: str
    latency_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    # SQLAlchemy 객체의 속성을 읽어 이 스키마에 지정한 필드만 응답으로 변환합니다.
    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    """대화 목록/생성 응답의 규격입니다. 생성·수정 시각과 선택적으로 메시지 목록을 포함합니다.
    """
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = []

    # SQLAlchemy 객체의 속성을 읽어 이 스키마에 지정한 필드만 응답으로 변환합니다.
    model_config = ConfigDict(from_attributes=True)


class ChatLogItem(BaseModel):
    """기록 표에 표시할 메시지 한 건입니다. DB 내부 번호는 API 연결용이며 FE에서 사용자에게 순번으로 표시하지
    않습니다.
    """
    id: int
    user_id: int
    username: str
    session_id: int
    role: str
    content: str
    latency_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    # SQLAlchemy 객체의 속성을 읽어 이 스키마에 지정한 필드만 응답으로 변환합니다.
    model_config = ConfigDict(from_attributes=True)


class ChatLogsResponse(BaseModel):
    """기록 페이지의 응답입니다. total은 전체 개수, items는 이번 페이지의 메시지 목록입니다.
    """
    total: int
    items: List[ChatLogItem]


class ChatStatsResponse(BaseModel):
    """기록 화면 통계의 응답입니다. 질문/답변 수·대화 수·평균 응답시간·성공률의 이름과 자료형을 고정합니다.
    """
    total_messages: int = Field(..., description="총 대화 메시지 수 (질문 + 답변)")
    total_questions: int = Field(..., description="총 사용자 질문 수")
    total_answers: int = Field(..., description="총 AI 답변 수")
    total_sessions: int = Field(..., description="총 대화 세션 수")
    avg_latency_ms: int = Field(..., description="평균 AI 응답 지연시간 (ms)")
    success_rate_percent: float = Field(..., description="AI 응답 성공률 (%)")

