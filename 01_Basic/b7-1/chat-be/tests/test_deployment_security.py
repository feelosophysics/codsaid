"""허용 출처와 운영 쿠키를 임시 DB에서 확인합니다. 실제 AI/운영 계정은 사용하지 않습니다."""
import pytest

from app.api.v1 import auth
from app.core.config import Settings


def test_cors_allows_configured_frontend_and_rejects_other_origin(isolated_chat):
    client, _, _ = isolated_chat
    headers = {
        "Origin": auth.settings.CORS_ALLOWED_ORIGINS[0],
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    allowed = client.options("/api/v1/chat/stream", headers=headers)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
    assert allowed.headers["access-control-allow-credentials"] == "true"
    headers["Origin"] = "https://untrusted.example"
    denied = client.options("/api/v1/chat/stream", headers=headers)
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
    # 단순 요청에도 허용하지 않은 출처의 응답 읽기 권한을 부여하지 않습니다.
    response = client.get("/api/v1/logs/stats", headers={"Origin": headers["Origin"]})
    assert "access-control-allow-origin" not in response.headers


def test_cors_configuration_uses_json_array(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://localhost:3000","http://127.0.0.1:3000"]')
    assert Settings(_env_file=None).CORS_ALLOWED_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]


@pytest.mark.parametrize("environment,secure", [("production", True), (" PROD ", True), ("development", False)])
def test_cookie_secure_by_environment_and_bearer_still_works(isolated_chat, monkeypatch, environment, secure):
    client, _, _ = isolated_chat
    monkeypatch.setattr(auth.settings, "APP_ENV", environment)
    client.cookies.clear()
    login = client.post("/api/v1/auth/login", json={"username": "reliability_user", "password": "auditPassword123"})
    assert login.status_code == 200
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert ("; secure" in cookie) is secure
    assert client.get("/api/v1/auth/me").status_code == (401 if secure else 200)
    client.cookies.clear()
    bearer = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 200
    logout = client.post("/api/v1/auth/logout")
    assert ("; secure" in logout.headers["set-cookie"].lower()) is secure
