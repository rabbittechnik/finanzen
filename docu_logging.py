"""Einfache strukturierte Ereignisse für Railway / DOCU_JSON_LOGS."""
from __future__ import annotations

import json
import logging
from typing import Any

_logger = logging.getLogger("docu")


def log_event(event: str, **fields: Any) -> None:
    """Eine Zeile JSON (sinnvoll wenn Root-Logging JSON-Formatter nutzt)."""
    try:
        line = json.dumps({"event": event, **fields}, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        line = json.dumps({"event": event, "msg": str(fields)}, ensure_ascii=False)
    _logger.info(line)


def log_openai_error(where: str, err: BaseException) -> None:
    log_event("openai_error", where=where, err_type=type(err).__name__, err=str(err))
