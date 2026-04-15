"""Optionaler E-Mail-Versand per SMTP (nur nach expliziter Nutzeraktion in der UI).

Typischer Anbieter **Gmail**: ``DOCU_SMTP_HOST=smtp.gmail.com``, Port ``587``,
``DOCU_SMTP_USER`` / ``DOCU_SMTP_FROM`` = Gmail-Adresse, ``DOCU_SMTP_PASSWORD`` = Google-**App-Passwort**
(nicht das normale Anmeldepasswort). Siehe README.

``socket.create_connection`` versucht automatisch alle Adressen (IPv4 + IPv6) und fällt bei
Fehlschlag auf die nächste zurück. Optional: ``DOCU_SMTP_ADDRESS_FAMILY=ipv4`` erzwingt nur IPv4.
"""
from __future__ import annotations

import os
import re
import socket
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr


def smtp_configured() -> bool:
    return bool(
        (os.environ.get("DOCU_SMTP_HOST") or "").strip()
        and (os.environ.get("DOCU_SMTP_USER") or "").strip()
        and (os.environ.get("DOCU_SMTP_PASSWORD") or "").strip()
        and (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    )


def _header_email(addr: str) -> str:
    """Nur die E-Mail-Adresse für From/To (robust bei „Name <a@b>" und fehlerhaften Parsern)."""
    s = (addr or "").strip()
    if not s:
        return ""
    try:
        parsed = parseaddr(s)
    except Exception:
        parsed = ("", "")
    if isinstance(parsed, tuple) and len(parsed) == 2:
        mail = (parsed[1] or "").strip()
        if mail and "@" in mail:
            return mail
    m = re.search(r"<([^<>@]+@[^<>@]+)>", s)
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", s)
    return m.group(1).strip() if m else s


def _resolve_smtp_host(host: str, port: int) -> str:
    """Bei DOCU_SMTP_ADDRESS_FAMILY=ipv4/ipv6 zur passenden IP-Adresse auflösen."""
    fam = (os.environ.get("DOCU_SMTP_ADDRESS_FAMILY") or "").strip().lower()
    family = None
    if fam in ("4", "ipv4", "inet"):
        family = socket.AF_INET
    elif fam in ("6", "ipv6", "inet6"):
        family = socket.AF_INET6
    if family is None:
        return host
    try:
        infos = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except socket.gaierror:
        pass
    return host


def send_email_smtp(*, to_addr: str, subject: str, body: str) -> None:
    """Versendet eine einfache Text-Mail (TLS/STARTTLS je nach Port)."""
    host = (os.environ.get("DOCU_SMTP_HOST") or "").strip()
    user = (os.environ.get("DOCU_SMTP_USER") or "").strip()
    # Gmail-App-Passwörter werden oft mit Leerzeichen gruppiert — für SMTP ohne Spaces verwenden.
    password = "".join((os.environ.get("DOCU_SMTP_PASSWORD") or "").split())
    from_addr = (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    port = int((os.environ.get("DOCU_SMTP_PORT") or "587").strip() or "587")
    timeout = float((os.environ.get("DOCU_SMTP_TIMEOUT") or "60").strip() or "60")
    if not (host and user and password and from_addr):
        raise RuntimeError("SMTP nicht vollständig konfiguriert (DOCU_SMTP_*).")

    to_norm = _header_email(to_addr)
    from_norm = _header_email(from_addr)
    if not to_norm or "@" not in to_norm:
        raise ValueError("Ungültige Empfänger-Adresse.")
    if not from_norm or "@" not in from_norm:
        raise ValueError("Ungültige Absender-Adresse (DOCU_SMTP_FROM).")

    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(ohne Betreff)"
    msg["From"] = from_norm
    msg["To"] = to_norm
    msg.set_content(body or "")

    context = ssl.create_default_context()
    connect_host = _resolve_smtp_host(host, port)

    if port == 465:
        with smtplib.SMTP_SSL(connect_host, port, context=context, timeout=timeout) as conn:
            if connect_host != host:
                conn._host = host
            conn.login(user, password)
            conn.send_message(msg)
    else:
        with smtplib.SMTP(connect_host, port, timeout=timeout) as conn:
            if connect_host != host:
                conn._host = host
            conn.starttls(context=context)
            conn.login(user, password)
            conn.send_message(msg)
