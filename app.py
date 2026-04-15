"""Streamlit UI: inbox import, document list, LLM extraction, matters and linking."""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import INBOX_DIR, LLM_TEXT_CHAR_LIMIT
from download_button import render_document_download
from email_draft_llm import EMAIL_SCENARIO_CHOICES, run_email_draft
from email_smtp import send_email_smtp, smtp_configured
from export_bulk import build_csv_bytes, build_zip_bytes
from ingest import save_uploaded_pdf_to_inbox
from db import (
    clear_payment_link,
    create_matter,
    create_person,
    document_needs_owner,
    documents_for_matter,
    find_documents_sharing_keys,
    get_document,
    get_extraction,
    init_db,
    link_document_to_matter,
    list_documents,
    list_documents_for_nav,
    list_matters,
    list_persons,
    matter_ids_for_document,
    set_document_archived,
    set_document_owner,
    set_include_monthly_expense,
    set_payment_link_pair,
    set_zahlstatus_for_document,
    set_zahlstatus_linked,
    unlink_document_from_matter,
)
from home_finance import is_expense_monthly_prompt_candidate
from nav_logic import NAV_KEYS_ORDER, NAV_LABELS, _norm_kind
from import_jobs import import_inbox_pdfs, import_one_pdf, run_llm_on_document
from home_overlay import maybe_show_home_overlay
from organizer_chat import SYSTEM_PROMPT, run_organizer_chat
from pwa_inject import inject_pwa_tags
from doc_context import filter_documents_by_context, normalize_docu_context_key
from fin_dashboard import render_fin_dashboard
from fin_layout import render_global_header_bar, render_navigation_column
from fin_ui_theme import inject_fin_ui_styles
from household_aggregate import aggregate_owner_totals

load_dotenv()


def _configure_json_logging() -> None:
    if os.environ.get("DOCU_JSON_LOGS", "").strip().lower() not in ("1", "true", "yes"):
        return
    fmt = logging.Formatter(
        '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(fmt)
    root.addHandler(h)
    root.setLevel(logging.INFO)
    logging.getLogger("streamlit").setLevel(logging.WARNING)


def _maybe_flush_llm_notify() -> None:
    if not st.session_state.pop("_llm_done_notify", None):
        return
    try:
        st.toast("KI-Analyse abgeschlossen.", icon="✅")
    except Exception:
        pass
    if os.environ.get("DOCU_PWA_NOTIFY", "").strip().lower() not in ("1", "true", "yes"):
        return
    components.html(
        "<script>"
        "try{if(window.Notification&&Notification.permission==='granted')"
        "{new Notification('Dokumenten-Organizer',{body:'KI-Analyse abgeschlossen.'});}"
        "}catch(e){}"
        "</script>",
        height=0,
        width=0,
    )


# Zweiphasige KI-Analyse (Chat-Feed); Chat-Panel (Pixel, gesamt inkl. Eingabe im rechten Block)
PENDING_LLM_KEY = "docu_pending_llm"
CHAT_PANEL_HEIGHT = int(os.environ.get("DOCU_CHAT_PANEL_HEIGHT", "640"))
CHAT_MSG_HEIGHT = int(os.environ.get("DOCU_CHAT_MSG_HEIGHT", "0")) or max(
    220, CHAT_PANEL_HEIGHT - 210
)

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








def _docu_context_key() -> str:
    return normalize_docu_context_key(str(st.session_state.get("docu_context_key") or "household"))


def _enqueue_owner_prompt(doc_id: int) -> None:
    if not document_needs_owner(doc_id):
        return
    q = st.session_state.setdefault("pending_owner_docs", [])
    if doc_id not in q:
        q.append(doc_id)


def _apply_import_owner(doc_id: int) -> None:
    """Nach Import: optional nur einer Person zuordnen — niemals „Haushalt“ (nur Auswertungs-Ansicht)."""
    ck = _docu_context_key()
    if ck in ("household", "all"):
        _enqueue_owner_prompt(doc_id)
        return
    if st.session_state.get("docu_assign_import_to_context") and ck.startswith("person:"):
        set_document_owner(doc_id, person_id=int(ck.split(":", 1)[1]))
        return
    _enqueue_owner_prompt(doc_id)


def _render_document_owner_editor(doc_id: int, doc: dict[str, Any]) -> None:
    """Nur Personen (Haushalt ist keine Speicher-Zuordnung)."""
    entries: list[tuple[str, int | None]] = [("— nicht zugeordnet —", None)]
    for p in list_persons():
        entries.append((f"Person: {p.get('name')}", int(p["id"])))
    labels = [e[0] for e in entries]
    cur_i = 0
    ok = (doc.get("owner_kind") or "").strip()
    for j, e in enumerate(entries):
        _, pid = e
        if pid is None and not ok:
            cur_i = j
            break
        if pid is not None and ok == "person" and int(doc.get("owner_person_id") or 0) == pid:
            cur_i = j
            break
    c_a, c_b = st.columns([3, 1])
    with c_a:
        pick = st.selectbox(
            "Zuordnung (Person)",
            range(len(labels)),
            index=min(cur_i, len(labels) - 1),
            format_func=lambda i: labels[i],
            key=f"doc_own_sb_{doc_id}",
        )
    with c_b:
        st.write("")
        st.write("")
        if st.button("Speichern", key=f"doc_own_go_{doc_id}"):
            _, pid = entries[int(pick)]
            set_document_owner(doc_id, person_id=pid)
            st.success("Zuordnung gespeichert.")
            st.rerun()


def _document_owner_label(doc: dict[str, Any]) -> str:
    ok = (doc.get("owner_kind") or "").strip()
    if not ok:
        return "— noch nicht zugeordnet —"
    if ok == "person" and doc.get("owner_person_id") is not None:
        pid = int(doc["owner_person_id"])
        for p in list_persons():
            if int(p["id"]) == pid:
                return f"Person: {p.get('name') or pid}"
        return f"Person #{pid}"
    if ok == "household":
        return "— veraltet: bitte Person zuweisen —"
    return "—"




def _render_owner_assignment_queue() -> None:
    q = st.session_state.setdefault("pending_owner_docs", [])
    if not q:
        return
    did = int(q[0])
    doc = get_document(did)
    if not doc:
        q.pop(0)
        return
    if not document_needs_owner(did):
        q.pop(0)
        return
    st.warning(
        f"**Wem gehört dieses Dokument?** #{did} — `{doc.get('original_filename')}`"
    )
    entries: list[tuple[str, int]] = []
    for p in list_persons():
        entries.append((f"Person: {p.get('name')}", int(p["id"])))
    if not entries:
        st.caption("Keine Person in der Datenbank — bitte App neu starten (DB-Init).")
        return
    labels = [e[0] for e in entries]
    choice = st.radio(
        "Zuordnung",
        labels,
        key=f"ownq_pick_{did}",
        horizontal=len(labels) <= 3,
    )
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Zuordnung speichern", type="primary", key=f"ownq_ok_{did}"):
            i = labels.index(choice)
            pid = entries[i][1]
            set_document_owner(did, person_id=pid)
            q.pop(0)
            st.rerun()
    with b2:
        if st.button("Später", key=f"ownq_skip_{did}"):
            q.pop(0)
            st.rerun()
    with st.expander("Neue Person anlegen & zuordnen"):
        nn = st.text_input("Name", key=f"ownq_nn_{did}")
        nr = st.text_input("Rolle (z. B. Kind)", key=f"ownq_nr_{did}")
        if st.button("Person anlegen & zuordnen", key=f"ownq_np_{did}"):
            if not (nn or "").strip():
                st.error("Name eingeben.")
            else:
                pid_new = create_person(name=nn.strip(), role=(nr or "").strip() or None)
                set_document_owner(did, person_id=pid_new)
                q.pop(0)
                st.rerun()


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
        '<div class="fin-callout-warn"><strong>Zahlstatus</strong> — bitte kurz angeben '
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
        '<div class="fin-callout-info"><strong>Monatsausgaben</strong> — soll dieser Beleg in die '
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
        st.session_state["_llm_done_notify"] = True
        st.rerun()




def main() -> None:
    _configure_json_logging()
    st.set_page_config(
        page_title="Finanzen — Dokumenten-Organizer",
        layout="wide",
        page_icon="📄",
    )
    inject_pwa_tags()
    inject_fin_ui_styles()
    init_db()
    _drain_pending_llm_job()
    _maybe_flush_llm_notify()
    if "auto_matter_after_llm" not in st.session_state:
        st.session_state.auto_matter_after_llm = True
    if "current_nav" not in st.session_state:
        st.session_state.current_nav = "home"
    if "docu_context_key" not in st.session_state:
        st.session_state.docu_context_key = "household"
    elif str(st.session_state.docu_context_key).startswith("household:"):
        st.session_state.docu_context_key = "household"
    maybe_show_home_overlay()

    st.markdown('<div class="fin-app-wrap">', unsafe_allow_html=True)
    render_global_header_bar(
        apply_import_owner=_apply_import_owner,
        enqueue_payment=_enqueue_payment_prompt,
    )
    nav_c, main_c = st.columns([0.28, 0.72], gap="medium")
    with nav_c:
        render_navigation_column()

    with main_c:
        _render_payment_status_queue()
        _render_monthly_expense_queue()
        _render_owner_assignment_queue()
        ctx_k = _docu_context_key()
        nav_now = st.session_state.get("current_nav", "home")
        if nav_now == "home":
            all_rows = list_documents()
            render_fin_dashboard(filter_documents_by_context(all_rows, ctx_k))
            if ctx_k == "household":
                st.caption(
                    "**Gesamter Haushalt:** Nur **Auswertung** über alle Personen (Einnahmen, Ausgaben, …). "
                    "PDFs und Dokumente können dem Haushalt **nicht** zugeordnet werden — bitte eine **Person** wählen oder nach dem Import zuordnen."
                )
            agg = aggregate_owner_totals(all_rows)
            tb = agg.get("totals_by_key") or {}
            if tb:
                with st.expander("Ausgaben nach Zuordnung (alle Belege, nicht nach Kontext gefiltert)", expanded=False):
                    st.caption(
                        "Summen aus KI-Betrag und Ausgaben-Ordnern — gleiche Logik wie Dashboard-Kacheln."
                    )
                    for k, v in sorted(tb.items(), key=lambda x: -x[1]):
                        label = k
                        if k.startswith("person:"):
                            pid = int(k.split(":", 1)[1])
                            label = next(
                                (f"{p.get('name')} (Person)" for p in list_persons() if int(p["id"]) == pid),
                                k,
                            )
                        elif k == "unassigned":
                            label = "Noch nicht zugeordnet"
                        st.write(f"**{label}:** {_fmt_de_eur(float(v))}")
                    st.write(f"**Summe:** {_fmt_de_eur(agg['grand_expense_eur'])}")
        else:
            st.markdown(
                '<div class="fin-card"><p style="margin:0;color:#cbd5e1;font-size:1rem;">'
                "PDFs erfassen, Text lokal auslesen, mit KI strukturieren und über Kennungen "
                "zu <strong style=\"color:#5eead4;\">Vorgängen</strong> bündeln."
                "</p></div>",
                unsafe_allow_html=True,
            )
    
        tab_inbox, tab_docs, tab_matters = st.tabs(["Posteingang", "Dokumente", "Vorgänge"])
    
        with tab_inbox:
            st.subheader("Posteingang vom Server")
            st.write(
                "Wenn dein Hosting einen gemeinsamen **Posteingang-Ordner** bereitstellt, "
                "lege dort PDFs ab und importiere sie mit **Jetzt einlesen**. "
                "Vom Rechner: **PDF hochladen** in der **Kopfzeile**."
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
                            rid = int(r["id"])
                            _apply_import_owner(rid)
                            _enqueue_payment_prompt(rid)
            st.divider()
            pdfs = sorted(INBOX_DIR.glob("*.pdf")) if INBOX_DIR.exists() else []
            st.write(f"Aktuell **{len(pdfs)}** PDF(s) im Posteingang.")
    
        with tab_docs:
            nav_key = st.session_state.get("current_nav", "home")
            st.subheader(NAV_LABELS.get(nav_key, "Dokumente"))
            rows = filter_documents_by_context(
                list_documents_for_nav(nav_key if nav_key != "home" else None),
                ctx_k,
            )
            if not rows:
                st.info(
                    "Noch keine Dokumente in diesem Bereich. PDFs in der **Kopfzeile** oder "
                    "Tab **Posteingang** importieren, dann KI-Analyse."
                )
            else:
                flat_map: dict[str, int] = {}
                if nav_key == "stromanbieter":
                    by_sub_fm: dict[str | None, list] = defaultdict(list)
                    for r in rows:
                        by_sub_fm[r.get("folder_sub")].append(r)
                    ordered_fm = sorted(by_sub_fm.keys(), key=lambda x: (x is None, (x or "")))
                    for sub in ordered_fm:
                        gname = sub if sub else "Ohne Anbietername"
                        for r in sorted(by_sub_fm[sub], key=lambda x: -int(x["id"])):
                            flat_map[f'#{r["id"]} — {r["original_filename"]} · {gname}'] = int(r["id"])
                else:
                    for r in rows:
                        flat_map[f'#{r["id"]} — {r["original_filename"]}'] = int(r["id"])

                ordered_labels = sorted(flat_map.keys(), key=lambda lab: -flat_map[lab])
                scen_labels_map = dict(EMAIL_SCENARIO_CHOICES)
                out_key = f"email_draft_out_{nav_key}"
                with st.expander("E-Mail-Entwurf (KI, mehrere Dokumente)", expanded=False):
                    st.caption(
                        "Nur Vorschlag — kein automatischer Versand. Keine Rechtsberatung; Inhalte prüfen. "
                        "Extrahierte Felder werden an die KI übermittelt (wie im Chat)."
                    )
                    pick_em = st.multiselect(
                        "Dokumente einbeziehen",
                        options=ordered_labels,
                        default=[],
                        key=f"email_draft_ms_{nav_key}",
                    )
                    scen_i = st.selectbox(
                        "Anlass",
                        [k for k, _ in EMAIL_SCENARIO_CHOICES],
                        format_func=lambda k: scen_labels_map[k],
                        key=f"email_draft_sc_{nav_key}",
                    )
                    em_notes = st.text_area(
                        "Zusätzliche Hinweise",
                        placeholder="z. B. gewünschte Laufzeit, bereits erfolgte Teilzahlungen …",
                        key=f"email_draft_notes_{nav_key}",
                        height=88,
                    )
                    if st.button("Entwurf erzeugen", key=f"email_draft_go_{nav_key}"):
                        if not pick_em:
                            st.warning("Bitte mindestens ein Dokument auswählen.")
                        else:
                            ids_em = [flat_map[x] for x in pick_em]
                            try:
                                with st.spinner("KI formuliert …"):
                                    st.session_state[out_key] = run_email_draft(
                                        doc_ids=ids_em,
                                        scenario_key=scen_i,
                                        user_notes=em_notes,
                                    )
                            except Exception as e:
                                st.error(str(e))
                if st.session_state.get(out_key):
                    st.markdown("##### Letzter E-Mail-Entwurf (KI)")
                    st.markdown(st.session_state[out_key])

                with st.expander("Export (ZIP / CSV)", expanded=False):
                    pick_z = st.multiselect(
                        "Dokumente für Export",
                        options=ordered_labels,
                        default=[],
                        key=f"exp_ms_{nav_key}",
                    )
                    if pick_z:
                        ids_z = [flat_map[x] for x in pick_z]
                        ez1, ez2 = st.columns(2)
                        zdata = build_zip_bytes(ids_z)
                        with ez1:
                            st.download_button(
                                "ZIP (PDFs)",
                                zdata,
                                file_name="export_pdfs.zip",
                                mime="application/zip",
                                key=f"dlz_{nav_key}",
                                use_container_width=True,
                            )
                        cdata = build_csv_bytes(ids_z)
                        with ez2:
                            st.download_button(
                                "CSV (Metadaten)",
                                cdata,
                                file_name="export_metadaten.csv",
                                mime="text/csv",
                                key=f"dlc_{nav_key}",
                                use_container_width=True,
                            )
                    else:
                        st.caption("Dokumente auswählen, dann ZIP oder CSV herunterladen.")

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
                else:
                    id_opts = {f'#{r["id"]} — {r["original_filename"]}': r["id"] for r in rows}
                keys_list = list(id_opts.keys())
                want = st.session_state.get("jump_doc_id")
                sel_index = 0
                if want is not None and keys_list:
                    ids_list = list(id_opts.values())
                    wi = int(want)
                    if wi in ids_list:
                        sel_index = int(ids_list.index(wi))
                if want is not None:
                    st.session_state.pop("jump_doc_id", None)
                sel_index = max(0, min(sel_index, len(keys_list) - 1)) if keys_list else 0
                choice = st.selectbox(
                    "Dokument wählen",
                    keys_list,
                    index=sel_index,
                    key=f"docpick_sb_{nav_key}",
                )
                doc_id = id_opts[choice]
                doc = get_document(doc_id)
                ext = get_extraction(doc_id)
                if st.session_state.get("docu_show_llm_ok") == doc_id:
                    st.success("Analyse gespeichert — Details im **KI-Chat (LUMO)** in der linken Sidebar.")
                    del st.session_state["docu_show_llm_ok"]

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### Metadaten")
                    st.write(f"**Datei:** {doc['original_filename']}")
                    st.caption(f"**Zuordnung:** {_document_owner_label(doc)}")
                    _render_document_owner_editor(doc_id, doc)
                    st.write(f"**Zeichen Text:** {doc['text_char_count']}")
                    with st.expander("Technische Details", expanded=False):
                        st.code(doc["stored_path"] or "—", language=None)
                        st.caption(f"SHA256 (Kurz): `{doc['sha256'][:16]}…`")
                    if doc.get("needs_ocr"):
                        st.error(
                            "Sehr wenig Text extrahiert – vermutlich gescanntes PDF. "
                            "Optional: `DOCU_ENABLE_OCR=1`, Tesseract + `pdf2image`/Poppler installieren "
                            "(siehe README)."
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
                    render_document_download(doc, key_prefix="tabdoc")
                    if st.button("Ins Archiv (aus Listen nehmen)", key=f"arch_{doc_id}"):
                        set_document_archived(doc_id, True)
                        st.success("Dokument archiviert — im Papierkorb (Navigation) wiederherstellbar.")
                        st.rerun()
                    with st.expander("Optional: E-Mail per SMTP senden", expanded=False):
                        if not smtp_configured():
                            st.caption(
                                "Für **Gmail**: `DOCU_SMTP_HOST=smtp.gmail.com`, Port `587`, Nutzer und Absender = "
                                "deine Gmail-Adresse, Passwort = **Google-App-Passwort** (16 Zeichen). "
                                "Alle fünf `DOCU_SMTP_*` in Railway/.env setzen — Details im **README**."
                            )
                        else:
                            to_a = st.text_input("An (E-Mail)", key=f"smtp_to_{doc_id}")
                            subj = st.text_input("Betreff", key=f"smtp_sub_{doc_id}")
                            body = st.text_area("Text", key=f"smtp_body_{doc_id}", height=160)
                            conf = st.checkbox("Versand ausdrücklich bestätigen", key=f"smtp_cf_{doc_id}")
                            if st.button("Senden", key=f"smtp_go_{doc_id}"):
                                if not conf:
                                    st.warning("Bitte Versand bestätigen.")
                                else:
                                    try:
                                        send_email_smtp(to_addr=to_a, subject=subj, body=body)
                                        st.success("E-Mail wurde über SMTP versendet.")
                                    except Exception as e:
                                        st.error(str(e))
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
                        render_document_download(d, key_prefix=f"matter{m['id']}")
                        if st.button("Entknüpfen", key=f"um_{m['id']}_{d['id']}"):
                            unlink_document_from_matter(int(d["id"]), int(m["id"]))
                            st.rerun()
    
if __name__ == "__main__":
    main()
