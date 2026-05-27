"""Generate updated knowledge base articles."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sidekick_qa.config import ARTICLES_JSON, HQ_SOURCES_JSON, OUTDATED_ARTICLES, UPDATED_KB_DIR
from sidekick_qa.models import Article, HQSource

BANNER = (
    "> **Editorial note:** Sections below were updated during Sidekick QA remediation. "
    "Canonical policy lives in Article 1 (Source of Truth). Assumptions flagged in CHANGELOG.\n\n"
)

ARTICLE_1_ADDENDUM = """
## Operational addendum (HQ sources, Jan 2026)

**Hyatt group program:** Standard properties 10% commission (up from 7%); luxury collection 12%; +1% bonus for 25+ room groups. Wedding/corporate blocks: 25% attrition; social groups: 30%. See HQ Source 3.

**TC credits:** Credits may be split across redemption types (e.g., one for group event, two converted to commission ~$800–1200 each). Confirm allocation 60–90 days before sailing with cruise line coordinator. See HQ Source 2.

**Wedding comp ratios:** 1:40 is standard but negotiable (often 1:30 at luxury properties). With 35 rooms at 1:30, one comp room is achievable. See HQ Source 1.
"""

PATCHES: dict[int, list[tuple[str, str]]] = {
    2: [
        (r"Hotels:\s*8\+ rooms", "Hotels: 10+ rooms"),
        (r"Cruises:\s*5\+ cabins", "Cruises: 8+ staterooms"),
        (r"groups of 8-15 people", "groups of 10-15 people"),
        (r"15-20% below your block size", "20-30% attrition (group must fill 70-80% of block)"),
        (r"typical attrition.*?15-20%", "typical attrition is 20-30%"),
    ],
    4: [
        (r"Recommended:\s*15% attrition", "Recommended: 20-25% attrition for weddings (see Article 1; do not push 15% aggressively)"),
        (r"Recommended:\s*15-18% attrition", "Recommended: 20-25% attrition for corporate groups"),
        (r"Recommended:\s*12-15% attrition", "Recommended: 18-22% attrition"),
        (r"Industry standard:\s*15-20% attrition", "Industry standard: 20-30% attrition (per Article 1)"),
        (r"Lower attrition = Better rates", "Lower attrition may result in higher room rates or fewer concessions—not always 'better rates'"),
        (r"Push for lower attrition.*?when:", "Push for lower attrition only when group is highly committed AND expert-approved:"),
        (r"Aim for 15% attrition as a starting point", "Aim for 20-30% attrition unless expert guidance says otherwise"),
    ],
    9: [
        (r"Hyatt.*?7%|7%.*?Hyatt", "Hyatt standard properties: 10% (enhanced program Jan 2026)"),
        (r"8-10% commission", "10-12% commission (verify current Hyatt group program)"),
        (r"Major chains.*?7-8%", "Major chains: typically 7-10% (Hyatt enhanced program: 10-12%)"),
    ],
    10: [
        (r"DMCs:\s*10-15% commission", "DMCs: 10-12% commission (custom itineraries; consider service fees)"),
        (r"Tour operators:\s*15-18% commission", "Tour operators: 16-18% on land packages"),
    ],
}

ARTICLE_8_ADDENDUM = """
### TC credit splitting (HQ Source 2)

Advisors may allocate TC credits across redemption types on the same sailing—for example, one credit for a group event (~$800 value) and two converted to additional commission (~$800–1200 each, varies by line). Confirm final cabin count before committing; redemption forms due 60–90 days pre-sailing.
"""

ARTICLE_3_ADDENDUM = """
### Comp room negotiation

Standard ratio is 1:40, but hotels—especially for weddings at luxury properties—may negotiate to 1:30 or 1:25. A 35-room block at 1:30 yields one comp room. See HQ Source 1.
"""


def _load_articles() -> list[Article]:
    return [Article(**a) for a in json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))]


def _load_hq() -> list[HQSource]:
    return [HQSource(**h) for h in json.loads(HQ_SOURCES_JSON.read_text(encoding="utf-8"))]


def patch_article(article: Article) -> str:
    body = article.body
    if article.id in PATCHES:
        for pattern, repl in PATCHES[article.id]:
            body = re.sub(pattern, repl, body, flags=re.IGNORECASE)
        body = BANNER + body

    if article.id == 1:
        body = body + ARTICLE_1_ADDENDUM
    elif article.id == 3:
        body = body + ARTICLE_3_ADDENDUM
    elif article.id == 8:
        body = body + ARTICLE_8_ADDENDUM
    elif article.id == 10:
        body += (
            "\n\n### Japan / custom groups (HQ Source 4)\n\n"
            "For custom incentive trips (e.g., 25-person Japan), consider: full DMC ($4,500–5,500/person, 10–12% commission + service fee), "
            "tour operator package ($3,500–4,000/person, 16–18%), or hybrid (TO for Tokyo/Kyoto + DMC for onsen, ~$4,000–4,200/person). "
            "Lead time critical for peak season (e.g., cherry blossom).\n"
        )

    if article.id in OUTDATED_ARTICLES:
        body = (
            f"> **Status:** This article was marked outdated. Critical thresholds aligned to Article 1.\n\n"
            + body
        )

    header = f"# Article {article.id}: {article.title}\n\n"
    meta = f"*Published: {article.published} | Status: {article.status}*\n\n"
    return header + meta + body


def write_updated_kb() -> Path:
    UPDATED_KB_DIR.mkdir(parents=True, exist_ok=True)
    articles = _load_articles()
    changelog_lines = [
        "# KB Remediation CHANGELOG",
        "",
        "Updates applied systematically from Article 1 + HQ sources during QA remediation.",
        "",
        "## Articles modified",
    ]

    for article in articles:
        content = patch_article(article)
        out_path = UPDATED_KB_DIR / f"article_{article.id:02d}.md"
        out_path.write_text(content, encoding="utf-8")
        if article.id in OUTDATED_ARTICLES or article.id in (1, 3, 8, 10):
            changelog_lines.append(f"- Article {article.id}: patched")

    changelog_lines.extend(
        [
            "",
            "## Assumptions for expert review",
            "- Wedding attrition 'best' rate varies by property and client risk tolerance (Conv 50).",
            "- Hyatt program terms apply to bookings Jan 2025+ per HQ email.",
            "- TC credit dollar amounts vary by cruise line and sailing.",
            "",
        ]
    )
    (UPDATED_KB_DIR / "CHANGELOG.md").write_text("\n".join(changelog_lines), encoding="utf-8")
    return UPDATED_KB_DIR
