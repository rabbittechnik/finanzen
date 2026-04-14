"""KI-gestützte E-Mail-Entwürfe aus ausgewählten Dokumenten (nur Vorschlag, kein Versand)."""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from config import OPENAI_MODEL
from docu_logging import log_openai_error
from db import get_document, get_extraction

EMAIL_DRAFT_MODEL = os.environ.get("DOCU_EMAIL_DRAFT_MODEL", OPENAI_MODEL)

# (interner Schlüssel, Anzeige für Selectbox)
EMAIL_SCENARIO_CHOICES: list[tuple[str, str]] = [
    ("ratenzahlung", "Ratenzahlung / Ratenzahlungsvereinbarung"),
    ("zahlungspause", "Zahlungspause / Stundung anfragen"),
    ("anwalt_unterlagen", "Unterlagen an Anwalt / Behörde nachreichen"),
    ("auskunft_wirtschaft", "Auskunft über wirtschaftliche Verhältnisse (o. Ä.)"),
    ("sonstiges", "Sonstiges (freier Text unten)"),
]


def _document_bundle(doc_id: int) -> dict[str, Any] | None:
    doc = get_document(doc_id)
    if not doc:
        return None
    ext = get_extraction(doc_id)
    bundle: dict[str, Any] = {
        "document_id": doc_id,
        "filename": doc.get("original_filename"),
        "document_date": ext.get("document_date") if ext else None,
        "sender_name": ext.get("sender_name") if ext else None,
        "subject": ext.get("subject") if ext else None,
        "summary_de": (ext.get("summary_de") or "")[:1200] if ext else None,
        "category": ext.get("category") if ext else None,
        "sender_role": ext.get("sender_role") if ext else None,
        "document_kind": ext.get("document_kind") if ext else None,
        "zahlstatus": ext.get("zahlstatus") if ext else None,
    }
    if ext:
        try:
            bundle["amounts"] = json.loads(ext.get("amounts_json") or "[]")
        except json.JSONDecodeError:
            bundle["amounts"] = []
        try:
            bundle["reference_ids"] = json.loads(ext.get("reference_ids_json") or "[]")
        except json.JSONDecodeError:
            bundle["reference_ids"] = []
    return bundle


def run_email_draft(
    *,
    doc_ids: list[int],
    scenario_key: str,
    user_notes: str,
) -> str:
    """Erzeugt einen E-Mail-Entwurf (Betreff + Text) auf Deutsch."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt.")

    ids = sorted({int(i) for i in doc_ids if int(i) > 0})
    if not ids:
        raise ValueError("Mindestens ein Dokument auswählen.")

    bundles = []
    for did in ids:
        b = _document_bundle(did)
        if b:
            bundles.append(b)

    if not bundles:
        raise ValueError("Keine gültigen Dokumente.")

    scenario_label = dict(EMAIL_SCENARIO_CHOICES).get(scenario_key, scenario_key)
    payload = json.dumps(bundles, ensure_ascii=False, indent=2)
    notes = (user_notes or "").strip()

    system = """Du hilfst beim Formulieren einer E-Mail auf Deutsch (Sie-Form oder neutral-sachlich).
Du bist kein Rechtsanwalt — keine Rechtsberatung, keine garantiert korrekten Fristen oder Ansprüche.
Formuliere einen **Entwurf**, den die Person in ihr E-Mail-Programm kopieren und anpassen kann.

Ausgabe-Struktur (genau diese Überschriften, Markdown):
## Betreff
(eine Zeile)

## E-Mailtext
(Anrede, sachlicher Hauptteil mit Bezug zu den gelieferten Dokumentdaten, Grußformel)

Wenn Daten fehlen (z. B. keine Aktenzeichen), Platzhalter in eckigen Klammern wie [Aktenzeichen einsetzen].
Keine erfundenen Beträge oder Daten — nur aus dem Kontext oder Platzhalter."""

    user_msg = (
        f"Anlass / Szenario: {scenario_label}\n\n"
        f"Zusätzliche Wünsche oder Sachverhalt vom Nutzer:\n{notes or '(keine)'}\n\n"
        f"Strukturierte Angaben aus der App (extrahierte Felder, mehrere Dokumente):\n{payload}"
    )

    client = OpenAI(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=EMAIL_DRAFT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.35,
        )
    except Exception as e:
        log_openai_error("run_email_draft", e)
        raise
    return (resp.choices[0].message.content or "").strip() or "(Keine Antwort)"
