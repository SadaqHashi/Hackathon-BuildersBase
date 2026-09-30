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
  .venv/                (gitignored; activate: .venv\Scripts\activate.bat)
  requirements.txt
  app/schemas.py        contract: AskRequest, Signal, Source, Conflict, AskResponse
  app/main.py           /health, /auth/login, /ask, /claims/{id}/verify; CORS allowlist
  app/security.py       login, in-memory bearer tokens (4h), require_role
  app/trust_score.py    deterministic signals + weighted trust_score
  app/engine.py         loads sources, scores them, conflicts, uncertainty, contact
  data/sources.json     OLD DE mock scenario, to be retired
  data/users.json       OLD DE users (Anna/Klaus/Sarah), to be replaced
data/
  corpus.json           Delvaux scenario, 9 docs: id, title, source_type, owner, updated_at, country, client, content
  experts.json          people lookup for "who to ask"
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
4. Backend core (Sadaq): token auth + roles, deterministic scoring (recency, ownership, source_type), naive conflict detection, verify endpoint

Known gaps in the current backend:
- `engine.py` reads the DE mock (`backend/data/sources.json`), not `data/corpus.json`
- `/ask` returns every source: no retrieval, no filtering by the logged-in user's clients
- `scope_match` and `corroboration` signals are not implemented
- Conflict detection is hardcoded (policy vs chat), not claim-based
- `Source` schema has no `client` field; `source_type` comment lacks `wiki` and `client_note` (needs a coordinated schema change)
- CORS still allows `localhost:5173` (React is dropped)

Pending in corpus: 8 to 10 filler docs (holiday pay, meal vouchers, company car, sick leave, onboarding, mobility budget...) so retrieval isn't trivial.

## Remaining roadmap
1. Connect Aikido account + repo (DO NOT run the audit yet, save credits)
2. Switch the backend to the Delvaux scenario: engine reads `data/corpus.json`, users.json becomes Jonas/Lars/Sofie, retire `sources.json`, CORS to 8501 only  <- NEXT
3. Retrieval + scoring: find relevant docs, add scope_match + corroboration signals
4. Frontend (Streamlit, parallel): one answer screen against /ask
5. LLM layer: claim extraction, conflict detection, explained answer via Gemini
6. Role-based access: consultants only see their own clients' docs (Vermeulen IDOR case)
7. FIRST Aikido AI Code Audit = "before" screenshot
8. DEMO_MODE=true: cached responses for demo questions so the repo works after GCP credits expire (1 week)
9. Fix Aikido findings, rescan = "after" screenshot (reserve 1 hour+)
10. docker-compose + README with "unfinished" section
11. Feature freeze ~90 min before deadline, record video, submit

## Security notes (Aikido checks business logic, IDOR, authn, authz)
- CORS stays restricted, no wildcard origins (tighten `allow_headers="*"` too)
- Access control enforced server-side from the session, never from request params
- Known issue: login accepts the hardcoded password "hackathon" for every user while users.json holds unused (fake) bcrypt hashes. Fix before or as part of the Aikido round.
- No keys in code or history
