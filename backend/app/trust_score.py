from datetime import datetime, timezone
from .schemas import Signal


def _recency_score(updated_at: str) -> Signal:
    try:
        updated = datetime.fromisoformat(updated_at)
    except ValueError:
        return Signal(name="recency", score=0.3, reason="Date format unknown")

    now = datetime.now(timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    days_old = (now - updated).days

    if days_old <= 90:
        return Signal(name="recency", score=0.95, reason=f"Updated {days_old} days ago")
    if days_old <= 365:
        return Signal(name="recency", score=0.7, reason=f"Updated {days_old} days ago")
    return Signal(name="recency", score=0.3, reason=f"Outdated ({days_old} days)")


def _ownership_score(owner: str | None) -> Signal:
    if owner:
        return Signal(name="ownership", score=1.0, reason=f"Owned by {owner}")
    return Signal(name="ownership", score=0.4, reason="No clear owner")


def _source_type_score(source_type: str) -> Signal:
    weights = {"policy": 0.95, "manual": 0.8, "email": 0.6, "client_note": 0.85, "wiki": 0.4, "chat": 0.3}
    score = weights.get(source_type, 0.5)
    return Signal(name="source_type", score=score, reason=f"Source type: {source_type}")


def _corroboration_score(source: dict, all_sources: list[dict]) -> Signal:
    others = [s for s in all_sources if s.get("id") != source.get("id")]
    if not others:
        return Signal(name="corroboration", score=0.5, reason="Only source available")
    same_type = [s for s in others if s.get("source_type") == source.get("source_type")]
    if same_type:
        return Signal(name="corroboration", score=0.9, reason=f"Corroborated by {len(same_type)} similar source(s)")
    return Signal(name="corroboration", score=0.4, reason="No corroborating sources of same type")


def compute_signals(source: dict, all_sources: list[dict] | None = None) -> list[Signal]:
    signals = [
        _recency_score(source.get("updated_at", "")),
        _ownership_score(source.get("owner")),
        _source_type_score(source.get("source_type", "unknown")),
    ]
    if all_sources:
        signals.append(_corroboration_score(source, all_sources))
    return signals


def compute_trust_score(signals: list[Signal]) -> float:
    if not signals:
        return 0.0
    weights = {"recency": 0.3, "ownership": 0.25, "source_type": 0.25, "corroboration": 0.2}
    total_weight = 0.0
    weighted_sum = 0.0
    for s in signals:
        w = weights.get(s.name, 0.2)
        weighted_sum += s.score * w
        total_weight += w
    return round(weighted_sum / total_weight, 2) if total_weight else 0.0
