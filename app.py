"""Streamlit app — Deliverable 1: Sidekick QA Framework."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Sidekick QA",
    page_icon="✓",
    layout="wide",
)

ROOT = Path(__file__).parent
import sys

sys.path.insert(0, str(ROOT))

from sidekick_qa.config import (  # noqa: E402
    ARTICLES_JSON,
    AUDIT_CACHE,
    CONVERSATIONS_JSON,
    ISSUE_LOG_CSV,
    PATTERN_ANALYSIS,
    REVIEW_QUEUE,
    UPDATED_KB_DIR,
)
from sidekick_qa.models import Conversation, ConversationAudit, ReviewOverride  # noqa: E402


def _api_key() -> str:
    return st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))


@st.cache_data
def load_conversations() -> list[dict]:
    return json.loads(CONVERSATIONS_JSON.read_text(encoding="utf-8"))


@st.cache_data
def load_audits() -> list[dict]:
    if not AUDIT_CACHE.exists():
        return []
    rows = []
    for line in AUDIT_CACHE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_review_queue() -> list[dict]:
    if REVIEW_QUEUE.exists():
        return json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
    return []


def save_review_queue(queue: list[dict]) -> None:
    REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE.write_text(json.dumps(queue, indent=2), encoding="utf-8")


def run_pipeline(clear_cache: bool = False, force_rules: bool = False) -> None:
    key = _api_key() if not force_rules else ""
    rules_only = force_rules or not bool(key)

    from sidekick_qa.evaluate.auditor import run_full_audit
    from sidekick_qa.remediate.exports import init_review_queue, write_issue_log
    from sidekick_qa.remediate.kb_patcher import write_updated_kb
    from sidekick_qa.remediate.patterns import write_pattern_analysis

    if rules_only:
        st.warning("No OPENAI_API_KEY — running rule-based audit (no embeddings/LLM).")
    else:
        from sidekick_qa.index.build_index import build_index

        with st.spinner("Building vector index..."):
            build_index(api_key=key)

    with st.spinner("Auditing 50 conversations..."):
        if clear_cache and AUDIT_CACHE.exists():
            AUDIT_CACHE.unlink()
        audits = run_full_audit(
            api_key=key or None,
            use_cache=not clear_cache,
            clear_cache=clear_cache,
            rules_only=rules_only,
        )
    init_review_queue(audits)
    write_issue_log(audits)
    write_pattern_analysis(audits)
    write_updated_kb()
    st.cache_data.clear()
    st.success("Audit complete!")


st.title("Sidekick QA Framework")
st.caption("RAG pipeline for auditing advisor–Sidekick conversations against the group bookings knowledge base.")

tab_run, tab_dash, tab_conv, tab_issues, tab_kb, tab_patterns, tab_review, tab_collab = st.tabs(
    [
        "Run Audit",
        "Dashboard",
        "Conversations",
        "Issue Log",
        "KB Updates",
        "Patterns",
        "Review Queue",
        "Collaboration",
    ]
)

with tab_run:
    st.subheader("Run full QA audit")
    st.markdown(
        "Builds the Chroma index, evaluates all 50 conversations with RAG + GPT-4o-mini, "
        "and exports Deliverable 2 artifacts."
    )
    clear = st.checkbox("Clear audit cache before run")
    force_rules = st.checkbox("Force rule-based audit (no API calls)")
    if st.button("Run Audit", type="primary"):
        run_pipeline(clear_cache=clear, force_rules=force_rules)

with tab_dash:
    audits = load_audits()
    if not audits:
        st.info("Run an audit first.")
    else:
        df = pd.DataFrame(audits)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pass", len(df[df["verdict"] == "pass"]))
        c2.metric("Issues", len(df[df["verdict"] == "issue"]))
        c3.metric("Expert review", len(df[df["verdict"] == "needs_expert_review"]))
        c4.metric("OK deferrals", len(df[df["verdict"] == "unanswerable_ok"]))
        st.subheader("By severity (issues + expert review)")
        flagged = df[df["verdict"].isin(["issue", "needs_expert_review"])]
        if not flagged.empty:
            st.bar_chart(flagged["severity"].value_counts())

with tab_conv:
    convs = load_conversations()
    audits = {a["conversation_id"]: a for a in load_audits()}
    cid = st.selectbox("Conversation", [c["id"] for c in convs])
    conv = next(c for c in convs if c["id"] == cid)
    st.markdown(f"**Cited articles:** {conv.get('cited_articles', [])}")
    st.markdown("**Advisor**")
    st.write(conv["advisor_question"])
    st.markdown("**Sidekick**")
    st.write(conv["sidekick_response"])
    if cid in audits:
        a = audits[cid]
        st.markdown(f"**Verdict:** `{a['verdict']}` | **Severity:** `{a['severity']}` | **Confidence:** {a.get('confidence', 0):.2f}")
        if a.get("issue_description"):
            st.warning(a["issue_description"])
        if a.get("proposed_fix"):
            st.info(f"**Proposed fix:** {a['proposed_fix']}")
        if a.get("evidence"):
            with st.expander("Evidence"):
                for e in a["evidence"]:
                    st.write(e)
        if a.get("rule_flags"):
            st.caption(f"Rule flags: {', '.join(a['rule_flags'])}")

with tab_issues:
    if ISSUE_LOG_CSV.exists():
        df = pd.read_csv(ISSUE_LOG_CSV)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download issue_log.csv",
            ISSUE_LOG_CSV.read_text(encoding="utf-8"),
            file_name="issue_log.csv",
            mime="text/csv",
        )
    else:
        st.info("Run audit to generate issue log.")

with tab_kb:
    if UPDATED_KB_DIR.exists():
        articles = sorted(UPDATED_KB_DIR.glob("article_*.md"))
        art_id = st.selectbox("Article", [p.stem for p in articles])
        path = UPDATED_KB_DIR / f"{art_id}.md"
        if path.exists():
            st.markdown(path.read_text(encoding="utf-8"))
        if (UPDATED_KB_DIR / "CHANGELOG.md").exists():
            with st.expander("CHANGELOG"):
                st.markdown((UPDATED_KB_DIR / "CHANGELOG.md").read_text(encoding="utf-8"))
    else:
        st.info("Run audit to generate updated KB.")

with tab_patterns:
    if PATTERN_ANALYSIS.exists():
        st.markdown(PATTERN_ANALYSIS.read_text(encoding="utf-8"))
    else:
        st.info("Run audit to generate pattern analysis.")

with tab_review:
    audits = {a["conversation_id"]: a for a in load_audits()}
    queue = load_review_queue()
    st.subheader("Human-in-the-loop review")
    expert_ids = [a["conversation_id"] for a in load_audits() if a.get("verdict") == "needs_expert_review"]
    if not expert_ids:
        expert_ids = [q["conversation_id"] for q in queue]
    if expert_ids:
        rid = st.selectbox("Conversation to review", expert_ids)
        audit = audits.get(rid, {})
        st.write(audit.get("issue_description", ""))
        action = st.radio("Action", ["approve_issue", "dismiss", "edit"])
        desc = st.text_area("Issue description", audit.get("issue_description", ""))
        fix = st.text_area("Proposed fix", audit.get("proposed_fix", ""))
        notes = st.text_input("Notes", "")
        if st.button("Save override"):
            queue = [q for q in queue if q["conversation_id"] != rid]
            queue.append(
                {
                    "conversation_id": rid,
                    "action": action,
                    "issue_description": desc,
                    "proposed_fix": fix,
                    "notes": notes,
                }
            )
            save_review_queue(queue)
            from sidekick_qa.remediate.exports import write_issue_log
            from sidekick_qa.evaluate.auditor import ConversationAudit

            all_audits = [ConversationAudit(**a) for a in load_audits()]
            write_issue_log(all_audits)
            st.success("Saved and refreshed issue log.")
    else:
        st.info("No items in review queue.")

with tab_collab:
    audits = load_audits()
    if audits:
        team = st.selectbox("Filter by team", ["all", "tour_ops", "booking_platform", "support"])
        rows = []
        for a in audits:
            if a["verdict"] not in ("issue", "needs_expert_review"):
                continue
            teams = a.get("stakeholder_teams") or []
            if team != "all" and team not in teams:
                continue
            rows.append(
                {
                    "conversation_id": a["conversation_id"],
                    "severity": a["severity"],
                    "teams": ", ".join(teams),
                    "issue": a.get("issue_description", "")[:120],
                    "fix": a.get("proposed_fix", "")[:80],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        if rows:
            summary = "\n".join(
                f"Conv {r['conversation_id']} [{r['severity']}]: {r['issue']}" for r in rows[:20]
            )
            st.text_area("Shareable summary (copy for Slack/email)", summary, height=200)
    else:
        st.info("Run audit first.")
