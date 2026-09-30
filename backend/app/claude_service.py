import json
import os
import hashlib
from pathlib import Path
from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "ai_cache.json"


class AIExplanation(BaseModel):
    summary: str
    agreement_level: str
    key_differences: list[str]
    recommendation: str


def _cache_key(sources_text: str, question: str) -> str:
    return hashlib.sha256(f"{question}::{sources_text}".encode()).hexdigest()[:16]


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _build_prompt(question: str, sources: list[dict]) -> str:
    source_blocks = []
    for s in sources:
        excerpt = s.get("excerpt", "").replace("<", "&lt;").replace(">", "&gt;")
        source_blocks.append(
            f"Source: {s['title']} (type: {s['source_type']}, updated: {s['updated_at']})\n"
            f"Excerpt: {excerpt}"
        )
    sources_text = "\n\n".join(source_blocks)
    return (
        f"Question: {question}\n\n"
        f"Below are excerpts from multiple sources. Compare them, identify agreements "
        f"and contradictions, and explain which source is most trustworthy and why.\n\n"
        f"{sources_text}\n\n"
        f"Respond in JSON with keys: summary (string), agreement_level (high/medium/low), "
        f"key_differences (list of strings), recommendation (string)."
    )


def _fallback_explanation(question: str, sources: list[dict]) -> AIExplanation:
    source_types = [s.get("source_type", "unknown") for s in sources]
    has_policy = "policy" in source_types
    has_chat = "chat" in source_types
    has_conflict = has_policy and has_chat

    if has_conflict:
        return AIExplanation(
            summary=f"Found {len(sources)} sources with conflicting information regarding: {question}",
            agreement_level="low",
            key_differences=[
                "Official policy documents and informal chat messages provide different answers.",
                "Dates and deadlines mentioned vary across sources.",
            ],
            recommendation="Rely on the official policy document as the primary source. "
                         "Verify informal claims with the responsible team before acting.",
        )
    return AIExplanation(
        summary=f"Found {len(sources)} sources regarding: {question}",
        agreement_level="high" if has_policy else "medium",
        key_differences=[],
        recommendation="Sources are largely consistent. Check recency of each source.",
    )


def compare_sources(question: str, sources: list[dict]) -> AIExplanation:
    sources_text = json.dumps([{"title": s.get("title"), "excerpt": s.get("excerpt")} for s in sources], default=str)
    key = _cache_key(sources_text, question)

    cache = _load_cache()
    if key in cache:
        return AIExplanation(**cache[key])

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return _fallback_explanation(question, sources)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(question, sources)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        result = AIExplanation(**parsed)

        cache[key] = result.model_dump()
        _save_cache(cache)
        return result

    except Exception:
        return _fallback_explanation(question, sources)
