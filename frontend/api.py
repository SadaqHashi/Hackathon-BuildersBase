"""Thin httpx client for the TrustLens backend. All auth and access control happen server-side."""
import os
from urllib.parse import quote

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 60.0


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _call(method: str, path: str, token: str | None = None, payload: dict | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = httpx.request(method, f"{API_URL}{path}", headers=headers, json=payload, timeout=TIMEOUT)
    except httpx.HTTPError:
        raise ApiError(f"Cannot reach the TrustLens API at {API_URL}. Is the backend running?")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except ValueError:
            detail = None
        # FastAPI validation errors come back as a list; don't echo those raw.
        if not isinstance(detail, str):
            detail = "The request was rejected."
        raise ApiError(detail, resp.status_code)
    return resp.json()


def login(username: str, password: str) -> dict:
    return _call("POST", "/auth/login", payload={"username": username, "password": password})


def ask(token: str, question: str) -> dict:
    return _call("POST", "/ask", token=token, payload={"question": question})


def verify(token: str, source_id: str, verified: bool) -> dict:
    return _call("POST", f"/claims/{quote(source_id, safe='')}/verify", token=token, payload={"verified": verified})


def verified_claims(token: str) -> dict:
    return _call("GET", "/claims/verified", token=token)
