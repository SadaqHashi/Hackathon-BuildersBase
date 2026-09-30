import json
from pathlib import Path
from .schemas import AskResponse, Source, Conflict
from .trust_score import compute_signals, compute_trust_score
from .claude_service import compare_sources

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_verified_claims: dict[str, dict] = {}


def _load_sources() -> list[dict]:
    with open(CORPUS_DIR / "corpus.json") as f:
        return json.load(f)


def _load_experts() -> list[dict]:
    path = CORPUS_DIR / "experts.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


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
            excerpt=src.get("excerpt") or src.get("content", ""),
            client=src.get("client"),
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

    experts = _load_experts()
    contact = None
    if experts:
        contact = f"{experts[0]['name']} ({experts[0]['role']})"
    else:
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
    already = set()

    formal = [s for s in sources if s.source_type in ("policy", "client_note")]
    informal = [s for s in sources if s.source_type in ("chat", "wiki")]

    for f in formal:
        for i in informal:
            if i.trust_score < 0.6:
                key = (f.id, i.id)
                if key not in already:
                    already.add(key)
                    conflicts.append(Conflict(
                        claim="Cutoff date",
                        source_ids=[f.id, i.id],
                        description=(
                            f"Official source ({f.title}) may contradict "
                            f"informal source ({i.title}). "
                            f"Trust scores differ: {f.trust_score} vs {i.trust_score}."
                        ),
                    ))

    outdated = [s for s in sources if s.trust_score < 0.5]
    current = [s for s in sources if s.trust_score >= 0.7]
    for o in outdated:
        if current and (current[0].id, o.id) not in already:
            already.add((current[0].id, o.id))
            conflicts.append(Conflict(
                claim="Outdated source",
                source_ids=[current[0].id, o.id],
                description=(
                    f"{o.title} (trust {o.trust_score}) may be outdated compared to "
                    f"{current[0].title} (trust {current[0].trust_score})."
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
