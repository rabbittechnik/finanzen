"""Gemeinsame Download-UI: nur Dateien unter DATA_DIR (kein Path-Traversal)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from config import DATA_DIR


def resolve_downloadable_path(stored_path: str | None) -> Path | None:
    """
    Liefert einen lesbaren Dateipfad nur wenn:
    - Pfad nicht leer
    - Datei existiert
    - aufgelöster Pfad liegt unter DATA_DIR
    """
    sp = (stored_path or "").strip()
    if not sp:
        return None
    raw = Path(sp).expanduser()
    try:
        base = DATA_DIR.resolve()
    except (OSError, RuntimeError):
        return None
    try:
        candidate = (raw if raw.is_absolute() else (DATA_DIR / raw)).resolve()
    except (OSError, RuntimeError):
        return None
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def render_document_download(doc: dict[str, Any], *, key_prefix: str) -> None:
    """Original-PDF (bzw. gespeicherte Datei) als Download anbieten."""
    did = int(doc["id"])
    path = resolve_downloadable_path(doc.get("stored_path"))
    if path is None:
        sp = (doc.get("stored_path") or "").strip()
        if not sp:
            st.caption("Kein Dateipfad gespeichert.")
        else:
            st.caption("Datei nicht verfügbar oder liegt außerhalb des Datenordners.")
        return
    try:
        data = path.read_bytes()
    except OSError:
        st.warning("Datei konnte nicht gelesen werden.")
        return
    fn = doc.get("original_filename") or path.name
    mime = "application/pdf" if str(fn).lower().endswith(".pdf") else "application/octet-stream"
    st.download_button(
        "Original herunterladen",
        data=data,
        file_name=fn,
        mime=mime,
        key=f"{key_prefix}_dl_{did}",
        use_container_width=True,
    )
