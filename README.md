# Sidekick QA Framework

Operational RAG pipeline to audit Fora Sidekick advisor responses on group bookings, categorize issues, propose KB fixes, and route work to Tour Ops, Booking Platform, and Support.

## Architecture

```
PDFs (fora_docs/) → ingest → data/processed/*.json
                              ↓
                    Chroma + OpenAI embeddings
                              ↓
         50 conversations → retrieve (KB + HQ + Article 1) → GPT-4o-mini audit
                              ↓
              outputs/: issue_log.csv, pattern_analysis.md, updated_kb/
```

**Deliverables:** Streamlit app (D1) · `outputs/` artifacts (D2) · this README runbook (D3).

## Prerequisites

- Python 3.9+
- OpenAI API key (for embeddings + LLM audit; `--rules-only` works without LLM calls)
- Optional: [Streamlit Community Cloud](https://streamlit.io/cloud) for a shareable URL

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Parse PDFs once (or use committed data/processed/)
python -m sidekick_qa.cli ingest

# Secrets
cp secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml → OPENAI_API_KEY = "sk-..."
```

## Run start-to-finish

| Step | Command / action |
|------|------------------|
| 1. Ingest | `python -m sidekick_qa.cli ingest` |
| 2. Index | `python -m sidekick_qa.cli index` |
| 3. Audit | `python -m sidekick_qa.cli audit` (add `--rules-only` if no API key) |
| 4. UI | `streamlit run app.py` → **Run Audit** tab → review **Review Queue** → download CSV |
| 5. Re-export | `python -m sidekick_qa.cli export` after human overrides |

**Outputs (Deliverable 2):**

| File | Description |
|------|-------------|
| `outputs/issue_log.csv` | `conversation_id`, `issue_description`, `proposed_fix` |
| `outputs/pattern_analysis.md` | Top systemic patterns |
| `outputs/updated_kb/article_01.md` … `article_10.md` | Remediated articles |
| `outputs/review_queue.json` | Human review state |

## AI vs human

| AI | Human |
|----|-------|
| Chunk/index KB + HQ sources | Approve or edit flagged rows in Review Queue |
| Retrieve context per conversation | Resolve KB vs HQ conflicts |
| Classify verdict, severity, issue type | Prioritize P0–P3 fixes |
| Propose article updates | Calibrate rubric over time |
| Generate pattern analysis | Sign off on CHANGELOG assumptions |

**Review when:** `confidence < 0.75`, `needs_expert_review`, or KB/HQ conflict (e.g., wedding attrition judgment).

## Key decision points

1. **pass** — Response matches Article 1 / HQ and is complete enough.
2. **issue** — Wrong numbers, outdated cited article, harmful omission, or overconfidence.
3. **unanswerable_ok** — Correct deferral when KB lacks data (e.g., Japan pricing).
4. **needs_expert_review** — Ambiguous tradeoffs; do not auto-log as defect until reviewed.

**Source hierarchy:** HQ expert sources → Article 1 (Source of Truth) → current articles → outdated articles (2, 4, 9, 10).

## Streamlit Cloud deploy

1. Push repo to GitHub.
2. [share.streamlit.io](https://share.streamlit.io) → New app → point to `app.py`.
3. **Secrets:** `OPENAI_API_KEY`
4. Ensure `data/processed/` is committed; index builds on first **Run Audit**.

## In-person session prep

1. Open app → select conversation by ID.
2. Re-run audit with updated `outputs/updated_kb/` indexed after KB edits.
3. Use **Collaboration** tab to filter by team for stakeholder handoffs.

## Project layout

- `sidekick_qa/` — pipeline (ingest, index, evaluate, remediate)
- `app.py` — Streamlit UI
- `fora_docs/` — case study PDFs
- `data/processed/` — structured JSON
- `outputs/` — generated deliverables
