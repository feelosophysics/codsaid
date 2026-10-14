# users 표의 설계입니다. ORM은 Python 객체를 DB 행으로 바꾸어 SQL을 직접 쓰는 양을 줄이는 도구입니다.
# Column은 한 칸(열), primary_key는 행을 구별하는 내부 번호, nullable=False는 빈 값을
# 허용하지 않는 조건입니다.
# relationship은 사용자 객체에서 관련 대화/메시지를 찾아갈 수 있게 연결합니다. 실제 비밀번호는 저장하지
# 않습니다.
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """사용자 한 행의 Python 표현입니다. username은 로그인 아이디, nickname은 표시 이름,
    password_hash는 비밀번호 해시입니다.
    """
    __tablename__ = "users"

    # DB가 행을 구분하는 내부 키입니다. index는 이 열로 찾는 조회를 돕고 이 번호는 사용자별 가입 순번이
    # 아닙니다.
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    nickname = Column(String(30), nullable=False)
    # 원문 비밀번호가 아니라 bcrypt 해시를 보관합니다. 로그인 검증은 core/security.py가 처리합니다.
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 다른 표의 연결된 데이터를 객체에서 찾아갈 수 있게 하는 관계 설정입니다.
    # 관련 대화를 객체로 찾아가게 합니다. delete-orphan은 소유 관계에서 제거된 자식 데이터를 정리하는
    # 설정입니다.
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """개발자가 객체를 출력했을 때 보일 간단한 설명을 만듭니다. API 응답 형식을 정하는 함수는 아닙니다.
        """
        return f"<User id={self.id} username='{self.username}'>"
