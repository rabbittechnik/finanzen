"""Layout- und Vergleichslogik für KI-gesteuerte Dokumentenansicht (Streamlit)."""
from __future__ import annotations

from typing import Any

from db import get_document, get_extraction


def _safe_amount(ext: dict[str, Any] | None) -> float | None:
    if not ext:
        return None
    v = ext.get("primary_amount_eur")
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_layout_instruction(
    *,
    mode: str,
    device: str,
    highlight_differences: bool,
    group_count: int,
    doc_total: int,
) -> dict[str, Any]:
    """
    Deterministische Layout-Regeln (keine freien KI-Layout-Raten).
    compare + mindestens zwei Gruppen → zwei Spalten (Gruppen nebeneinander).
    """
    dev = (device or "pc").strip().lower()
    if dev not in ("pc", "tablet", "tv"):
        dev = "pc"
    m = (mode or "browse").strip().lower()
    if m not in ("browse", "compare"):
        m = "browse"
    hi = bool(highlight_differences)

    if m == "compare" and group_count >= 2:
        return {
            "device": dev,
            "layout": "side_by_side",
            "columns": 2,
            "mode": "compare",
            "highlight_differences": hi,
        }
    if doc_total <= 1:
        return {
            "device": dev,
            "layout": "single",
            "columns": 1,
            "mode": "browse",
            "highlight_differences": False,
        }
    if doc_total == 2:
        return {
            "device": dev,
            "layout": "side_by_side",
            "columns": 2,
            "mode": m,
            "highlight_differences": hi and doc_total == 2,
        }
    if doc_total == 3:
        return {
            "device": dev,
            "layout": "grid",
            "columns": 3,
            "mode": "browse",
            "highlight_differences": hi,
        }
    return {
        "device": dev,
        "layout": "grid",
        "columns": 2,
        "mode": "browse",
        "highlight_differences": hi,
    }


def flatten_group_document_ids(groups: list[dict[str, Any]]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for g in groups:
        for raw in g.get("document_ids") or []:
            did = int(raw)
            if did not in seen:
                seen.add(did)
                out.append(did)
    return out


def compare_groups_snapshot(groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Metriken nur aus DB; keine erfundenen Werte."""
    rows: list[dict[str, Any]] = []
    for g in groups:
        label = (g.get("label") or "Gruppe").strip() or "Gruppe"
        for raw in g.get("document_ids") or []:
            did = int(raw)
            doc = get_document(did)
            if not doc:
                continue
            ext = get_extraction(did)
            amt = _safe_amount(ext)
            rows.append(
                {
                    "group_label": label,
                    "document_id": did,
                    "amount_eur": amt,
                    "date": (ext or {}).get("document_date") if ext else None,
                    "vendor": (ext or {}).get("sender_name") if ext else None,
                    "summary": ((ext or {}).get("summary_de") or "")[:160] if ext else "",
                    "filename": doc.get("original_filename"),
                }
            )
    if not rows:
        return None
    highest_id: int | None = None
    best: float | None = None
    for r in rows:
        a = r.get("amount_eur")
        if a is None:
            continue
        if best is None or a > best:
            best = a
            highest_id = int(r["document_id"])

    diff_line: str | None = None
    amounts_only = [r for r in rows if r.get("amount_eur") is not None]
    if len(amounts_only) == 2:
        a0, a1 = float(amounts_only[0]["amount_eur"]), float(amounts_only[1]["amount_eur"])
        d = a0 - a1
        diff_line = f"Differenz ({amounts_only[0]['group_label']} vs. {amounts_only[1]['group_label']}): {d:+.2f} €"

    return {
        "documents": rows,
        "highest_amount_document_id": highest_id,
        "difference_summary": diff_line,
    }
