# TrustLens - Project Rules

## What this is
SD Worx hackathon project. A question goes in, out comes a trust status, trust score with reasons, sources side by side, and an expert contact. An expert can verify a claim, flipping uncertain to trusted.

## Architecture
- **Backend**: FastAPI + Pydantic (`backend/app/`). Person 1 owns this.
- **Frontend**: Streamlit calling the API via httpx (`frontend/`). Person 2 owns this.
- **No database**: data lives in JSON files (`backend/data/`), sessions in memory.

## Rules
- `schemas.py` is the contract. Do NOT change it without agreement from both sides.
- Trust score logic lives only in code (`trust_score.py`), never hardcoded in prompts.
- AI (Google GenAI) only compares and explains — it does not decide trust scores.
- Source text is untrusted input. Always sanitize/escape.
- Auth and authorization happen in the backend only.
- No secrets in code. Use `.env` (already in `.gitignore`).

## Ownership
- Person 1: `backend/`, `tests/`
- Person 2: `frontend/`, `docs/`, `README.md`
- Shared: `schemas.py` (coordinate changes), `.env.example`

## Running
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
