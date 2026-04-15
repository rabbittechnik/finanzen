"""KPIs und Zeilenlisten für das Finanz-Dashboard (Kacheln + Detail)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import home_finance as hf
from home_finance import EXPENSE_NAV_FOLDERS, compute_home_stats


def _de_month_label(y: int, m: int) -> str:
    return f"{hf._DE_MONTHS[m]} {y}"


def _in_year(document_date: str | None, created_at: str | None, y: int) -> bool:
    dd = hf._parse_doc_date(document_date)
    if dd and dd.year == y:
        return True
    cm = hf._parse_created_month(created_at)
    if cm and cm[0] == y:
        return True
    return False


def _expense_row(
    r: dict[str, Any], *, y: int, m: int, monthly_only: bool | None
) -> bool:
    """Ausgabe-Beleg im Kalendermonat (ohne Lohn/Mahnung). monthly_only True = nur monatlich; None = alle."""
    if not hf._row_is_extraction_join(r):
        return False
    nf = r.get("nav_folder") or ""
    if nf not in EXPENSE_NAV_FOLDERS:
        return False
    if hf._norm_kind(r.get("document_kind")) in ("payslip", "reminder", "payment_demand"):
        return False
    if not hf._in_calendar_month(r.get("document_date"), r.get("created_at"), y, m):
        return False
    if monthly_only is True and not hf.counts_toward_monthly_expenses_row(r):
        return False
    return True


def _income_row(r: dict[str, Any], y: int, m: int) -> bool:
    if not hf._row_is_extraction_join(r):
        return False
    if not (
        hf._norm_kind(r.get("document_kind")) == "payslip" or r.get("nav_folder") == "lohnabrechnungen"
    ):
        return False
    return hf._in_calendar_month(r.get("document_date"), r.get("created_at"), y, m)


def _nav_expense_row(r: dict[str, Any], nav: str, y: int, m: int) -> bool:
    if (r.get("nav_folder") or "") != nav:
        return False
    return _expense_row(r, y=y, m=m, monthly_only=None)


_OEPNV_KW = (
    "deutschlandticket",
    "monatskarte",
    "öpnv",
    "oepnv",
    "bvg",
    "vbb",
    "nahverkehr",
    "öffi",
    "ticket",
    "abo",
)


def _oepnv_row(r: dict[str, Any], y: int, m: int) -> bool:
    if not _expense_row(r, y=y, m=m, monthly_only=None):
        return False
    if (r.get("nav_folder") or "") != "schriftverkehr":
        return False
    blob = f"{r.get('subject') or ''} {r.get('summary_de') or ''}".lower()
    return any(k in blob for k in _OEPNV_KW)


@dataclass
class DashboardMetrics:
    year: int
    month: int
    month_label: str
    income_eur: float
    income_count: int
    expense_all_eur: float
    expense_all_count: int
    expense_monthly_eur: float
    saldo_eur: float
    fixkosten_result_eur: float
    debt_open_eur: float
    debt_open_count: int
    debt_open_docs: int
    strom_year: int
    strom_bezahlt_eur: float
    strom_gefordert_eur: float
    strom_diff_eur: float
    cat_haus_eur: float
    cat_handy_eur: float
    cat_vers_eur: float
    cat_oepnv_eur: float


def compute_dashboard_metrics(rows: list[dict[str, Any]], y: int, m: int) -> DashboardMetrics:
    # Schulden-Summe aus home: zeitlich unabhängig (alle offenen Forderungen), nicht nach y/m gefiltert.
    home = compute_home_stats(rows)
    y_strom = date.today().year

    debt_docs_n = 0
    for r in rows:
        if not hf._row_is_extraction_join(r):
            continue
        ext = {k: r.get(k) for k in ("document_kind", "nav_folder", "zahlstatus")}
        if hf._is_debt_candidate(ext) and not hf._is_paid(ext, r):
            debt_docs_n += 1

    income = 0.0
    inc_n = 0
    exp_all = 0.0
    exp_all_n = 0
    exp_monthly = 0.0

    strom_b, strom_g = 0.0, 0.0
    h_haus = h_handy = h_vers = h_oepnv = 0.0

    for r in rows:
        if _income_row(r, y, m):
            inc = hf._payslip_net(r)
            if inc > 0:
                income += inc
                inc_n += 1

        if _expense_row(r, y=y, m=m, monthly_only=None):
            amt = hf._primary_eur(r)
            if amt > 0:
                exp_all += amt
                exp_all_n += 1

        if _expense_row(r, y=y, m=m, monthly_only=True):
            exp_monthly += hf._primary_eur(r)

        if (r.get("nav_folder") or "") == "stromanbieter" and hf._row_is_extraction_join(r):
            if _in_year(r.get("document_date"), r.get("created_at"), y_strom):
                amt = hf._primary_eur(r)
                if hf._is_paid(r, r):
                    strom_b += amt
                else:
                    if hf._norm_kind(r.get("document_kind")) not in ("payslip",):
                        strom_g += amt

        if _nav_expense_row(r, "haustelefon_internet", y, m):
            h_haus += hf._primary_eur(r)
        if _nav_expense_row(r, "handyvertraege", y, m):
            h_handy += hf._primary_eur(r)
        if _nav_expense_row(r, "versicherungsscheine", y, m):
            h_vers += hf._primary_eur(r)
        if _oepnv_row(r, y, m):
            h_oepnv += hf._primary_eur(r)

    saldo = income - exp_all
    fix_res = income - exp_monthly
    strom_diff = strom_b - strom_g

    return DashboardMetrics(
        year=y,
        month=m,
        month_label=_de_month_label(y, m),
        income_eur=income,
        income_count=inc_n,
        expense_all_eur=exp_all,
        expense_all_count=exp_all_n,
        expense_monthly_eur=exp_monthly,
        saldo_eur=saldo,
        fixkosten_result_eur=fix_res,
        debt_open_eur=home.debt_open_eur,
        debt_open_count=home.debt_groups,
        debt_open_docs=debt_docs_n,
        strom_year=y_strom,
        strom_bezahlt_eur=strom_b,
        strom_gefordert_eur=strom_g,
        strom_diff_eur=strom_diff,
        cat_haus_eur=h_haus,
        cat_handy_eur=h_handy,
        cat_vers_eur=h_vers,
        cat_oepnv_eur=h_oepnv,
    )


def _monthly_label(r: dict[str, Any]) -> str:
    v = r.get("include_monthly_expense")
    if v is None:
        return "—"
    try:
        return "Ja" if int(v) == 1 else "Nein"
    except (TypeError, ValueError):
        return "—"


def list_tile_rows(
    rows: list[dict[str, Any]],
    tile_id: str,
    y: int,
    m: int,
    *,
    monthly_only: bool,
    strom_year: int | None = None,
) -> list[dict[str, Any]]:
    """Flache Zeilen für Detail-Tabelle."""
    out: list[dict[str, Any]] = []
    y_strom = int(strom_year or date.today().year)

    def add_row(r: dict[str, Any], *, typ: str, amount: float) -> None:
        out.append(
            {
                "id": int(r["id"]),
                "filename": r.get("original_filename") or "—",
                "amount_eur": amount,
                "document_date": r.get("document_date") or "—",
                "nav": r.get("nav_folder") or "—",
                "kind": typ,
                "monthly": _monthly_label(r),
            }
        )

    if tile_id == "einnahmen":
        for r in rows:
            if _income_row(r, y, m):
                amt = hf._payslip_net(r)
                if amt > 0:
                    add_row(r, typ="Einnahme", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    if tile_id == "ausgaben":
        mo: bool | None = True if monthly_only else None
        for r in rows:
            if _expense_row(r, y=y, m=m, monthly_only=mo):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="Ausgabe", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    if tile_id == "fixkosten":
        for r in rows:
            if _expense_row(r, y=y, m=m, monthly_only=True):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="Fixkosten", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    if tile_id == "saldo":
        for r in rows:
            if _income_row(r, y, m):
                amt = hf._payslip_net(r)
                if amt > 0:
                    add_row(r, typ="Einnahme", amount=amt)
        mo: bool | None = True if monthly_only else None
        for r in rows:
            if _expense_row(r, y=y, m=m, monthly_only=mo):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="Ausgabe", amount=amt)
        return sorted(out, key=lambda x: (0 if x["kind"] == "Einnahme" else 1, -x["amount_eur"]))

    if tile_id == "schulden":
        for r in rows:
            if not hf._row_is_extraction_join(r):
                continue
            ext = {k: r.get(k) for k in ("document_kind", "nav_folder", "zahlstatus")}
            if hf._is_debt_candidate(ext) and not hf._is_paid(ext, r):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="Schuld", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    if tile_id == "strom_jahr":
        for r in rows:
            if (r.get("nav_folder") or "") != "stromanbieter" or not hf._row_is_extraction_join(r):
                continue
            if not _in_year(r.get("document_date"), r.get("created_at"), y_strom):
                continue
            amt = hf._primary_eur(r)
            if amt <= 0:
                continue
            st = "Bezahlt" if hf._is_paid(r, r) else "Offen / gefordert"
            add_row(r, typ=st, amount=amt)
        return sorted(out, key=lambda x: x["kind"])

    nav_map = {
        "haus": "haustelefon_internet",
        "handy": "handyvertraege",
        "versicherungen": "versicherungsscheine",
    }
    if tile_id in nav_map:
        nav = nav_map[tile_id]
        for r in rows:
            if _nav_expense_row(r, nav, y, m):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="Ausgabe", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    if tile_id == "oepnv":
        for r in rows:
            if _oepnv_row(r, y, m):
                amt = hf._primary_eur(r)
                if amt > 0:
                    add_row(r, typ="ÖPNV", amount=amt)
        return sorted(out, key=lambda x: -x["amount_eur"])

    return []
