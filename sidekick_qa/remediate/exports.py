"""Export deliverable 2 artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sidekick_qa.config import ISSUE_LOG_CSV, OUTPUTS_DIR, REVIEW_QUEUE
from sidekick_qa.models import ConversationAudit, ReviewOverride


def load_review_overrides() -> dict[int, ReviewOverride]:
    if not REVIEW_QUEUE.exists():
        return {}
    data = json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
    return {item["conversation_id"]: ReviewOverride(**item) for item in data}


def write_issue_log(audits: list[ConversationAudit]) -> Path:
    overrides = load_review_overrides()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for audit in audits:
        ov = overrides.get(audit.conversation_id)
        if ov and ov.action == "dismiss":
            continue
        if ov and ov.action in ("approve_issue", "edit"):
            rows.append(
                {
                    "conversation_id": str(audit.conversation_id),
                    "issue_description": ov.issue_description or audit.issue_description,
                    "proposed_fix": ov.proposed_fix or audit.proposed_fix,
                }
            )
            continue
        if audit.verdict == "issue":
            rows.append(
                {
                    "conversation_id": str(audit.conversation_id),
                    "issue_description": audit.issue_description,
                    "proposed_fix": audit.proposed_fix,
                }
            )

    with ISSUE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["conversation_id", "issue_description", "proposed_fix"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return ISSUE_LOG_CSV


def init_review_queue(audits: list[ConversationAudit]) -> None:
    """Seed review queue from low-confidence or expert-review audits."""
    if REVIEW_QUEUE.exists():
        return
    queue = []
    for a in audits:
        if a.verdict == "needs_expert_review":
            queue.append(
                {
                    "conversation_id": a.conversation_id,
                    "action": "approve_issue",
                    "issue_description": a.issue_description,
                    "proposed_fix": a.proposed_fix,
                    "notes": "Auto-queued for expert review",
                }
            )
    REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
