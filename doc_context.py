"""Dokument-Kontext (Haushalt / Person) — zentral für Filter ohne Zirkelimporte."""
from __future__ import annotations

from typing import Any


def normalize_docu_context_key(raw: str | None) -> str:
    r = (raw or "all").strip()
    if r.startswith("household:"):
        return "household"
    return r


def filter_documents_by_context(
    rows: list[dict[str, Any]], context_key: str | None
) -> list[dict[str, Any]]:
    ck = normalize_docu_context_key(context_key)
    if ck in ("all", "household"):
        return rows
    if ck.startswith("person:"):
        pid = int(ck.split(":", 1)[1])
        return [
            r
            for r in rows
            if (r.get("owner_kind") or "") == "person"
            and int(r.get("owner_person_id") or 0) == pid
        ]
    return rows
