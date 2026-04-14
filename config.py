"""App configuration. Override via environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
# Avatar für den Assistenten „Lumo“ (PNG). Datei `static/lumo.png` im Projekt ablegen oder DOCU_LUMO_AVATAR setzen.
LUMO_AVATAR_PATH = Path(os.environ.get("DOCU_LUMO_AVATAR", str(STATIC_DIR / "lumo.png")))


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

# Zwei-Phasen-Extraktion: bei sehr langem Text zuerst KI-Zusammenfassung (Anfang/Mitte/Ende), dann JSON-Extraktion.
LLM_TWO_PHASE = os.environ.get("DOCU_LLM_TWO_PHASE", "").strip().lower() in ("1", "true", "yes")

# KI-Extraktion (Dokumente) und — sofern nicht DOCU_CHAT_MODEL gesetzt — der Chat nutzen dasselbe Modell.
OPENAI_MODEL = os.environ.get("DOCU_OPENAI_MODEL", "gpt-4o-mini")

for d in (DATA_DIR, INBOX_DIR, ARCHIVE_DIR):
    d.mkdir(parents=True, exist_ok=True)
