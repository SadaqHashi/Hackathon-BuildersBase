import re
from datetime import datetime, timezone
from .schemas import Signal

# Recency is deliberately the lightest weight: "newest wins" is the trap we demo.
WEIGHTS = {
    "recency": 0.10,
    "ownership": 0.20,
    "source_type": 0.20,
    "scope_match": 0.25,
    "corroboration": 0.25,
}

SOURCE_TYPES = {
    "policy": (0.95, "Official policy document"),
    "client_note": (0.85, "Client-specific agreement on file"),
    "manual": (0.8, "Internal manual"),
    "email": (0.6, "Email: official channel, but not a controlled document"),
    "wiki": (0.4, "Wiki page: informal, anyone can edit"),
    "chat": (0.3, "Chat message: informal and unreviewed"),
}

_ORDINAL = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b")
_EXCEPTION_SCOPE = re.compile(r"\b(enterprise|addendum)\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

Claim = tuple[str, int]  # (scope, value): ("general", 5) or ("enterprise", 7)


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def extract_claims(text: str) -> list[Claim]:
    """Deterministic claim extraction: ordinal cutoff days, tagged general or enterprise.

    "moves from the 8th to the 5th" states the 5th; the "from the" value is history, not a claim.
    """
    claims: list[Claim] = []
    for sentence in _SENTENCE.split(text or ""):
        scope = "enterprise" if _EXCEPTION_SCOPE.search(sentence) else "general"
        for m in _ORDINAL.finditer(sentence):
            if sentence[:m.start()].lower().endswith("from the "):
                continue
            claim = (scope, int(m.group(1)))
            if claim not in claims:
                claims.append(claim)
    return claims


def superseded_by(source: dict, all_sources: list[dict]) -> dict | None:
    return next((s for s in all_sources if s.get("supersedes") == source.get("id")), None)


def _recency_score(source: dict, all_sources: list[dict], now: datetime) -> Signal:
    newer = superseded_by(source, all_sources)
    if newer:
        return Signal(name="recency", score=0.05,
                      reason=f"Superseded by \"{newer['title']}\" ({newer['updated_at']})")
    try:
        updated = datetime.fromisoformat(source.get("updated_at", ""))
    except ValueError:
        return Signal(name="recency", score=0.3, reason="Date format unknown")
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    days_old = (now - updated).days

    if days_old <= 90:
        return Signal(name="recency", score=0.95, reason=f"Updated {days_old} days ago")
    if days_old <= 365:
        return Signal(name="recency", score=0.7, reason=f"Updated {days_old} days ago")
    return Signal(name="recency", score=0.3, reason=f"Outdated ({days_old} days)")


def _ownership_score(source: dict) -> Signal:
    owner = source.get("owner")
    source_type = source.get("source_type")
    if not owner:
        return Signal(name="ownership", score=0.2,
                      reason="No owner: nobody is accountable for keeping this up to date")
    if source_type == "chat":
        return Signal(name="ownership", score=0.5,
                      reason=f"Chat message by {owner}: an author, not an accountable document owner")
    if source_type == "email":
        return Signal(name="ownership", score=0.8, reason=f"Sent by {owner}")
    return Signal(name="ownership", score=1.0, reason=f"Maintained by {owner}")


def _source_type_score(source_type: str) -> Signal:
    score, label = SOURCE_TYPES.get(source_type, (0.5, f"Unknown source type ({source_type})"))
    return Signal(name="source_type", score=score, reason=label)


def _scope_score(source: dict, user_country: str, target_client: str | None) -> Signal:
    country = source.get("country")
    client = source.get("client")
    if user_country != "ALL" and country != user_country:
        return Signal(name="scope_match", score=0.0, reason=f"Applies to {country}, not {user_country}")
    if client:
        if client == target_client:
            return Signal(name="scope_match", score=1.0, reason=f"Specific to {client}")
        return Signal(name="scope_match", score=0.2, reason=f"About a different client ({client})")
    if target_client:
        return Signal(name="scope_match", score=0.7,
                      reason=f"General {country} rule, not specific to {target_client}")
    return Signal(name="scope_match", score=0.9, reason=f"General {country} rule")


def _corroboration_score(source: dict, all_sources: list[dict]) -> Signal:
    claims = extract_claims(source.get("content", ""))
    if not claims:
        return Signal(name="corroboration", score=0.5, reason="Makes no checkable claim on this topic")

    # Only owned, current sources from the same country count as independent evidence.
    peers = [
        s for s in all_sources
        if s.get("id") != source.get("id")
        and s.get("country") == source.get("country")
        and s.get("owner")
        and not superseded_by(s, all_sources)
    ]
    if not peers:
        return Signal(name="corroboration", score=0.4,
                      reason=f"No other {source.get('country')} source to compare against")

    best: Signal | None = None
    for claim in claims:
        scope, value = claim
        supporters = {
            p["owner"] for p in peers
            if claim in extract_claims(p.get("content", "")) and p["owner"] != source.get("owner")
        }
        contradictors = [
            p["title"] for p in peers
            if any(c[0] == scope and c[1] != value for c in extract_claims(p.get("content", "")))
        ]
        label = f"the {ordinal(value)}" + (" (enterprise exception)" if scope == "enterprise" else "")
        if len(supporters) >= 2:
            signal = Signal(name="corroboration", score=1.0,
                            reason=f"{len(supporters)} independent sources back {label}")
        elif supporters:
            signal = Signal(name="corroboration", score=0.75,
                            reason=f"Backed by one independent source ({next(iter(supporters))}) on {label}")
        elif contradictors:
            signal = Signal(name="corroboration", score=0.1,
                            reason=f"No source backs {label}; contradicted by {', '.join(contradictors)}")
        else:
            signal = Signal(name="corroboration", score=0.4, reason=f"No other source mentions {label}")
        if best is None or signal.score > best.score:
            best = signal
    return best


def compute_signals(
    source: dict,
    all_sources: list[dict] | None = None,
    user_country: str = "ALL",
    target_client: str | None = None,
    now: datetime | None = None,
) -> list[Signal]:
    all_sources = all_sources or [source]
    now = now or datetime.now(timezone.utc)
    return [
        _recency_score(source, all_sources, now),
        _ownership_score(source),
        _source_type_score(source.get("source_type", "unknown")),
        _scope_score(source, user_country, target_client),
        _corroboration_score(source, all_sources),
    ]


def compute_trust_score(signals: list[Signal]) -> float:
    total_weight = sum(WEIGHTS.get(s.name, 0.0) for s in signals)
    if not total_weight:
        return 0.0
    weighted_sum = sum(s.score * WEIGHTS.get(s.name, 0.0) for s in signals)
    return round(weighted_sum / total_weight, 2)
