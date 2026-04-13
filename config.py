"""App configuration. Override via environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DOCU_DATA_DIR", str(BASE_DIR / "data")))
INBOX_DIR = DATA_DIR / "inbox"
ARCHIVE_DIR = DATA_DIR / "archive"
DB_PATH = Path(os.environ.get("DOCU_DB_PATH", str(DATA_DIR / "documents.db")))

# Text sent to LLM (characters). Full text stays local in SQLite.
LLM_TEXT_CHAR_LIMIT = int(os.environ.get("DOCU_LLM_CHAR_LIMIT", "12000"))

OPENAI_MODEL = os.environ.get("DOCU_OPENAI_MODEL", "gpt-4o-mini")

for d in (DATA_DIR, INBOX_DIR, ARCHIVE_DIR):
    d.mkdir(parents=True, exist_ok=True)
