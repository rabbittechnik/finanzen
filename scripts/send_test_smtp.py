#!/usr/bin/env python3
"""Sendet eine Testmail über DOCU_SMTP_* (liest .env im Projektroot)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from email_smtp import send_email_smtp, smtp_configured  # noqa: E402


def main() -> None:
    if not smtp_configured():
        print("SMTP nicht konfiguriert: setze DOCU_SMTP_HOST, PORT, USER, PASSWORD, FROM in .env")
        sys.exit(1)
    import os

    to = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    if not to:
        print("Empfänger fehlt: python scripts/send_test_smtp.py empfaenger@example.com")
        sys.exit(1)
    send_email_smtp(
        to_addr=to,
        subject="Docu-Organizer — SMTP-Test",
        body="Dies ist eine automatische Testmail aus scripts/send_test_smtp.py",
    )
    print("Testmail gesendet an:", to)


if __name__ == "__main__":
    main()
