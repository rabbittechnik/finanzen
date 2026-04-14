"""Optional HTTP Basic Auth vor der Streamlit-ASGI-App (DOCU_BASIC_AUTH_*)."""
from __future__ import annotations

import base64
import os
from typing import Any, Awaitable, Callable

Send = Callable[[dict[str, Any]], Awaitable[None]]


class BasicAuthASGI:
    """ASGI-3-Wrapper: schützt alle Routen, wenn Nutzername und Passwort gesetzt sind."""

    def __init__(self, app: Any, username: str, password: str) -> None:
        self.app = app
        self.username = username
        self.password = password

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw_headers = scope.get("headers") or []
        auth_val = ""
        for k, v in raw_headers:
            if k.lower() == b"authorization":
                auth_val = v.decode("latin-1", errors="replace")
                break
        if self._authorized(auth_val):
            await self.app(scope, receive, send)
            return
        await self._send401(send)

    def _authorized(self, header: str) -> bool:
        if not header.startswith("Basic "):
            return False
        try:
            raw = base64.b64decode(header[6:].strip()).decode("utf-8")
            u, _, p = raw.partition(":")
            return u == self.username and p == self.password
        except Exception:
            return False

    async def _send401(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"www-authenticate", b'Basic realm="Docu Organizer"'),
                    (b"content-type", b"text/plain; charset=utf-8"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Unauthorized"})


def wrap_basic_auth_if_configured(inner: Any) -> Any:
    user = (os.environ.get("DOCU_BASIC_AUTH_USER") or "").strip()
    pw = (os.environ.get("DOCU_BASIC_AUTH_PASSWORD") or "").strip()
    if user and pw:
        return BasicAuthASGI(inner, user, pw)
    return inner
