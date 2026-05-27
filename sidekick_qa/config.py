"""Configuration and paths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORA_DOCS = ROOT / "fora_docs"
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "chroma"
OUTPUTS_DIR = ROOT / "outputs"

ARTICLES_JSON = PROCESSED_DIR / "articles.json"
CONVERSATIONS_JSON = PROCESSED_DIR / "conversations.json"
HQ_SOURCES_JSON = PROCESSED_DIR / "hq_sources.json"

AUDIT_CACHE = OUTPUTS_DIR / "audit_cache.jsonl"
ISSUE_LOG_CSV = OUTPUTS_DIR / "issue_log.csv"
PATTERN_ANALYSIS = OUTPUTS_DIR / "pattern_analysis.md"
REVIEW_QUEUE = OUTPUTS_DIR / "review_queue.json"
UPDATED_KB_DIR = OUTPUTS_DIR / "updated_kb"

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K = 8
CONFIDENCE_THRESHOLD = 0.75

OUTDATED_ARTICLES = {2, 4, 9, 10}
