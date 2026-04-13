"""Scan inbox and persist documents."""
from __future__ import annotations

import json
import shutil
from typing import Any

from db import document_by_sha256, insert_document
from ingest import archive_destination, extract_pdf_text, file_sha256, iter_inbox_pdfs


def import_inbox_pdfs() -> list[dict[str, Any]]:
    """Copy each new PDF from inbox to archive, extract text, insert row. Skips duplicates by SHA256."""
    results: list[dict[str, Any]] = []
    for pdf in iter_inbox_pdfs():
        sha = file_sha256(pdf)
        if document_by_sha256(sha):
            results.append(
                {
                    "status": "duplicate",
                    "filename": pdf.name,
                    "sha256": sha,
                }
            )
            continue
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
        results.append(
            {
                "status": "imported",
                "id": doc_id,
                "filename": pdf.name,
                "stored_path": str(dest),
                "needs_ocr": needs_ocr,
                "text_preview": (text[:500] + "…") if len(text) > 500 else text,
            }
        )
    return results


def run_llm_on_document(doc_id: int) -> dict[str, Any]:
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
    upsert_extraction(doc_id, **payload)
    replace_reference_keys(doc_id, payload["reference_ids"])
    return normalized
