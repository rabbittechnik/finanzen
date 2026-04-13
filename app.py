"""Streamlit UI: inbox import, document list, LLM extraction, matters and linking."""
from __future__ import annotations

import json
import os

import streamlit as st
from dotenv import load_dotenv

from config import ARCHIVE_DIR, DATA_DIR, DB_PATH, INBOX_DIR, LLM_TEXT_CHAR_LIMIT
from db import (
    create_matter,
    documents_for_matter,
    find_documents_sharing_keys,
    get_document,
    get_extraction,
    init_db,
    link_document_to_matter,
    list_documents,
    list_matters,
    matter_ids_for_document,
    unlink_document_from_matter,
)
from import_jobs import import_inbox_pdfs, run_llm_on_document
from privacy_notes import PRIVACY_UI_DE
from home_overlay import maybe_show_home_overlay

load_dotenv()

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


def main() -> None:
    st.set_page_config(page_title="Dokumenten-Organizer", layout="wide")
    init_db()
    maybe_show_home_overlay()

    st.title("Dokumenten-Organizer")
    st.caption("Erfassung, Textauszug, KI-Strukturierung und Vorgänge über gemeinsame Kennungen.")

    with st.sidebar:
        st.subheader("Pfade")
        st.text(f"Daten: {DATA_DIR}")
        st.text(f"Posteingang: {INBOX_DIR}")
        st.text(f"Archiv: {ARCHIVE_DIR}")
        st.text(f"DB: {DB_PATH}")
        st.divider()
        with st.expander("Datenschutz"):
            st.markdown(PRIVACY_UI_DE)
        st.divider()
        key_set = bool(os.environ.get("OPENAI_API_KEY"))
        st.write("API-Schlüssel: " + ("gesetzt" if key_set else "**fehlt** (.env / OPENAI_API_KEY)"))
        st.caption(f"KI-Textlimit: {LLM_TEXT_CHAR_LIMIT} Zeichen")

    tab_inbox, tab_docs, tab_matters = st.tabs(["Posteingang", "Dokumente", "Vorgänge"])

    with tab_inbox:
        st.subheader("PDFs aus Posteingang importieren")
        st.write(
            "Legen Sie PDF-Dateien in den Ordner **inbox** (siehe Sidebar), dann auf **Jetzt einlesen**."
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
        st.divider()
        pdfs = sorted(INBOX_DIR.glob("*.pdf")) if INBOX_DIR.exists() else []
        st.write(f"Aktuell **{len(pdfs)}** PDF(s) im Posteingang.")

    with tab_docs:
        st.subheader("Alle Dokumente")
        rows = list_documents()
        if not rows:
            st.info("Noch keine Dokumente. Importieren Sie PDFs im Tab Posteingang.")
        else:
            id_opts = {f'#{r["id"]} — {r["original_filename"]}': r["id"] for r in rows}
            choice = st.selectbox("Dokument wählen", list(id_opts.keys()))
            doc_id = id_opts[choice]
            doc = get_document(doc_id)
            ext = get_extraction(doc_id)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Metadaten")
                st.write(f"**Datei:** {doc['original_filename']}")
                st.write(f"**Archiv:** `{doc['stored_path']}`")
                st.write(f"**SHA256:** `{doc['sha256'][:16]}…`")
                st.write(f"**Zeichen Text:** {doc['text_char_count']}")
                if doc.get("needs_ocr"):
                    st.error(
                        "Sehr wenig Text extrahiert – vermutlich gescanntes PDF. "
                        "Optional später OCR (z. B. Tesseract) ergänzen."
                    )
                if ext:
                    st.write(
                        f"**Kategorie:** {CATEGORY_DE.get(ext['category'], ext['category'])}"
                    )
                    st.write(f"**Rolle Absender:** {ROLE_DE.get(ext['sender_role'], ext['sender_role'])}")
                    st.write(f"**Absender:** {ext['sender_name'] or '—'}")
                    st.write(f"**Betreff:** {ext['subject'] or '—'}")
                    st.write(f"**Datum:** {ext['document_date'] or '—'}")
                    st.write(f"**Kurzfassung:** {ext['summary_de'] or '—'}")
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
                    try:
                        with st.spinner("KI-Analyse…"):
                            run_llm_on_document(doc_id)
                        st.success("Analyse gespeichert.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

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


if __name__ == "__main__":
    main()
