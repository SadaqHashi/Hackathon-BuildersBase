import json
from pathlib import Path
from .schemas import AskResponse, Source, Conflict
from .trust_score import compute_signals, compute_trust_score
from .claude_service import compare_sources

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_verified_claims: dict[str, dict] = {}


def _load_sources() -> list[dict]:
    with open(DATA_DIR / "sources.json") as f:
        return json.load(f)


def ask(question: str, user_country: str = "ALL") -> AskResponse:
    raw_sources = _load_sources()

    if user_country != "ALL":
        raw_sources = [s for s in raw_sources if s.get("country") == user_country]

    sources = []
    for src in raw_sources:
        signals = compute_signals(src, all_sources=raw_sources)
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

    ai = compare_sources(question, raw_sources)
    answer = ai.summary
    if ai.recommendation:
        answer += f" {ai.recommendation}"

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
        answer=answer,
        sources=sources,
        conflicts=conflicts,
        uncertainty=uncertainty,
        contact=contact,
    )


def _detect_conflicts(sources: list[Source]) -> list[Conflict]:
    conflicts = []
    by_type: dict[str, list[Source]] = {}
    for s in sources:
        by_type.setdefault(s.source_type, []).append(s)

    formal = by_type.get("policy", []) + by_type.get("manual", [])
    informal = by_type.get("chat", []) + by_type.get("email", [])

    if formal and informal:
        low_trust_informal = [s for s in informal if s.trust_score < 0.6]
        if low_trust_informal:
            conflicts.append(Conflict(
                claim="Settlement deadline",
                source_ids=[formal[0].id, low_trust_informal[0].id],
                description=(
                    f"Official source ({formal[0].title}) may contradict "
                    f"informal source ({low_trust_informal[0].title}). "
                    f"Trust scores differ significantly."
                ),
            ))

    high_trust = [s for s in sources if s.trust_score >= 0.7]
    low_trust = [s for s in sources if s.trust_score < 0.5]
    if high_trust and low_trust:
        for lt in low_trust:
            if lt.id not in [c.source_ids[1] for c in conflicts if len(c.source_ids) > 1]:
                conflicts.append(Conflict(
                    claim="Source reliability",
                    source_ids=[high_trust[0].id, lt.id],
                    description=(
                        f"{lt.title} has low trust ({lt.trust_score}) compared to "
                        f"{high_trust[0].title} ({high_trust[0].trust_score}). "
                        f"Verify before relying on it."
                    ),
                ))

    return conflicts


def verify_claim(claim_id: str, expert_username: str, verified: bool) -> dict:
    _verified_claims[claim_id] = {
        "claim_id": claim_id,
        "verified_by": expert_username,
        "verified": verified,
        "status": "verified" if verified else "rejected",
    }
    return _verified_claims[claim_id]


def get_verified_claims() -> dict[str, dict]:
    return _verified_claims
