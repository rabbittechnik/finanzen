"""Navigation folders (sidebar) derived from LLM extraction fields."""
from __future__ import annotations

from typing import Any

# internal keys -> German labels (sidebar)
NAV_LABELS: dict[str, str] = {
    "home": "Saldo",
    "rechnungen": "Rechnungen",
    "mahnungen": "Mahnungen",
    "lohnabrechnungen": "Lohnabrechnungen",
    "schriftverkehr": "Schriftverkehr",
    "amtsgericht": "Amtsschreiben",
    "versicherungsscheine": "Versicherungsscheine",
    "stromanbieter": "Stromanbieter",
    "haustelefon_internet": "Haustelefon/Internet",
    "handyvertraege": "Handyverträge",
}

NAV_KEYS_ORDER = list(NAV_LABELS.keys())


def _norm_kind(raw: str | None) -> str:
    k = (raw or "other").strip().lower()
    aliases = {
        "mahnung": "reminder",
        "dunning": "reminder",
        "inkasso": "reminder",
        "rechnung": "invoice",
        "lohn": "payslip",
        "lohnabrechnung": "payslip",
        "gehaltsabrechnung": "payslip",
        "zahlungsaufforderung": "payment_demand",
    }
    return aliases.get(k, k)


def nav_from_normalized(n: dict[str, Any]) -> tuple[str | None, str | None]:
    """
    Returns (nav_folder_key, folder_sub).
    folder_sub names the subfolder under Stromanbieter (Wechsel = neuer Anbietername).
    """
    kind = _norm_kind(n.get("document_kind"))
    cat = str(n.get("category") or "other")
    sender = (n.get("sender_name") or "").strip()
    util = (n.get("utility_provider_name") or "").strip() or sender or "Unbekannter Anbieter"

    if kind in ("reminder", "payment_demand"):
        return ("mahnungen", None)
    if kind == "payslip" or cat == "payroll":
        return ("lohnabrechnungen", None)
    if kind in ("court", "amtsgericht"):
        return ("amtsgericht", None)
    if kind == "insurance_policy" or cat == "insurance":
        return ("versicherungsscheine", None)
    if kind == "mobile_contract":
        return ("handyvertraege", None)
    if kind == "home_telecom":
        return ("haustelefon_internet", None)
    if kind == "correspondence":
        return ("schriftverkehr", None)
    if cat == "energy" or kind == "utility_bill":
        return ("stromanbieter", util[:120])
    if kind == "invoice":
        return ("rechnungen", None)
    if cat == "telecom":
        return ("handyvertraege", None)
    if cat == "housing_internet":
        return ("haustelefon_internet", None)
    if cat == "legal":
        return ("schriftverkehr", None)
    if cat == "government":
        return ("schriftverkehr", None)
    return ("schriftverkehr", None)
