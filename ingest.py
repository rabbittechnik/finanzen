"""Import PDFs from inbox: hash dedup, text extraction, archive copy."""
from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from pypdf import PdfReader

from config import ARCHIVE_DIR, INBOX_DIR


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
