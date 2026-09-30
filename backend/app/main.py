from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .schemas import AskRequest, AskResponse
from .security import login, get_current_user, require_role, validate_question
from .engine import ask as engine_ask, verify_claim, get_verified_claims

load_dotenv()

app = FastAPI(title="TrustLens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class LoginRequest(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


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
    validate_question(req.question)
    return engine_ask(req.question, user)


@app.post("/claims/{claim_id}/verify")
def verify(
    req: VerifyRequest,
    claim_id: str = Path(max_length=64, pattern=r"^[a-z0-9-]+$"),
    user: dict = Depends(get_current_user),
):
    require_role(user, ["expert", "admin"])
    return verify_claim(claim_id, user, req.verified)


@app.get("/claims/verified")
def list_verified(user: dict = Depends(get_current_user)):
    return get_verified_claims()
