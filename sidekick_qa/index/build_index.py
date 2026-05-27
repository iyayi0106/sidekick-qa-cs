"""Build Chroma vector index from processed JSON."""

from __future__ import annotations

import json
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from sidekick_qa.config import (
    ARTICLES_JSON,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    HQ_SOURCES_JSON,
    PROCESSED_DIR,
)
from sidekick_qa.index.chunking import chunk_text
from sidekick_qa.models import Article, HQSource

COLLECTION_NAME = "sidekick_kb"

TEAM_BY_ARTICLE = {
    1: "booking_platform",
    2: "booking_platform",
    3: "tour_ops",
    4: "tour_ops",
    5: "support",
    6: "support",
    7: "booking_platform",
    8: "booking_platform",
    9: "booking_platform",
    10: "tour_ops",
}

HQ_TEAM = {
    1: "tour_ops",
    2: "booking_platform",
    3: "booking_platform",
    4: "tour_ops",
}


def _load_articles() -> list[Article]:
    data = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    return [Article(**a) for a in data]


def _load_hq() -> list[HQSource]:
    data = json.loads(HQ_SOURCES_JSON.read_text(encoding="utf-8"))
    return [HQSource(**h) for h in data]


def _prefix(doc_type: str, meta: dict[str, Any], body: str) -> str:
    label = meta.get("title", meta.get("article_id", meta.get("hq_id", "")))
    status = meta.get("status", "")
    return f"[{doc_type} | {label} | {status}]\n{body}"


def build_index(api_key: str | None = None) -> chromadb.Collection:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    ef = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for article in _load_articles():
        chunks = chunk_text(article.body, CHUNK_SIZE, CHUNK_OVERLAP)
        team = TEAM_BY_ARTICLE.get(article.id, "booking_platform")
        for i, chunk in enumerate(chunks):
            cid = f"article_{article.id:02d}_chunk_{i:03d}"
            meta = {
                "doc_type": "article",
                "article_id": article.id,
                "title": article.title,
                "status": article.status,
                "team": team,
                "chunk_index": i,
            }
            ids.append(cid)
            documents.append(_prefix("Article", meta, chunk))
            metadatas.append(meta)

    for hq in _load_hq():
        chunks = chunk_text(hq.body, CHUNK_SIZE, CHUNK_OVERLAP)
        team = HQ_TEAM.get(hq.id, "tour_ops")
        topics = ",".join(hq.topics)
        for i, chunk in enumerate(chunks):
            cid = f"hq_{hq.id:02d}_chunk_{i:03d}"
            meta = {
                "doc_type": "hq_source",
                "hq_id": hq.id,
                "title": hq.title,
                "status": "hq_truth",
                "team": team,
                "topics": topics,
                "chunk_index": i,
            }
            ids.append(cid)
            documents.append(_prefix("HQ", meta, chunk))
            metadatas.append(meta)

    # Batch add in groups of 100
    batch = 100
    for start in range(0, len(ids), batch):
        end = start + batch
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"Indexed {len(ids)} chunks into {CHROMA_DIR}")
    return collection


def get_collection(api_key: str | None = None) -> chromadb.Collection:
    ef = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
