from datetime import datetime, timedelta, timezone
from backend.app.trust_score import compute_signals, compute_trust_score, extract_claims, ordinal

NOW = datetime(2026, 9, 30, tzinfo=timezone.utc)


def _days_ago(n: int) -> str:
    return (NOW - timedelta(days=n)).date().isoformat()


def _doc(id, content="", source_type="policy", owner="HR", days=10, **extra) -> dict:
    return {"id": id, "title": id, "content": content, "source_type": source_type, "owner": owner,
            "updated_at": _days_ago(days), "country": "BE", "client": None, **extra}


def _score(doc, docs, **kw) -> float:
    return compute_trust_score(compute_signals(doc, docs, user_country="BE", now=NOW, **kw))


def _signal(doc, docs, name, **kw):
    return next(s for s in compute_signals(doc, docs, user_country="BE", now=NOW, **kw) if s.name == name)


# --- claim extraction ---

def test_extracts_general_and_enterprise_claims():
    text = ("Input must be received no later than the 5th working day. "
            "Enterprise clients with a signed SLA addendum may submit until the 7th working day.")
    assert extract_claims(text) == [("general", 5), ("enterprise", 7)]


def test_ignores_the_old_value_in_a_change_statement():
    assert extract_claims("The cutoff moves from the 8th to the 5th working day.") == [("general", 5)]


def test_no_claims_in_plain_text():
    assert extract_claims("Standard cutoff applies. Contact person: An Claes.") == []


def test_ordinal():
    assert [ordinal(n) for n in (1, 2, 3, 5, 11, 12, 13, 21)] == \
        ["1st", "2nd", "3rd", "5th", "11th", "12th", "13th", "21st"]


# --- signals ---

def test_policy_scores_higher_than_chat():
    policy = _doc("p", source_type="policy")
    chat = _doc("c", source_type="chat", owner="Someone")
    assert _score(policy, [policy, chat]) > _score(chat, [policy, chat])


def test_recent_scores_higher_than_old():
    recent, old = _doc("r", days=10), _doc("o", days=800)
    assert _score(recent, [recent]) > _score(old, [old])


def test_owned_scores_higher_than_unowned():
    owned, unowned = _doc("a"), _doc("b", owner=None)
    assert _score(owned, [owned]) > _score(unowned, [unowned])


def test_chat_author_is_not_an_accountable_owner():
    chat = _doc("c", source_type="chat", owner="Lars")
    assert _signal(chat, [chat], "ownership").score < 1.0


def test_superseded_source_gets_minimal_recency():
    old = _doc("v2", "Cutoff is the 8th working day.", days=5)
    new = _doc("v3", "Cutoff is the 5th working day.", supersedes="v2")
    assert _signal(old, [old, new], "recency").score <= 0.1


def test_corroboration_requires_same_claim_not_same_type():
    a = _doc("a", "Cutoff is the 5th working day.", owner="Ops")
    b = _doc("b", "Cutoff is the 5th working day.", owner="Compliance", source_type="email")
    c = _doc("c", "Cutoff is the 8th working day.", owner="Other")
    docs = [a, b, c]
    assert _signal(a, docs, "corroboration").score >= 0.75
    assert _signal(c, docs, "corroboration").score <= 0.1


def test_same_owner_does_not_corroborate_itself():
    a = _doc("a", "Cutoff is the 5th working day.", owner="Ops")
    b = _doc("b", "Cutoff is the 5th working day.", owner="Ops")
    assert _signal(a, [a, b], "corroboration").score < 0.75


def test_no_claim_is_neutral():
    doc = _doc("a", "Nothing to see here.")
    assert _signal(doc, [doc], "corroboration").score == 0.5


def test_scope_match():
    general = _doc("g")
    client = _doc("c", client="Delvaux")
    other_country = _doc("nl", country="NL")
    assert _signal(client, [client], "scope_match", target_client="Delvaux").score == 1.0
    assert _signal(general, [general], "scope_match", target_client="Delvaux").score == 0.7
    assert _signal(other_country, [other_country], "scope_match").score == 0.0


def test_newest_unbacked_chat_loses_to_corroborated_policy():
    policy = _doc("p", "Cutoff is the 5th working day.", owner="Ops", days=100)
    email = _doc("e", "Cutoff is the 5th working day.", owner="Compliance", source_type="email", days=100)
    chat = _doc("c", "Pretty sure the cutoff is the 10th now.", owner="Lars", source_type="chat", days=1)
    docs = [policy, email, chat]
    assert _score(chat, docs) < _score(policy, docs)
    assert _score(chat, docs) < _score(email, docs)


def test_score_always_between_0_and_1():
    docs = [_doc("1"), _doc("2", owner=None, source_type="chat", days=3000),
            {"id": "3", "updated_at": "invalid", "owner": None, "source_type": "unknown", "country": "BE"}]
    for doc in docs:
        assert 0.0 <= _score(doc, docs) <= 1.0
