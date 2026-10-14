# 데이터베이스 연결을 준비합니다. SQLite는 별도 DB 서버 없이 한 파일에 데이터를 보관합니다.
# engine은 DB에 연결하는 통로, SessionLocal은 요청별 작업 공간을 만드는 공장, Base는 표 설계의 공통
# 부모입니다.
# 이 파일의 Session은 DB 작업 공간이며, 사용자의 대화 묶음인 ChatSession과는 다른 개념입니다.
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.core.config import get_settings

settings = get_settings()

# SQLite 연결의 실행 스레드 제약을 조정합니다. 같은 DB 세션을 동시에 사용해도 된다는 뜻은 아닙니다.
# SQLite 연결을 여러 실행 스레드에서 사용할 수 있게 합니다. 이것이 같은 DB 세션의 무제한 동시 사용을 안전하게
# 만드는 것은 아닙니다.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# autoflush=False라 자동 전송 대신 필요한 지점의 flush를 사용합니다. commit해야 저장이 확정됩니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """요청에 쓸 DB 작업 공간을 만들고 yield로 전달합니다. finally는 성공·실패 어느 경우든 실행되어 연결을
    닫습니다.
    """
    db = SessionLocal()
    try:
        # yield는 DB 연결을 요청 함수에 빌려 주고 실행을 잠시 멈춥니다. 요청이 끝나면 아래 finally로
        # 돌아옵니다.
        yield db
    # 예외가 생겨도 실행됩니다. 연결을 닫아 다음 요청에 불필요한 자원이나 실패 상태가 남지 않게 합니다.
    finally:
        db.close()


def init_db() -> None:
    """표 설계들을 등록한 뒤 없는 표를 만듭니다. create_all은 기존 표의 열을 자동 수정하거나 DB 내용을
    지우는 마이그레이션 도구가 아닙니다.
    """
    # 표 설계 파일들을 불러와 Base.metadata에 모든 모델을 등록합니다.
    import app.models.user  # noqa: F401
    import app.models.chat  # noqa: F401
    Base.metadata.create_all(bind=engine)
