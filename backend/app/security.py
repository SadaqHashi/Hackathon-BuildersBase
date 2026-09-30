import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException, Header

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_tokens: dict[str, dict] = {}


def _load_users() -> list[dict]:
    with open(DATA_DIR / "users.json") as f:
        return json.load(f)


def login(username: str, password: str) -> dict:
    users = _load_users()
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Demo mode: accept "hackathon" as password for all users
    if password != "hackathon":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "username": username,
        "role": user["role"],
        "country": user["country"],
        "clients": user.get("clients", []),
        "display_name": user["display_name"],
        "expires": datetime.now(timezone.utc) + timedelta(hours=4),
    }
    return {"token": token, "role": user["role"], "display_name": user["display_name"]}


def get_current_user(authorization: str = Header(default="")) -> dict:
    token = authorization.replace("Bearer ", "")
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


def require_not_self(user: dict, target_username: str):
    if user["username"] == target_username:
        raise HTTPException(status_code=403, detail="Cannot verify your own claims")


def validate_input_length(text: str, max_length: int = 2000):
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail=f"Input exceeds maximum length of {max_length} characters")
