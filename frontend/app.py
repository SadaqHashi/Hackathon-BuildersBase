"""TrustLens answer screen.

Security note: everything shown comes from documents or the API and is untrusted. Every value that goes into
HTML passes through esc() first; nothing from the API is ever rendered as raw HTML or markdown.
"""
import html
import re

import streamlit as st

import api

st.set_page_config(page_title="TrustLens", layout="centered")

DEMO_QUESTIONS = [
    "What's the payroll input cutoff for Brouwerij Delvaux?",
    "What's the payroll input cutoff for Garage Vermeulen?",
    "What's the general payroll input cutoff?",
]
SIGNAL_LABELS = {
    "recency": "Up to date",
    "ownership": "Owner",
    "source_type": "Kind of source",
    "scope_match": "Applies to you",
    "corroboration": "Backed by others",
}
TYPE_LABELS = {
    "policy": "Policy",
    "client_note": "Client note",
    "manual": "Manual",
    "email": "Email",
    "wiki": "Wiki",
    "chat": "Chat",
}
# Traffic-light groups, in display order.
GROUPS = {
    "green": ("Safe to rely on", "Used for the answer and well supported.", ":material/verified:", True),
    "orange": ("Check before using", "Relevant, but informal or not decisive on its own.", ":material/warning:", False),
    "red": ("Don't rely on", "Outdated, wrong scope, unowned or contradicted.", ":material/block:", False),
}
TRUSTED = 0.75

CSS = """
<style>
.block-container {padding-top: 2.2rem;}
.tl-brand {font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em;}
.tl-tagline {color: #59636e; margin: 0.1rem 0 1.4rem 0;}
.tl-answer {background: #fff; border: 1px solid #d8dee4; border-left: 5px solid #2f5bea; border-radius: 12px;
  padding: 1.2rem 1.4rem; margin: 0.4rem 0 0.8rem 0;}
.tl-label {font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #59636e;}
.tl-headline {font-size: 1.6rem; font-weight: 700; line-height: 1.25; margin: 0.25rem 0 0.4rem 0;}
.tl-sub {color: #31373d; line-height: 1.5;}
.tl-facts {display: flex; flex-wrap: wrap; gap: 0.5rem 1.4rem; margin-top: 0.9rem; padding-top: 0.8rem;
  border-top: 1px solid #eef1f4; font-size: 0.92rem;}
.tl-facts b {color: #1f2328;}
.tl-pill {display: inline-block; padding: 0.1rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
.tl-green {background: #dafbe1; color: #116329;}
.tl-orange {background: #fff1d6; color: #8a4b00;}
.tl-red {background: #ffebe9; color: #a40e26;}
.tl-neutral {background: #eef1f4; color: #424a53;}
.tl-tally {display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.2rem 0 0.2rem 0;}
.tl-src {background: #fff; border: 1px solid #d8dee4; border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.6rem;}
.tl-src-green {border-left: 4px solid #2da44e;}
.tl-src-orange {border-left: 4px solid #d4a72c;}
.tl-src-red {border-left: 4px solid #cf222e;}
.tl-src-top {display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start;}
.tl-src-title {font-weight: 650;}
.tl-meta {color: #59636e; font-size: 0.83rem; margin-top: 0.1rem;}
.tl-why {margin-top: 0.45rem; font-size: 0.92rem; color: #31373d;}
.tl-src details {margin-top: 0.5rem;}
.tl-src summary {cursor: pointer; color: #2f5bea; font-size: 0.85rem;}
.tl-sigrow {display: flex; gap: 0.5rem; align-items: baseline; font-size: 0.85rem; padding: 0.2rem 0;}
.tl-sigrow b {min-width: 8.5rem;}
.tl-dot {width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; flex-shrink: 0;}
.tl-dot-green {background: #2da44e;} .tl-dot-orange {background: #d4a72c;} .tl-dot-red {background: #cf222e;}
.tl-quote {margin-top: 0.5rem; padding: 0.5rem 0.75rem; background: #f6f8fa; border-radius: 8px;
  font-size: 0.88rem; color: #31373d; white-space: pre-wrap;}
.tl-crow {display: flex; gap: 0.8rem; padding: 0.3rem 0; border-top: 1px dashed #e4e8ec; font-size: 0.92rem;}
.tl-crow:first-of-type {border-top: none;}
.tl-cval {min-width: 3rem; font-weight: 700;}
</style>
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def color(score: float) -> str:
    if score >= TRUSTED:
        return "green"
    if score >= 0.4:
        return "orange"
    return "red"


# ---------- parsing the backend's prose into structure ----------

def split_answer(answer: str) -> tuple[str, str]:
    head, sep, rest = answer.partition(". ")
    return (head + "." if sep else head), rest


def parse_uncertainty(text: str) -> tuple[str, str, list[dict], str | None]:
    """'Low: ... Not relied on: A says the 8th: why | B ... Confirm with X.' -> parts."""
    confirm = None
    if " Confirm with " in text:
        text, confirm = text.rsplit(" Confirm with ", 1)
        confirm = confirm.rstrip(".")
    summary, _, rejected_text = text.partition(" Not relied on: ")
    lvl, _, summary_rest = summary.partition(":")
    rejected = []
    for item in filter(None, (i.strip() for i in rejected_text.rstrip(".").split(" | "))):
        title, says, rest = item.partition(" says ")
        claim, _, reason = rest.partition(": ")
        if says:
            rejected.append({"title": title, "claim": claim, "reason": reason})
    return lvl.strip(), summary_rest.strip(), rejected, confirm


def parse_backers(answer_rest: str) -> list[str]:
    m = re.search(r"Backed by \d+ source\(s\): (.*?)\.(?: |$)", answer_rest)
    return [t.strip() for t in m.group(1).split(", ")] if m else []


def classify(source: dict, rejected: list[dict], backers: list[str]) -> tuple[str, str]:
    """Traffic-light group + one plain-language reason.

    Several chats share a title, so a rejected item only matches a source with the same title whose weakest
    signal is exactly the stated reason (the backend reports the weakest signal as the reason).
    """
    weakest = min(source["signals"], key=lambda s: s["score"])
    for r in rejected:
        if r["title"] == source["title"] and r["reason"] == weakest["reason"]:
            return "red", f"Says {r['claim']}, but: {r['reason']}"
    if source["title"] in backers:
        if source["trust_score"] >= TRUSTED:
            reasons = {s["name"]: s for s in source["signals"]}
            parts = [reasons[n]["reason"] for n in ("source_type", "ownership") if n in reasons]
            if reasons.get("scope_match", {}).get("score", 0) >= 1.0:
                parts.append(reasons["scope_match"]["reason"])
            return "green", " · ".join(parts)
        return "orange", f"Supports the answer, but: {weakest['reason']}"
    return "orange", f"Not used for this answer. {weakest['reason']}"


# ---------- session ----------

def logout(message: str | None = None):
    for key in ("token", "user", "result", "verified"):
        st.session_state.pop(key, None)
    if message:
        st.session_state["flash"] = message


def call(fn, *args):
    """Run an API call; on 401 drop the session, on other errors show the message."""
    try:
        return fn(*args)
    except api.ApiError as e:
        if e.status == 401:
            logout("Your session expired. Please sign in again.")
            st.rerun()
        st.error(str(e))
        return None


def refresh_verified():
    data = call(api.verified_claims, st.session_state["token"])
    st.session_state["verified"] = data or {}


# ---------- rendering ----------

def render_sidebar():
    with st.sidebar:
        if "flash" in st.session_state:
            st.warning(st.session_state.pop("flash"))
        if "token" in st.session_state:
            user = st.session_state["user"]
            st.markdown("**Signed in as**")
            st.text(f"{user['display_name']} ({user['role']})")
            if st.button("Sign out", width="stretch"):
                logout()
                st.rerun()
        else:
            st.markdown("### Sign in")
            with st.form("login"):
                username = st.text_input("Username", placeholder="jonas, lars or sofie")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", width="stretch", type="primary"):
                    try:
                        data = api.login(username.strip(), password)
                    except api.ApiError as e:
                        st.error(str(e))
                    else:
                        st.session_state["token"] = data["token"]
                        st.session_state["user"] = {"display_name": data["display_name"], "role": data["role"]}
                        st.rerun()
        st.divider()
        st.caption("Trust is computed by code from each document's metadata: how recent it is, who owns it, "
                   "what kind of source it is, whether it applies to you and whether other sources back it. "
                   "The AI only explains; it never decides what to trust.")


def render_answer(result: dict, lvl: str, summary: str, confirm: str | None, tally: dict[str, int]):
    headline, rest = split_answer(result["answer"])
    # The source list already shows what backs the answer; keep only the extra context sentence(s).
    rest = re.sub(r"Backed by \d+ source\(s\): .*?\.(?: |$)", "", rest).strip()
    lvl_class = {"low": "green", "medium": "orange", "high": "red"}.get(lvl.lower(), "neutral")
    who = confirm or result.get("contact") or "No one identified"

    st.markdown(
        f'<div class="tl-answer"><div class="tl-label">Answer</div>'
        f'<div class="tl-headline">{esc(headline)}</div>'
        + (f'<div class="tl-sub">{esc(rest)}</div>' if rest else "")
        + f'<div class="tl-facts">'
        f'<span>Uncertainty: <span class="tl-pill tl-{lvl_class}">{esc(lvl or "Unknown")}</span> {esc(summary)}</span>'
        f'<span>Not sure? Ask <b>{esc(who)}</b></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    pills = "".join(
        f'<span class="tl-pill tl-{g}">{n} {GROUPS[g][0].lower()}</span>' for g, n in tally.items() if n
    )
    st.markdown(f'<div class="tl-tally">{pills}</div>', unsafe_allow_html=True)


def render_conflicts(conflicts: list[dict]):
    if not conflicts:
        return
    label = f"Sources disagree on {len(conflicts)} point{'s' if len(conflicts) > 1 else ''}. See who says what"
    with st.expander(label, icon=":material/compare_arrows:"):
        for c in conflicts:
            rows = []
            for part in c["description"].split("; "):
                value, _, who = part.partition(": ")
                rows.append(f'<div class="tl-crow"><span class="tl-cval">{esc(value)}</span><span>{esc(who)}</span></div>')
            st.markdown(f'<div class="tl-label" style="margin-top:0.4rem">{esc(c["claim"])}</div>{"".join(rows)}',
                        unsafe_allow_html=True)


def render_source(s: dict, group: str, why: str, verification: dict | None, is_expert: bool):
    meta = " · ".join(esc(x) for x in (
        TYPE_LABELS.get(s["source_type"], s["source_type"]),
        s["owner"] or "No owner",
        s["updated_at"],
        s.get("client") or s["country"],
    ))
    signal_rows = "".join(
        f'<div class="tl-sigrow"><span class="tl-dot tl-dot-{color(sig["score"])}"></span>'
        f'<b>{esc(SIGNAL_LABELS.get(sig["name"], sig["name"]))}</b><span>{esc(sig["reason"])}</span></div>'
        for sig in s["signals"]
    )
    verified_by = (verification or {}).get("verified_by") or s.get("verified_by")
    if verification and not verification.get("verified"):
        badge = f' <span class="tl-pill tl-red">Rejected by expert ({esc(verified_by)})</span>'
    elif verified_by:
        badge = f' <span class="tl-pill tl-green">Verified by expert ({esc(verified_by)})</span>'
    else:
        badge = ""

    st.markdown(
        f'<div class="tl-src tl-src-{group}">'
        f'<div class="tl-src-top"><div><div class="tl-src-title">{esc(s["title"])}</div>'
        f'<div class="tl-meta">{meta}</div></div>'
        f'<span class="tl-pill tl-{group}">trust {s["trust_score"]:.2f}</span></div>'
        f'<div class="tl-why">{esc(why)}{badge}</div>'
        f'<details><summary>Show details</summary>{signal_rows}'
        f'<div class="tl-quote">{esc(s["excerpt"])}</div></details>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if is_expert:
        c1, c2, _ = st.columns([1, 1, 3])
        for col, label, verdict in ((c1, "Verify", True), (c2, "Reject", False)):
            if col.button(label, key=f"{label}-{s['id']}", width="stretch"):
                if call(api.verify, st.session_state["token"], s["id"], verdict) is not None:
                    refresh_verified()
                    st.toast(("Verified: " if verdict else "Rejected: ") + s["title"])
                    st.rerun()


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    render_sidebar()

    st.markdown('<div class="tl-brand">TrustLens</div>'
                '<div class="tl-tagline">Find an answer, and see exactly why you can (or can\'t) rely on it.</div>',
                unsafe_allow_html=True)

    if "token" not in st.session_state:
        st.info("Sign in on the left to ask a question. Demo users: jonas, lars (consultants), sofie (expert). "
                "Password: hackathon.")
        return

    with st.form("ask"):
        question = st.selectbox("Your question", DEMO_QUESTIONS, index=0, accept_new_options=True,
                                help="Pick a question or type your own. This demo covers payroll input cutoffs.")
        submitted = st.form_submit_button("Ask", type="primary")
    if submitted and question:
        with st.spinner("Checking sources..."):
            result = call(api.ask, st.session_state["token"], question)
        if result is not None:
            st.session_state["result"] = result
            refresh_verified()

    result = st.session_state.get("result")
    if not result:
        return

    lvl, summary, rejected, confirm = parse_uncertainty(result["uncertainty"])
    backers = parse_backers(split_answer(result["answer"])[1])
    grouped: dict[str, list] = {g: [] for g in GROUPS}
    for s in result["sources"]:
        group, why = classify(s, rejected, backers)
        grouped[group].append((s, why))

    render_answer(result, lvl, summary, confirm, {g: len(items) for g, items in grouped.items()})
    render_conflicts(result["conflicts"])

    st.markdown('<div class="tl-label" style="margin:1.2rem 0 0.4rem 0">Sources</div>', unsafe_allow_html=True)
    verified = st.session_state.get("verified", {})
    is_expert = st.session_state["user"]["role"] in ("expert", "admin")
    for group, (title, hint, icon, expanded) in GROUPS.items():
        items = grouped[group]
        if not items:
            continue
        with st.expander(f":{group}[**{title}**] ({len(items)})", icon=icon, expanded=expanded):
            st.caption(hint)
            for s, why in items:
                render_source(s, group, why, verified.get(s["id"]), is_expert)


main()
