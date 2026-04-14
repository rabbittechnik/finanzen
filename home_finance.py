"""KPI-Berechnungen für die Home-Ansicht: Einnahmen, Schuldensumme (dedupliziert), Ausgaben."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from nav_logic import _norm_kind

EXPENSE_NAV_FOLDERS = frozenset(
    {
        "rechnungen",
        "stromanbieter",
        "haustelefon_internet",
        "handyvertraege",
        "versicherungsscheine",
        "schriftverkehr",
        "amtsgericht",
    }
)


def is_expense_monthly_prompt_candidate(ext: dict[str, Any]) -> bool:
    """Zahlungsbelege (Rechnungen etc.), keine Mahnung/Lohn."""
    kind = _norm_kind(ext.get("document_kind"))
    if kind in ("reminder", "payment_demand", "payslip"):
        return False
    nf = ext.get("nav_folder") or ""
    return nf in EXPENSE_NAV_FOLDERS


def counts_toward_monthly_expenses_row(row: dict[str, Any]) -> bool:
    """0 = explizit nicht in Monatsausgaben; NULL/1 = zählen."""
    v = row.get("include_monthly_expense")
    if v is None:
        return True
    try:
        return int(v) != 0
    except (TypeError, ValueError):
        return True


def _month_bounds(today: date | None = None) -> tuple[date, date]:
    t = today or date.today()
    start = date(t.year, t.month, 1)
    if t.month == 12:
        end = date(t.year, 12, 31)
    else:
        end = date(t.year, t.month + 1, 1)
        end = date.fromordinal(end.toordinal() - 1)
    return start, end


def _parse_doc_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _parse_created_month(created_at: str | None) -> tuple[int, int] | None:
    if not created_at:
        return None
    try:
        d = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        return (d.year, d.month)
    except ValueError:
        try:
            d = date.fromisoformat(str(created_at)[:10])
            return (d.year, d.month)
        except ValueError:
            return None


def _in_calendar_month(
    document_date: str | None, created_at: str | None, y: int, m: int
) -> bool:
    dd = _parse_doc_date(document_date)
    if dd and dd.year == y and dd.month == m:
        return True
    cm = _parse_created_month(created_at)
    if cm and cm == (y, m):
        return True
    return False


def _max_eur_from_amounts_json(amounts_json: str | None) -> float:
    try:
        arr = json.loads(amounts_json or "[]")
    except json.JSONDecodeError:
        return 0.0
    best = 0.0
    for a in arr:
        if not isinstance(a, dict):
            continue
        cur = str(a.get("currency") or "").upper()
        if cur and cur not in ("EUR", "€"):
            continue
        v = a.get("value")
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > best:
            best = fv
    return best


def _primary_eur(row: dict[str, Any]) -> float:
    v = row.get("primary_amount_eur")
    if v is not None:
        try:
            fv = float(v)
            if fv > 0:
                return fv
        except (TypeError, ValueError):
            pass
    return _max_eur_from_amounts_json(row.get("amounts_json"))


def _payslip_net(row: dict[str, Any]) -> float:
    v = row.get("payslip_net_income_eur")
    if v is not None:
        try:
            fv = float(v)
            if fv > 0:
                return fv
        except (TypeError, ValueError):
            pass
    return _max_eur_from_amounts_json(row.get("amounts_json"))


def _sender_slug(name: str | None) -> str:
    return " ".join((name or "").strip().lower().split())


def _refs_list(row: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        raw = json.loads(row.get("reference_ids_json") or "[]")
    except json.JSONDecodeError:
        return []
    return [r for r in raw if isinstance(r, dict)]


def _first_ref_val(refs: list[dict[str, Any]], id_type: str) -> str | None:
    for r in refs:
        if r.get("id_type") == id_type:
            v = str(r.get("value") or "").strip()
            if v:
                return v
    return None


def debt_identity_key(doc_id: int, row: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    """
    Eine Forderung pro Aktenzeichen (priorisiert), sonst Kunde+Rechnung, sonst eindeutig pro Dokument.
    Gleiche Kanzlei, verschiedene Aktenzeichen → verschiedene Keys.
    """
    sender = _sender_slug(row.get("sender_name"))
    case_ref = _first_ref_val(refs, "case_reference")
    if case_ref:
        return f"{sender}|case:{case_ref}"
    cust = _first_ref_val(refs, "customer_number")
    inv = _first_ref_val(refs, "invoice_number")
    if cust and inv:
        return f"{sender}|cust:{cust}|inv:{inv}"
    if cust:
        return f"{sender}|cust:{cust}"
    if inv:
        return f"{sender}|inv:{inv}"
    return f"{sender}|doc:{doc_id}"


def _is_debt_candidate(row: dict[str, Any]) -> bool:
    kind = _norm_kind(row.get("document_kind"))
    nav = row.get("nav_folder") or ""
    if kind in ("reminder", "payment_demand"):
        return True
    if nav == "mahnungen":
        return True
    return False


def _is_paid(row: dict[str, Any], doc: dict[str, Any]) -> bool:
    zs = (row.get("zahlstatus") or doc.get("initial_zahlstatus") or "").lower()
    return zs == "bezahlt"


class DSU:
    def __init__(self) -> None:
        self.p: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.p.setdefault(x, x)
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        self.p[rb] = ra


def _row_is_extraction_join(r: dict[str, Any]) -> bool:
    return r.get("category") is not None or r.get("document_kind") is not None


@dataclass
class HomeFinanceStats:
    income_month_eur: float
    debt_open_eur: float
    expense_month_eur: float
    debt_groups: int
    month_label: str


_DE_MONTHS = (
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def compute_home_stats(rows: list[dict[str, Any]]) -> HomeFinanceStats:
    """
    rows: Ergebnis von list_documents() (JOIN extractions).
    """
    start, _end = _month_bounds()
    y, m = start.year, start.month
    month_label = f"{_DE_MONTHS[m]} {y}"

    income = 0.0
    expenses = 0.0

    debt_doc_ids: list[int] = []
    debt_rows: dict[int, dict[str, Any]] = {}
    debt_docs_meta: dict[int, dict[str, Any]] = {}

    for r in rows:
        did = int(r["id"])
        ext_slice = {
            "document_id": did,
            "category": r.get("category"),
            "sender_name": r.get("sender_name"),
            "sender_role": r.get("sender_role"),
            "subject": r.get("subject"),
            "document_date": r.get("document_date"),
            "amounts_json": r.get("amounts_json"),
            "reference_ids_json": r.get("reference_ids_json"),
            "summary_de": r.get("summary_de"),
            "nav_folder": r.get("nav_folder"),
            "document_kind": r.get("document_kind"),
            "zahlstatus": r.get("zahlstatus"),
            "primary_amount_eur": r.get("primary_amount_eur"),
            "payslip_net_income_eur": r.get("payslip_net_income_eur"),
        }
        if not _row_is_extraction_join(r):
            continue

        if _norm_kind(r.get("document_kind")) == "payslip" or r.get("nav_folder") == "lohnabrechnungen":
            if _in_calendar_month(r.get("document_date"), r.get("created_at"), y, m):
                income += _payslip_net({**r, **ext_slice})

        nf = r.get("nav_folder") or ""
        if nf in EXPENSE_NAV_FOLDERS and _norm_kind(r.get("document_kind")) not in (
            "payslip",
            "reminder",
            "payment_demand",
        ):
            if _in_calendar_month(r.get("document_date"), r.get("created_at"), y, m):
                if counts_toward_monthly_expenses_row(r):
                    expenses += _primary_eur(r)

        if _is_debt_candidate(ext_slice) and not _is_paid(ext_slice, r):
            debt_doc_ids.append(did)
            debt_rows[did] = ext_slice
            debt_docs_meta[did] = r

    dsu = DSU()
    key_to_rep: dict[str, int] = {}

    for did in debt_doc_ids:
        row = {**debt_rows[did], **debt_docs_meta[did]}
        refs = _refs_list(row)
        key = debt_identity_key(did, row, refs)
        if key in key_to_rep:
            dsu.union(did, key_to_rep[key])
        else:
            key_to_rep[key] = did

    for did in debt_doc_ids:
        ext_row = debt_rows[did]
        pid = ext_row.get("linked_payment_doc_id")
        if pid and int(pid) in debt_rows:
            dsu.union(did, int(pid))

    components: dict[int, list[int]] = defaultdict(list)
    for did in debt_doc_ids:
        components[dsu.find(did)].append(did)

    debt_sum = 0.0
    for _, members in components.items():

        def _doc_sort_key(mid: int) -> tuple[date, int]:
            mr = {**debt_rows[mid], **debt_docs_meta[mid]}
            dd = _parse_doc_date(mr.get("document_date")) or date(1900, 1, 1)
            return (dd, mid)

        lead_id = max(members, key=_doc_sort_key)
        lead_row = {**debt_rows[lead_id], **debt_docs_meta[lead_id]}
        debt_sum += _primary_eur(lead_row)

    return HomeFinanceStats(
        income_month_eur=income,
        debt_open_eur=debt_sum,
        expense_month_eur=expenses,
        debt_groups=len(components),
        month_label=month_label,
    )
