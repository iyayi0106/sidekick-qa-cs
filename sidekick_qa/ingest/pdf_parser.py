"""Extract structured data from Fora case-study PDFs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

from sidekick_qa.config import (
    ARTICLES_JSON,
    CONVERSATIONS_JSON,
    FORA_DOCS,
    HQ_SOURCES_JSON,
    OUTDATED_ARTICLES,
    PROCESSED_DIR,
)
from sidekick_qa.models import Article, Conversation, HQSource

HQ_TOPIC_MAP = {
    1: ["wedding", "attrition", "comp_ratio", "hotel_contracts"],
    2: ["cruise_tc", "tc_credits", "gap_points"],
    3: ["hyatt_commission", "hotel_commission"],
    4: ["dmc_to_japan", "tour_operator", "dmc"],
}

CONV_PATTERN = re.compile(
    r"CONVERSATION\s+(\d+)\s*[^\n]*Articles?\s*([\d,\s]+)\s*\n"
    r"ADVISOR\s*\n(.*?)\nSIDEKICK\s*\n(.*?)(?=\nCONVERSATION\s+\d+|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _clean(text: str) -> str:
    text = re.sub(r"\x00", "", text)
    text = re.sub(r"Confidential[^\n]*\n", "", text)
    text = re.sub(r"-- \d+ of \d+ --\s*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf_text(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    return _clean("\n".join(parts))


def parse_articles(text: str) -> list[Article]:
    articles: list[Article] = []
    pattern = re.compile(
        r"ARTICLE\s+(\d+)\s*\n(.+?)(?=\nARTICLE\s+\d+\s*\n|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise ValueError("No articles found in Knowledge-Base.pdf")

    for m in matches:
        aid = int(m.group(1))
        block = m.group(2).strip()
        lines = block.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        published = ""
        pub_m = re.search(r"Published:\s*(.+)", body, re.I)
        if pub_m:
            published = pub_m.group(1).strip()

        status: str = "current"
        header_blob = block[:500].lower()
        if "source of truth" in header_blob:
            status = "source_of_truth"
        elif aid in OUTDATED_ARTICLES or "outdated" in header_blob:
            status = "outdated"

        articles.append(
            Article(
                id=aid,
                title=title,
                published=published,
                status=status,  # type: ignore[arg-type]
                body=body,
            )
        )
    return sorted(articles, key=lambda a: a.id)


def parse_conversations(text: str) -> list[Conversation]:
    convs: list[Conversation] = []
    for m in CONV_PATTERN.finditer(text):
        cid = int(m.group(1))
        cited_raw = m.group(2)
        cited = [int(x) for x in re.findall(r"\d+", cited_raw)]
        question = m.group(3).strip()
        response = m.group(4).strip()
        convs.append(
            Conversation(
                id=cid,
                cited_articles=cited,
                advisor_question=question,
                sidekick_response=response,
            )
        )
    return sorted(convs, key=lambda c: c.id)


def parse_hq_sources(text: str) -> list[HQSource]:
    sources: list[HQSource] = []
    pattern = re.compile(
        r"SOURCE\s+(\d+)\s*\n(.+?)(?=\nSOURCE\s+\d+\s*\n|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        sid = int(m.group(1))
        block = m.group(2).strip()
        lines = block.split("\n", 2)
        title = lines[0].strip() if lines else f"HQ Source {sid}"
        rest = lines[2].strip() if len(lines) > 2 else (lines[1].strip() if len(lines) > 1 else block)

        fmt = ""
        date = ""
        participants = ""
        fmt_m = re.search(r"Format:\s*(.+)", rest, re.I)
        if fmt_m:
            fmt = fmt_m.group(1).strip()
        date_m = re.search(r"Date:\s*(.+)", rest, re.I)
        if date_m:
            date = date_m.group(1).strip()
        part_m = re.search(r"Participants:\s*(.+)", rest, re.I)
        if part_m:
            participants = part_m.group(1).strip()

        topics = HQ_TOPIC_MAP.get(sid, [])
        sources.append(
            HQSource(
                id=sid,
                title=title,
                format=fmt,
                date=date,
                participants=participants,
                body=rest,
                topics=topics,
            )
        )
    return sorted(sources, key=lambda s: s.id)


def run_ingest() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    kb_text = _extract_pdf_text(FORA_DOCS / "Knowledge-Base.pdf")
    conv_text = _extract_pdf_text(FORA_DOCS / "Sample-Conversations.pdf")
    hq_text = _extract_pdf_text(FORA_DOCS / "HQ-Sources.pdf")

    articles = parse_articles(kb_text)
    conversations = parse_conversations(conv_text)
    hq_sources = parse_hq_sources(hq_text)

    ARTICLES_JSON.write_text(
        json.dumps([a.model_dump() for a in articles], indent=2), encoding="utf-8"
    )
    CONVERSATIONS_JSON.write_text(
        json.dumps([c.model_dump() for c in conversations], indent=2),
        encoding="utf-8",
    )
    HQ_SOURCES_JSON.write_text(
        json.dumps([h.model_dump() for h in hq_sources], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(articles)} articles, {len(conversations)} conversations, {len(hq_sources)} HQ sources")


if __name__ == "__main__":
    run_ingest()
