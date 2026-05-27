"""RAG retrieval with Source-of-Truth and HQ boosting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sidekick_qa.config import TOP_K
from sidekick_qa.index.build_index import get_collection
from sidekick_qa.models import Conversation

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "wedding": ["wedding", "attrition", "comp room", "comp ratio", "resort fee"],
    "cruise_tc": ["tc credit", "tour conductor", "gap point", "cruise group", "stateroom", "cabin"],
    "hyatt_commission": ["hyatt", "commission"],
    "dmc_to_japan": ["dmc", "tour operator", "japan", "italy", "custom itinerary"],
}


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None = None


def _detect_topics(text: str) -> set[str]:
    lower = text.lower()
    found: set[str] = set()
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw in lower for kw in kws):
            found.add(topic)
    return found


def retrieve_context(
    conversation: Conversation,
    api_key: str | None = None,
    top_k: int = TOP_K,
) -> list[RetrievedChunk]:
    collection = get_collection(api_key=api_key)
    query = f"{conversation.advisor_question}\n{conversation.sidekick_response}"
    topics = _detect_topics(query)

    results = collection.query(
        query_texts=[query],
        n_results=top_k + 6,
        include=["documents", "metadatas", "distances"],
    )

    seen: set[str] = set()
    chunks: list[RetrievedChunk] = []

    def _add_from_result(idx: int) -> None:
        doc_id = results["ids"][0][idx]
        if doc_id in seen:
            return
        seen.add(doc_id)
        chunks.append(
            RetrievedChunk(
                id=doc_id,
                text=results["documents"][0][idx],
                metadata=results["metadatas"][0][idx],
                distance=results["distances"][0][idx] if results.get("distances") else None,
            )
        )

    for i in range(len(results["ids"][0])):
        _add_from_result(i)

    # Boost: always include Article 1 chunks relevant to query
    sot = collection.query(
        query_texts=[query],
        n_results=3,
        where={"article_id": 1},
        include=["documents", "metadatas", "distances"],
    )
    for i in range(len(sot["ids"][0])):
        doc_id = sot["ids"][0][i]
        if doc_id not in seen:
            seen.add(doc_id)
            chunks.append(
                RetrievedChunk(
                    id=doc_id,
                    text=sot["documents"][0][i],
                    metadata=sot["metadatas"][0][i],
                    distance=sot["distances"][0][i] if sot.get("distances") else None,
                )
            )

    # Boost HQ sources by topic metadata
    if topics:
        all_hq = collection.get(
            where={"doc_type": "hq_source"},
            include=["documents", "metadatas"],
        )
        for i, meta in enumerate(all_hq.get("metadatas") or []):
            doc_topics = (meta or {}).get("topics", "")
            if any(t in doc_topics for t in topics):
                doc_id = all_hq["ids"][i]
                if doc_id not in seen and len(chunks) < top_k + 8:
                    seen.add(doc_id)
                    chunks.append(
                        RetrievedChunk(
                            id=doc_id,
                            text=all_hq["documents"][i],
                            metadata=meta or {},
                        )
                    )

    return chunks[: top_k + 6]


def format_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for c in chunks:
        src = c.metadata.get("title", c.id)
        parts.append(f"--- {src} ({c.id}) ---\n{c.text}")
    return "\n\n".join(parts)
