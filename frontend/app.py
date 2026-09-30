"""TrustLens answer screen.

Security note: everything shown comes from documents or the API and is untrusted. Every value that goes into
HTML passes through esc() first; nothing from the API is ever rendered as raw HTML or markdown.
"""
import html
import re

import streamlit as st

import api

st.set_page_config(page_title="TrustLens", layout="wide")

DEMO_QUESTIONS = [
    "What's the payroll input cutoff for Brouwerij Delvaux?",
    "What's the payroll input cutoff for Garage Vermeulen?",
]
SIGNAL_LABELS = {
    "recency": "Recency",
    "ownership": "Ownership",
    "source_type": "Source type",
    "scope_match": "Scope",
    "corroboration": "Corroboration",
}
TYPE_LABELS = {
    "policy": "Policy",
    "client_note": "Client note",
    "manual": "Manual",
    "email": "Email",
    "wiki": "Wiki",
    "chat": "Chat",
}
_ORDINAL = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\b")

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
.tl-brand {font-size: 1.9rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0;}
.tl-tagline {color: #59636e; margin-top: 0.1rem; margin-bottom: 1.2rem;}
.tl-card {background: #fff; border: 1px solid #d8dee4; border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 0.9rem;}
.tl-answer {border-left: 5px solid #2f5bea;}
.tl-label {font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #59636e; margin-bottom: 0.35rem;}
.tl-headline {font-size: 1.55rem; font-weight: 700; line-height: 1.25; margin-bottom: 0.4rem;}
.tl-sub {color: #31373d; line-height: 1.5;}
.tl-pill {display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
.tl-good {background: #dafbe1; color: #116329;}
.tl-mid {background: #fff4c5; color: #7d4e00;}
.tl-bad {background: #ffebe9; color: #a40e26;}
.tl-neutral {background: #eef1f4; color: #424a53;}
.tl-conflict {border-left: 5px solid #d4a72c; background: #fffdf3;}
.tl-crow {display: flex; gap: 0.7rem; align-items: baseline; padding: 0.3rem 0; border-top: 1px dashed #eadfb8;}
.tl-crow:first-of-type {border-top: none;}
.tl-cval {min-width: 3.2rem; font-weight: 700;}
.tl-rejected {margin: 0.2rem 0 0 0; padding-left: 1.1rem; color: #31373d;}
.tl-rejected li {margin-bottom: 0.25rem;}
.tl-src-head {display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;}
.tl-src-title {font-weight: 700; font-size: 1.05rem;}
.tl-meta {color: #59636e; font-size: 0.85rem; margin-top: 0.15rem;}
.tl-score {font-size: 1.5rem; font-weight: 700; line-height: 1;}
.tl-score-cap {font-size: 0.7rem; color: #59636e; text-align: right;}
.tl-bar {height: 6px; background: #eef1f4; border-radius: 3px; margin: 0.6rem 0 0.7rem 0; overflow: hidden;}
.tl-bar > div {height: 100%; border-radius: 3px;}
.tl-bar-good {background: #2da44e;} .tl-bar-mid {background: #d4a72c;} .tl-bar-bad {background: #cf222e;}
.tl-signals {display: flex; flex-wrap: wrap; gap: 0.4rem;}
.tl-sig {border-radius: 8px; padding: 0.3rem 0.55rem; font-size: 0.8rem; line-height: 1.3; max-width: 100%;}
.tl-sig b {margin-right: 0.3rem;}
.tl-quote {margin-top: 0.75rem; padding: 0.55rem 0.8rem; background: #f6f8fa; border-radius: 8px; color: #31373d; font-size: 0.9rem; white-space: pre-wrap;}
.tl-status {margin-top: 0.6rem; font-size: 0.85rem;}
.tl-muted {opacity: 0.72;}
</style>
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def level(score: float) -> str:
    if score >= 0.75:
        return "good"
    if score >= 0.4:
        return "mid"
    return "bad"


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


def source_status(source: dict, rejected: list[dict], backers: list[str]) -> tuple[str, str] | None:
    """Two chats share a title, so match rejected items on title AND the claimed value in the text."""
    for r in rejected:
        values = _ORDINAL.findall(r["claim"])
        if r["title"] == source["title"] and all(v in source["excerpt"] for v in values):
            return "bad", f"Not relied on: {r['reason']}"
    if source["title"] in backers:
        return "good", "Supports the answer"
    return None


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
        st.markdown("### Sign in")
        if "flash" in st.session_state:
            st.warning(st.session_state.pop("flash"))
        if "token" in st.session_state:
            user = st.session_state["user"]
            st.text(f"{user['display_name']} ({user['role']})")
            if st.button("Sign out", width="stretch"):
                logout()
                st.rerun()
        else:
            with st.form("login"):
                username = st.text_input("Username", placeholder="jonas, lars or sofie")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", width="stretch"):
                    try:
                        data = api.login(username.strip(), password)
                    except api.ApiError as e:
                        st.error(str(e))
                    else:
                        st.session_state["token"] = data["token"]
                        st.session_state["user"] = {"display_name": data["display_name"], "role": data["role"]}
                        st.rerun()
        st.divider()
        st.caption("Trust scores are computed by code from document metadata. "
                   "The AI only explains; it never decides what to trust.")


def render_answer(result: dict, rejected: list[dict], lvl: str, summary: str, confirm: str | None):
    headline, rest = split_answer(result["answer"])
    lvl_class = {"low": "good", "medium": "mid", "high": "bad"}.get(lvl.lower(), "neutral")
    contact = result.get("contact")

    left, right = st.columns([2.2, 1])
    with left:
        st.markdown(
            f'<div class="tl-card tl-answer"><div class="tl-label">Answer</div>'
            f'<div class="tl-headline">{esc(headline)}</div>'
            f'<div class="tl-sub">{esc(rest)}</div></div>',
            unsafe_allow_html=True,
        )
    with right:
        who = esc(confirm or contact or "No one identified")
        st.markdown(
            f'<div class="tl-card"><div class="tl-label">Uncertainty</div>'
            f'<span class="tl-pill tl-{lvl_class}">{esc(lvl or "Unknown")}</span>'
            f'<div class="tl-sub" style="margin-top:0.5rem">{esc(summary)}</div></div>'
            f'<div class="tl-card"><div class="tl-label">Who to ask</div>'
            f'<div class="tl-sub"><b>{who}</b></div></div>',
            unsafe_allow_html=True,
        )

    if rejected:
        items = "".join(
            f'<li><b>{esc(r["title"])}</b> says {esc(r["claim"])}: {esc(r["reason"])}</li>' for r in rejected
        )
        st.markdown(
            f'<div class="tl-card"><div class="tl-label">Not relied on, and why</div>'
            f'<ul class="tl-rejected">{items}</ul></div>',
            unsafe_allow_html=True,
        )


def render_conflicts(conflicts: list[dict]):
    for c in conflicts:
        rows = []
        for part in c["description"].split("; "):
            value, _, who = part.partition(": ")
            rows.append(f'<div class="tl-crow"><span class="tl-cval">{esc(value)}</span><span>{esc(who)}</span></div>')
        st.markdown(
            f'<div class="tl-card tl-conflict"><div class="tl-label">Conflict surfaced: {esc(c["claim"])}</div>'
            f'{"".join(rows)}</div>',
            unsafe_allow_html=True,
        )


def render_source(rank: int, s: dict, status, verification: dict | None, is_expert: bool):
    lvl = level(s["trust_score"])
    meta = " Â· ".join(esc(x) for x in (
        TYPE_LABELS.get(s["source_type"], s["source_type"]),
        s["owner"] or "No owner",
        f"updated {s['updated_at']}",
        s["country"],
        s.get("client"),
    ) if x)
    signals = "".join(
        f'<span class="tl-sig tl-{level(sig["score"])}"><b>{esc(SIGNAL_LABELS.get(sig["name"], sig["name"]))}</b>'
        f'{esc(sig["reason"])}</span>'
        for sig in s["signals"]
    )
    badges = []
    if status:
        badges.append(f'<span class="tl-pill tl-{status[0]}">{esc(status[1])}</span>')
    if verification:
        ok = verification.get("verified")
        badges.append(
            f'<span class="tl-pill tl-{"good" if ok else "bad"}">'
            f'{"Verified" if ok else "Rejected"} by expert ({esc(verification.get("verified_by"))})</span>'
        )
    elif s.get("verified_by"):
        badges.append(f'<span class="tl-pill tl-good">Verified by expert ({esc(s["verified_by"])})</span>')
    status_html = f'<div class="tl-status">{" ".join(badges)}</div>' if badges else ""
    muted = " tl-muted" if status and status[0] == "bad" else ""

    st.markdown(
        f'<div class="tl-card{muted}">'
        f'<div class="tl-src-head"><div><div class="tl-src-title">#{rank} {esc(s["title"])}</div>'
        f'<div class="tl-meta">{meta}</div></div>'
        f'<div><div class="tl-score">{s["trust_score"]:.2f}</div><div class="tl-score-cap">trust</div></div></div>'
        f'<div class="tl-bar"><div class="tl-bar-{lvl}" style="width:{int(round(s["trust_score"] * 100))}%"></div></div>'
        f'<div class="tl-signals">{signals}</div>'
        f'<div class="tl-quote">{esc(s["excerpt"])}</div>'
        f'{status_html}</div>',
        unsafe_allow_html=True,
    )

    if is_expert:
        c1, c2, _ = st.columns([1, 1, 4])
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
                '<div class="tl-tagline">From "I found something" to "I understand why I can rely on it."</div>',
                unsafe_allow_html=True)

    if "token" not in st.session_state:
        st.info("Sign in on the left to ask a question. Demo users: jonas, lars (consultants), sofie (expert).")
        return

    with st.form("ask"):
        question = st.selectbox("Your question", DEMO_QUESTIONS, index=0, accept_new_options=True)
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

    render_answer(result, rejected, lvl, summary, confirm)
    render_conflicts(result["conflicts"])

    sources = result["sources"]
    st.markdown(f'<div class="tl-label" style="margin-top:0.8rem">Sources ({len(sources)}), ranked by trust</div>',
                unsafe_allow_html=True)
    verified = st.session_state.get("verified", {})
    is_expert = st.session_state["user"]["role"] in ("expert", "admin")
    for rank, s in enumerate(sources, start=1):
        render_source(rank, s, source_status(s, rejected, backers), verified.get(s["id"]), is_expert)


main()
