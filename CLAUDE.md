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
  app/security.py       PBKDF2 password hashes, in-memory bearer tokens (4h), require_role, input validation
  app/trust_score.py    deterministic claim extraction (regex) + 5 signals: recency (incl. supersession),
                        ownership, source_type, scope_match, corroboration (claim-based, independent owners)
  app/engine.py         client-based access filter, keyword retrieval, deterministic answer, claim-based
                        conflicts, uncertainty text, contact (never the asker)
  app/claude_service.py Gemini explanation only (model via GEMINI_MODEL), JSON cache; returns None without key
  data/users.json       Jonas (consultant, Delvaux), Lars (consultant, Vermeulen), Sofie (expert); PBKDF2 hashes
  data/ai_cache.json    cached AI responses for demo resilience
data/
  corpus.json           Delvaux scenario, 9 docs: id, title, source_type, owner, updated_at, country, client,
                        content, optional supersedes (id of the doc it replaces)
  experts.json          people lookup for "who to ask"
tests/                  run from repo root: backend\.venv\Scripts\python.exe -m pytest -q
  test_security.py      auth, RBAC, real IDOR (client filter), input validation, demo scenario
  test_trust_score.py   claim extraction and every signal
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
9. Trust logic fixed so the demo tells the right story: Delvaux question answers "7th working day",
   client note ranks first, "10th now" chat scores 0.46 with reason "no source backs the 10th; contradicted by ..."
10. Client-based access control (Jonas never sees Vermeulen docs), PBKDF2 login, strict Bearer parsing,
    CORS headers restricted, empty question rejected, verify endpoint checks claim exists + not own source
11. 37 passing tests

How the answer is decided (deterministic, no LLM):
- Voters = sources that are owned, not superseded, in scope (scope_match >= 0.7) and not contradicted-and-unbacked
- If a source specific to the asked client states an enterprise claim, the enterprise scope applies, else general
- Per claimed value, sum voters' trust; highest wins. Everything else is listed under "Not relied on" with its weakest signal

## Still open
- **Expert verification has no visible effect.** `/claims/{id}/verify` stores the verdict, but `/ask` ignores it.
  The "uncertain -> trusted" flip needs `verified_by: str | None = None` on `Source` (schema change, needs both sides).
- **Claim extraction is a regex** for "Nth" ordinals tagged general/enterprise. Works for cutoff questions only.
  Filler docs with other ordinals (e.g. "paid by the 25th") would create false claims and conflicts.
  Replace or back it with LLM extraction (roadmap 5); keep the regex as the DEMO_MODE fallback.
- **Retrieval is keyword overlap** (stopwords removed), no relevance ranking.
- **Demo password is the weak shared "hackathon"**, now hashed in users.json instead of hardcoded, but still weak.
- **Duplicate titles:** two chats are both "Teams #payroll-be". The UI must show owner + date next to titles.
- **No login rate limiting**; token store is in-memory (lost on restart).
- **Gemini model unverified:** default `GEMINI_MODEL=gemini-2.5-flash`; check it is available on our GCP account.
  Also check whether a plain `GOOGLE_API_KEY` bills the GCP credits or whether we need Vertex AI (GCP_PROJECT_ID).
- **Filler docs** (8-10) still pending in corpus.json so retrieval isn't trivial.
- **Not committed yet:** all trust-logic and security changes are local on `main`. Put them on a branch + PR.

## For Sadaq (read before pulling)
Adrian's session rewrote parts of the backend you own. Summary of what changed and why:
- `trust_score.py`: rewritten. Old corroboration counted "another source of the same type" as support, so the wrong
  "10th now" chat scored 0.79 (above the correct email) and superseded v2 was "corroborated" by v3.
  Now: regex claim extraction, corroboration = same claimed value from a different owner, new `scope_match` signal,
  supersession via `supersedes` field in corpus.json, chat authors are not accountable owners, recency weight 0.10.
- `engine.py`: rewritten. `ask(question, user)` now takes the whole session user (was `user_country`).
  Adds client-based access filter (IDOR fix), keyword retrieval, deterministic answer, claim-based conflicts,
  uncertainty text listing what was not relied on and why, contact is never the asker.
  NL docs are no longer filtered out; they are shown with scope_match 0.0 so the "wrong country" trap is visible.
  `verify_claim(claim_id, user, verified)` now takes the user dict, returns 404 for unknown/invisible ids
  and 403 when an expert verifies their own source. Claim ids are corpus doc ids.
- `claude_service.py`: bug fix, it read `excerpt` but the corpus field is `content`, so Gemini got empty text.
  Now receives scored `Source` objects with signals, is told not to re-rank, returns `None` without key
  (old generic fallback said "rely on the official policy", which is wrong for Delvaux). Model via `GEMINI_MODEL`.
- `security.py`: PBKDF2 hashes in users.json replace the hardcoded password check (same demo password),
  strict `Bearer` parsing, expired-token purge. `validate_input_length` renamed to `validate_question` (also rejects empty).
- `main.py`: `load_dotenv()`, CORS headers limited, login field max lengths, claim_id path pattern.
- `users.json`: real PBKDF2 hashes (the old bcrypt-looking hashes were fake and unused).
- Tests: 37 passing. Old `TestIDOR` did not test access; replaced with real client-filter tests.
  `test_empty_question` now expects 400. Demo scenario tests assert the 7th answer and the chat ranking.
- `schemas.py`: NOT changed. Proposal to agree on: add `verified_by` to `Source` for the verification flip.

## Remaining roadmap
1. ~~Connect Aikido account + repo~~
2. ~~Switch backend to Delvaux scenario~~ DONE
3. ~~Retrieval + scoring, scope_match, claim-based corroboration~~ DONE (basic)
4. Frontend (Streamlit): one answer screen against /ask  <- NEXT
5. LLM layer: claim extraction, conflict detection, explained answer via Gemini
6. ~~Role-based access: consultants only see their own clients' docs~~ DONE
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
- CORS restricted to localhost:8501, headers limited to Authorization + Content-Type
- Access control enforced server-side from the session, never from request params
- Passwords: PBKDF2-SHA256 (600k iterations) in users.json, constant-time compare, dummy hash for unknown users.
  Demo password is still the weak shared "hackathon" (documented, not in code).
- Input validated: /ask question non-empty and max 2000 chars, login field lengths, claim_id pattern
- Source text is sanitized and delimited before it goes into the Gemini prompt
- No keys in code or history
