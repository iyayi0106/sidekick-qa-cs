"""QA rubric, rule checks, and team routing."""

from __future__ import annotations

import re

from sidekick_qa.models import Conversation, ConversationAudit

# Patterns that indicate likely factual errors vs ground truth
RULE_CHECKS: list[dict] = [
    {
        "id": "hotel_min_8",
        "pattern": r"\b8\+?\s*rooms?\b",
        "context": r"hotel|room block",
        "message": "States 8+ hotel rooms; Article 1 requires 10+ rooms",
        "severity": "P0",
        "fix": "Update Article 2 hotel minimum to 10+ rooms",
        "articles": [2],
        "teams": ["booking_platform"],
    },
    {
        "id": "cruise_min_5",
        "pattern": r"\b5\+?\s*(cabins?|staterooms?)\b",
        "context": r"cruise|stateroom|cabin",
        "message": "States 5+ cruise cabins; Article 1 requires 8+ staterooms",
        "severity": "P0",
        "fix": "Update Article 2 cruise minimum to 8+ staterooms",
        "articles": [2],
        "teams": ["booking_platform"],
    },
    {
        "id": "wedding_attrition_15",
        "pattern": r"15%?\s*attrition",
        "context": r"wedding",
        "message": "Recommends 15% wedding attrition; HQ/Source of Truth suggests 20-25% is standard",
        "severity": "P1",
        "fix": "Update Article 4 wedding attrition guidance; align with Article 1 and HQ Source 1",
        "articles": [4],
        "teams": ["tour_ops"],
    },
    {
        "id": "hyatt_commission_low",
        "pattern": r"hyatt.*?(7|8)[-–]?10%|8-10%.*hyatt",
        "context": r"hyatt|commission",
        "message": "Hyatt group commission outdated (7-8%); HQ Source 3: 10% standard, 12% luxury",
        "severity": "P1",
        "fix": "Update Article 9 and add Hyatt program note to Article 1",
        "articles": [9],
        "teams": ["booking_platform"],
    },
    {
        "id": "lower_attrition_better_rates",
        "pattern": r"lower attrition.*(better|improve).*rate|push for (10|15)% attrition",
        "context": r"attrition",
        "message": "Suggests lower attrition improves rates; contradicts Article 3 negotiation guidance",
        "severity": "P1",
        "fix": "Revise Article 4 attrition negotiation section",
        "articles": [4],
        "teams": ["tour_ops"],
    },
]


def _is_false_positive_hotel_min(conversation: Conversation) -> bool:
    """Skip flag when 8+ appears only as sub-minimum context."""
    resp = conversation.sidekick_response.lower()
    if "courtesy hold" in resp or "below the 10-room" in resp or "below group minimum" in resp:
        return True
    if re.search(r"10\+?\s*(is the|room minimum|standard threshold|rooms)", resp):
        return True
    if "starting at 8" in resp and "10+" in resp:
        return True
    return False


def run_rule_checks(conversation: Conversation) -> list[str]:
    """Return list of rule flag messages."""
    combined = f"{conversation.advisor_question}\n{conversation.sidekick_response}".lower()
    flags: list[str] = []
    for rule in RULE_CHECKS:
        if rule["id"] == "hotel_min_8" and _is_false_positive_hotel_min(conversation):
            continue
        if re.search(rule["pattern"], combined, re.I):
            ctx = rule.get("context", "")
            if not ctx or re.search(ctx, combined, re.I):
                flags.append(rule["message"])
    return flags


def rule_to_audit_hints(conversation: Conversation) -> dict:
    """Map rule hits to suggested severity and fix."""
    combined = f"{conversation.advisor_question}\n{conversation.sidekick_response}".lower()
    hints: dict = {"flags": [], "severity": "P3", "fix": "", "articles": [], "teams": []}
    for rule in RULE_CHECKS:
        if rule["id"] == "hotel_min_8" and _is_false_positive_hotel_min(conversation):
            continue
        if re.search(rule["pattern"], combined, re.I):
            ctx = rule.get("context", "")
            if not ctx or re.search(ctx, combined, re.I):
                hints["flags"].append(rule["message"])
                hints["severity"] = rule["severity"]
                hints["fix"] = rule["fix"]
                hints["articles"] = list(set(hints["articles"] + rule["articles"]))
                hints["teams"] = list(set(hints["teams"] + rule["teams"]))
    return hints


SYSTEM_PROMPT = """You are a QA auditor for Fora Travel's Sidekick AI advisor chatbot.
Evaluate whether Sidekick's response is accurate, complete, and appropriately sourced.

Hierarchy of truth:
1. HQ expert sources (highest for operational nuance)
2. Article 1 (Source of Truth) for canonical policy
3. Other current articles
4. Outdated articles (2, 4, 9, 10) should NOT be trusted over Article 1

Verdicts:
- pass: Accurate and sufficiently complete
- issue: Clear factual error, harmful omission, or misleading guidance
- needs_expert_review: Ambiguous judgment, conflicting sources, or borderline cases
- unanswerable_ok: Sidekick correctly defers when KB lacks info (not a defect)

Issue types (when not pass): factual_error, outdated_kb_cited, incomplete,
kb_contradiction, hallucination, wrong_priority

Severity: P0=critical wrong policy/numbers, P1=significant error, P2=minor gap, P3=style/nuance

Stakeholder teams: tour_ops, booking_platform, support

Be conservative: only flag real quality problems. Many responses are correct.
"""


def build_user_prompt(conversation: Conversation, context: str, rule_hints: dict) -> str:
    cited = ", ".join(str(a) for a in conversation.cited_articles)
    rules = "\n".join(f"- {f}" for f in rule_hints.get("flags", [])) or "None"
    return f"""## Conversation {conversation.id}
Cited articles: {cited}

### Advisor question
{conversation.advisor_question}

### Sidekick response
{conversation.sidekick_response}

### Rule-based pre-checks
{rules}

### Retrieved knowledge base context
{context}

Return JSON matching this schema:
{{
  "conversation_id": {conversation.id},
  "verdict": "pass|issue|needs_expert_review|unanswerable_ok",
  "issue_types": [],
  "severity": "P0|P1|P2|P3",
  "issue_description": "",
  "proposed_fix": "",
  "kb_action": "update_article|deprecate_article|add_hq_source|flag_unanswerable|no_action|expert_review",
  "target_articles": [],
  "stakeholder_teams": [],
  "evidence": ["short quotes from context"],
  "confidence": 0.0
}}
"""
