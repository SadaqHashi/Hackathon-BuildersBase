from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str

class Signal(BaseModel):
    name: str      # recency, ownership, scope_match, source_type, corroboration
    score: float   # 0.0 - 1.0
    reason: str    # human-readable, shown in UI

class Source(BaseModel):
    id: str
    title: str
    owner: str | None
    updated_at: str
    country: str
    source_type: str   # policy, manual, chat, email, wiki, client_note
    excerpt: str
    client: str | None = None
    signals: list[Signal]
    trust_score: float

class Conflict(BaseModel):
    claim: str
    source_ids: list[str]
    description: str

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    conflicts: list[Conflict]
    uncertainty: str
    contact: str | None