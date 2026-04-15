"""E-Mail-Versand: bevorzugt Resend API (HTTPS), Fallback auf SMTP.

**Resend (empfohlen für Railway/Cloud):**
``DOCU_RESEND_API_KEY`` setzen, ``DOCU_SMTP_FROM`` als Absender.
Domain muss in Resend verifiziert sein. Kostenlos bis 3 000 Mails/Monat.

**SMTP (Fallback, z. B. lokal):**
``DOCU_SMTP_HOST``, ``DOCU_SMTP_USER``, ``DOCU_SMTP_PASSWORD``, ``DOCU_SMTP_FROM`` setzen.
Port 465 (SSL) oder 587 (STARTTLS). Optional: ``DOCU_SMTP_ADDRESS_FAMILY=ipv4``.
"""
from __future__ import annotations

import logging
import os
import re
import socket
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr

log = logging.getLogger(__name__)


def _resend_configured() -> bool:
    return bool((os.environ.get("DOCU_RESEND_API_KEY") or "").strip())


def _smtp_configured() -> bool:
    return bool(
        (os.environ.get("DOCU_SMTP_HOST") or "").strip()
        and (os.environ.get("DOCU_SMTP_USER") or "").strip()
        and (os.environ.get("DOCU_SMTP_PASSWORD") or "").strip()
        and (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    )


def smtp_configured() -> bool:
    """True wenn Resend ODER SMTP konfiguriert ist."""
    return _resend_configured() or _smtp_configured()


def _header_email(addr: str) -> str:
    """Nur die E-Mail-Adresse für From/To."""
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


# ---------------------------------------------------------------------------
# Resend (HTTPS, Port 443 — funktioniert auf Railway)
# ---------------------------------------------------------------------------

def _send_via_resend(*, to_addr: str, subject: str, body: str, from_addr: str) -> None:
    import resend

    api_key = (os.environ.get("DOCU_RESEND_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("DOCU_RESEND_API_KEY fehlt.")
    resend.api_key = api_key

    params: dict = {
        "from": from_addr,
        "to": [to_addr],
        "subject": subject or "(ohne Betreff)",
        "text": body or "",
    }
    result = resend.Emails.send(params)
    log.info("Resend OK: id=%s", result.get("id") if isinstance(result, dict) else result)


# ---------------------------------------------------------------------------
# SMTP (Fallback für lokale / Nicht-Railway-Umgebungen)
# ---------------------------------------------------------------------------

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


def _send_via_smtp(*, to_addr: str, subject: str, body: str, from_addr: str) -> None:
    host = (os.environ.get("DOCU_SMTP_HOST") or "").strip()
    user = (os.environ.get("DOCU_SMTP_USER") or "").strip()
    password = "".join((os.environ.get("DOCU_SMTP_PASSWORD") or "").split())
    port = int((os.environ.get("DOCU_SMTP_PORT") or "587").strip() or "587")
    timeout = float((os.environ.get("DOCU_SMTP_TIMEOUT") or "60").strip() or "60")
    if not (host and user and password):
        raise RuntimeError("SMTP nicht vollständig konfiguriert (DOCU_SMTP_*).")

    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(ohne Betreff)"
    msg["From"] = from_addr
    msg["To"] = to_addr
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


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def send_email_smtp(*, to_addr: str, subject: str, body: str) -> None:
    """Versendet eine E-Mail: Resend (wenn konfiguriert), sonst SMTP."""
    from_addr = (os.environ.get("DOCU_SMTP_FROM") or "").strip()
    if not from_addr:
        raise RuntimeError("DOCU_SMTP_FROM fehlt.")

    to_norm = _header_email(to_addr)
    from_norm = _header_email(from_addr)
    if not to_norm or "@" not in to_norm:
        raise ValueError("Ungültige Empfänger-Adresse.")
    if not from_norm or "@" not in from_norm:
        raise ValueError("Ungültige Absender-Adresse (DOCU_SMTP_FROM).")

    if _resend_configured():
        _send_via_resend(to_addr=to_norm, subject=subject, body=body, from_addr=from_norm)
    elif _smtp_configured():
        _send_via_smtp(to_addr=to_norm, subject=subject, body=body, from_addr=from_norm)
    else:
        raise RuntimeError(
            "E-Mail nicht konfiguriert. Entweder DOCU_RESEND_API_KEY (empfohlen) "
            "oder DOCU_SMTP_HOST/USER/PASSWORD/FROM setzen."
        )
