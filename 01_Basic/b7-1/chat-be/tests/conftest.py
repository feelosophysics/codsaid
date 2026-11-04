# 여러 시험이 공유하는 준비/정리 함수를 모읍니다. fixture는 시험 전에 필요한 객체를 만들고 끝난 뒤 정리하는
# pytest 기능입니다.
# monkeypatch는 시험 동안만 설정이나 함수를 바꾸는 도구이고 tmp_path는 시험별 임시 폴더입니다.
# 시험 실행기에서 먼저 임시 DB·빈 AI 키를 설정해야 앱 import 시에도 운영 DB와 실제 API를 쓰지 않습니다.
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import abuse
from app.api.v1 import chat
from app.core.database import Base, get_db
from app.core.logging import logger
from app.main import app


# fixture는 시험의 공통 준비 함수입니다. autouse=True이면 각 시험이 이름을 요청하지 않아도 자동
# 적용됩니다.
@pytest.fixture(autouse=True)
def fresh_request_guard(monkeypatch):
    """매 시험에 새 요청 제한기를 만들어 앞 시험의 횟수가 다음 시험에 영향을 주지 않게 합니다.
    """
    monkeypatch.setattr(abuse, "guard", abuse.RequestGuard())


# fixture는 시험의 공통 준비 함수입니다. autouse=True이면 각 시험이 이름을 요청하지 않아도 자동
# 적용됩니다.
@pytest.fixture(autouse=True)
def capture_server_logs(caplog):
    """시험용 로그 수집기를 붙이고 끝나면 뗍니다. 성공/실패 사건과 민감정보 비출력을 assert로 검사할 수 있게
    합니다.
    """
    logger.addHandler(caplog.handler)
    yield
    logger.removeHandler(caplog.handler)


# fixture는 시험의 공통 준비 함수입니다. autouse=True이면 각 시험이 이름을 요청하지 않아도 자동
# 적용됩니다.
@pytest.fixture
def isolated_chat(tmp_path, monkeypatch):
    """임시 DB와 시험용 사용자를 준비하고 API의 DB 연결을 대체합니다. finally에서 대체 설정과 연결을
    정리합니다.
    """
    engine = create_engine(
        "sqlite:///" + (tmp_path / "chat.db").as_posix(),
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    def db_dependency():
        """시험용 DB 작업 공간을 API에 제공하고 사용 후 닫습니다. 운영 get_db 대신 시험 동안만
        연결됩니다.
        """
        with factory() as db:
            yield db

    # 실제 API가 사용하는 get_db를 시험용 연결로 바꿉니다. 마지막에 제거해야 다음 시험에 대체 설정이 남지
    # 않습니다.
    app.dependency_overrides[get_db] = db_dependency
    monkeypatch.setattr(chat, "SessionLocal", factory)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.post("/api/v1/auth/register", json={
                "username": "reliability_user", "nickname": "Audit", "password": "auditPassword123"
            }).status_code == 201
            assert client.post("/api/v1/auth/login", json={
                "username": "reliability_user", "password": "auditPassword123"
            }).status_code == 200
            yield client, factory, engine
    # 시험이 실패해도 연결/대체 설정을 정리합니다. 시험 간 상태가 섞여 잘못 통과하거나 실패하는 것을 줄입니다.
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
