"""Strukturierte Dokumentensuche für den KI-Chat (Filter auf Metadaten aus list_documents)."""
from __future__ import annotations

from typing import Any

from db import list_documents, resolve_person_ids_by_name
from nav_logic import NAV_KEYS_ORDER, _norm_kind


def _parse_date(s: str | None) -> str | None:
    if not s:
        return None
    t = str(s).strip()
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        return t[:10]
    return None


def _norm_category_filter(raw: str | None) -> str:
    if not raw:
        return ""
    s = str(raw).strip().lower()
    aliases = {
        "strom": "energy",
        "gas": "energy",
        "energie": "energy",
        "anwalt": "legal",
        "rechtsanwalt": "legal",
        "recht": "legal",
        "kanzlei": "legal",
        "versicherung": "insurance",
        "versicherungen": "insurance",
        "behörde": "government",
        "behoerde": "government",
        "behörden": "government",
        "amt": "government",
        "bank": "banking",
        "lohn": "payroll",
        "gehalt": "payroll",
        "telekom": "telecom",
        "handy": "telecom",
        "internet": "housing_internet",
        "miete": "housing_internet",
        "krankenkasse": "health",
        "gesundheit": "health",
    }
    return aliases.get(s, s)


def _row_matches_category(row: dict[str, Any], token: str) -> bool:
    if not token:
        return True
    cat = (row.get("category") or "").strip().lower()
    nav = (row.get("nav_folder") or "").strip()
    kind = _norm_kind(row.get("document_kind"))
    role = (row.get("sender_role") or "").strip().lower()

    if token == "energy":
        return cat == "energy" or nav == "stromanbieter" or kind == "utility_bill"
    if token == "legal":
        return cat == "legal" or role == "lawyer"
    if token == "government":
        return cat == "government" or role == "government"
    if token == "banking":
        return cat == "banking" or role == "bank"
    if token == "insurance":
        return cat == "insurance" or role == "insurer" or nav == "versicherungsscheine"
    if token == "payroll":
        return cat == "payroll" or kind == "payslip" or nav == "lohnabrechnungen"
    if token == "telecom":
        return cat == "telecom" or kind == "mobile_contract" or nav == "handyvertraege"
    if token == "housing_internet":
        return cat == "housing_internet" or kind == "home_telecom" or nav == "haustelefon_internet"
    if token == "health":
        return cat == "health"
    if token == "contract":
        return cat == "contract"
    # fallback: substring on category label
    return token in cat or cat in token


def _row_matches_type(row: dict[str, Any], want: str) -> bool:
    if not want:
        return True
    got = _norm_kind(row.get("document_kind"))
    return got == want


def _row_matches_owner(
    row: dict[str, Any],
    *,
    person_id: int | None,
    unassigned_only: bool,
    person_name: str | None,
    all_persons_scope: bool,
) -> bool:
    if all_persons_scope:
        return True
    if unassigned_only:
        return (row.get("owner_kind") or "").strip() == ""
    if person_id is not None:
        return (row.get("owner_kind") or "") == "person" and int(row.get("owner_person_id") or 0) == int(
            person_id
        )
    if person_name and (person_name := person_name.strip()):
        ids = resolve_person_ids_by_name(person_name)
        if not ids:
            return False
        oid = row.get("owner_person_id")
        if (row.get("owner_kind") or "") != "person" or oid is None:
            return False
        return int(oid) in ids
    return True


def _row_matches_vendor(row: dict[str, Any], needle: str) -> bool:
    if not needle:
        return True
    n = needle.casefold()
    for key in ("sender_name", "subject", "original_filename", "folder_sub", "summary_de"):
        v = row.get(key)
        if v and n in str(v).casefold():
            return True
    return False


def _row_matches_dates(row: dict[str, Any], date_from: str | None, date_to: str | None) -> bool:
    d = _parse_date(row.get("document_date"))
    if date_from and d and d < date_from:
        return False
    if date_to and d and d > date_to:
        return False
    if date_from and not d:
        return False
    if date_to and not d:
        return False
    return True


def _amount_for_sort(row: dict[str, Any]) -> float:
    """Für absteigende Beträge: fehlender Betrag sortiert nach hinten."""
    v = row.get("primary_amount_eur")
    try:
        if v is None:
            return float("-inf")
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def _amount_for_asc(row: dict[str, Any]) -> float:
    """Für aufsteigende Beträge: fehlender Betrag sortiert nach hinten."""
    v = row.get("primary_amount_eur")
    try:
        if v is None:
            return float("inf")
        return float(v)
    except (TypeError, ValueError):
        return float("inf")


def _date_key(row: dict[str, Any]) -> str:
    d = _parse_date(row.get("document_date"))
    return d or "0000-00-00"


def search_documents(
    *,
    type: str | None = None,
    category: str | None = None,
    vendor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    nav_folder: str | None = None,
    person_id: int | None = None,
    person_name: str | None = None,
    unassigned_only: bool = False,
    all_persons_scope: bool = False,
    limit: int = 1,
    sort: str = "date_desc",
) -> list[dict[str, Any]]:
    """
    Filter auf der aktuellen Dokumentliste (nicht archiviert).
    type: document_kind (deutsch/englisch, wird normalisiert).
    category: Kategorie oder umgangssprachliche Begriffe (z. B. strom, anwalt).
    vendor: Teilstring in Absender/Betreff/Dateiname.
    sort: date_desc | date_asc | amount_desc | amount_asc
    Standard limit=1 (ohne explizite Mengenangabe in der Nutzerfrage).
    person_id / person_name: Zuordnungsfilter. ``all_persons_scope=True``: alle Personen (Haushalts-Ansicht / KI).
    """
    date_from = _parse_date(date_from)
    date_to = _parse_date(date_to)
    type_n = _norm_kind(type) if type else ""
    cat_tok = _norm_category_filter(category)
    vendor_s = (vendor or "").strip()
    nav = (nav_folder or "").strip()
    if nav and nav not in NAV_KEYS_ORDER:
        nav = ""

    pid = int(person_id) if person_id is not None else None
    pnm = (person_name or "").strip() or None
    ua = bool(unassigned_only)
    aps = bool(all_persons_scope)

    lim = max(1, min(int(limit or 1), 50))
    sort_key = (sort or "date_desc").strip().lower()
    if sort_key not in ("date_desc", "date_asc", "amount_desc", "amount_asc"):
        sort_key = "date_desc"

    rows = list_documents()
    out: list[dict[str, Any]] = []
    for r in rows:
        if nav and (r.get("nav_folder") or "").strip() != nav:
            continue
        if type_n and not _row_matches_type(r, type_n):
            continue
        if cat_tok and not _row_matches_category(r, cat_tok):
            continue
        if vendor_s and not _row_matches_vendor(r, vendor_s):
            continue
        if not _row_matches_dates(r, date_from, date_to):
            continue
        if not _row_matches_owner(
            r,
            person_id=pid,
            unassigned_only=ua,
            person_name=pnm,
            all_persons_scope=aps,
        ):
            continue
        out.append(r)

    if sort_key == "date_desc":
        out.sort(key=lambda x: (_date_key(x), int(x["id"])), reverse=True)
    elif sort_key == "date_asc":
        out.sort(key=lambda x: (_date_key(x), int(x["id"])))
    elif sort_key == "amount_desc":
        out.sort(key=lambda x: (_amount_for_sort(x), _date_key(x), int(x["id"])), reverse=True)
    else:
        out.sort(key=lambda x: (_amount_for_asc(x), _date_key(x), int(x["id"])))

    return out[:lim]


def documents_as_assistant_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Schlankes JSON-Format für die KI (id, type, category, vendor, date, amount, tags, file_path)."""
    slim: list[dict[str, Any]] = []
    for r in rows:
        amt = r.get("primary_amount_eur")
        try:
            amt_out = float(amt) if amt is not None else None
        except (TypeError, ValueError):
            amt_out = None
        tags: list[str] = []
        sub = (r.get("subject") or "").strip()
        if sub:
            tags.append(sub)
        role = (r.get("sender_role") or "").strip()
        if role:
            tags.append(role)
        slim.append(
            {
                "id": int(r["id"]),
                "type": r.get("document_kind"),
                "category": r.get("category"),
                "vendor": r.get("sender_name"),
                "date": r.get("document_date"),
                "amount": amt_out,
                "tags": tags,
                "file_path": r.get("stored_path"),
                "nav_folder": r.get("nav_folder"),
                "summary": (r.get("summary_de") or "")[:240],
                "zahlstatus": r.get("zahlstatus"),
                "original_filename": r.get("original_filename"),
                "owner_kind": r.get("owner_kind"),
                "person_name": r.get("person_display_name"),
            }
        )
    return slim
