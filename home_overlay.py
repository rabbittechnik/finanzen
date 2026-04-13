"""Start-Overlay (Modal) pro Browser-Session; Inhalt aus home_overlay.md."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from privacy_notes import PRIVACY_UI_DE

_OVERLAY_MD = Path(__file__).resolve().parent / "home_overlay.md"
_SESSION_KEY = "home_overlay_dismissed"

_DEFAULT_BODY = """
## Dokumenten-Organizer

Willkommen. Legen Sie PDFs im Posteingang ab, importieren Sie sie und nutzen Sie optional die KI-Analyse.
Details zum Datenschutz finden Sie unten in der Kurzfassung oder in der Sidebar.
""".strip()


def _overlay_markdown() -> str:
    if _OVERLAY_MD.is_file():
        text = _OVERLAY_MD.read_text(encoding="utf-8").strip()
        if text:
            return text
    return _DEFAULT_BODY


def _mark_overlay_dismissed() -> None:
    st.session_state[_SESSION_KEY] = True


def _overlay_dismiss_callback() -> None:
    _mark_overlay_dismissed()


@st.dialog("Willkommen", width="large", on_dismiss=_overlay_dismiss_callback)
def _home_overlay_dialog() -> None:
    st.markdown(_overlay_markdown())
    with st.expander("Datenschutz (Kurzfassung)"):
        st.markdown(PRIVACY_UI_DE)
    if st.button("Verstanden, weiter", type="primary", use_container_width=True):
        _mark_overlay_dismissed()
        st.rerun()


def maybe_show_home_overlay() -> None:
    if st.session_state.get(_SESSION_KEY):
        return
    _home_overlay_dialog()
