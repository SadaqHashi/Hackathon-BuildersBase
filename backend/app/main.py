from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import AskRequest, AskResponse, Source, Signal, Conflict

app = FastAPI(title="TrustLens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    return AskResponse(
        answer="Stub answer for: " + req.question,
        sources=[
            Source(
                id="doc-1", title="BE Payroll Policy 2026", owner="Payroll BE",
                updated_at="2026-07-01", country="BE", source_type="policy",
                excerpt="Final pay must be settled within 30 days.",
                signals=[
                    Signal(name="recency", score=0.95, reason="Updated 3 months ago"),
                    Signal(name="ownership", score=1.0, reason="Owned by Payroll BE"),
                ],
                trust_score=0.92,
            )
        ],
        conflicts=[
            Conflict(claim="Final pay deadline", source_ids=["doc-1", "chat-7"],
                     description="Policy says 30 days, 2024 Teams message says 45.")
        ],
        uncertainty="Unclear whether the rule applies to part-time contracts.",
        contact="Payroll BE team",
    )