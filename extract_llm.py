"""Structured document analysis via OpenAI API. See privacy notes in module docstring."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from config import LLM_TEXT_CHAR_LIMIT, OPENAI_MODEL
from nav_logic import nav_from_normalized

load_dotenv()

# Privacy: only a prefix of extracted_text is sent to the API. Full text remains in SQLite locally.
# Do not log full document bodies to stdout in production.

EXTRACTION_JSON_INSTRUCTIONS = """
Du analysierst den Text eines deutschen Schreibens (Rechnung, Mahnung, Vertrag, Lohn, Versicherung, Behörde, Anwalt, Strom/Gas, Telekom, Internet, Miete, Sonstiges).
Antworte NUR mit gültigem JSON (kein Markdown), exakt diesem Schema:
{
  "category": one of
    "energy","legal","payroll","insurance","contract","telecom","housing_internet",
    "government","banking","health","other",
  "document_kind": one of
    "invoice","reminder","payslip","insurance_policy","court","correspondence",
    "mobile_contract","home_telecom","utility_bill","other",
  "utility_provider_name": bei Strom-/Gas-/Energieanbieter der Firmenname für Ordner (string oder null),
  "sender_name": string oder null,
  "sender_role": one of
    "utility","lawyer","employer","insurer","telco","landlord","bank","government","collection_agency","other",
  "subject": Kurzbetreff string oder null,
  "document_date": "YYYY-MM-DD" oder null,
  "amounts": [ { "currency": "EUR"|"CHF"|"USD"|string, "value": number|null, "description": string|null } ],
  "reference_ids": [
    { "id_type": "customer_number"|"contract_number"|"invoice_number"|"case_reference"|"meter_number"|"policy_number"|"iban_reference"|"other",
      "value": string }
  ],
  "summary_de": ein kurzer deutscher Satz (Inhalt für Nutzer)
}
document_kind: "invoice"=Rechnung, "reminder"=Mahnung/Inkasso, "payslip"=Lohnabrechnung, "insurance_policy"=Versicherungsschein/-police,
"court"=Amtsgericht/Gericht, "correspondence"=Schriftverkehr, "mobile_contract"=Handyvertrag, "home_telecom"=Festnetz/Internet zu Hause,
"utility_bill"=Energieabrechnung ohne klare Rechnung, "other".
Bei Mahnung und zugehöriger Rechnung dieselbe invoice_number in reference_ids setzen, wenn im Text vorhanden.
Extrahiere alle sinnvollen Referenznummern/Kundennummern/Vertrags-/Rechnungs-/Aktenzeichen wörtlich wie im Text.
"""


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[…Text gekürzt für API; vollständig lokal gespeichert…]"


def extract_document_fields(extracted_text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY fehlt. Legen Sie die Variable in .env oder der Umgebung an."
        )
    client = OpenAI(api_key=api_key)
    payload = _truncate(extracted_text, LLM_TEXT_CHAR_LIMIT)
    user_content = f"{EXTRACTION_JSON_INSTRUCTIONS}\n\n--- Dokumenttext ---\n{payload}"

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Du bist ein präziser Assistent für strukturierte Dokumentenextraktion. Nur JSON ausgeben.",
            },
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return _normalize_extraction(data)


def _normalize_extraction(data: dict[str, Any]) -> dict[str, Any]:
    allowed_cat = {
        "energy",
        "legal",
        "payroll",
        "insurance",
        "contract",
        "telecom",
        "housing_internet",
        "government",
        "banking",
        "health",
        "other",
    }
    allowed_role = {
        "utility",
        "lawyer",
        "employer",
        "insurer",
        "telco",
        "landlord",
        "bank",
        "government",
        "collection_agency",
        "other",
    }
    allowed_doc_kind = {
        "invoice",
        "reminder",
        "payslip",
        "insurance_policy",
        "court",
        "correspondence",
        "mobile_contract",
        "home_telecom",
        "utility_bill",
        "other",
    }
    cat = data.get("category") or "other"
    if cat not in allowed_cat:
        cat = "other"
    role = data.get("sender_role") or "other"
    if role not in allowed_role:
        role = "other"
    doc_kind = data.get("document_kind") or "other"
    if doc_kind not in allowed_doc_kind:
        doc_kind = "other"
    if doc_kind == "other" and role == "collection_agency":
        doc_kind = "reminder"
    util_name = data.get("utility_provider_name")
    if util_name is not None:
        util_name = str(util_name).strip() or None
    raw_amounts = data.get("amounts") if isinstance(data.get("amounts"), list) else []
    amounts: list[dict[str, Any]] = []
    for a in raw_amounts:
        if isinstance(a, dict):
            amounts.append(
                {
                    "currency": a.get("currency"),
                    "value": a.get("value"),
                    "description": a.get("description"),
                }
            )
    refs = data.get("reference_ids") if isinstance(data.get("reference_ids"), list) else []
    clean_refs: list[dict[str, str]] = []
    for r in refs:
        if not isinstance(r, dict):
            continue
        it = str(r.get("id_type") or "other")
        if it not in {
            "customer_number",
            "contract_number",
            "invoice_number",
            "case_reference",
            "meter_number",
            "policy_number",
            "iban_reference",
            "other",
        }:
            it = "other"
        val = str(r.get("value") or "").strip()
        if val:
            clean_refs.append({"id_type": it, "value": val})
    doc_date = data.get("document_date")
    if doc_date is not None:
        doc_date = str(doc_date)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", doc_date):
            doc_date = None
    return {
        "category": cat,
        "document_kind": doc_kind,
        "utility_provider_name": util_name,
        "sender_name": data.get("sender_name"),
        "sender_role": role,
        "subject": data.get("subject"),
        "document_date": doc_date,
        "amounts": amounts,
        "reference_ids": clean_refs,
        "summary_de": (data.get("summary_de") or "").strip() or None,
    }


def extraction_to_db_payload(normalized: dict[str, Any], raw_json: str) -> dict[str, Any]:
    nav_folder, folder_sub = nav_from_normalized(normalized)
    return {
        "category": normalized["category"],
        "sender_name": normalized.get("sender_name"),
        "sender_role": normalized["sender_role"],
        "subject": normalized.get("subject"),
        "document_date": normalized.get("document_date"),
        "amounts": normalized.get("amounts") or [],
        "reference_ids": normalized.get("reference_ids") or [],
        "summary_de": normalized.get("summary_de"),
        "raw_json": raw_json,
        "nav_folder": nav_folder,
        "folder_sub": folder_sub,
        "document_kind": normalized.get("document_kind"),
        "linked_payment_doc_id": None,
        "zahlstatus": None,
    }
