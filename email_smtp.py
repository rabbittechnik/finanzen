"""Optionaler E-Mail-Versand per SMTP (nur nach expliziter Nutzeraktion in der UI).

Typischer Anbieter **Gmail**: ``DOCU_SMTP_HOST=smtp.gmail.com``, Port ``587``,
``DOCU_SMTP_USER`` / ``DOCU_SMTP_FROM`` = Gmail-Adresse, ``DOCU_SMTP_PASSWORD`` = Google-**App-Passwort**
(nicht das normale Anmeldepasswort). Siehe README.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_configured() -> bool:
    return bool(
        (os.environ.get("DOCU_SMTP_HOST") or "").strip()
        and (os.environ.get("DOCU_SMTP_USER") or "").strip()
        and (os.environ.get("DOCU_SMTP_PASSWORD") or "").strip()
        and (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    )


def send_email_smtp(*, to_addr: str, subject: str, body: str) -> None:
    """Versendet eine einfache Text-Mail (TLS/STARTTLS je nach Port)."""
    host = (os.environ.get("DOCU_SMTP_HOST") or "").strip()
    user = (os.environ.get("DOCU_SMTP_USER") or "").strip()
    # Gmail-App-Passwörter werden oft mit Leerzeichen gruppiert — für SMTP ohne Spaces verwenden.
    password = "".join((os.environ.get("DOCU_SMTP_PASSWORD") or "").split())
    from_addr = (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    port = int((os.environ.get("DOCU_SMTP_PORT") or "587").strip() or "587")
    if not (host and user and password and from_addr):
        raise RuntimeError("SMTP nicht vollständig konfiguriert (DOCU_SMTP_*).")

    to_addr = (to_addr or "").strip()
    if not to_addr or "@" not in to_addr:
        raise ValueError("Ungültige Empfänger-Adresse.")

    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(ohne Betreff)"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body or "")

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.ehlo()
        context = ssl.create_default_context()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)
