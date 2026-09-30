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
- Old Delvaux client file (2024) says 6th: superseded by the current client file (`supersedes`), shows as a
  second conflict "Enterprise addendum cutoff: 6th (superseded) vs 7th"
- Teams chat by Pieter Claes (Garage Vermeulen) says "7th as well I think": client-specific but unbacked and
  contradicted. Lars's demo moment: answer stays the 5th. Jonas never sees it (client filter).

Demo questions (frontend dropdown, all verified):
- jonas: "What's the payroll input cutoff for Brouwerij Delvaux?" -> 7th, 2 conflicts
- lars: "What's the payroll input cutoff for Garage Vermeulen?" -> 5th, Pieter's chat not relied on
- anyone: "What's the general payroll input cutoff?" -> 5th

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
- **Sadaq**: `backend/` (incl. LLM layer, trust logic, security, DEMO_MODE), `tests/`
- **Adrian**: `frontend/` (Streamlit), `docs/`, `README.md`. Works on branch `adrian`.
- Shared: `schemas.py` (coordinate changes), `.env.example`, `data/`
- In Adrian's sessions: touch only `frontend/` (+ docs/README). Do NOT edit `backend/` or `tests/`.
  If the frontend needs a backend change, add it under "Requests for Sadaq" instead of changing it.

## Requests for Sadaq (from frontend)
1. **docker-compose is broken for the backend.** In the container `engine.py` resolves `CORPUS_DIR` to `/data`
   (three parents up from `/app/app/engine.py`), but compose mounts `./data` at `/app/data`, so the corpus is not found
   and every answer is "No source...". The same mount also hides `backend/data` (users.json -> login fails) and is
   `:ro`, so writing `demo_cache.json` / `ai_cache.json` fails. Suggest: make the corpus path configurable
   (`CORPUS_DIR` env var) and mount `./data` at e.g. `/corpus:ro`.
2. **DEMO_MODE cache hides verification.** A cached /ask response keeps the old `verified_by`, so after Sofie verifies,
   Jonas re-asking the same question sees no change. Apply `verified_by` after reading the cache (or skip caching it).
3. **Structured fields instead of prose** (frontend currently parses the text, which breaks if wording changes):
   `supporting_source_ids: list[str]`, `not_relied_on: list[{source_id, claim, reason}]`,
   `uncertainty_level: "low" | "medium" | "high"`. Optional, additive schema change.
4. Rejected verifications are not in /ask (`verified_by` only set when verified=True). Frontend reads
   `/claims/verified` for now, so this is low priority.
5. **Non-cutoff questions give wrong answers.** Claim extraction only knows "Nth" ordinals, so e.g.
   "What is the max meal voucher contribution?" answers "The 1st working day" (from the onboarding email) and
   "When must payroll registration be done for a new hire?" answers "The 5th" (should be the 3rd).
   Frontend now says "covers payroll input cutoffs only". Decision (Adrian): stay in the cutoff domain for the demo.
6. **One document conflicting with itself:** the onboarding email states the 1st and the 3rd working day
   (two different deadlines) and shows up as a conflict "1st vs 3rd" with only that email on both sides.
7. **Retrieval noise:** "...cutoff in Belgium?" pulls in holiday pay, meal vouchers, sick leave and mobility policies
   because "Belgium" is in their titles. Demo list uses "What's the general payroll input cutoff?" instead.

## Repo structure (current)
```
.gitignore / .env.example / README.md / CLAUDE.md
docker-compose.yml      backend + frontend containers
backend/
  Dockerfile            Python 3.13-slim, uvicorn on port 8000
  requirements.txt      fastapi, uvicorn, python-dotenv, google-genai, pytest, httpx
  app/schemas.py        contract: AskRequest, Signal, Source (client + verified_by), Conflict, AskResponse
  app/main.py           /health, /auth/login, /ask, /claims/{id}/verify, /claims/verified; CORS 8501
  app/security.py       PBKDF2 hashes, bearer tokens (4h), role checks, input validation, rate limiting
  app/trust_score.py    deterministic claim extraction (regex) + 5 signals: recency (incl. supersession),
                        ownership, source_type, scope_match, corroboration (claim-based, independent owners)
  app/engine.py         client-based access filter, keyword retrieval, deterministic answer, claim-based
                        conflicts, uncertainty text, contact (never the asker), DEMO_MODE caching,
                        verified_by shown on sources after expert verification
  app/claude_service.py Gemini explanation only (model via GEMINI_MODEL), JSON cache; returns None without key
  data/users.json       Jonas (consultant, Delvaux), Lars (consultant, Vermeulen), Sofie (expert); PBKDF2 hashes
  data/ai_cache.json    cached AI responses for demo resilience
  data/demo_cache.json  DEMO_MODE cached responses (auto-populated)
data/
  corpus.json           18 docs: 9 cutoff scenario (Delvaux traps) + 9 filler (holiday pay, meal vouchers,
                        company car, sick leave, onboarding, mobility budget, payslip codes)
  experts.json          people lookup for "who to ask"
tests/                  run: py -m pytest tests/ -v
  test_security.py      auth, RBAC, real IDOR (client filter), input validation, demo scenario
  test_trust_score.py   claim extraction and every signal
frontend/
  app.py                Streamlit answer screen (newbie-friendly): answer card with uncertainty + who to ask,
                        tally pills, conflicts in one expander, sources in 3 collapsible traffic-light groups:
                        green "Safe to rely on" (supports answer, trust >= 0.75, open by default),
                        orange "Check before using" (weak supporter or context), red "Don't rely on" (backend
                        rejected it). Each card: title, meta, trust, one "why" line; "Show details" reveals the
                        5 signals + source text. Verify/Reject buttons for experts.
                        All API/document text escaped via esc() before HTML.
  api.py                httpx client (API_URL env, default http://localhost:8000); 401 -> session dropped
  .streamlit/config.toml light theme, port 8501, telemetry off
  Dockerfile            non-root, used by docker-compose
  requirements.txt      streamlit, httpx
```

## Running (cmd)
```
cd backend
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Test at http://localhost:8000/docs. Log in via `/auth/login`, then send `Authorization: Bearer <token>`.

Frontend (second cmd window, backend must be running):
```
cd frontend
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501, sign in as jonas / hackathon.

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
12. Filler docs: 9 non-cutoff docs (holiday pay, meal vouchers, company car, sick leave, onboarding,
    mobility budget, payslip codes, NL sick leave, holiday chat rumor) — corpus now 18 docs
13. DEMO_MODE=true caches full /ask responses in demo_cache.json so demo works without GCP credits
14. Login rate limiting: 5 attempts per 15 min per username (429 on exceed)
15. Expert verification flip: verified_by field on Source, /ask shows who verified each source
16. docker-compose.yml + backend/Dockerfile for containerized deployment

How the answer is decided (deterministic, no LLM):
- Voters = sources that are owned, not superseded, in scope (scope_match >= 0.7) and not contradicted-and-unbacked
- If a source specific to the asked client states an enterprise claim, the enterprise scope applies, else general
- Per claimed value, sum voters' trust; highest wins. Everything else is listed under "Not relied on" with its weakest signal

## Still open
- **Claim extraction is a regex** for "Nth" ordinals tagged general/enterprise. Works for cutoff questions only.
  Filler docs with other ordinals (e.g. "paid by the 25th") could create false claims and conflicts.
  Replace or back it with LLM extraction (roadmap 5); keep the regex as the DEMO_MODE fallback.
- **Retrieval is keyword overlap** (stopwords removed), no relevance ranking.
- **Demo password is the weak shared "hackathon"**, hashed but still weak.
- **Duplicate titles:** two chats are both "Teams #payroll-be". The UI must show owner + date next to titles.
- **Token store is in-memory** (lost on restart). Acceptable for hackathon.
- **Gemini model unverified:** default `GEMINI_MODEL=gemini-2.5-flash`; check it is available on our GCP account.

## Remaining roadmap
1. ~~Connect Aikido account + repo~~
2. ~~Switch backend to Delvaux scenario~~ DONE
3. ~~Retrieval + scoring, scope_match, claim-based corroboration~~ DONE
4. ~~Frontend (Streamlit): one answer screen against /ask~~ DONE (first version, branch `adrian`)
5. LLM layer: claim extraction via Gemini (optional, regex works for demo)
6. ~~Role-based access: IDOR client filter~~ DONE
7. FIRST Aikido AI Code Audit = "before" screenshot
8. ~~DEMO_MODE~~ DONE (set DEMO_MODE=true in .env)
9. Fix Aikido findings, rescan = "after" screenshot (reserve 1 hour+)
10. ~~docker-compose~~ DONE + README with "unfinished" section
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
- Passwords: PBKDF2-SHA256 (600k iterations) in users.json, constant-time compare, dummy hash for unknown users
- Login rate limiting: 5 failed attempts per 15 min per username (returns 429)
- Input validated: /ask question non-empty and max 2000 chars, login field lengths, claim_id pattern
- Source text is sanitized and delimited before it goes into the Gemini prompt
- Expert cannot verify own source (403)
- No keys in code or history
