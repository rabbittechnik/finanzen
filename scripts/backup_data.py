#!/usr/bin/env python3
"""
Sichert documents.db, den Posteingang (inbox/) und das Archiv (archive/) in eine ZIP-Datei.

Nutzt dieselbe Konfiguration wie die App (DOCU_DATA_DIR, DOCU_DB_PATH).

Beispiel:
  python scripts/backup_data.py
  python scripts/backup_data.py C:\\Backups\\docu_backup.zip
"""
from __future__ import annotations

import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from config import ARCHIVE_DIR, DATA_DIR, DB_PATH, INBOX_DIR  # noqa: E402


def _add_tree(zf: zipfile.ZipFile, root: Path, *, under: str) -> None:
    """Alle Dateien unter ``root`` mit Präfix ``under/`` in die ZIP legen."""
    if not root.exists():
        return
    prefix = under.strip("/").replace("\\", "/")
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root)
            rel_s = str(rel).replace("\\", "/")
            arc = f"{prefix}/{rel_s}" if prefix else rel_s
            zf.write(p, arcname=arc)


def main() -> None:
    default_name = "backup_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".zip"
    dest = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path(default_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.is_file():
            zf.write(DB_PATH, arcname="documents.db")
        _add_tree(zf, ARCHIVE_DIR, under="archive")
        _add_tree(zf, INBOX_DIR, under="inbox")
    print(f"Backup geschrieben: {dest.resolve()}")


if __name__ == "__main__":
    main()
