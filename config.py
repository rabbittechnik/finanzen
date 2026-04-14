"""App configuration. Override via environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _default_data_dir() -> Path:
    """
    Lokal: ./data unter dem Projektordner.
    Railway: Standard ist das gemountete Volume ``/dokumente`` (bleibt bei Deploys/Upgrades erhalten),
    sofern ``DOCU_DATA_DIR`` nicht gesetzt ist.
    """
    if os.environ.get("DOCU_DATA_DIR"):
        return Path(os.environ["DOCU_DATA_DIR"])
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
        return Path("/dokumente")
    return BASE_DIR / "data"


DATA_DIR = _default_data_dir()
INBOX_DIR = DATA_DIR / "inbox"
ARCHIVE_DIR = DATA_DIR / "archive"
DB_PATH = Path(os.environ.get("DOCU_DB_PATH", str(DATA_DIR / "documents.db")))

# Text sent to LLM (characters). Full text stays local in SQLite.
LLM_TEXT_CHAR_LIMIT = int(os.environ.get("DOCU_LLM_CHAR_LIMIT", "12000"))

OPENAI_MODEL = os.environ.get("DOCU_OPENAI_MODEL", "gpt-4o-mini")

for d in (DATA_DIR, INBOX_DIR, ARCHIVE_DIR):
    d.mkdir(parents=True, exist_ok=True)
