from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .schemas import AskRequest, AskResponse
from .security import login, get_current_user, require_role, validate_input_length
from .engine import ask as engine_ask, verify_claim, get_verified_claims

app = FastAPI(title="TrustLens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class VerifyRequest(BaseModel):
    verified: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    return login(req.username, req.password)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, user: dict = Depends(get_current_user)):
    require_role(user, ["consultant", "expert", "admin"])
    validate_input_length(req.question)
    return engine_ask(req.question, user_country=user.get("country", "ALL"))


@app.post("/claims/{claim_id}/verify")
def verify(claim_id: str, req: VerifyRequest, user: dict = Depends(get_current_user)):
    require_role(user, ["expert", "admin"])
    return verify_claim(claim_id, user["username"], req.verified)


@app.get("/claims/verified")
def list_verified(user: dict = Depends(get_current_user)):
    return get_verified_claims()