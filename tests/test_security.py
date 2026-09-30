from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
DELVAUX_Q = "What's the payroll input cutoff for Brouwerij Delvaux?"
VERMEULEN_Q = "What's the payroll input cutoff for Garage Vermeulen?"


def _login(username: str = "jonas", password: str = "hackathon") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _ask(username: str, question: str) -> dict:
    resp = client.post("/ask", json={"question": question}, headers=_auth_header(_login(username)))
    assert resp.status_code == 200
    return resp.json()


class TestAuth:
    def test_login_success(self):
        resp = client.post("/auth/login", json={"username": "jonas", "password": "hackathon"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["role"] == "consultant"

    def test_login_wrong_password(self):
        resp = client.post("/auth/login", json={"username": "jonas", "password": "wrong"})
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

    def test_token_without_bearer_scheme_rejected(self):
        token = _login("jonas")
        resp = client.post("/ask", json={"question": "test"}, headers={"Authorization": token})
        assert resp.status_code == 401


class TestRoleBasedAccess:
    def test_consultant_can_ask(self):
        _ask("jonas", "payroll cutoff?")

    def test_consultant_cannot_verify(self):
        token = _login("jonas")
        resp = client.post("/claims/pol-be-cutoff-v3/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_expert_can_verify(self):
        token = _login("sofie")
        resp = client.post("/claims/pol-be-cutoff-v3/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 200

    def test_expert_cannot_verify_own_source(self):
        token = _login("sofie")
        resp = client.post("/claims/email-compliance-v3/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_verify_unknown_claim_is_404(self):
        token = _login("sofie")
        resp = client.post("/claims/does-not-exist/verify", json={"verified": True}, headers=_auth_header(token))
        assert resp.status_code == 404


class TestIDOR:
    def test_consultant_cannot_see_other_clients_docs(self):
        ids = {s["id"] for s in _ask("jonas", VERMEULEN_Q)["sources"]}
        assert "client-note-vermeulen" not in ids

    def test_other_consultant_cannot_see_delvaux_docs(self):
        sources = _ask("lars", DELVAUX_Q)["sources"]
        assert all(s["client"] != "Brouwerij Delvaux" for s in sources)

    def test_consultant_sees_own_client_docs(self):
        ids = {s["id"] for s in _ask("jonas", DELVAUX_Q)["sources"]}
        assert "client-note-delvaux" in ids


class TestInputValidation:
    def test_oversized_question_rejected(self):
        token = _login("jonas")
        resp = client.post("/ask", json={"question": "a" * 2001}, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_max_length_question_accepted(self):
        _ask("jonas", "a" * 2000)

    def test_empty_question_rejected(self):
        token = _login("jonas")
        resp = client.post("/ask", json={"question": "   "}, headers=_auth_header(token))
        assert resp.status_code == 400


class TestDemoScenario:
    def test_delvaux_answer_is_7th(self):
        r = _ask("jonas", DELVAUX_Q)
        assert r["answer"].startswith("The 7th working day")
        assert r["sources"][0]["id"] == "client-note-delvaux"

    def test_newest_chat_is_not_trusted(self):
        r = _ask("jonas", DELVAUX_Q)
        scores = {s["id"]: s["trust_score"] for s in r["sources"]}
        assert scores["chat-teams-10th"] < scores["pol-be-cutoff-v3"]
        assert scores["chat-teams-10th"] < scores["email-compliance-v3"]
        assert "10th" in r["uncertainty"]

    def test_conflict_is_surfaced(self):
        r = _ask("jonas", DELVAUX_Q)
        assert any("chat-teams-10th" in c["source_ids"] for c in r["conflicts"])

    def test_contact_is_not_the_asker(self):
        assert "Jonas" not in (_ask("jonas", DELVAUX_Q)["contact"] or "")


class TestHealthEndpoint:
    def test_health_no_auth(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
