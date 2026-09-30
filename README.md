# TrustLens
Adrian Dyszczak & Sadaq Hashi

**Find an answer, and see exactly why you can (or can't) rely on it.**

Built for the SD Worx challenge at Tectonic Hackathon 2026: *"Unlock the Knowledge Within. Find it. Understand it. Trust it."*

TrustLens helps a payroll consultant move from "I found something" to "I understand why I can rely on it". Instead of one black-box answer, it shows every source it found, scores each one on five transparent trust signals, surfaces where sources disagree, and says who to ask when in doubt.

> All documents, clients and people in this repo are fictional. The payroll rules are invented internal process, not real law.

---

## The moment of doubt

Jonas Peeters, payroll consultant, asks: **"What's the payroll input cutoff for Brouwerij Delvaux?"**

His company's knowledge is scattered and contradictory:

| Source | Says | Problem |
|---|---|---|
| Policy BE v3 (2026) | 5th working day, 7th for enterprise clients with an SLA addendum | none |
| Client file Brouwerij Delvaux | 7th working day (SLA addendum signed) | none, this is the authoritative exception |
| Compliance email (Sofie Maes) | confirms the v3 change | none |
| Policy BE v2 (2023) | 8th | outdated, replaced by v3 |
| Client file Delvaux (2024) | 6th | outdated, replaced by the 2026 file |
| Wiki cheat sheet | 8th | nobody owns it |
| Policy NL | 3rd | wrong country |
| **Teams chat, last month** | **"the 10th now"** | **newest source, but unsourced and wrong** |

A "newest wins" or "most similar text wins" system gets this wrong. TrustLens answers **the 7th working day**, puts the chat under "Don't rely on" with the reason *"No source backs the 10th; contradicted by Policy v3, Compliance email"*, and shows the 5th / 8th / 10th disagreement openly.

It also enforces access: Jonas never sees documents of Garage Vermeulen, a client of his colleague Lars.

---

## How it works

**Trust is decided by code, not by an AI.** Every number on screen can be traced to a rule.

```
question ─► access filter ─► find documents ─► extract claims ─► score 5 signals ─► vote ─► answer
            (your clients     (keyword match)   ("5th working     per document       (trusted,
             only)                               day", general                        current, in-scope
                                                 or enterprise)                       sources only)
```

### The five trust signals

| Signal | Question it answers | Example reason shown to the user |
|---|---|---|
| Up to date | How recent is it? Has it been replaced? | "Superseded by Payroll Input Cutoff - Belgium (v3)" |
| Owner | Is someone accountable for it? | "No owner: nobody is accountable for keeping this up to date" |
| Kind of source | Policy, client note, email, wiki or chat? | "Chat message: informal and unreviewed" |
| Applies to you | Right country? Right client? | "Applies to NL, not BE" |
| Backed by others | Do independent sources (different owners) say the same? | "No source backs the 10th; contradicted by ..." |

Each document's trust score is a weighted average of these signals and is always shown together with them. Recency has the lowest weight on purpose: newest is not the same as right.

### How the answer is chosen

1. Only sources that are **owned, current, in scope and not contradicted** get a vote.
2. If a source specific to the asked client states an exception (enterprise SLA addendum), the exception applies.
3. Per claimed value, the trust scores of its supporters are added up. The highest total wins.
4. Everything else is listed as "Don't rely on", each with its weakest signal as the reason.

### Where the AI fits

Google Gemini is optional. When a `GOOGLE_API_KEY` is set, it receives the already-scored sources and adds a short explanation, with the instruction that the scores are final. Without a key the app works exactly the same. The answer is fully deterministic and reproducible.

### Expert verification

An expert (Sofie Maes, Payroll Compliance Lead) can mark a source as verified or rejected. Consultants then see "Verified by expert" on that source. Experts cannot verify their own documents.

---

## Run it locally

Requirements: **Python 3.13** and Git. Two terminals: one for the API, one for the UI.

**1. Clone**
```
git clone https://github.com/SadaqHashi/Hackathon-BuildersBase.git
cd Hackathon-BuildersBase
copy .env.example .env
```
(macOS/Linux: `cp .env.example .env`). The `.env` can stay as is; Gemini is optional.

**2. Backend (terminal 1)**

Windows (cmd):
```
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
macOS/Linux:
```
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
API docs: http://localhost:8000/docs

**3. Frontend (terminal 2)**

Windows (cmd):
```
cd frontend
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
```
macOS/Linux: same as above with `python3.13` and `source .venv/bin/activate`.

Open **http://localhost:8501** and sign in.

### Demo users

All passwords: `hackathon` (demo only).

| Username | Who | What to try |
|---|---|---|
| `jonas` | Payroll consultant, client Brouwerij Delvaux | "What's the payroll input cutoff for Brouwerij Delvaux?" gives the 7th, with 2 conflicts. Ask about Garage Vermeulen: its documents stay hidden. |
| `lars` | Payroll consultant, client Garage Vermeulen | "What's the payroll input cutoff for Garage Vermeulen?" gives the 5th; a colleague's "7th as well I think" chat is not relied on. |
| `sofie` | Payroll Compliance Lead (expert) | Verify or reject sources. Try verifying her own email: refused. |

### Optional settings (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | empty | Enables the Gemini explanation |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `DEMO_MODE` | `false` | `true` caches full answers so the demo works offline |

### Tests

From the repo root, with the backend venv:
```
backend\.venv\Scripts\python.exe -m pytest -q
```
37 tests: authentication, role checks, client isolation (IDOR), input validation, every trust signal, and the full demo scenario.

---

## Security

- **Server-side access control.** Consultants only receive documents of their own clients; the filter runs on the logged-in session, never on client-sent ids.
- **Authentication.** PBKDF2-SHA256 password hashes (600k iterations), constant-time comparison, same response for unknown users, bearer tokens with a 4-hour expiry, login rate limiting (5 attempts per 15 minutes).
- **Authorization.** Role checks per endpoint; only experts can verify, and not their own sources.
- **Untrusted content.** Document text is escaped before it is shown and delimited before it goes into an LLM prompt.
- **Input validation.** Question length limits, login field limits, strict id pattern on the verify endpoint.
- **CORS** restricted to the frontend origin; no secrets in code (`.env` is gitignored).
- **Aikido AI Code Audit.** Findings fixed so far include dependency CVEs in starlette, pillow and pandas (pinned to patched versions).

---

## Project structure

```
backend/
  app/main.py            API endpoints, CORS
  app/engine.py          access filter, retrieval, answer, conflicts, uncertainty, who to ask
  app/trust_score.py     claim extraction and the five trust signals
  app/security.py        login, tokens, roles, rate limiting, input validation
  app/claude_service.py  optional Gemini explanation (file name is historical)
  data/users.json        demo users with password hashes
frontend/
  app.py                 Streamlit answer screen
  api.py                 HTTP client for the backend
data/
  corpus.json            the fictional knowledge base (policies, client files, emails, wiki, chats)
  experts.json           who to ask, per topic
tests/                   pytest suite
```

---

## What's unfinished

We chose depth on one workflow over breadth. Known limitations:

- **Only payroll input cutoff questions are supported.** Claims are extracted with a pattern that recognises "Nth working day". Questions on other topics (holiday pay, meal vouchers, ...) currently get a wrong or empty answer instead of an honest "I can't verify this". Next step: Gemini extracts structured claims (topic, value, unit) once per document, reviewed and stored as data, while scoring stays in code.
- **Retrieval is keyword matching**, not semantic search.
- **docker-compose does not work yet.** The backend container cannot find the corpus (path mismatch with the mounted volume). Use the local setup above.
- **The frontend reads parts of the answer from text** (which sources support it, which don't). Structured fields in the API response would be more robust.
- **Everything is in memory**: sessions and expert verifications are lost on restart. There is no database.
- **Demo password** is shared and weak by design; real deployment would use SSO.

---

## Team

Built by [adinho97](https://github.com/adinho97) and [SadaqHashi](https://github.com/SadaqHashi) at Tectonic Hackathon 2026.
