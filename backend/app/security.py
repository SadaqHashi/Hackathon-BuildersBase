import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException, Header

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TOKEN_TTL = timedelta(hours=4)
_tokens: dict[str, dict] = {}

# Compared against when the username is unknown, so response time doesn't reveal valid users.
_DUMMY_HASH = "pbkdf2_sha256$600000$" + "00" * 16 + "$" + "00" * 32


def _load_users() -> list[dict]:
    with open(DATA_DIR / "users.json", encoding="utf-8") as f:
        return json.load(f)


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def _purge_expired():
    now = datetime.now(timezone.utc)
    for token in [t for t, s in _tokens.items() if s["expires"] < now]:
        del _tokens[token]


def login(username: str, password: str) -> dict:
    user = next((u for u in _load_users() if u["username"] == username), None)
    password_ok = _verify_password(password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _purge_expired()
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "username": username,
        "role": user["role"],
        "country": user["country"],
        "clients": user.get("clients", []),
        "display_name": user["display_name"],
        "expires": datetime.now(timezone.utc) + TOKEN_TTL,
    }
    return {"token": token, "role": user["role"], "display_name": user["display_name"]}


def get_current_user(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = _tokens.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if datetime.now(timezone.utc) > session["expires"]:
        del _tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")
    return session


def require_role(user: dict, allowed_roles: list[str]):
    if user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def validate_question(text: str, max_length: int = 2000):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail=f"Input exceeds maximum length of {max_length} characters")
