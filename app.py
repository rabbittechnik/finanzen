"""Streamlit UI: inbox import, document list, LLM extraction, matters and linking."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from config import INBOX_DIR, LLM_TEXT_CHAR_LIMIT
from ingest import save_uploaded_pdf_to_inbox
from db import (
    clear_payment_link,
    create_matter,
    documents_for_matter,
    find_documents_sharing_keys,
    get_document,
    get_extraction,
    init_db,
    link_document_to_matter,
    list_documents,
    list_documents_for_nav,
    list_matters,
    matter_ids_for_document,
    set_include_monthly_expense,
    set_payment_link_pair,
    set_zahlstatus_for_document,
    set_zahlstatus_linked,
    unlink_document_from_matter,
)
from home_finance import compute_home_stats, is_expense_monthly_prompt_candidate
from nav_logic import NAV_KEYS_ORDER, NAV_LABELS, _norm_kind
from import_jobs import import_inbox_pdfs, import_one_pdf, run_llm_on_document
from privacy_notes import PRIVACY_UI_DE
from home_overlay import maybe_show_home_overlay
from organizer_chat import SYSTEM_PROMPT, run_organizer_chat
from ui_theme import inject_neon_styles

load_dotenv()

# Zweiphasige KI-Analyse (Chat-Feed); Scroll-Höhe Chat-Verlauf (Pixel)
PENDING_LLM_KEY = "docu_pending_llm"
CHAT_SCROLL_HEIGHT = int(os.environ.get("DOCU_CHAT_SCROLL_HEIGHT", "660"))

CATEGORY_DE = {
    "energy": "Energie (Strom/Gas)",
    "legal": "Recht / Anwalt",
    "payroll": "Lohn / Gehalt",
    "insurance": "Versicherung",
    "contract": "Vertrag",
    "telecom": "Telekom / Mobilfunk",
    "housing_internet": "Wohnen / Internet",
    "government": "Behörde",
    "banking": "Bank",
    "health": "Gesundheit",
    "other": "Sonstiges",
}

ROLE_DE = {
    "utility": "Versorger",
    "lawyer": "Anwalt / Kanzlei",
    "employer": "Arbeitgeber",
    "insurer": "Versicherer",
    "telco": "Telekom",
    "landlord": "Vermieter / Wohnen",
    "bank": "Bank",
    "government": "Behörde",
    "collection_agency": "Inkasso",
    "other": "Sonstiges",
}


def _fmt_de_eur(v: float) -> str:
    return f"{v:.2f} €".replace(".", ",")


def _enqueue_payment_prompt(doc_id: int) -> None:
    q = st.session_state.setdefault("pending_zahlstatus_docs", [])
    if doc_id not in q:
        q.append(doc_id)


def _enqueue_monthly_expense_prompt(doc_id: int) -> None:
    q = st.session_state.setdefault("pending_monthly_expense_docs", [])
    if doc_id not in q:
        q.append(doc_id)


def _render_payment_status_queue() -> None:
    q = st.session_state.setdefault("pending_zahlstatus_docs", [])
    if not q:
        return
    did = int(q[0])
    doc = get_document(did)
    if not doc:
        q.pop(0)
        st.rerun()
        return
    init = (doc.get("initial_zahlstatus") or "").strip()
    ext = get_extraction(did)
    zs_ext = (ext.get("zahlstatus") or "").strip() if ext else ""
    if zs_ext or init:
        q.pop(0)
        st.rerun()
        return
    st.markdown(
        '<div class="neon-card" style="border-color:rgba(251,191,36,0.35);margin-bottom:1rem;">'
        "<strong style='color:#fcd34d;'>Zahlstatus</strong> — bitte kurz angeben "
        f"(Dokument <span style='color:#a5f3fc;'>#{did}</span> · "
        f"{doc.get('original_filename', '')})</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        choice = st.radio(
            "Ist diese Zahlungsaufforderung / Mahnung / Rechnung bereits beglichen?",
            ("offen", "bezahlt"),
            format_func=lambda x: "Noch offen" if x == "offen" else "Bereits bezahlt / erledigt",
            horizontal=True,
            key=f"pq_choice_{did}",
        )
    with c2:
        if st.button("Speichern", type="primary", key=f"pq_ok_{did}"):
            set_zahlstatus_for_document(did, choice)
            q.pop(0)
            st.success("Gespeichert.")
            st.rerun()
    with c3:
        if st.button("Später", key=f"pq_skip_{did}"):
            q.pop(0)
            st.rerun()


def _render_monthly_expense_queue() -> None:
    q = st.session_state.setdefault("pending_monthly_expense_docs", [])
    if not q:
        return
    did = int(q[0])
    doc = get_document(did)
    if not doc:
        q.pop(0)
        st.rerun()
        return
    ext = get_extraction(did)
    if not ext or not is_expense_monthly_prompt_candidate(ext):
        q.pop(0)
        st.rerun()
        return
    if ext.get("include_monthly_expense") is not None:
        q.pop(0)
        st.rerun()
        return
    st.markdown(
        '<div class="neon-card" style="border-color:rgba(110,231,255,0.35);margin-bottom:1rem;">'
        "<strong style='color:#7dd3fc;'>Monatsausgaben</strong> — soll dieser Beleg in die "
        f"<strong>monatlichen Ausgaben</strong> auf der Startseite einfließen? "
        f"(Dokument <span style='color:#a5f3fc;'>#{did}</span> · "
        f"{doc.get('original_filename', '')})</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        choice = st.radio(
            "Zu den monatlichen Ausgaben dieses Monats zählen?",
            (1, 0),
            format_func=lambda x: "Ja, mitzählen" if x == 1 else "Nein, nicht mitzählen",
            horizontal=True,
            key=f"mq_choice_{did}",
        )
    with c2:
        if st.button("Speichern", type="primary", key=f"mq_ok_{did}"):
            set_include_monthly_expense(did, int(choice))
            q.pop(0)
            st.success("Gespeichert.")
            st.rerun()
    with c3:
        if st.button("Später", key=f"mq_skip_{did}"):
            q.pop(0)
            st.rerun()


def _render_home_dashboard() -> None:
    stats = compute_home_stats(list_documents())
    intro_html = """<p style="color:#94a3b8;font-size:0.95rem;margin:0 0 0.75rem 0;">
Überblick aus KI-Extraktion und Kennungen - Schuldensumme zählt offene Forderungen
<strong style="color:#a5f3fc;">pro Aktenzeichen/Kundennummer nur einmal</strong>
(verknüpfte Mahnung + Rechnung nicht doppelt).</p>"""
    st.markdown(intro_html, unsafe_allow_html=True)
    kpi_html = f"""<div class="neon-kpi-row">
<div class="neon-kpi">
<div class="neon-kpi-label">Einnahmen (Lohn)</div>
<div class="neon-kpi-value">{_fmt_de_eur(stats.income_month_eur)}</div>
<div class="neon-kpi-sub">Nach Lohnabrechnung - <strong>{stats.month_label}</strong>
(Netto laut KI-Feld <code>payslip_net_income_eur</code>)</div></div>
<div class="neon-kpi magenta">
<div class="neon-kpi-label">Schuldensumme (offen)</div>
<div class="neon-kpi-value">{_fmt_de_eur(stats.debt_open_eur)}</div>
<div class="neon-kpi-sub">Zahlungsaufforderungen &amp; Mahnungen -
<strong>{stats.debt_groups}</strong> getrennte Kennung(en)</div></div>
<div class="neon-kpi gold">
<div class="neon-kpi-label">Ausgaben (Monat)</div>
<div class="neon-kpi-value">{_fmt_de_eur(stats.expense_month_eur)}</div>
<div class="neon-kpi-sub">Ohne Ihre Auswahl zählen passende Belege vorläufig mit;
<strong>Nein</strong> schließt explizit aus. Kalendermonat <strong>{stats.month_label}</strong>
(Datum laut Dokument).</div></div>
</div>"""
    st.markdown(kpi_html, unsafe_allow_html=True)


def _trim_chat_messages(msgs: list[dict[str, Any]], *, keep_non_system: int = 24) -> list[dict[str, Any]]:
    sys = [m for m in msgs if m.get("role") == "system"]
    rest = [m for m in msgs if m.get("role") != "system"]
    return sys + rest[-keep_non_system:]


def _ensure_chat_messages() -> None:
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]


def _append_chat_activity(text: str) -> None:
    _ensure_chat_messages()
    st.session_state.ai_chat_messages.append({"role": "assistant", "content": text})
    st.session_state.ai_chat_messages = _trim_chat_messages(
        st.session_state.ai_chat_messages, keep_non_system=40
    )


def _after_llm_document_hooks(doc_id: int, _out: dict[str, Any] | None) -> None:
    """Zahlstatus-/Monatsausgaben-Warteschlange wie nach bisherigem KI-Button."""
    ext2 = get_extraction(doc_id)
    if not ext2:
        return
    nk = _norm_kind(ext2.get("document_kind"))
    navf = ext2.get("nav_folder") or ""
    if (nk in ("invoice", "reminder", "payment_demand") or navf == "mahnungen") and not (
        ext2.get("zahlstatus") or ""
    ).strip():
        doc2 = get_document(doc_id)
        if doc2 and not (doc2.get("initial_zahlstatus") or "").strip():
            _enqueue_payment_prompt(doc_id)
    if is_expense_monthly_prompt_candidate(ext2) and ext2.get("include_monthly_expense") is None:
        _enqueue_monthly_expense_prompt(doc_id)


def _drain_pending_llm_job() -> None:
    """Start-/Ende-Meldungen im Chat; Analyse in Phase 2 (eigener Rerun)."""
    job = st.session_state.get(PENDING_LLM_KEY)
    if not job:
        return
    phase = job.get("phase")
    doc_id = int(job["doc_id"])
    fname = str(job.get("filename") or "")

    if phase == 1:
        if not os.environ.get("OPENAI_API_KEY"):
            st.session_state.pop(PENDING_LLM_KEY, None)
            st.error("OPENAI_API_KEY fehlt — KI-Analyse nicht möglich.")
            return
        _append_chat_activity(
            f"**Dokument-KI** startet … **#{doc_id}** `{fname}`\n\n"
            "_Strukturieren, Ablage, Kennungen — bitte kurz warten._"
        )
        job["phase"] = 2
        st.session_state[PENDING_LLM_KEY] = job
        st.rerun()

    if phase == 2:
        doc = get_document(doc_id)
        if not doc:
            _append_chat_activity(f"**Dokument-KI** abgebrochen: Dokument **#{doc_id}** nicht gefunden.")
            st.session_state.pop(PENDING_LLM_KEY, None)
            st.rerun()
            return
        try:
            out = run_llm_on_document(
                doc_id,
                auto_matter=bool(st.session_state.get("auto_matter_after_llm", True)),
            )
        except Exception as e:
            _append_chat_activity(f"**Dokument-KI Fehler** (#{doc_id}): {e}")
            st.session_state.pop(PENDING_LLM_KEY, None)
            st.rerun()
            return

        ext2 = get_extraction(doc_id)
        lines = [
            f"**Dokument-KI fertig** **#{doc_id}** `{doc.get('original_filename', '')}`",
        ]
        if ext2:
            navf = ext2.get("nav_folder") or ""
            nav_label = NAV_LABELS.get(navf, navf or "—")
            fs = ext2.get("folder_sub")
            lines.append(f"- **Ablage:** {nav_label}" + (f" → `{fs}`" if fs else ""))
            lines.append(f"- **Art:** `{ext2.get('document_kind') or '—'}`")
            lines.append(
                f"- **Kategorie:** {CATEGORY_DE.get(ext2.get('category'), ext2.get('category') or '—')}"
            )
            sd = (ext2.get("summary_de") or "").strip()
            if sd:
                tail = "…" if len(sd) > 280 else ""
                lines.append(f"- **Kurz:** {sd[:280]}{tail}")
        am = out.get("_auto_matter") if isinstance(out, dict) else None
        if am:
            lines.append(
                f"- **Vorgang:** #{am['matter_id']} — {am['title']} ({am['linked_count']} Dok.)"
            )
        _append_chat_activity("\n".join(lines))
        _after_llm_document_hooks(doc_id, out if isinstance(out, dict) else None)
        st.session_state.pop(PENDING_LLM_KEY, None)
        st.session_state["docu_show_llm_ok"] = doc_id
        st.rerun()


def _render_assistant_chat() -> None:
    st.markdown(
        '<div class="neon-chat-panel"><p class="sidebar-brand" style="font-size:0.95rem;margin:0 0 0.5rem 0;">'
        "KI-Assistent</p>"
        "<p class=\"sidebar-muted\" style=\"margin:0 0 0.75rem 0;\">Fragen zur App, Belege finden, "
        "Ablage per Tool ändern (nach KI-Analyse). Dokument-KI schreibt hier beim Analysieren mit.</p></div>",
        unsafe_allow_html=True,
    )
    if not os.environ.get("OPENAI_API_KEY"):
        st.caption("Chat benötigt `OPENAI_API_KEY`.")
        return
    _ensure_chat_messages()
    try:
        scroll = st.container(height=CHAT_SCROLL_HEIGHT, border=True)
    except TypeError:
        scroll = st.container()
    with scroll:
        for m in st.session_state.ai_chat_messages:
            if m.get("role") == "system":
                continue
            with st.chat_message(m["role"]):
                st.markdown(m.get("content") or "")
    prompt = st.chat_input("Frage zum Organizer …", key="organizer_chat_input")
    if prompt:
        _ensure_chat_messages()
        st.session_state.ai_chat_messages.append({"role": "user", "content": prompt})
        st.session_state.ai_chat_messages = _trim_chat_messages(
            st.session_state.ai_chat_messages, keep_non_system=28
        )
        try:
            with st.spinner("KI antwortet…"):
                reply = run_organizer_chat(st.session_state.ai_chat_messages)
            st.session_state.ai_chat_messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.session_state.ai_chat_messages.append(
                {"role": "assistant", "content": f"**Fehler:** {e}"}
            )
        st.rerun()
    if st.button("Chat leeren", key="organizer_chat_clear"):
        _ensure_chat_messages()
        st.session_state.ai_chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Dokumenten-Organizer",
        layout="wide",
        page_icon="📄",
    )
    inject_neon_styles()
    init_db()
    _drain_pending_llm_job()
    if "auto_matter_after_llm" not in st.session_state:
        st.session_state.auto_matter_after_llm = True
    if "current_nav" not in st.session_state:
        st.session_state.current_nav = "home"
    maybe_show_home_overlay()

    with st.sidebar:
        st.markdown('<p class="sidebar-brand">Navigation</p>', unsafe_allow_html=True)
        nav_options = list(NAV_KEYS_ORDER)
        nav_display = [NAV_LABELS[k] for k in nav_options]
        picked = st.radio(
            "Bereich",
            nav_options,
            format_func=lambda k: NAV_LABELS[k],
            key="sidebar_nav_choice",
            label_visibility="collapsed",
        )
        st.session_state.current_nav = picked
        st.caption(
            "Nach KI-Analyse werden Dokumente den Ordnern zugeordnet. "
            "Stromanbieter: Unterordner = Anbietername (Wechsel = neuer Ordner)."
        )
        st.divider()
        st.markdown(
            '<p class="sidebar-muted">Deine Unterlagen bleiben auf diesem Server. '
            "Zum Einlesen PDFs im Tab **Posteingang** hochladen.</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        key_set = bool(os.environ.get("OPENAI_API_KEY"))
        if key_set:
            st.markdown('<span class="pill-ok">KI-Verbindung aktiv</span>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<span class="pill-warn">KI: Schlüssel fehlt</span>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Lege `OPENAI_API_KEY` in den Einstellungen deines Hostings "
                "(z. B. Railway → Variables) an."
            )
        st.caption(f"Pro Analyse maximal ca. {LLM_TEXT_CHAR_LIMIT:,} Zeichen Text an die KI.")
        st.divider()
        st.checkbox(
            "Nach KI: Vorgänge automatisch (gleiche Kunden-/Vertragsnr.)",
            key="auto_matter_after_llm",
            help=(
                "Wenn die KI eine Kunden- oder Vertragsnummer findet, werden alle Dokumente "
                "mit derselben Kennung einem Vorgang zugeordnet (neu oder bestehend)."
            ),
        )
        st.divider()
        with st.expander("Datenschutz"):
            st.markdown(PRIVACY_UI_DE)

    main_c, chat_c = st.columns([2.15, 1], gap="medium")
    with main_c:
        nav_now = st.session_state.get("current_nav", "home")
        st.title("Dokumenten-Organizer")
        _render_payment_status_queue()
        _render_monthly_expense_queue()
        if nav_now == "home":
            _render_home_dashboard()
        else:
            st.markdown(
                '<div class="neon-card"><p style="margin:0;color:#cbd5e1;font-size:1rem;">'
                "PDFs erfassen, Text lokal auslesen, mit KI strukturieren und über Kennungen "
                "zu <strong style='color:#a5f3fc;'>Vorgängen</strong> bündeln."
                "</p></div>",
                unsafe_allow_html=True,
            )
    
        tab_inbox, tab_docs, tab_matters = st.tabs(["Posteingang", "Dokumente", "Vorgänge"])
    
        with tab_inbox:
            st.subheader("PDFs hochladen")
            st.write("PDFs hier ablegen – optional gleich ins Archiv übernehmen (wie Posteingang).")
            up = st.file_uploader(
                "Dateien wählen",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
            auto_import = st.checkbox("Hochgeladene PDFs sofort einlesen", value=True)
            if up:
                if st.button("Upload starten", type="primary"):
                    for f in up:
                        path = save_uploaded_pdf_to_inbox(f.getvalue(), f.name)
                        st.caption(f"Gespeichert: `{path.name}`")
                        if auto_import:
                            with st.spinner(f"Import: {path.name}…"):
                                r = import_one_pdf(path)
                            if r["status"] == "duplicate":
                                st.warning(f'Duplikat: **{r["filename"]}**')
                            elif r["status"] == "error":
                                st.error(r.get("message", "Fehler"))
                            else:
                                ocr = " (wenig Text – vermutlich Scan)" if r.get("needs_ocr") else ""
                                st.success(f'Importiert: **{r["filename"]}** → ID {r["id"]}{ocr}')
                                _enqueue_payment_prompt(int(r["id"]))
                    st.rerun()
    
            st.divider()
            st.subheader("Posteingang vom Server")
            st.write(
                "Wenn dein Hosting einen gemeinsamen **Posteingang-Ordner** bereitstellt, "
                "kannst du dort PDFs ablegen und mit **Jetzt einlesen** importieren. "
                "Am einfachsten nutzt du den **Upload** oben."
            )
            if st.button("Jetzt einlesen", type="primary"):
                with st.spinner("Import läuft…"):
                    results = import_inbox_pdfs()
                if not results:
                    st.info("Keine PDFs im Posteingang.")
                else:
                    for r in results:
                        if r["status"] == "duplicate":
                            st.warning(f'Duplikat übersprungen: **{r["filename"]}**')
                        else:
                            ocr = " (wenig Text – vermutlich Scan)" if r.get("needs_ocr") else ""
                            st.success(f'Importiert: **{r["filename"]}** → ID {r["id"]}{ocr}')
                            _enqueue_payment_prompt(int(r["id"]))
            st.divider()
            pdfs = sorted(INBOX_DIR.glob("*.pdf")) if INBOX_DIR.exists() else []
            st.write(f"Aktuell **{len(pdfs)}** PDF(s) im Posteingang.")
    
        with tab_docs:
            nav_key = st.session_state.get("current_nav", "home")
            st.subheader(NAV_LABELS.get(nav_key, "Dokumente"))
            rows = list_documents_for_nav(nav_key if nav_key != "home" else None)
            if not rows:
                st.info("Noch keine Dokumente in diesem Bereich. Import im Tab Posteingang, dann KI-Analyse.")
            else:
                if nav_key == "stromanbieter":
                    by_sub: dict[str | None, list] = defaultdict(list)
                    for r in rows:
                        by_sub[r.get("folder_sub")].append(r)
                    ordered = sorted(by_sub.keys(), key=lambda x: (x is None, (x or "")))
                    id_opts: dict[str, int] = {}
                    for sub in ordered:
                        label = sub if sub else "Ohne Anbietername"
                        st.markdown(f"**{label}**")
                        for r in sorted(by_sub[sub], key=lambda x: -int(x["id"])):
                            id_opts[f'#{r["id"]} — {r["original_filename"]}'] = r["id"]
                    choice = st.selectbox("Dokument wählen", list(id_opts.keys()))
                else:
                    id_opts = {f'#{r["id"]} — {r["original_filename"]}': r["id"] for r in rows}
                    choice = st.selectbox("Dokument wählen", list(id_opts.keys()))
                doc_id = id_opts[choice]
                doc = get_document(doc_id)
                ext = get_extraction(doc_id)
                if st.session_state.get("docu_show_llm_ok") == doc_id:
                    st.success("Analyse gespeichert — Details im **KI-Chat** rechts.")
                    del st.session_state["docu_show_llm_ok"]

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### Metadaten")
                    st.write(f"**Datei:** {doc['original_filename']}")
                    st.write(f"**Zeichen Text:** {doc['text_char_count']}")
                    with st.expander("Technische Details", expanded=False):
                        st.code(doc["stored_path"] or "—", language=None)
                        st.caption(f"SHA256 (Kurz): `{doc['sha256'][:16]}…`")
                    if doc.get("needs_ocr"):
                        st.error(
                            "Sehr wenig Text extrahiert – vermutlich gescanntes PDF. "
                            "Optional später OCR (z. B. Tesseract) ergänzen."
                        )
                    if ext:
                        nf = ext.get("nav_folder")
                        fs = ext.get("folder_sub")
                        ablage = NAV_LABELS.get(nf, nf or "—")
                        if fs:
                            ablage = f"{ablage} → **{fs}**"
                        st.markdown(f"**Ablage:** {ablage}")
                        dk = ext.get("document_kind") or "—"
                        st.write(f"**Dokumentart (KI):** {dk}")
                        st.write(
                            f"**Kategorie:** {CATEGORY_DE.get(ext['category'], ext['category'])}"
                        )
                        st.write(f"**Rolle Absender:** {ROLE_DE.get(ext['sender_role'], ext['sender_role'])}")
                        st.write(f"**Absender:** {ext['sender_name'] or '—'}")
                        st.write(f"**Betreff:** {ext['subject'] or '—'}")
                        st.write(f"**Datum:** {ext['document_date'] or '—'}")
                        st.write(f"**Kurzfassung:** {ext['summary_de'] or '—'}")
                        partner_id = ext.get("linked_payment_doc_id")
                        if partner_id:
                            pdoc = get_document(int(partner_id))
                            pname = pdoc["original_filename"] if pdoc else "?"
                            kind = (ext.get("document_kind") or "").lower()
                            if kind == "invoice":
                                st.info(f"**Verknüpfte Mahnung:** #{int(partner_id)} — {pname}")
                            elif kind == "reminder":
                                st.info(f"**Verknüpfte Rechnung:** #{int(partner_id)} — {pname}")
                            else:
                                st.info(f"**Zahlstatus-Partner:** #{int(partner_id)} — {pname}")
                        zs = ext.get("zahlstatus")
                        if zs or partner_id:
                            zlab = {"offen": "Offen", "bezahlt": "Bezahlt / erledigt"}.get(
                                zs or "offen", zs or "—"
                            )
                            st.write(f"**Zahlstatus:** {zlab}")
                        if is_expense_monthly_prompt_candidate(ext):
                            im = ext.get("include_monthly_expense")
                            imlab = (
                                "Noch nicht gewählt (zählt vorläufig mit)"
                                if im is None
                                else ("Ja, in Monatsausgaben" if int(im) == 1 else "Nein, nicht in Monatsausgaben")
                            )
                            st.write(f"**Monatsausgaben:** {imlab}")
                            mce = st.radio(
                                "Zu den monatlichen Ausgaben zählen?",
                                (1, 0),
                                index=0 if im is None or int(im) == 1 else 1,
                                format_func=lambda x: "Ja" if x == 1 else "Nein",
                                horizontal=True,
                                key=f"mce_edit_{doc_id}",
                            )
                            if st.button("Monatsausgaben speichern", key=f"mce_save_{doc_id}"):
                                set_include_monthly_expense(doc_id, int(mce))
                                st.success("Gespeichert.")
                                st.rerun()
                        try:
                            amounts = json.loads(ext["amounts_json"] or "[]")
                            if amounts:
                                st.json(amounts)
                        except json.JSONDecodeError:
                            pass
                        try:
                            refs = json.loads(ext["reference_ids_json"] or "[]")
                            if refs:
                                st.markdown("**Referenzen / Kennungen:**")
                                st.json(refs)
                        except json.JSONDecodeError:
                            pass
    
                with c2:
                    st.markdown("#### Aktionen")
                    if st.button("Mit KI analysieren", key=f"llm_{doc_id}"):
                        st.session_state[PENDING_LLM_KEY] = {
                            "phase": 1,
                            "doc_id": doc_id,
                            "filename": doc.get("original_filename", ""),
                        }
                        st.rerun()
    
                    matters = list_matters()
                    current = matter_ids_for_document(doc_id)
                    st.markdown("**Vorgang zuordnen**")
                    if matters:
                        m_labels = {f"#{m['id']} — {m['title']}": m["id"] for m in matters}
                        pick = st.selectbox("Vorgang", list(m_labels.keys()), key=f"mp_{doc_id}")
                        mid = m_labels[pick]
                        if st.button("Zu Vorgang hinzufügen", key=f"link_{doc_id}"):
                            link_document_to_matter(doc_id, mid)
                            st.success("Verknüpft.")
                            st.rerun()
                        if mid in current:
                            if st.button("Aus diesem Vorgang entfernen", key=f"unlink_{doc_id}_{mid}"):
                                unlink_document_from_matter(doc_id, mid)
                                st.rerun()
                    else:
                        st.caption("Legen Sie zuerst einen Vorgang im Tab „Vorgänge“ an.")
    
                    show_pay_ui = ext and (
                        ext.get("document_kind") in ("invoice", "reminder", "payment_demand")
                        or ext.get("nav_folder") in ("rechnungen", "mahnungen")
                    )
                    if show_pay_ui:
                        st.markdown("#### Rechnung ↔ Mahnung (Zahlstatus)")
                        if ext.get("linked_payment_doc_id"):
                            status_val = ext.get("zahlstatus") or "offen"
                            opts = ["offen", "bezahlt"]
                            labels = {"offen": "Offen", "bezahlt": "Bezahlt (Rechnung) / Erledigt (Mahnung)"}
                            idx = opts.index(status_val) if status_val in opts else 0
                            new_status = st.radio(
                                "Gemeinsamer Zahlstatus",
                                opts,
                                index=idx,
                                format_func=lambda x: labels[x],
                                key=f"paystat_{doc_id}",
                                horizontal=True,
                            )
                            if st.button("Zahlstatus speichern", key=f"save_pay_{doc_id}"):
                                if new_status != status_val:
                                    set_zahlstatus_linked(doc_id, new_status)
                                    st.success("Gespeichert.")
                                    st.rerun()
                            if st.button("Verknüpfung aufheben", key=f"unlink_pay_{doc_id}"):
                                clear_payment_link(doc_id)
                                st.rerun()
                        else:
                            all_docs = list_documents()
                            others = [
                                r
                                for r in all_docs
                                if int(r["id"]) != doc_id
                                and r.get("document_kind")
                                in ("invoice", "reminder", "payment_demand")
                            ]
                            if others:
                                labels_map = {
                                    f'#{r["id"]} — {r["original_filename"]} ({r.get("document_kind")})': int(
                                        r["id"]
                                    )
                                    for r in others
                                }
                                pick = st.selectbox("Partner-Dokument", list(labels_map.keys()), key=f"ppick_{doc_id}")
                                if st.button("Verknüpfen (gemeinsamer Zahlstatus)", key=f"plink_{doc_id}"):
                                    set_payment_link_pair(doc_id, labels_map[pick])
                                    st.success("Verknüpft — Zahlstatus zunächst **Offen**.")
                                    st.rerun()
                            else:
                                st.caption("Kein weiteres Dokument mit Art Rechnung/Mahnung vorhanden.")
    
                    st.markdown("#### Mögliche zusammenhängende Dokumente")
                    related = find_documents_sharing_keys(doc_id)
                    if not related:
                        st.caption(
                            "Keine Treffer über gleiche Kennung (nach KI-Analyse Referenzen extrahieren)."
                        )
                    else:
                        seen: set[int] = set()
                        for r in related:
                            oid = r["id"]
                            if oid in seen:
                                continue
                            seen.add(oid)
                            st.write(
                                f"— **#{oid}** {r['original_filename']} · Kennung `{r['key_value']}` "
                                f"({r['id_type']}) · {CATEGORY_DE.get(r.get('category') or '', r.get('category') or '')} "
                                f"/ {ROLE_DE.get(r.get('sender_role') or '', r.get('sender_role') or '')}"
                            )
    
                with st.expander("Rohtext (lokal)"):
                    st.text_area(
                        "extracted_text",
                        value=doc["extracted_text"] or "",
                        height=320,
                        disabled=True,
                        label_visibility="collapsed",
                    )
    
        with tab_matters:
            st.subheader("Vorgänge (Themen / Fälle)")
            st.write(
                "Mehrere Dokumente (z. B. Rechnung Versorger + Schreiben Anwalt) können **einem Vorgang** "
                "zugeordnet werden. Kategorie und Rolle bleiben je Dokument gespeichert."
            )
            title = st.text_input("Neuer Vorgang – Titel", placeholder="z. B. Strom Kunde 12345")
            if st.button("Vorgang anlegen"):
                if title.strip():
                    mid = create_matter(title.strip())
                    st.success(f"Vorgang #{mid} angelegt.")
                    st.rerun()
                else:
                    st.warning("Bitte Titel eingeben.")
    
            st.divider()
            for m in list_matters():
                with st.expander(f"#{m['id']} — {m['title']} ({m['doc_count']} Dok.)"):
                    for d in documents_for_matter(m["id"]):
                        st.write(
                            f"**#{d['id']}** {d['original_filename']} — "
                            f"{CATEGORY_DE.get(d.get('category') or '', d.get('category') or '—')} · "
                            f"{ROLE_DE.get(d.get('sender_role') or '', d.get('sender_role') or '—')}"
                        )
                        if st.button("Entknüpfen", key=f"um_{m['id']}_{d['id']}"):
                            unlink_document_from_matter(int(d["id"]), int(m["id"]))
                            st.rerun()
    
    

    with chat_c:
        _render_assistant_chat()

if __name__ == "__main__":
    main()
