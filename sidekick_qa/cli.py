"""CLI for Sidekick QA pipeline."""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sidekick QA RAG pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Parse PDFs to data/processed/")
    sub.add_parser("index", help="Build Chroma vector index")
    p_audit = sub.add_parser("audit", help="Run full conversation audit")
    p_audit.add_argument("--clear-cache", action="store_true")
    p_audit.add_argument("--rules-only", action="store_true", help="Skip LLM; use rule-based audit")
    sub.add_parser("export", help="Generate issue log, patterns, updated KB")

    args = parser.parse_args()

    if args.command == "ingest":
        from sidekick_qa.ingest.pdf_parser import run_ingest

        run_ingest()
    elif args.command == "index":
        from sidekick_qa.index.build_index import build_index

        build_index(api_key=os.environ.get("OPENAI_API_KEY"))
    elif args.command == "audit":
        from sidekick_qa.evaluate.auditor import run_full_audit
        from sidekick_qa.remediate.exports import init_review_queue, write_issue_log
        from sidekick_qa.remediate.kb_patcher import write_updated_kb
        from sidekick_qa.remediate.patterns import write_pattern_analysis

        audits = run_full_audit(
            clear_cache=args.clear_cache,
            rules_only=args.rules_only,
        )
        init_review_queue(audits)
        write_issue_log(audits)
        write_pattern_analysis(audits)
        write_updated_kb()
        print("Audit complete. Outputs in outputs/")
    elif args.command == "export":
        import json

        from sidekick_qa.config import AUDIT_CACHE
        from sidekick_qa.evaluate.auditor import ConversationAudit
        from sidekick_qa.remediate.exports import write_issue_log
        from sidekick_qa.remediate.kb_patcher import write_updated_kb
        from sidekick_qa.remediate.patterns import write_pattern_analysis

        audits = []
        if AUDIT_CACHE.exists():
            for line in AUDIT_CACHE.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    audits.append(ConversationAudit(**json.loads(line)))
        write_issue_log(audits)
        write_pattern_analysis(audits)
        write_updated_kb()
        print("Exported deliverables to outputs/")


if __name__ == "__main__":
    main()
