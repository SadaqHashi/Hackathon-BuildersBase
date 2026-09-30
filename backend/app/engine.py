import json
import os
import re
from pathlib import Path
from fastapi import HTTPException
from .schemas import AskResponse, Source, Conflict
from .trust_score import compute_signals, compute_trust_score, extract_claims, ordinal, superseded_by
from .claude_service import compare_sources

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_CACHE_FILE = CACHE_DIR / "demo_cache.json"

# Words too common to make a document relevant on their own.
_STOPWORDS = {
    "what", "whats", "the", "for", "and", "our", "are", "is", "was", "does", "which", "when",
    "how", "who", "can", "with", "from", "this", "that", "payroll", "client", "clients",
}
# Signals below this never count toward the answer (wrong country, other client).
_IN_SCOPE = 0.7
# Corroboration at or below this means: no source backs the claim and others contradict it.
_CONTRADICTED = 0.1

_verified_claims: dict[str, dict] = {}


def _load_json(name: str) -> list[dict]:
    path = CORPUS_DIR / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower().replace("-", "").replace("'", ""))
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def can_see(doc: dict, user: dict) -> bool:
    """Consultants only see client-specific documents for their own clients."""
    if user["role"] in ("expert", "admin"):
        return True
    return doc.get("client") is None or doc.get("client") in user.get("clients", [])


def _is_relevant(doc: dict, question_terms: set[str]) -> bool:
    doc_terms = _terms(f"{doc.get('title', '')} {doc.get('client') or ''} {doc.get('content', '')}")
    return bool(question_terms & doc_terms)


def _target_client(question: str, docs: list[dict]) -> str | None:
    q = question.lower()
    return next((d["client"] for d in docs if d.get("client") and d["client"].lower() in q), None)


def _signal(source: Source, name: str) -> float:
    return next((s.score for s in source.signals if s.name == name), 0.0)


def _weakest_reason(source: Source) -> str:
    return min(source.signals, key=lambda s: s.score).reason


def _load_demo_cache() -> dict:
    if DEMO_CACHE_FILE.exists():
        with open(DEMO_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_demo_cache(cache: dict):
    with open(DEMO_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def ask(question: str, user: dict) -> AskResponse:
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if demo_mode:
        cache = _load_demo_cache()
        cache_key = f"{user['username']}::{question.strip().lower()}"
        if cache_key in cache:
            return AskResponse(**cache[cache_key])

    visible = [d for d in _load_json("corpus.json") if can_see(d, user)]
    question_terms = _terms(question)
    docs = [d for d in visible if _is_relevant(d, question_terms)]
    target_client = _target_client(question, docs)
    user_country = user.get("country", "ALL")

    sources: list[Source] = []
    claims_by_id: dict[str, list] = {}
    superseded_ids: set[str] = set()
    for doc in docs:
        signals = compute_signals(doc, docs, user_country=user_country, target_client=target_client)
        claims_by_id[doc["id"]] = extract_claims(doc.get("content", ""))
        if superseded_by(doc, docs):
            superseded_ids.add(doc["id"])
        verification = _verified_claims.get(doc["id"])
        sources.append(Source(
            id=doc["id"],
            title=doc["title"],
            owner=doc.get("owner"),
            updated_at=doc["updated_at"],
            country=doc["country"],
            source_type=doc["source_type"],
            excerpt=doc.get("content", ""),
            client=doc.get("client"),
            verified_by=verification["verified_by"] if verification and verification["verified"] else None,
            signals=signals,
            trust_score=compute_trust_score(signals),
        ))
    sources.sort(key=lambda s: s.trust_score, reverse=True)

    if not sources:
        return AskResponse(
            answer="No source you have access to covers this question.",
            sources=[],
            conflicts=[],
            uncertainty="High: nothing to base an answer on.",
            contact=_pick_contact(question_terms, user, []),
        )

    # Only current, owned, in-scope sources that aren't contradicted-and-unbacked vote on the answer.
    voters = [
        s for s in sources
        if s.owner
        and s.id not in superseded_ids
        and _signal(s, "scope_match") >= _IN_SCOPE
        and _signal(s, "corroboration") > _CONTRADICTED
    ]
    scope = "general"
    if target_client and any(
        s.client == target_client and any(c[0] == "enterprise" for c in claims_by_id[s.id]) for s in voters
    ):
        scope = "enterprise"

    winner, supporters, rivals = _tally(voters, claims_by_id, scope)
    contact = _pick_contact(question_terms, user, supporters)
    conflicts = _detect_conflicts(sources, claims_by_id, superseded_ids, user_country)

    if winner is None:
        answer = "The sources you can see do not state a clear answer."
        uncertainty = "High: no current, owned source in scope makes a checkable claim."
    else:
        answer = _answer_text(winner, supporters, scope, target_client, voters, claims_by_id)
        uncertainty = _uncertainty_text(winner, supporters, rivals, sources, claims_by_id, scope, contact)

    ai = compare_sources(question, sources)
    if ai:
        answer += f" {ai.summary}"

    response = AskResponse(
        answer=answer,
        sources=sources,
        conflicts=conflicts,
        uncertainty=uncertainty,
        contact=contact,
    )

    if demo_mode:
        cache[cache_key] = response.model_dump()
        _save_demo_cache(cache)

    return response


def _tally(voters: list[Source], claims_by_id: dict, scope: str):
    """Sum trust per claimed value within the applicable scope. Highest total wins."""
    totals: dict[int, float] = {}
    backers: dict[int, list[Source]] = {}
    for s in voters:
        for c_scope, value in claims_by_id[s.id]:
            if c_scope == scope:
                totals[value] = totals.get(value, 0.0) + s.trust_score
                backers.setdefault(value, []).append(s)
    if not totals:
        return None, [], {}
    winner = max(totals, key=totals.get)
    rivals = {v: backers[v] for v in backers if v != winner}
    return winner, backers[winner], rivals


def _titles(sources: list[Source]) -> str:
    return ", ".join(s.title for s in sources)


def _answer_text(winner, supporters, scope, target_client, voters, claims_by_id) -> str:
    subject = f" for {target_client}" if target_client else ""
    text = f"The {ordinal(winner)} working day{subject}. Backed by {len(supporters)} source(s): {_titles(supporters)}."
    if scope == "enterprise":
        general, general_backers, _ = _tally(voters, claims_by_id, "general")
        if general is not None and general != winner:
            text += (
                f" This is a client-specific exception (enterprise SLA addendum);"
                f" the general rule is the {ordinal(general)} working day ({_titles(general_backers)})."
            )
    return text


def _uncertainty_text(winner, supporters, rivals, sources, claims_by_id, scope, contact) -> str:
    owners = {s.owner for s in supporters}
    if rivals:
        rival_text = "; ".join(f"the {ordinal(v)} ({_titles(b)})" for v, b in rivals.items())
        level = f"Medium: current in-scope sources disagree ({rival_text})."
    elif len(owners) >= 2:
        level = f"Low: {len(owners)} independent owners agree on the {ordinal(winner)}."
    else:
        level = "Medium: only one owner states this."

    rejected = []
    for s in sources:
        values = [v for c_scope, v in claims_by_id[s.id] if c_scope == scope or c_scope == "general"]
        if values and s not in supporters and not any(s in b for b in rivals.values()):
            claimed = ", ".join(ordinal(v) for v in values)
            rejected.append(f"{s.title} says the {claimed}: {_weakest_reason(s)}")
    text = level
    if rejected:
        text += " Not relied on: " + " | ".join(rejected) + "."
    if contact and (rivals or len(owners) < 2):
        text += f" Confirm with {contact}."
    return text


def _detect_conflicts(sources, claims_by_id, superseded_ids, user_country) -> list[Conflict]:
    """One conflict per scope where same-country sources state different values. Never hidden."""
    labels = {"general": "General cutoff", "enterprise": "Enterprise addendum cutoff"}
    conflicts = []
    for scope in ("general", "enterprise"):
        by_value: dict[int, list[Source]] = {}
        for s in sources:
            if user_country != "ALL" and s.country != user_country:
                continue
            for c_scope, value in claims_by_id[s.id]:
                if c_scope == scope:
                    by_value.setdefault(value, []).append(s)
        if len(by_value) < 2:
            continue

        def tag(s: Source) -> str:
            notes = []
            if s.id in superseded_ids:
                notes.append("superseded")
            if not s.owner:
                notes.append("no owner")
            return f"{s.title} ({', '.join(notes)})" if notes else s.title

        description = "; ".join(
            f"{ordinal(v)}: {', '.join(tag(s) for s in group)}" for v, group in sorted(by_value.items())
        )
        conflicts.append(Conflict(
            claim=f"{labels[scope]} ({user_country})",
            source_ids=list(dict.fromkeys(s.id for group in by_value.values() for s in group)),
            description=description,
        ))
    return conflicts


def _pick_contact(question_terms: set[str], user: dict, supporters: list[Source]) -> str | None:
    """Topic expert first; otherwise the owner of a backing source. Never the asker."""
    me = user.get("display_name")
    for expert in _load_json("experts.json"):
        topics = {t.lower() for t in expert.get("topics", [])}
        if topics & question_terms and expert["name"] != me:
            return f"{expert['name']} ({expert['role']})"
    owner = next((s.owner for s in supporters if s.owner and s.owner != me), None)
    return owner


def verify_claim(claim_id: str, user: dict, verified: bool) -> dict:
    doc = next((d for d in _load_json("corpus.json") if d["id"] == claim_id and can_see(d, user)), None)
    if doc is None:
        raise HTTPException(status_code=404, detail="Unknown claim")
    if doc.get("owner") == user.get("display_name"):
        raise HTTPException(status_code=403, detail="Cannot verify your own source")
    _verified_claims[claim_id] = {
        "claim_id": claim_id,
        "verified_by": user["username"],
        "verified": verified,
        "status": "verified" if verified else "rejected",
    }
    return _verified_claims[claim_id]


def get_verified_claims() -> dict[str, dict]:
    return _verified_claims
