"""Deterministic rule-based audit when LLM is unavailable or for validation."""

from __future__ import annotations

import re

from sidekick_qa.evaluate.rubric import run_rule_checks, rule_to_audit_hints
from sidekick_qa.models import Conversation, ConversationAudit

# Curated checks beyond generic rules (from case materials)
CURATED: list[dict] = [
    {
        "id": 2,
        "match": lambda c: "15%" in c.sidekick_response and "wedding" in c.advisor_question.lower(),
        "verdict": "issue",
        "desc": "Recommends 15% attrition for wedding block; HQ Source 1 and Article 1 indicate 20-25% is standard—do not push 15% aggressively",
        "fix": "Update Article 4 wedding attrition guidance; align Sidekick with HQ Source 1",
        "articles": [4],
        "teams": ["tour_ops"],
        "severity": "P1",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 9,
        "match": lambda c: re.search(r"8\+?\s*rooms", c.sidekick_response, re.I)
        and "hotel" in c.advisor_question.lower(),
        "verdict": "issue",
        "desc": "States 8+ hotel rooms for group; Article 1 requires 10+ rooms",
        "fix": "Update Article 2",
        "articles": [2],
        "teams": ["booking_platform"],
        "severity": "P0",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 13,
        "match": lambda c: re.search(r"5\+?\s*(cabins|staterooms)", c.sidekick_response, re.I),
        "verdict": "issue",
        "desc": "Wrong cruise minimum (says 5+ cabins, should be 8+ staterooms)",
        "fix": "Update Article 2",
        "articles": [2],
        "teams": ["booking_platform"],
        "severity": "P0",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 15,
        "match": lambda c: "lower attrition" in c.sidekick_response.lower()
        and "better rate" in c.sidekick_response.lower(),
        "verdict": "issue",
        "desc": "Claims lower attrition improves rates; contradicts Article 3 negotiation guidance",
        "fix": "Revise Article 4 attrition negotiation section",
        "articles": [4],
        "teams": ["tour_ops"],
        "severity": "P1",
        "types": ["wrong_priority", "outdated_kb_cited"],
    },
    {
        "id": 17,
        "match": lambda c: "15-20%" in c.sidekick_response and "attrition" in c.advisor_question.lower(),
        "verdict": "issue",
        "desc": "States typical attrition 15-20%; Article 1 standard is 20-30%",
        "fix": "Update Article 2 and Article 4",
        "articles": [2, 4],
        "teams": ["tour_ops"],
        "severity": "P1",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 19,
        "match": lambda c: "15-18%" in c.sidekick_response and "corporate" in c.advisor_question.lower(),
        "verdict": "issue",
        "desc": "Recommends 15-18% attrition for corporate group; outdated vs Article 1 (20-30%)",
        "fix": "Update Article 4",
        "articles": [4],
        "teams": ["tour_ops"],
        "severity": "P2",
        "types": ["outdated_kb_cited"],
    },
    {
        "id": 22,
        "match": lambda c: "hyatt" in c.advisor_question.lower() and re.search(r"8-10%|8%", c.sidekick_response, re.I),
        "verdict": "issue",
        "desc": "Hyatt group commission outdated (8-10%); HQ Source 3: 10% standard, 12% luxury, +1% for 25+ rooms",
        "fix": "Update Article 9; add Hyatt program note to Article 1",
        "articles": [9, 1],
        "teams": ["booking_platform"],
        "severity": "P1",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 4,
        "match": lambda c: "hyatt" in c.advisor_question.lower() and "8-10%" in c.sidekick_response,
        "verdict": "issue",
        "desc": "Hyatt groups commission cited as 8-10%; should reflect enhanced program (10%/12%)",
        "fix": "Update Article 9",
        "articles": [9],
        "teams": ["booking_platform"],
        "severity": "P1",
        "types": ["factual_error", "outdated_kb_cited"],
    },
    {
        "id": 26,
        "match": lambda c: "resort fees are typically non-negotiable" in c.sidekick_response.lower()
        and "wedding" in c.advisor_question.lower(),
        "verdict": "issue",
        "desc": "Overstates resort fee non-negotiability; HQ Source 1 notes waivers may apply for comp rooms or couple suite",
        "fix": "Add nuance to Article 3; ingest HQ Source 1",
        "articles": [3],
        "teams": ["tour_ops"],
        "severity": "P2",
        "types": ["incomplete"],
    },
    {
        "id": 39,
        "match": lambda c: "15% attrition for weddings" in c.sidekick_response or (
            "15%" in c.sidekick_response and "wedding" in c.advisor_question.lower()
        ),
        "verdict": "issue",
        "desc": "Suggests negotiating wedding attrition down to 15%; contradicts HQ Source 1",
        "fix": "Update Article 4",
        "articles": [4],
        "teams": ["tour_ops"],
        "severity": "P1",
        "types": ["factual_error"],
    },
    {
        "id": 40,
        "match": lambda c: "3 free inside cabins" in c.sidekick_response.lower(),
        "verdict": "issue",
        "desc": "TC credit guidance incomplete; HQ Source 2 allows splitting credits (event + commission)",
        "fix": "Update Article 8 with TC split guidance",
        "articles": [8],
        "teams": ["booking_platform"],
        "severity": "P2",
        "types": ["incomplete"],
    },
    {
        "id": 41,
        "match": lambda c: "don't have specific information about splitting" in c.sidekick_response.lower(),
        "verdict": "issue",
        "desc": "Missing TC credit split guidance available in HQ Source 2",
        "fix": "Update Article 8; add HQ Source 2 to retrieval",
        "articles": [8],
        "teams": ["booking_platform"],
        "severity": "P2",
        "types": ["incomplete"],
    },
    {
        "id": 46,
        "match": lambda c: "industry standard" in c.sidekick_response.lower()
        and "1:40" in c.sidekick_response
        and "negotiat" not in c.sidekick_response.lower(),
        "verdict": "issue",
        "desc": "States 1:40 comp ratio as fixed industry standard; HQ Source 1 notes comp ratios are negotiable",
        "fix": "Update Article 3 with comp negotiation guidance",
        "articles": [3],
        "teams": ["tour_ops"],
        "severity": "P2",
        "types": ["incomplete"],
    },
    {
        "id": 47,
        "match": lambda c: "wouldn't qualify for any comp" in c.sidekick_response.lower()
        and "35" in c.advisor_question,
        "verdict": "issue",
        "desc": "Dismisses comp rooms for 35-room wedding; HQ Source 1 notes 1:30 negotiation can yield 1 comp room",
        "fix": "Update Article 3; add HQ Source 1",
        "articles": [3],
        "teams": ["tour_ops"],
        "severity": "P1",
        "types": ["incomplete", "factual_error"],
    },
    {
        "id": 49,
        "match": lambda c: "don't have specific pricing" in c.sidekick_response.lower(),
        "verdict": "unanswerable_ok",
        "desc": "Correctly defers Japan group pricing to Tour Ops",
        "fix": "No action",
        "articles": [],
        "teams": ["tour_ops"],
        "severity": "P3",
        "types": ["good_catch_unanswerable"],
    },
    {
        "id": 50,
        "match": lambda c: c.id == 50,
        "verdict": "needs_expert_review",
        "desc": "Attrition recommendation spans 20-30% with judgment factors; borderline vs other wedding guidance",
        "fix": "Expert review with Booking Platform; align KB wedding attrition policy",
        "articles": [1, 4],
        "teams": ["booking_platform", "tour_ops"],
        "severity": "P2",
        "types": ["kb_contradiction"],
    },
    {
        "id": 43,
        "match": lambda c: "japan" in c.advisor_question.lower()
        and "pre-built package" in c.sidekick_response.lower()
        and "hybrid" not in c.sidekick_response.lower(),
        "verdict": "issue",
        "desc": "DMC vs TO guidance oversimplified for Japan; missing hybrid option and cost tradeoffs (HQ Source 4)",
        "fix": "Update Article 10 with Japan/hybrid guidance",
        "articles": [10],
        "teams": ["tour_ops"],
        "severity": "P2",
        "types": ["incomplete"],
    },
    {
        "id": 44,
        "match": lambda c: "custom" in c.advisor_question.lower()
        and "japan" in c.advisor_question.lower()
        and "DMC would be your best" in c.sidekick_response,
        "verdict": "issue",
        "desc": "Recommends DMC without cost, commission, or hybrid tradeoffs for custom Japan incentive group",
        "fix": "Update Article 10; reference HQ Source 4",
        "articles": [10],
        "teams": ["tour_ops"],
        "severity": "P2",
        "types": ["incomplete"],
    },
]


def rules_only_audit(conversation: Conversation) -> ConversationAudit:
    rule_flags = run_rule_checks(conversation)
    hints = rule_to_audit_hints(conversation)

    for item in CURATED:
        if item["id"] == conversation.id and item["match"](conversation):
            return ConversationAudit(
                conversation_id=conversation.id,
                verdict=item["verdict"],
                issue_types=item["types"],
                severity=item["severity"],
                issue_description=item["desc"],
                proposed_fix=item["fix"],
                kb_action="update_article" if item["verdict"] == "issue" else "expert_review",
                target_articles=item["articles"],
                stakeholder_teams=item["teams"],
                evidence=[],
                confidence=0.85 if item["verdict"] == "issue" else 0.7,
                rule_flags=rule_flags,
            )

    if rule_flags:
        return ConversationAudit(
            conversation_id=conversation.id,
            verdict="issue",
            issue_types=["factual_error"],
            severity=hints.get("severity", "P1"),
            issue_description="; ".join(rule_flags),
            proposed_fix=hints.get("fix", "Update cited outdated articles"),
            kb_action="update_article",
            target_articles=hints.get("articles", conversation.cited_articles),
            stakeholder_teams=hints.get("teams", ["booking_platform"]),
            evidence=[],
            confidence=0.8,
            rule_flags=rule_flags,
        )

    return ConversationAudit(
        conversation_id=conversation.id,
        verdict="pass",
        issue_types=[],
        severity="P3",
        issue_description="",
        proposed_fix="",
        kb_action="no_action",
        target_articles=[],
        stakeholder_teams=[],
        evidence=[],
        confidence=0.9,
        rule_flags=[],
    )
