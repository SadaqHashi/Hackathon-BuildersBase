import json
from pathlib import Path
from .schemas import AskResponse, Source, Signal, Conflict
from .trust_score import compute_signals, compute_trust_score

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_sources() -> list[dict]:
    with open(DATA_DIR / "sources.json") as f:
        return json.load(f)


def ask(question: str) -> AskResponse:
    raw_sources = _load_sources()
    sources = []
    for src in raw_sources:
        signals = compute_signals(src)
        trust = compute_trust_score(signals)
        sources.append(Source(
            id=src["id"],
            title=src["title"],
            owner=src.get("owner"),
            updated_at=src["updated_at"],
            country=src["country"],
            source_type=src["source_type"],
            excerpt=src["excerpt"],
            signals=signals,
            trust_score=trust,
        ))

    conflicts = _detect_conflicts(sources)
    highest = max((s.trust_score for s in sources), default=0)
    if highest >= 0.8 and not conflicts:
        uncertainty = "Low uncertainty — sources largely agree."
    elif conflicts:
        uncertainty = "Sources conflict on key claims. Expert verification recommended."
    else:
        uncertainty = "Moderate uncertainty — limited corroboration."

    contact_source = max(sources, key=lambda s: s.trust_score) if sources else None
    contact = contact_source.owner if contact_source and contact_source.owner else None

    return AskResponse(
        answer=f"Based on {len(sources)} sources regarding: {question}",
        sources=sources,
        conflicts=conflicts,
        uncertainty=uncertainty,
        contact=contact,
    )


def _detect_conflicts(sources: list[Source]) -> list[Conflict]:
    conflicts = []
    policy_sources = [s for s in sources if s.source_type == "policy"]
    chat_sources = [s for s in sources if s.source_type == "chat"]
    if policy_sources and chat_sources:
        conflicts.append(Conflict(
            claim="Settlement deadline",
            source_ids=[policy_sources[0].id, chat_sources[0].id],
            description=f"Policy ({policy_sources[0].title}) and chat ({chat_sources[0].title}) may disagree on deadlines.",
        ))
    return conflicts


def verify_claim(claim_id: str, expert_username: str, verified: bool) -> dict:
    return {
        "claim_id": claim_id,
        "verified_by": expert_username,
        "verified": verified,
        "status": "verified" if verified else "rejected",
    }
