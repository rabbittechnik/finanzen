"""Finanz-UI: linke Spalte (Navigation + LUMO + Werkzeuge), Hauptbereich in app.py."""
from __future__ import annotations

import json
import os
from typing import Any, Callable

import streamlit as st

from config import LLM_TEXT_CHAR_LIMIT, LUMO_AVATAR_PATH
from db import (
    get_document,
    get_extraction,
    list_archived_documents,
    list_documents,
    list_persons,
    list_reference_key_clusters,
    set_document_archived,
)
from doc_context import filter_documents_by_context, normalize_docu_context_key
from email_smtp import send_email_smtp, smtp_configured
from import_jobs import import_one_pdf
from ingest import save_uploaded_pdf_to_inbox
from nav_logic import NAV_KEYS_ORDER, NAV_LABELS
from organizer_chat import SYSTEM_PROMPT, run_organizer_chat
from privacy_notes import PRIVACY_UI_DE


def _lumo_avatar_chat() -> str:
    try:
        p = LUMO_AVATAR_PATH.resolve()
        if p.is_file():
            return str(p)
    except OSError:
        pass
    return "\u2728"


def _trim_chat(msgs: list[dict[str, Any]], *, keep_non_system: int = 28) -> list[dict[str, Any]]:
    sys = [m for m in msgs if m.get("role") == "system"]
    rest = [m for m in msgs if m.get("role") != "system"]
    return sys + rest[-keep_non_system:]


def _ensure_chat() -> None:
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]


def _apply_chat_effects(effects: list[dict[str, Any]]) -> None:
    for eff in effects:
        if eff.get("action") != "show_document":
            continue
        did = int(eff["document_id"])
        dev = str(eff.get("target_device") or "pc").lower()
        doc = get_document(did)
        if not doc:
            continue
        ext = get_extraction(did)
        nf = "home"
        if ext and (ext.get("nav_folder") or "").strip() in NAV_KEYS_ORDER:
            nf = str(ext.get("nav_folder")).strip()
        st.session_state["current_nav"] = nf
        st.session_state["fin_nav_radio"] = nf
        st.session_state["jump_doc_id"] = did
        if dev == "tv":
            st.session_state["docu_pending_device_hint"] = (
                "**Ausgabe TV:** Dokument ist hier vorgewählt. Auf dem Fernseher dieselbe App öffnen und "
                f"**Dokument #{did}** unter **{NAV_LABELS.get(nf, nf)}** ansteuern."
            )
        elif dev == "tablet":
            st.session_state["docu_pending_device_hint"] = (
                f"**Ausgabe Tablet:** Dokument **#{did}** ist auf diesem Gerät vorgewählt — auf dem Tablet "
                "dieselbe Ansicht öffnen."
            )


def _doc_ctx() -> str:
    return normalize_docu_context_key(str(st.session_state.get("docu_context_key") or "household"))


def _family_options() -> tuple[list[str], dict[str, str]]:
    """Interne Keys zu Anzeige (ASCII-freundlich; erweiterbar)."""
    opts: list[tuple[str, str]] = [
        ("household", "[HH] Gesamter Haushalt"),
    ]
    for p in list_persons():
        pid = int(p["id"])
        name = str(p.get("name") or f"Person {pid}")
        role = (p.get("role") or "").strip()
        tag = "[P]"
        if role:
            rl = role.lower()
            if any(x in rl for x in ("kind", "sohn", "tochter")):
                tag = "[Kind]"
            elif any(x in rl for x in ("partner", "gefährt", "freund", "freundin")):
                tag = "[Partner]"
        label = f"{tag} {name}"
        if role:
            label = f"{label} ({role})"
        opts.append((f"person:{pid}", label))
    keys = [k for k, _ in opts]
    labels = {k: lab for k, lab in opts}
    return keys, labels


def render_global_header_bar(
    *,
    apply_import_owner: Callable[[int], None],
    enqueue_payment: Callable[[int], None],
) -> None:
    """Volle Breite: Titel, PDF-Upload, Familie/Jahr/Monat, Aktualisieren."""
    keys, labels_map = _family_options()
    cur = _doc_ctx()
    if cur == "all":
        cur = "household"
        st.session_state.docu_context_key = "household"
    if cur not in keys:
        cur = keys[0]
        st.session_state.docu_context_key = cur
    idx = keys.index(cur)

    from datetime import date as _date

    t = _date.today()
    if "fin_ctx_year" not in st.session_state:
        st.session_state.fin_ctx_year = t.year
    if "fin_ctx_month" not in st.session_state:
        st.session_state.fin_ctx_month = t.month

    y_opts = list(range(2000, 2101))
    fy = int(st.session_state.fin_ctx_year)
    fm = int(st.session_state.fin_ctx_month)
    y_idx = min(max(0, fy - 2000), len(y_opts) - 1)

    _months = (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    )
    m_opts = list(range(1, 13))

    try:
        _hdr = st.container(border=True)
    except TypeError:
        _hdr = st.container()
    with _hdr:
        _render_global_header_inner(
            keys=keys,
            labels_map=labels_map,
            idx=idx,
            y_opts=y_opts,
            y_idx=y_idx,
            _months=_months,
            m_opts=m_opts,
            fm=fm,
            apply_import_owner=apply_import_owner,
            enqueue_payment=enqueue_payment,
        )


def _render_global_header_inner(
    *,
    keys: list[str],
    labels_map: dict[str, str],
    idx: int,
    y_opts: list[int],
    y_idx: int,
    _months: tuple[str, ...],
    m_opts: list[int],
    fm: int,
    apply_import_owner: Callable[[int], None],
    enqueue_payment: Callable[[int], None],
) -> None:
    la, lb, lc, ld, le, lf = st.columns([1.35, 1.5, 1.55, 0.52, 0.72, 0.62], gap="small")
    with la:
        st.markdown(
            '<p class="fin-header-title">Finanzen – Dokumenten-Organizer</p>',
            unsafe_allow_html=True,
        )
    with lb:
        st.markdown('<p class="fin-top-field-label">PDF (max. 200MB)</p>', unsafe_allow_html=True)
    with lc:
        st.markdown('<p class="fin-top-field-label">Familie / Kontext</p>', unsafe_allow_html=True)
    with ld:
        st.markdown('<p class="fin-top-field-label">Jahr</p>', unsafe_allow_html=True)
    with le:
        st.markdown('<p class="fin-top-field-label">Monat</p>', unsafe_allow_html=True)
    with lf:
        st.markdown('<p class="fin-top-field-label">Aktualisieren</p>', unsafe_allow_html=True)

    ca, cb, cc, cd, ce, cf = st.columns(
        [1.35, 1.5, 1.55, 0.52, 0.72, 0.62],
        gap="small",
        vertical_alignment="bottom",
    )
    with ca:
        st.markdown('<span class="fin-header-title-gap"></span>', unsafe_allow_html=True)
    with cb:
        up = st.file_uploader(
            "PDF",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="fin_pdf_up",
        )
        auto_import = st.checkbox(
            "Sofort einlesen",
            value=True,
            key="fin_pdf_auto",
        )
        if up and st.button("Upload starten", type="primary", key="fin_pdf_go", use_container_width=True):
            for f in up:
                path = save_uploaded_pdf_to_inbox(f.getvalue(), f.name)
                if auto_import:
                    with st.spinner(f"Import: {path.name}…"):
                        r = import_one_pdf(path)
                    if r["status"] == "duplicate":
                        st.warning(f"Duplikat: **{r['filename']}**")
                    elif r["status"] == "error":
                        st.error(r.get("message", "Fehler"))
                    else:
                        ocr = " (Scan?)" if r.get("needs_ocr") else ""
                        st.success(f"Importiert: **{r['filename']}** → ID {r['id']}{ocr}")
                        apply_import_owner(int(r["id"]))
                        enqueue_payment(int(r["id"]))
            st.rerun()
    with cc:
        picked = st.selectbox(
            "Familie",
            keys,
            index=idx,
            format_func=lambda k: labels_map.get(k, k),
            key="fin_family_ctx",
            label_visibility="collapsed",
            help=(
                "Haushalt: gemeinsame Kennzahlen, keine PDF-Zuordnung. "
                "Person: gefiltert; unten optional Auto-Zuordnung beim Import."
            ),
        )
        st.session_state.docu_context_key = picked
    with cd:
        st.session_state.fin_ctx_year = st.selectbox(
            "Jahr",
            y_opts,
            index=y_idx,
            key="fin_top_year",
            label_visibility="collapsed",
        )
    with ce:
        st.session_state.fin_ctx_month = st.selectbox(
            "Monat",
            m_opts,
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: _months[x - 1],
            key="fin_top_month",
            label_visibility="collapsed",
        )
    with cf:
        if st.button("Aktualisieren", key="fin_top_update", type="primary", use_container_width=True):
            st.rerun()

    is_person = str(st.session_state.get("docu_context_key") or "").startswith("person:")
    if not is_person:
        st.session_state.docu_assign_import_to_context = False
    st.markdown('<p class="fin-header-assign-hint"></p>', unsafe_allow_html=True)
    st.checkbox(
        "Neue PDF-Imports der gewählten Person zuordnen",
        key="docu_assign_import_to_context",
        disabled=not is_person,
        help="Nur bei einer einzelnen Person — nicht im Haushalt-Modus.",
    )


def _smtp_test_sidebar() -> None:
    if not smtp_configured():
        return
    if st.button("SMTP Testmail", key="fin_smtp_test", use_container_width=True):
        frm = (os.environ.get("DOCU_SMTP_FROM") or "").strip()
        if not frm:
            st.error("`DOCU_SMTP_FROM` fehlt.")
        else:
            try:
                with st.spinner("Sende …"):
                    send_email_smtp(
                        to_addr=frm,
                        subject="Docu-Organizer — SMTP-Test",
                        body="Testmail aus dem Finanz-UI.\n",
                    )
                st.success(f"Gesendet an {frm}")
            except Exception as e:
                st.error(str(e))


def render_navigation_column() -> None:
    st.markdown('<div class="fin-nav-radio">', unsafe_allow_html=True)
    if "fin_nav_radio" not in st.session_state:
        st.session_state.fin_nav_radio = st.session_state.get("current_nav", "home")
    picked = st.radio(
        "Navigation",
        list(NAV_KEYS_ORDER),
        format_func=lambda k: NAV_LABELS[k],
        key="fin_nav_radio",
        label_visibility="collapsed",
    )
    st.session_state.current_nav = picked
    st.markdown("</div>", unsafe_allow_html=True)

    render_lumo_column(compact=True)

    st.divider()

    with st.expander("Hilfe & Tipps", expanded=False):
        st.markdown(
            '<p class="fin-muted" style="margin:0 0 0.5rem 0;">'
            "**App installieren:** Über das Install-Symbol in der Adressleiste (Chrome/Edge).</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="fin-muted" style="margin:0;">'
            "Nach der KI-Analyse landen Dokumente in den Ordnern. "
            "Stromanbieter: Unterordner = Anbietername.</p>",
            unsafe_allow_html=True,
        )

    st.divider()
    if os.environ.get("OPENAI_API_KEY"):
        st.markdown('<span class="fin-pill-ok">KI-Verbindung aktiv</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="fin-pill-warn">KI: Schlüssel fehlt</span>', unsafe_allow_html=True)
    st.caption(f"Max. ca. {LLM_TEXT_CHAR_LIMIT:,} Zeichen pro Analyse.")
    _smtp_test_sidebar()

    st.checkbox(
        "Nach KI: Vorgänge automatisch (gleiche Kunden-/Vertragsnr.)",
        key="auto_matter_after_llm",
        help=(
            "Wenn die KI eine Kunden- oder Vertragsnummer findet, werden alle Dokumente "
            "mit derselben Kennung einem Vorgang zugeordnet."
        ),
    )

    st.divider()
    st.markdown('<p class="fin-nav-heading">Weitere Funktionen</p>', unsafe_allow_html=True)
    st.text_input(
        "Suche",
        key="global_doc_search_input",
        placeholder="Dateiname, Absender, Kennung …",
        label_visibility="collapsed",
    )
    if st.button("Treffer anzeigen", key="fin_search_go"):
        st.session_state["doc_search_q"] = (
            st.session_state.get("global_doc_search_input") or ""
        ).strip().lower()
    dq = (st.session_state.get("doc_search_q") or "").strip()
    if dq:
        hits: list[dict[str, Any]] = []
        for r in filter_documents_by_context(list_documents(), _doc_ctx()):
            parts = [
                str(r.get("original_filename") or "").lower(),
                str(r.get("summary_de") or "").lower(),
                str(r.get("sender_name") or "").lower(),
                str(r.get("subject") or "").lower(),
            ]
            try:
                refs = json.loads(r.get("reference_ids_json") or "[]")
                if isinstance(refs, list):
                    for ref in refs:
                        if isinstance(ref, dict):
                            parts.append(str(ref.get("value") or "").lower())
            except json.JSONDecodeError:
                pass
            if dq in " ".join(parts):
                hits.append(r)
        if not hits:
            st.caption("Keine Treffer.")
        else:
            for r in hits[:25]:
                if st.button(f"#{r['id']} — {r.get('original_filename')}", key=f"fin_srch_{r['id']}"):
                    nf = (r.get("nav_folder") or "").strip()
                    if nf not in NAV_KEYS_ORDER:
                        nf = "home"
                    st.session_state["current_nav"] = nf
                    st.session_state["fin_nav_radio"] = nf
                    st.session_state["jump_doc_id"] = int(r["id"])
                    st.rerun()

    with st.expander("Papierkorb", expanded=False):
        arch = list_archived_documents()
        if not arch:
            st.caption("Leer.")
        else:
            for r in arch[:35]:
                c_a, c_b = st.columns([3, 1])
                with c_a:
                    st.caption(f"#{r['id']} — {r.get('original_filename')}")
                with c_b:
                    if st.button("Wiederherstellen", key=f"fin_unarch_{r['id']}"):
                        set_document_archived(int(r["id"]), False)
                        st.rerun()

    with st.expander("Gleiche Kennung", expanded=False):
        clusters = list_reference_key_clusters(limit=25)
        if not clusters:
            st.caption("Keine Gruppen.")
        else:
            for ci, c in enumerate(clusters):
                st.caption(f"{c.get('id_type')} · {c.get('doc_count')} Dok.")
                for j, did in enumerate(c["document_ids"][:6]):
                    if st.button(f"Öffnen #{did}", key=f"fin_clus_{ci}_{j}"):
                        drow = get_document(did)
                        nf = "home"
                        if drow:
                            ext0 = get_extraction(did)
                            if ext0 and (ext0.get("nav_folder") or "").strip() in NAV_KEYS_ORDER:
                                nf = str(ext0.get("nav_folder")).strip()
                        st.session_state["current_nav"] = nf
                        st.session_state["fin_nav_radio"] = nf
                        st.session_state["jump_doc_id"] = int(did)
                        st.rerun()

    with st.expander("Datenschutz", expanded=False):
        st.markdown(PRIVACY_UI_DE)


def render_lumo_column(*, compact: bool = False) -> None:
    wrap_cls = "fin-sidebar-lumo" if compact else ""
    if wrap_cls:
        st.markdown(f'<div class="{wrap_cls}">', unsafe_allow_html=True)

    st.markdown(
        '<p class="fin-lumo-title">KI-Chat (LUMO)</p>',
        unsafe_allow_html=True,
    )

    av_w = 36 if compact else 44
    a1, a2 = st.columns([0.28, 0.72])
    with a1:
        if LUMO_AVATAR_PATH.is_file():
            st.image(str(LUMO_AVATAR_PATH.resolve()), width=av_w)
        else:
            st.markdown("### " + "\u2728")
    with a2:
        st.markdown(
            '<p class="fin-lumo-greet">'
            "Hallo! Ich bin Lumo — wie kann ich helfen?</p>",
            unsafe_allow_html=True,
        )

    if not os.environ.get("OPENAI_API_KEY"):
        st.info("Bitte `OPENAI_API_KEY` setzen, um mit Lumo zu chatten.")
        if wrap_cls:
            st.markdown("</div>", unsafe_allow_html=True)
        return

    _ensure_chat()
    fy = int(st.session_state.get("fin_ctx_year", 2026))
    fm = int(st.session_state.get("fin_ctx_month", 4))
    _mn = (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    )
    qa_text = f"Zeige mir meine Finanzen für {_mn[fm - 1]} {fy}"
    if st.button(qa_text, key="fin_lumo_quick_fin", use_container_width=True):
        _ensure_chat()
        st.session_state.ai_chat_messages.append({"role": "user", "content": qa_text})
        st.session_state.ai_chat_messages = _trim_chat(st.session_state.ai_chat_messages)
        try:
            with st.spinner("Lumo …"):
                eff: list[dict[str, Any]] = []
                reply = run_organizer_chat(
                    st.session_state.ai_chat_messages,
                    tool_effects=eff,
                )
                _apply_chat_effects(eff)
            st.session_state.ai_chat_messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.session_state.ai_chat_messages.append(
                {"role": "assistant", "content": f"**Fehler:** {e}"}
            )
        st.rerun()

    _def_h = "200" if compact else "280"
    sb_msg = int(os.environ.get("DOCU_SIDEBAR_CHAT_MSG", _def_h))
    try:
        scroll = st.container(height=sb_msg, border=True)
    except TypeError:
        scroll = st.container()
    with scroll:
        lumo_av = _lumo_avatar_chat()
        if st.session_state.get("docu_pending_device_hint"):
            st.info(str(st.session_state.pop("docu_pending_device_hint")), icon="\U0001F4FA")
        for m in st.session_state.ai_chat_messages:
            if m.get("role") == "system":
                continue
            role = m.get("role") or "assistant"
            if role == "assistant":
                with st.chat_message("assistant", avatar=lumo_av):
                    st.markdown(m.get("content") or "")
            else:
                with st.chat_message(role):
                    st.markdown(m.get("content") or "")

    if st.button("Chat leeren", key="fin_chat_clear", use_container_width=True):
        st.session_state.ai_chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()

    with st.form("fin_lumo_form", clear_on_submit=True):
        prompt = st.text_input(
            "Nachricht",
            label_visibility="collapsed",
            placeholder="Nachricht an Lumo …",
        )
        submitted = st.form_submit_button("Senden", type="primary", use_container_width=True)

    if submitted and (prompt or "").strip():
        _ensure_chat()
        st.session_state.ai_chat_messages.append({"role": "user", "content": (prompt or "").strip()})
        st.session_state.ai_chat_messages = _trim_chat(st.session_state.ai_chat_messages)
        try:
            with st.spinner("Lumo …"):
                eff: list[dict[str, Any]] = []
                reply = run_organizer_chat(
                    st.session_state.ai_chat_messages,
                    tool_effects=eff,
                )
                _apply_chat_effects(eff)
            st.session_state.ai_chat_messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.session_state.ai_chat_messages.append(
                {"role": "assistant", "content": f"**Fehler:** {e}"}
            )
        st.rerun()

    if wrap_cls:
        st.markdown("</div>", unsafe_allow_html=True)
