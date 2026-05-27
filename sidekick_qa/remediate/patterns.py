"""Aggregate systemic patterns from audit results."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from sidekick_qa.config import AUDIT_CACHE, PATTERN_ANALYSIS
from sidekick_qa.models import ConversationAudit


def load_audits() -> list[ConversationAudit]:
    audits: list[ConversationAudit] = []
    if not AUDIT_CACHE.exists():
        return audits
    for line in AUDIT_CACHE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            audits.append(ConversationAudit(**json.loads(line)))
    return audits


def generate_pattern_analysis(audits: list[ConversationAudit]) -> str:
    issues = [a for a in audits if a.verdict in ("issue", "needs_expert_review")]
    issue_types = Counter()
    cited_articles = Counter()
    severities = Counter()
    teams = Counter()

    for a in issues:
        for t in a.issue_types:
            issue_types[t] += 1
        severities[a.severity] += 1
        for art in a.target_articles:
            cited_articles[art] += 1
        for team in a.stakeholder_teams:
            teams[team] += 1

    lines = [
        "# Pattern Analysis — Sidekick Group Bookings QA",
        "",
        f"**Conversations audited:** {len(audits)}",
        f"**Issues flagged:** {len([a for a in audits if a.verdict == 'issue'])}",
        f"**Expert review queue:** {len([a for a in audits if a.verdict == 'needs_expert_review'])}",
        f"**Passed:** {len([a for a in audits if a.verdict == 'pass'])}",
        f"**Correct deferrals:** {len([a for a in audits if a.verdict == 'unanswerable_ok'])}",
        "",
        "## Top systemic patterns",
        "",
    ]

    patterns = [
        (
            "Outdated KB articles driving errors",
            "Articles 2, 4, 9, and 10 contain superseded minimums, attrition, and commission guidance. "
            "Sidekick cites these and produces wrong hotel/cruise minimums, wedding attrition advice, and Hyatt rates.",
            cited_articles,
            {2, 4, 9, 10},
        ),
        (
            "Inverted or outdated attrition negotiation guidance",
            "Article 4 suggests pushing 15% attrition and that lower attrition improves rates. "
            "Article 3 and HQ Source 1 indicate 20-30% is standard and wedding blocks should not over-optimize attrition.",
            issue_types,
            {"wrong_priority", "factual_error"},
        ),
        (
            "Missing HQ operational nuance",
            "TC credit splitting, Hyatt 2026 program rates, comp ratio negotiation, and Japan DMC/TO hybrid options "
            "exist in HQ sources but are absent or incomplete in Sidekick responses.",
            teams,
            {"booking_platform", "tour_ops"},
        ),
        (
            "Overconfident answers vs appropriate deferral",
            "Some responses state definitive policy where KB is silent; others correctly defer to Tour Ops (e.g., Japan pricing).",
            None,
            None,
        ),
        (
            "DMC vs tour operator oversimplification",
            "Article 10 and Sidekick responses lack hybrid approach, cost ranges, and commission tradeoffs documented in HQ Source 4.",
            cited_articles,
            {10},
        ),
    ]

    for i, (title, desc, counter, keys) in enumerate(patterns, 1):
        lines.append(f"### {i}. {title}")
        lines.append("")
        lines.append(desc)
        lines.append("")
        if counter and keys:
            if isinstance(keys, set):
                related = sum(counter.get(k, 0) for k in keys)
            else:
                related = sum(counter.get(k, 0) for k in keys if isinstance(k, str))
            lines.append(f"- Related issue count (proxy): {related}")
        lines.append("")

    lines.extend(["## Issue type breakdown", ""])
    for t, count in issue_types.most_common():
        lines.append(f"- `{t}`: {count}")

    lines.extend(["", "## Articles most often targeted for fixes", ""])
    for art, count in cited_articles.most_common(10):
        lines.append(f"- Article {art}: {count}")

    lines.extend(["", "## Severity distribution (flagged conversations)", ""])
    for sev, count in severities.most_common():
        lines.append(f"- {sev}: {count}")

    lines.extend(["", "## Stakeholder routing", ""])
    for team, count in teams.most_common():
        lines.append(f"- {team}: {count}")

    lines.append("")
    lines.append("## Assumptions flagged for expert review")
    lines.append("")
    expert = [a for a in audits if a.verdict == "needs_expert_review"]
    for a in expert[:15]:
        lines.append(f"- Conv {a.conversation_id}: {a.issue_description or 'Borderline judgment call'}")
    if not expert:
        lines.append("- None beyond standard review queue.")

    return "\n".join(lines)


def write_pattern_analysis(audits: list[ConversationAudit] | None = None) -> "Path":
    from pathlib import Path

    audits = audits or load_audits()
    text = generate_pattern_analysis(audits)
    PATTERN_ANALYSIS.parent.mkdir(parents=True, exist_ok=True)
    PATTERN_ANALYSIS.write_text(text, encoding="utf-8")
    return PATTERN_ANALYSIS
