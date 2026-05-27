"""Pydantic models for pipeline data."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Article(BaseModel):
    id: int
    title: str
    published: str = ""
    status: Literal["source_of_truth", "outdated", "current"] = "current"
    body: str


class Conversation(BaseModel):
    id: int
    cited_articles: list[int] = Field(default_factory=list)
    advisor_question: str
    sidekick_response: str


class HQSource(BaseModel):
    id: int
    title: str
    format: str = ""
    date: str = ""
    participants: str = ""
    body: str
    topics: list[str] = Field(default_factory=list)


class ConversationAudit(BaseModel):
    conversation_id: int
    verdict: Literal["pass", "issue", "needs_expert_review", "unanswerable_ok"]
    issue_types: list[str] = Field(default_factory=list)
    severity: Literal["P0", "P1", "P2", "P3"] = "P3"
    issue_description: str = ""
    proposed_fix: str = ""
    kb_action: Literal[
        "update_article",
        "deprecate_article",
        "add_hq_source",
        "flag_unanswerable",
        "no_action",
        "expert_review",
    ] = "no_action"
    target_articles: list[int] = Field(default_factory=list)
    stakeholder_teams: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    rule_flags: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)


class ReviewOverride(BaseModel):
    conversation_id: int
    action: Literal["approve_issue", "dismiss", "edit"]
    issue_description: str = ""
    proposed_fix: str = ""
    notes: str = ""
