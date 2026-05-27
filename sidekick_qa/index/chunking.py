"""Text chunking utilities."""

from __future__ import annotations

import re

from sidekick_qa.config import CHUNK_OVERLAP, CHUNK_SIZE


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\n+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks by character count."""
    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                # Split long paragraph
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    piece = para[start:end]
                    if piece:
                        chunks.append(piece)
                    start = end - overlap
                current = ""
    if current:
        chunks.append(current)

    # Add overlap between chunks
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        overlapped.append(prev_tail + "\n" + chunks[i])
    return overlapped
