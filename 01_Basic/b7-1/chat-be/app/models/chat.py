# 대화 묶음과 메시지 표를 설계합니다. ForeignKey는 다른 표의 내부 번호를 가리켜 데이터 사이의 관계를 만듭니다.
# 사용자 한 명 → 여러 대화 → 여러 메시지 순서입니다. role은 질문(user)인지 답변(assistant)인지
# 나타냅니다.
# UTC는 시간대에 상관없이 기준을 맞추는 시각입니다. 브라우저가 보여줄 때 한국 시간으로 바꿉니다.
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatSession(Base):
    """사용자가 이어서 질문하는 대화 묶음 한 개입니다. title은 화면 제목이고 id는 DB 연결용 번호입니다.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # users 표의 id를 가리키는 외래키입니다. 이 관계가 메시지/대화의 소유자를 연결합니다.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), default="새 대화", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    # lambda는 이름 없는 작은 함수입니다. 함수를 넘겨야 행을 만들거나 수정하는 시점마다 새 현재 시각을
    # 계산합니다.
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # 다른 표의 연결된 데이터를 객체에서 찾아갈 수 있게 하는 관계 설정입니다.
    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    def __repr__(self) -> str:
        """개발자가 객체를 출력했을 때 보일 간단한 설명을 만듭니다. API 응답 형식을 정하는 함수는 아닙니다.
        """
        return f"<ChatSession id={self.id} title='{self.title}'>"


class ChatMessage(Base):
    """질문 또는 AI 답변 한 건입니다. session_id로 대화에 연결하고 user_id로 소유자를 연결합니다.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    # 이 메시지가 속한 대화의 내부 번호입니다. DB 연결에 쓰며 사용자에게 보일 대화 순번은 아닙니다.
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    # users 표의 id를 가리키는 외래키입니다. 이 관계가 메시지/대화의 소유자를 연결합니다.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 질문(user) 또는 AI 답변(assistant) 역할입니다.
    content = Column(Text, nullable=False)
    
    # 응답시간·성공/실패·오류 종류를 저장해 동작을 확인하는 필드입니다.
    # 답변을 얻는 데 걸린 밀리초입니다. 오류 답변의 상태와 함께 보고 성능/실패를 구분합니다.
    latency_ms = Column(Integer, nullable=True, default=0)
    status = Column(String(20), default="success", nullable=False)  # 성공(success), 시간 초과(timeout), 오류(error) 상태입니다.
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # 다른 표의 연결된 데이터를 객체에서 찾아갈 수 있게 하는 관계 설정입니다.
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="messages")

    def __repr__(self) -> str:
        """개발자가 객체를 출력했을 때 보일 간단한 설명을 만듭니다. API 응답 형식을 정하는 함수는 아닙니다.
        """
        return f"<ChatMessage id={self.id} role='{self.role}' status='{self.status}'>"
