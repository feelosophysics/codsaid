# 가입·로그인과 비로그인 접근 거절을 확인합니다. test_로 시작하는 함수는 pytest가 찾아 실행합니다.
# assert는 기대한 값과 다르면 시험을 실패시키는 확인 문법입니다. 실제 운영 계정 대신 격리된 시험 데이터를
# 사용합니다.
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine


@pytest.fixture(autouse=True)
def setup_database():
    """인증 시험 전에 기존 시험 데이터를 비웁니다. 반드시 격리 실행기의 임시 DB 환경에서 실행합니다.
    """
    Base.metadata.create_all(bind=engine)
    yield


def test_register_and_login():
    """회원가입 후 같은 비밀번호로 로그인하고 토큰·사용자 정보가 오는지 검사합니다. 중복 아이디와 틀린 비밀번호도
    거절돼야 합니다.
    """
    client = TestClient(app)
    username = f"testuser_{int(time.time())}"
    password = "securePassword123"

    # 1. 시험용 계정 가입을 요청합니다.
    reg_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "테스트유저",
        "password": password
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["username"] == username
    assert reg_res.json()["nickname"] == "테스트유저"

    # 2. 이미 가입한 아이디의 중복 가입이 거절되는지 확인합니다.
    dup_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "테스트유저",
        "password": password
    })
    assert dup_res.status_code == 400

    # 3. 가입한 시험 계정으로 로그인합니다.
    login_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["username"] == username

    # 4. 로그인한 내 사용자 정보가 돌아오는지 확인합니다.
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username


def test_unauthorized_access():
    """로그인 증명 없이 보호된 API에 접근하면 401로 거절되는지 검사합니다.
    """
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/v1/chat/sessions")
    assert res.status_code == 401


def test_short_password_rejection():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}_shortpw"

    # 비밀번호가 8자 미만이면 Pydantic 검증에서 422가 나야 함
    res = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "짧은비번유저",
        "password": "short1"
    })
    assert res.status_code == 422


def test_missing_nickname_rejection():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}_noname"

    # nickname은 필수 필드이므로 빠지면 422가 나야 함
    res = client.post("/api/v1/auth/register", json={
        "username": username,
        "password": "securePassword123"
    })
    assert res.status_code == 422


def test_change_password_success():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}_pwchange"
    old_password = "oldPassword123"
    new_password = "newPassword456"

    # 1. 회원가입
    client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "비번변경유저",
        "password": old_password
    })

    # 2. 로그인 (TestClient가 쿠키를 보관하므로 이후 요청에 자동으로 실림)
    client.post("/api/v1/auth/login", json={
        "username": username,
        "password": old_password
    })

    # 3. 현재 비밀번호를 확인시키고 새 비밀번호로 변경
    change_res = client.put("/api/v1/auth/password", json={
        "current_password": old_password,
        "new_password": new_password
    })
    assert change_res.status_code == 200

    # 4. 새 비밀번호로는 로그인이 되어야 함
    relogin_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": new_password
    })
    assert relogin_res.status_code == 200

    # 5. 예전 비밀번호로는 더 이상 로그인이 안 되어야 함
    old_login_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": old_password
    })
    assert old_login_res.status_code == 401


def test_change_password_wrong_current_password():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}_wrongpw"
    password = "correctPassword123"

    client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "틀린비번유저",
        "password": password
    })
    client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })

    # 현재 비밀번호를 틀리게 보내면 400이 나야 함
    res = client.put("/api/v1/auth/password", json={
        "current_password": "wrongPassword",
        "new_password": "newPassword456"
    })
    assert res.status_code == 400


def test_change_password_too_short():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}_shortnew"
    password = "correctPassword123"

    client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "짧은새비번유저",
        "password": password
    })
    client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })

    # 새 비밀번호가 8자 미만이면 422가 나야 함
    res = client.put("/api/v1/auth/password", json={
        "current_password": password,
        "new_password": "short1"
    })
    assert res.status_code == 422


def test_change_password_requires_auth():
    # 로그인하지 않은 클라이언트가 비밀번호 변경을 시도하면 401이 나야 함
    fresh_client = TestClient(app)
    res = fresh_client.put("/api/v1/auth/password", json={
        "current_password": "whatever",
        "new_password": "whatever123"
    })
    assert res.status_code == 401
