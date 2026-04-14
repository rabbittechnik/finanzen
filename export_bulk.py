"""ZIP- und CSV-Export mehrerer Dokumente."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from db import get_document, get_extraction
from download_button import resolve_downloadable_path


def _unique_arc_name(filename: str, used: dict[str, int]) -> str:
    fn = filename or "document.bin"
    if fn not in used:
        used[fn] = 0
        return fn
    used[fn] += 1
    p = Path(fn)
    return f"{p.stem}_{used[fn]}{p.suffix}"


def build_zip_bytes(doc_ids: list[int]) -> bytes:
    buf = io.BytesIO()
    used: dict[str, int] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for did in sorted({int(x) for x in doc_ids}):
            d = get_document(did)
            if not d:
                continue
            p = resolve_downloadable_path(d.get("stored_path"))
            if p is None:
                continue
            arc = _unique_arc_name(str(d.get("original_filename") or p.name), used)
            zf.writestr(arc, p.read_bytes())
    return buf.getvalue()


def build_csv_bytes(doc_ids: list[int]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(
        [
            "id",
            "filename",
            "document_date",
            "sender",
            "subject",
            "summary",
            "kind",
            "nav_folder",
            "betrag_hinweis",
        ]
    )
    for did in sorted({int(x) for x in doc_ids}):
        d = get_document(did)
        if not d:
            continue
        ext = get_extraction(did) or {}
        amt = ""
        try:
            arr = json.loads(ext.get("amounts_json") or "[]")
            if isinstance(arr, list) and arr:
                amt = json.dumps(arr[:3], ensure_ascii=False)[:200]
        except Exception:
            pass
        w.writerow(
            [
                did,
                d.get("original_filename") or "",
                ext.get("document_date") or "",
                ext.get("sender_name") or "",
                ext.get("subject") or "",
                ((ext.get("summary_de") or "")[:800]),
                ext.get("document_kind") or "",
                ext.get("nav_folder") or "",
                amt,
            ]
        )
    return out.getvalue().encode("utf-8-sig")
