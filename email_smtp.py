"""Optionaler E-Mail-Versand per SMTP (nur nach expliziter Nutzeraktion in der UI).

Typischer Anbieter **Gmail**: ``DOCU_SMTP_HOST=smtp.gmail.com``, Port ``587``,
``DOCU_SMTP_USER`` / ``DOCU_SMTP_FROM`` = Gmail-Adresse, ``DOCU_SMTP_PASSWORD`` = Google-**App-Passwort**
(nicht das normale Anmeldepasswort). Siehe README.

Viele Hosting-Umgebungen haben keinen IPv6-Egress; ``smtplib`` wählt sonst oft zuerst IPv6,
was zu ``[Errno 101] Network is unreachable`` führt. Deshalb werden Zieladressen
standardmäßig **IPv4 vor IPv6** versucht. Optional: ``DOCU_SMTP_ADDRESS_FAMILY=ipv4`` nur IPv4.
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


def _smtp_sockaddr_candidates(host: str, port: int) -> list[tuple]:
    """Sockaddr-Tupel für TCP; IPv4 zuerst (reduziert ENETUNREACH ohne IPv6-Route)."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise OSError(f"SMTP: Hostname nicht auflösbar: {host!r}") from e
    v4 = [item[4] for item in infos if item[0] == socket.AF_INET]
    v6 = [item[4] for item in infos if item[0] == socket.AF_INET6]
    fam = (os.environ.get("DOCU_SMTP_ADDRESS_FAMILY") or "").strip().lower()
    if fam in ("4", "ipv4", "inet"):
        return v4 or v6
    if fam in ("6", "ipv6", "inet6"):
        return v6 or v4
    return v4 + v6


def _raise_smtp_unreachable(host: str, port: int, last: BaseException | None) -> None:
    hint = (
        "Häufig: Server hat keine IPv6-Route; die App versucht IPv4 zuerst. "
        "Falls es weiterhin scheitert: DOCU_SMTP_ADDRESS_FAMILY=ipv4 setzen oder "
        "SMTP-Port/Firewall beim Hosting prüfen (ausgehend 587/465)."
    )
    if isinstance(last, OSError) and last.errno == 101:
        raise OSError(
            f"SMTP: Netzwerk nicht erreichbar für {host!r}:{port}. {hint}"
        ) from last
    if last is not None:
        raise OSError(f"SMTP: Keine Verbindung zu {host!r}:{port}. {hint}") from last
    raise OSError(f"SMTP: Keine Adresse für {host!r}:{port}.")


def _reply_pair(conn: smtplib.SMTP) -> tuple[int, bytes | str]:
    """getreply() liefert (code, msg); bei Abweichungen klare Fehlermeldung statt ValueError."""
    raw = conn.getreply()
    if isinstance(raw, tuple) and len(raw) == 2:
        return raw[0], raw[1]
    raise OSError(f"SMTP: unerwartete Server-Antwort: {raw!r}")


def _header_email(addr: str) -> str:
    """Nur die E-Mail-Adresse für From/To (robust bei „Name <a@b>“ und fehlerhaften Parsern)."""
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

    to_raw = (to_addr or "").strip()
    to_norm = _header_email(to_raw)
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

    candidates = _smtp_sockaddr_candidates(host, port)
    if not candidates:
        raise OSError(f"SMTP: Keine TCP-Adresse für {host!r}:{port}.")

    last_err: BaseException | None = None
    context = ssl.create_default_context()

    if port == 465:
        for sockaddr in candidates:
            smtp_ssl: smtplib.SMTP_SSL | None = None
            plain: socket.socket | None = None
            try:
                plain = socket.create_connection(sockaddr, timeout=timeout)
                try:
                    tls_sock = context.wrap_socket(plain, server_hostname=host)
                except Exception:
                    try:
                        plain.close()
                    except OSError:
                        pass
                    raise
                plain = None
                try:
                    smtp_ssl = smtplib.SMTP_SSL(host="", port=0, context=context, timeout=timeout)
                except Exception:
                    try:
                        tls_sock.close()
                    except OSError:
                        pass
                    raise
                smtp_ssl._host = host
                smtp_ssl.sock = tls_sock
                smtp_ssl.file = tls_sock.makefile("rb")
                code, _intro = _reply_pair(smtp_ssl)
                if code != 220:
                    raise smtplib.SMTPConnectError(code, _intro)
                smtp_ssl.login(user, password)
                smtp_ssl.send_message(msg)
                try:
                    smtp_ssl.quit()
                except Exception:
                    pass
                smtp_ssl = None
                return
            except smtplib.SMTPAuthenticationError:
                if smtp_ssl is not None:
                    try:
                        smtp_ssl.close()
                    except OSError:
                        pass
                raise
            except OSError as e:
                last_err = e
            except smtplib.SMTPException as e:
                last_err = e
            finally:
                if plain is not None:
                    try:
                        plain.close()
                    except OSError:
                        pass
                if smtp_ssl is not None:
                    try:
                        smtp_ssl.close()
                    except OSError:
                        pass
        _raise_smtp_unreachable(host, port, last_err)
        return

    for sockaddr in candidates:
        smtp_plain: smtplib.SMTP | None = None
        try:
            smtp_plain = smtplib.SMTP(timeout=timeout)
            smtp_plain._host = host
            smtp_plain.sock = socket.create_connection(sockaddr, timeout=timeout)
            smtp_plain.file = smtp_plain.sock.makefile("rb")
            code, _intro = _reply_pair(smtp_plain)
            if code != 220:
                raise smtplib.SMTPConnectError(code, _intro)
            smtp_plain.ehlo()
            smtp_plain.starttls(context=context)
            smtp_plain.ehlo()
            smtp_plain.login(user, password)
            smtp_plain.send_message(msg)
            try:
                smtp_plain.quit()
            except Exception:
                pass
            smtp_plain = None
            return
        except smtplib.SMTPAuthenticationError:
            if smtp_plain is not None:
                try:
                    smtp_plain.close()
                except OSError:
                    pass
            raise
        except OSError as e:
            last_err = e
        except smtplib.SMTPException as e:
            last_err = e
        finally:
            if smtp_plain is not None:
                try:
                    smtp_plain.close()
                except OSError:
                    pass
    _raise_smtp_unreachable(host, port, last_err)
