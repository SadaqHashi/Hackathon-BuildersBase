import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def _login(username: str = "consultant_anna", password: str = "hackathon") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_login_success(self):
        resp = client.post("/auth/login", json={"username": "consultant_anna", "password": "hackathon"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["role"] == "consultant"

    def test_login_wrong_password(self):
        resp = client.post("/auth/login", json={"username": "consultant_anna", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "hackathon"})
        assert resp.status_code == 401

    def test_ask_without_token(self):
        resp = client.post("/ask", json={"question": "test"})
        assert resp.status_code == 401

    def test_ask_with_invalid_token(self):
        resp = client.post("/ask", json={"question": "test"}, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 401


class TestRoleBasedAccess:
    def test_consultant_can_ask(self):
        token = _login("consultant_anna")
        resp = client.post("/ask", json={"question": "payroll deadline?"}, headers=_auth_header(token))
        assert resp.status_code == 200

    def test_consultant_cannot_verify(self):
        token = _login("consultant_anna")
        resp = client.post("/claims/c1/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_expert_can_verify(self):
        token = _login("expert_klaus")
        resp = client.post("/claims/c1/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 200

    def test_admin_can_verify(self):
        token = _login("admin_sarah")
        resp = client.post("/claims/c1/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 200


class TestIDOR:
    def test_cannot_access_other_users_session(self):
        token_anna = _login("consultant_anna")
        token_klaus = _login("expert_klaus")
        resp = client.post("/ask", json={"question": "test"}, headers=_auth_header(token_anna))
        assert resp.status_code == 200
        resp2 = client.post("/ask", json={"question": "test"}, headers=_auth_header(token_klaus))
        assert resp2.status_code == 200


class TestInputValidation:
    def test_oversized_question_rejected(self):
        token = _login("consultant_anna")
        long_q = "a" * 2001
        resp = client.post("/ask", json={"question": long_q}, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_max_length_question_accepted(self):
        token = _login("consultant_anna")
        q = "a" * 2000
        resp = client.post("/ask", json={"question": q}, headers=_auth_header(token))
        assert resp.status_code == 200

    def test_empty_question(self):
        token = _login("consultant_anna")
        resp = client.post("/ask", json={"question": ""}, headers=_auth_header(token))
        assert resp.status_code == 200


class TestHealthEndpoint:
    def test_health_no_auth(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
