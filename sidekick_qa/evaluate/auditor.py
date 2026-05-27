"""RAG-based conversation auditor."""

from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

from sidekick_qa.config import (
    AUDIT_CACHE,
    CHAT_MODEL,
    CONFIDENCE_THRESHOLD,
    CONVERSATIONS_JSON,
    OUTPUTS_DIR,
)
from sidekick_qa.evaluate.rubric import (
    SYSTEM_PROMPT,
    build_user_prompt,
    rule_to_audit_hints,
    run_rule_checks,
)
from sidekick_qa.index.retrieve import format_context, retrieve_context
from sidekick_qa.models import Conversation, ConversationAudit


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        try:
            import streamlit as st

            key = st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            pass
    if not key:
        raise ValueError("OPENAI_API_KEY not set in environment or Streamlit secrets")
    return key


def load_conversations() -> list[Conversation]:
    data = json.loads(CONVERSATIONS_JSON.read_text(encoding="utf-8"))
    return [Conversation(**c) for c in data]


def _load_cache() -> dict[int, ConversationAudit]:
    if not AUDIT_CACHE.exists():
        return {}
    cache: dict[int, ConversationAudit] = {}
    for line in AUDIT_CACHE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            audit = ConversationAudit(**json.loads(line))
            cache[audit.conversation_id] = audit
    return cache


def _save_cache(cache: dict[int, ConversationAudit]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [cache[k].model_dump_json() for k in sorted(cache)]
    AUDIT_CACHE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _update_cache(audit: ConversationAudit) -> None:
    cache = _load_cache()
    cache[audit.conversation_id] = audit
    _save_cache(cache)


def audit_conversation(
    conversation: Conversation,
    api_key: str | None = None,
    use_cache: bool = True,
    rules_only: bool = False,
) -> ConversationAudit:
    cache = _load_cache() if use_cache else {}
    if use_cache and conversation.id in cache:
        return cache[conversation.id]

    if rules_only:
        from sidekick_qa.evaluate.rules_audit import rules_only_audit

        audit = rules_only_audit(conversation)
        _update_cache(audit)
        return audit

    try:
        key = api_key or _get_api_key()
    except ValueError:
        from sidekick_qa.evaluate.rules_audit import rules_only_audit

        audit = rules_only_audit(conversation)
        _update_cache(audit)
        return audit
    chunks = retrieve_context(conversation, api_key=key)
    context = format_context(chunks)
    rule_hints = rule_to_audit_hints(conversation)
    rule_flags = run_rule_checks(conversation)

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(conversation, context, rule_hints)},
        ],
    )
    raw = json.loads(response.choices[0].message.content or "{}")
    audit = ConversationAudit(
        conversation_id=conversation.id,
        verdict=raw.get("verdict", "pass"),
        issue_types=raw.get("issue_types", []),
        severity=raw.get("severity", "P3"),
        issue_description=raw.get("issue_description", ""),
        proposed_fix=raw.get("proposed_fix", ""),
        kb_action=raw.get("kb_action", "no_action"),
        target_articles=raw.get("target_articles", conversation.cited_articles),
        stakeholder_teams=raw.get("stakeholder_teams", []),
        evidence=raw.get("evidence", []),
        confidence=float(raw.get("confidence", 0.8)),
        rule_flags=rule_flags,
        retrieved_chunk_ids=[c.id for c in chunks],
    )

    # Elevate verdict if rules fired strongly
    if rule_flags and audit.verdict == "pass":
        audit.verdict = "issue"
        if not audit.issue_description:
            audit.issue_description = "; ".join(rule_flags)
        if not audit.proposed_fix and rule_hints.get("fix"):
            audit.proposed_fix = rule_hints["fix"]
        audit.severity = rule_hints.get("severity", audit.severity)
        audit.target_articles = rule_hints.get("articles") or audit.target_articles
        audit.stakeholder_teams = rule_hints.get("teams") or audit.stakeholder_teams
        if "factual_error" not in audit.issue_types:
            audit.issue_types.append("factual_error")

    if audit.confidence < CONFIDENCE_THRESHOLD and audit.verdict == "issue":
        audit.verdict = "needs_expert_review"

    _update_cache(audit)
    return audit


def run_full_audit(
    api_key: str | None = None,
    use_cache: bool = True,
    clear_cache: bool = False,
    rules_only: bool = False,
) -> list[ConversationAudit]:
    if clear_cache and AUDIT_CACHE.exists():
        AUDIT_CACHE.unlink()
    cache = _load_cache() if use_cache else {}

    conversations = load_conversations()
    results: list[ConversationAudit] = []
    for conv in conversations:
        if use_cache and conv.id in cache:
            results.append(cache[conv.id])
            continue
        audit = audit_conversation(
            conv, api_key=api_key, use_cache=False, rules_only=rules_only
        )
        results.append(audit)
        print(f"Conv {conv.id}: {audit.verdict} ({audit.severity})")
    return results
