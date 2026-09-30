from backend.app.trust_score import compute_signals, compute_trust_score


def test_policy_scores_higher_than_chat():
    policy = {"id": "1", "updated_at": "2026-09-01", "owner": "HR", "source_type": "policy"}
    chat = {"id": "2", "updated_at": "2026-09-01", "owner": None, "source_type": "chat"}
    all_src = [policy, chat]

    p_signals = compute_signals(policy, all_src)
    c_signals = compute_signals(chat, all_src)

    assert compute_trust_score(p_signals) > compute_trust_score(c_signals)


def test_recent_scores_higher_than_old():
    recent = {"id": "1", "updated_at": "2026-09-01", "owner": "HR", "source_type": "policy"}
    old = {"id": "2", "updated_at": "2024-01-01", "owner": "HR", "source_type": "policy"}

    r_signals = compute_signals(recent)
    o_signals = compute_signals(old)

    assert compute_trust_score(r_signals) > compute_trust_score(o_signals)


def test_owned_scores_higher_than_unowned():
    owned = {"id": "1", "updated_at": "2026-09-01", "owner": "Payroll DE", "source_type": "manual"}
    unowned = {"id": "2", "updated_at": "2026-09-01", "owner": None, "source_type": "manual"}

    assert compute_trust_score(compute_signals(owned)) > compute_trust_score(compute_signals(unowned))


def test_corroboration_with_similar_sources():
    src1 = {"id": "1", "updated_at": "2026-09-01", "owner": "HR", "source_type": "policy"}
    src2 = {"id": "2", "updated_at": "2026-08-01", "owner": "Legal", "source_type": "policy"}
    all_src = [src1, src2]

    signals = compute_signals(src1, all_src)
    corr = next(s for s in signals if s.name == "corroboration")
    assert corr.score >= 0.8


def test_no_corroboration_alone():
    src = {"id": "1", "updated_at": "2026-09-01", "owner": "HR", "source_type": "policy"}
    signals = compute_signals(src, [src])
    corr = next(s for s in signals if s.name == "corroboration")
    assert corr.score == 0.5


def test_score_always_between_0_and_1():
    sources = [
        {"id": "1", "updated_at": "2026-09-01", "owner": "HR", "source_type": "policy"},
        {"id": "2", "updated_at": "2020-01-01", "owner": None, "source_type": "chat"},
        {"id": "3", "updated_at": "invalid", "owner": None, "source_type": "unknown"},
    ]
    for src in sources:
        score = compute_trust_score(compute_signals(src, sources))
        assert 0.0 <= score <= 1.0
