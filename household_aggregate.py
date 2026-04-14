"""Summen nach Person / Haushalt (Ausgaben aus Extraktion + nav_folder)."""
from __future__ import annotations

from typing import Any

import home_finance as hf
from nav_logic import _norm_kind


def _amount(r: dict[str, Any]) -> float:
    v = r.get("primary_amount_eur")
    try:
        if v is None:
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _is_expense_row(r: dict[str, Any]) -> bool:
    if not hf._row_is_extraction_join(r):
        return False
    nf = r.get("nav_folder") or ""
    if nf not in hf.EXPENSE_NAV_FOLDERS:
        return False
    if _norm_kind(r.get("document_kind")) in ("payslip", "reminder", "payment_demand"):
        return False
    return True


def aggregate_owner_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Summiert primary_amount_eur für Ausgaben-Belege nach Zuordnung (nur Personen).
    Schlüssel: 'person:{id}' | 'unassigned'
    """
    totals: dict[str, float] = {}
    for r in rows:
        if not _is_expense_row(r):
            continue
        a = _amount(r)
        ok = (r.get("owner_kind") or "").strip()
        if ok == "person" and r.get("owner_person_id") is not None:
            k = f"person:{int(r['owner_person_id'])}"
        else:
            k = "unassigned"
        totals[k] = totals.get(k, 0.0) + a
    return {"totals_by_key": totals, "grand_expense_eur": sum(totals.values())}
