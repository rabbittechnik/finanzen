"""Import PDFs from inbox: hash dedup, text extraction, archive copy."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

from pypdf import PdfReader

from config import ARCHIVE_DIR, INBOX_DIR


def try_ocr_pdf(path: Path, *, max_pages: int = 8) -> str:
    """
    Optional OCR (Tesseract) für gescannte PDFs.
    Benötigt: ``DOCU_ENABLE_OCR=1``, installiertes Tesseract, optional ``pdf2image`` + Poppler.
    """
    try:
        import pytesseract  # type: ignore[import-untyped]
        from pdf2image import convert_from_path  # type: ignore[import-untyped]
    except ImportError:
        return ""
    try:
        images = convert_from_path(str(path), first_page=1, last_page=max(1, max_pages))
    except Exception:
        return ""
    parts: list[str] = []
    for im in images:
        try:
            parts.append(pytesseract.image_to_string(im, lang="deu+eng") or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf_text(path: Path, max_pages: int = 50) -> tuple[str, bool]:
    """
    Returns (text, needs_ocr).
    needs_ocr True when extracted text is very short (likely scan).
    """
    text_parts: list[str] = []
    try:
        reader = PdfReader(str(path))
        n = min(len(reader.pages), max_pages)
        for i in range(n):
            page = reader.pages[i]
            t = page.extract_text() or ""
            text_parts.append(t)
    except Exception:
        return "", True
    full = "\n".join(text_parts).strip()
    # Heuristic: scanned PDFs often yield almost nothing
    needs = len(full) < 40
    if needs and os.environ.get("DOCU_ENABLE_OCR", "").strip() in ("1", "true", "yes"):
        ocr_text = try_ocr_pdf(path, max_pages=min(10, max_pages))
        if len(ocr_text) > len(full):
            full = ocr_text
            needs = len(full) < 40
    return full, needs


def iter_inbox_pdfs() -> list[Path]:
    if not INBOX_DIR.exists():
        return []
    return sorted(INBOX_DIR.glob("*.pdf"), key=lambda p: p.name.lower())


def archive_destination(original: Path) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = original.stem[:80]
    unique = uuid.uuid4().hex[:10]
    return ARCHIVE_DIR / f"{unique}_{safe_stem}{original.suffix.lower()}"


def safe_inbox_filename(original_name: str) -> str:
    """Dateiname nur für den Posteingang; verhindert Pfad-Manipulation."""
    base = Path(original_name).name.strip()
    if not base.lower().endswith(".pdf"):
        base = (base + ".pdf") if base else "upload.pdf"
    stem, suf = base[:-4], base[-4:].lower()
    stem = re.sub(r"[^\w\s.\-äöüÄÖÜß]+", "_", stem, flags=re.UNICODE).strip("._ ") or "scan"
    stem = stem[:120]
    return f"{stem}{suf}"


def save_uploaded_pdf_to_inbox(data: bytes, original_name: str) -> Path:
    """Schreibt Bytes in den Posteingang; bei Namenskollision ein kurzes Suffix."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_inbox_filename(original_name)
    dest = INBOX_DIR / name
    if dest.exists():
        dest = INBOX_DIR / f"{dest.stem}_{uuid.uuid4().hex[:6]}{dest.suffix}"
    dest.write_bytes(data)
    return dest
