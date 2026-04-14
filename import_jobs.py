"""Scan inbox and persist documents."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from db import (
    clear_document_initial_zahlstatus,
    create_matter,
    document_by_sha256,
    document_ids_for_reference_key,
    find_matter_for_reference_key,
    get_extraction,
    insert_document,
    link_document_to_matter,
    try_auto_link_invoice_reminder,
    try_auto_link_same_case_reference,
)
from ingest import archive_destination, extract_pdf_text, file_sha256, iter_inbox_pdfs


def import_one_pdf(pdf: Path) -> dict[str, Any]:
    """Ein PDF aus dem Posteingang ins Archiv kopieren, Text extrahieren, in DB anlegen."""
    if pdf.suffix.lower() != ".pdf":
        return {"status": "error", "filename": pdf.name, "message": "Kein PDF"}
    sha = file_sha256(pdf)
    if document_by_sha256(sha):
        return {
            "status": "duplicate",
            "filename": pdf.name,
            "sha256": sha,
        }
    dest = archive_destination(pdf)
    shutil.copy2(pdf, dest)
    text, needs_ocr = extract_pdf_text(dest)
    doc_id = insert_document(
        original_filename=pdf.name,
        stored_path=str(dest.resolve()),
        sha256=sha,
        extracted_text=text,
        needs_ocr=needs_ocr,
    )
    return {
        "status": "imported",
        "id": doc_id,
        "filename": pdf.name,
        "stored_path": str(dest),
        "needs_ocr": needs_ocr,
        "text_preview": (text[:500] + "…") if len(text) > 500 else text,
    }


def import_inbox_pdfs() -> list[dict[str, Any]]:
    """Copy each new PDF from inbox to archive, extract text, insert row. Skips duplicates by SHA256."""
    return [import_one_pdf(pdf) for pdf in iter_inbox_pdfs()]


def auto_assign_matter_from_extraction(doc_id: int) -> dict[str, Any] | None:
    """
    Ordnet Dokumente mit gleicher Kunden- oder Vertragsnummer einem gemeinsamen Vorgang zu.
    Nutzt nur bereits gespeicherte Extraktion + reference_keys.
    """
    from db import get_extraction

    ext = get_extraction(doc_id)
    if not ext:
        return None
    try:
        refs: list[dict[str, Any]] = json.loads(ext["reference_ids_json"] or "[]")
    except json.JSONDecodeError:
        return None
    primary: dict[str, Any] | None = None
    for prefer in ("customer_number", "contract_number"):
        for r in refs:
            if not isinstance(r, dict):
                continue
            if r.get("id_type") != prefer:
                continue
            val = str(r.get("value") or "").strip()
            if val:
                primary = {"id_type": prefer, "value": val}
                break
        if primary:
            break
    if not primary:
        return None
    id_type = str(primary["id_type"])
    key_value = str(primary["value"])
    sender = (ext.get("sender_name") or "").strip() or "Absender unbekannt"
    label = "Kundennr." if id_type == "customer_number" else "Vertragsnr."
    title = f"{sender} — {label} {key_value}"[:200]

    matter_id = find_matter_for_reference_key(id_type, key_value)
    if matter_id is None:
        matter_id = create_matter(title)
    doc_ids = document_ids_for_reference_key(id_type, key_value)
    for oid in doc_ids:
        link_document_to_matter(oid, matter_id)
    return {
        "matter_id": matter_id,
        "title": title,
        "id_type": id_type,
        "key_value": key_value,
        "linked_count": len(doc_ids),
    }


def run_llm_on_document(doc_id: int, *, auto_matter: bool = True) -> dict[str, Any]:
    """Load text, call LLM, save extraction + reference keys."""
    from db import (
        get_document,
        replace_reference_keys,
        upsert_extraction,
    )
    from extract_llm import extraction_to_db_payload, extract_document_fields

    doc = get_document(doc_id)
    if not doc:
        raise ValueError("Dokument nicht gefunden")
    text = doc["extracted_text"] or ""
    normalized = extract_document_fields(text)
    raw_json = json.dumps(normalized, ensure_ascii=False)
    payload = extraction_to_db_payload(normalized, raw_json)
    prev = get_extraction(doc_id)
    prev_zs = (prev.get("zahlstatus") or "").strip() if prev else ""
    if prev:
        if prev.get("linked_payment_doc_id"):
            payload["linked_payment_doc_id"] = prev["linked_payment_doc_id"]
        if prev_zs:
            payload["zahlstatus"] = prev["zahlstatus"]
        if prev.get("include_monthly_expense") is not None:
            payload["include_monthly_expense"] = int(prev["include_monthly_expense"])
    ini = (doc.get("initial_zahlstatus") or "").strip()
    if not (payload.get("zahlstatus") or "").strip() and not prev_zs and ini in ("offen", "bezahlt"):
        payload["zahlstatus"] = ini
    upsert_extraction(doc_id, **payload)
    replace_reference_keys(doc_id, payload["reference_ids"])
    try_auto_link_invoice_reminder(doc_id)
    try_auto_link_same_case_reference(doc_id)
    if ini in ("offen", "bezahlt") and not prev_zs:
        clear_document_initial_zahlstatus(doc_id)
    matter_info: dict[str, Any] | None = None
    if auto_matter:
        matter_info = auto_assign_matter_from_extraction(doc_id)
    if matter_info:
        normalized["_auto_matter"] = matter_info
    return normalized
