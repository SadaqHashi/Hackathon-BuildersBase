# TrustLens: Tectonic Hackathon 2026 (SD Worx challenge)

## Working agreement
- Work step by step. Finish one step, then ask permission before starting the next.
- Be critical and direct. No sugar coating, no padding, no em-dashes.
- Dev machine is Windows, using **cmd** (not PowerShell). Give cmd commands.
- Never commit secrets. Run `git status` before every `git add .`; `.env` must never appear.

## The challenge
SD Worx: "Unlock the Knowledge Within. Find it. Understand it. Trust it."
Build a focused proof of concept that helps an employee move from "I found something" to "I understand why I can rely on it." One role, one workflow, one moment of doubt. Judges explicitly reject black-box answers.

Judging: Originality 30%, Technical ability 30%, Fit to challenge 30%, Security (Aikido AI Code Audit) 10%.
Submission: short description, demo video under 3 min, public GitHub repo, Aikido before/after screenshots, README (what it is, how to run, what's unfinished).

## Core product decision
A question goes in. Out comes an answer, ranked sources side by side with trust reasons, surfaced conflicts, what's uncertain, and who to ask. An expert can verify a claim, flipping it from uncertain to trusted.

Explainable, decomposed trust:
- Trust signals are computed **deterministically from metadata** in `trust_score.py`, each with a human-readable reason:
  recency, ownership, scope_match (country/client), source_type, corroboration.
- A per-source `trust_score` is a weighted aggregate of those signals. It is always shown together with its signals, never alone. There is no single overall confidence % for the answer.
- Trust logic lives only in code, never in prompts. The LLM (Google GenAI / Gemini via GCP credits) only extracts claims, detects conflicts and writes the explanation. It does not decide trust.
- Conflicts between sources are **surfaced**, never hidden. We never silently pick one winner.

## Scenario / demo
Role: payroll consultant (Jonas Peeters). Question: "What's the payroll input cutoff for Brouwerij Delvaux?"
Correct answer: **7th working day** (enterprise SLA addendum). General BE rule is the 5th.
Traps in `data/corpus.json` (all fictional internal process, not real law):
- BE policy v2 (2023) says 8th: outdated
- NL policy says 3rd: wrong country
- Ownerless wiki cheat sheet says 8th: orphaned duplicate
- Teams chat 2026 says "10th now": MOST RECENT but unsourced and wrong. Key demo moment: "newest wins" fails.
- Compliance email from Sofie Maes confirms v3 change
- Client note Delvaux: authoritative source for the exception
- Client note Garage Vermeulen belongs to Lars Wouters: Jonas must NOT see it (IDOR demo)

Expert for verification: Sofie Maes (Payroll Compliance Lead BE).

## Architecture
- **Backend**: Python 3.13, FastAPI + Pydantic, uvicorn, python-dotenv, google-genai (`backend/app/`)
- **Frontend**: Streamlit calling the API via httpx (`frontend/`, port 8501)
- **No database**: data in JSON files, sessions (auth tokens) in memory
- Run later via docker-compose

## Rules
- `schemas.py` is the contract. Do NOT change it without agreement from both sides.
- Source text is untrusted input. Always sanitize/escape (also before it goes into an LLM prompt).
- Auth and authorization happen in the backend only. Never trust a client-sent user/client id.
- No secrets in code or history. Use `.env` (gitignored); GCP service account files (`gcp-*.json`) are gitignored.

## Ownership
- Person 1: `backend/`, `tests/`
- Person 2: `frontend/`, `docs/`, `README.md`
- Shared: `schemas.py` (coordinate changes), `.env.example`, `data/`

## Repo structure (current)
```
.gitignore / .env.example / README.md / CLAUDE.md
backend/
  requirements.txt      fastapi, uvicorn, python-dotenv, google-genai, pytest, httpx
  app/schemas.py        contract: AskRequest, Signal, Source (incl client field), Conflict, AskResponse
  app/main.py           /health, /auth/login, /ask, /claims/{id}/verify, /claims/verified; CORS 8501
  app/security.py       login, in-memory bearer tokens (4h), require_role, input validation
  app/trust_score.py    4 signals: recency, ownership, source_type, corroboration (weighted)
  app/engine.py         loads data/corpus.json, scores, conflicts, experts.json for contact
  app/claude_service.py Google GenAI comparison with JSON cache + fallback (no API key needed)
  data/users.json       Jonas (consultant, Delvaux), Lars (consultant, Vermeulen), Sofie (expert)
  data/ai_cache.json    cached AI responses for demo resilience
data/
  corpus.json           Delvaux scenario, 9 docs: id, title, source_type, owner, updated_at, country, client, content
  experts.json          people lookup for "who to ask"
tests/
  test_security.py      auth, RBAC, IDOR, input validation (13 tests)
  test_trust_score.py   scoring logic (6 tests)
frontend/               not started
```

## Running (cmd)
```
cd backend
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Test at http://localhost:8000/docs. Log in via `/auth/login`, then send `Authorization: Bearer <token>`.

## Status
Done:
1. Repo + secret hygiene (.gitignore, .env.example)
2. Backend scaffold with response contract
3. Delvaux corpus (9 trap docs) + experts.json
4. Backend core: token auth + roles, deterministic scoring (recency, ownership, source_type, corroboration), conflict detection, verify endpoint
5. Switched to Delvaux scenario: engine reads data/corpus.json, users are Jonas/Lars/Sofie, sources.json retired, CORS 8501 only
6. AI service (claude_service.py): Google GenAI source comparison with JSON cache + auto-fallback without API key
7. Schema updated: Source has client field, source_type supports wiki and client_note
8. trust_score.py: weights for wiki (0.4) and client_note (0.85), corroboration signal
9. 19 passing tests (auth, RBAC, IDOR, input validation, trust scoring)

Known gaps:
- `/ask` returns all 9 sources: no retrieval, no filtering by question relevance
- `scope_match` signal not implemented (country/client matching)
- No client-based access control yet: Jonas can still see Garage Vermeulen docs (IDOR)
- Conflict detection is type-based (formal vs informal), not claim-based
- Login still uses hardcoded password "hackathon" for all users
- Pending in corpus: 8-10 filler docs so retrieval isn't trivial

## Remaining roadmap
1. ~~Connect Aikido account + repo~~
2. ~~Switch backend to Delvaux scenario~~ DONE
3. Retrieval + scoring: find relevant docs, add scope_match signal  <- NEXT
4. Frontend (Streamlit, parallel): one answer screen against /ask
5. LLM layer: claim extraction, conflict detection, explained answer via Gemini
6. Role-based access: consultants only see their own clients' docs (Vermeulen IDOR case)
7. FIRST Aikido AI Code Audit = "before" screenshot
8. DEMO_MODE=true: cached responses for demo questions so the repo works after GCP credits expire (1 week)
9. Fix Aikido findings, rescan = "after" screenshot (reserve 1 hour+)
10. docker-compose + README with "unfinished" section
11. Feature freeze ~90 min before deadline, record video, submit

## Login credentials (demo)
All users use password `hackathon`. Usernames: `jonas`, `lars`, `sofie`.

## API endpoints
| Method | Path | Auth | Role |
|--------|------|------|------|
| GET | /health | No | - |
| POST | /auth/login | No | - |
| POST | /ask | Yes | consultant, expert |
| POST | /claims/{id}/verify | Yes | expert only |
| GET | /claims/verified | Yes | any logged in |

## Security notes (Aikido checks business logic, IDOR, authn, authz)
- CORS restricted to localhost:8501 (tighten `allow_headers="*"` before Aikido)
- Access control enforced server-side from the session, never from request params
- Known issue: login accepts hardcoded password "hackathon" for all users. Fix before Aikido round.
- Input length validated (max 2000 chars on /ask)
- No keys in code or history
