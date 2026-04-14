"""KI-Assistent mit Tool-Zugriff auf Dokumentliste, Suche und manuelle Ablage (nav_folder)."""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from config import OPENAI_MODEL
from docu_logging import log_openai_error
from db import (
    get_document,
    get_extraction,
    list_documents,
    list_matters,
    list_persons,
    update_extraction_nav_folder,
)
from document_search import documents_as_assistant_rows, search_documents
from nav_logic import NAV_KEYS_ORDER, NAV_LABELS

CHAT_MODEL = os.environ.get("DOCU_CHAT_MODEL", OPENAI_MODEL)

NAV_ALLOWED = [k for k in NAV_KEYS_ORDER if k != "home"]


def _nav_catalog_text() -> str:
    lines = ["Erlaubte nav_folder-Schlüssel (exakt so verwenden):"]
    for k in NAV_ALLOWED:
        lines.append(f"  - {k}: {NAV_LABELS.get(k, k)}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""Du bist **Lumo**, der freundliche Dokumenten- und Finanzassistent in der Streamlit-App „Dokumenten-Organizer“ (deutsche Unterlagen).
Wenn der Nutzer dich mit „Lumo“, „Hey Lumo“ o. Ä. anspricht, antworte kurz als Lumo (du darfst den Namen verwenden) und bleibe sachlich hilfreich.

{_nav_catalog_text()}

Datenmodell (nach KI-Analyse vorhanden): id, type=document_kind, category, vendor=sender_name, date=document_date,
amount=primary_amount_eur (EUR), tags aus Betreff/Rolle, file_path=stored_path, nav_folder=Ablage.

**Pflicht für Fragen nach Belegen, Beträgen, Mahnungen, Anbietern, Zeiträumen:** zuerst `search_documents` aufrufen — keine Dokumente erfinden, keine Treffer ohne Tool behaupten.
`list_documents_compact` nur wenn eine komplette Übersicht nötig ist (z. B. „alle IDs“, Sortieren im Kopf unmöglich).

Umgangssprache → Filter (Beispiele):
- „Anwalt“ / „Recht“ → category „legal“ oder vendor-Teilstring
- „Rechtsanwalt Heuberger“ → vendor „Heuberger“
- „letzte Stromrechnung“ → category „energy“ oder nav_folder „stromanbieter“, type „invoice“, sort date_desc, limit 1
- „Mahnungen“ → type „reminder“ (ggf. auch payment_demand)
- „teuerste Rechnung dieses Jahr“ → type „invoice“, date_from/date_to Kalenderjahr, sort amount_desc, limit 1

Antworten: strukturiert (Datum, Betrag, Kurzbeschreibung), bei mehreren Treffern sinnvortiert (meist neueste zuerst — erledigt durch search_documents).
Keine Treffer: klar sagen, passende Kategorien/Ordner aus NAV-Katalog nennen.
Optional: Wenn der Nutzer auf einem anderen Gerät anzeigen will, `show_document` nutzen (pc/tablet/tv); „Fernseher“/„TV“ → tv.

**Personen:** Jedes Dokument gehört höchstens einer **Person** (`owner_kind` person / unzugeordnet). Es gibt **keinen** Speicher „Haushalt“ für Belege.
**Haushalt** in der UI ist nur eine **Aggregations-Ansicht** über alle Personen — bei Fragen wie „alle Handykosten im Haushalt“: `all_persons_scope: true` setzen und ggf. category/vendor/type filtern; optional pro Person nach `person_id` einzeln suchen und Beträge vergleichen.
Suchfilter: `person_id`, `person_name`, `unassigned_only`, `all_persons_scope` (Gesamt über alle Personen).
„Meine …“ → Hauptnutzer (`is_primary` in list_persons).

Weitere Tools:
- `list_persons_compact` — Personen (id, name, rolle, is_primary)
- `list_matters_compact` — Vorgänge
- `set_document_folder` — Ablage ändern (nur mit bestehender Extraktion)

Antworte freundlich und knapp auf Deutsch. Ordnerwechsel: IDs und Zielablage bestätigen.
Ohne Extraktion: Hinweis „Mit KI analysieren“ im Dokumenten-Tab.
Erfinde keine Dokument-IDs — IDs nur aus Tool-Ergebnissen.
"""


def _tool_list_documents_compact() -> str:
    rows = list_documents()[:80]
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": int(r["id"]),
                "filename": r.get("original_filename"),
                "nav_folder": r.get("nav_folder"),
                "folder_sub": r.get("folder_sub"),
                "document_kind": r.get("document_kind"),
                "zahlstatus": r.get("zahlstatus"),
                "document_date": r.get("document_date"),
                "summary": (r.get("summary_de") or "")[:200],
                "owner_kind": r.get("owner_kind"),
                "person_name": r.get("person_display_name"),
            }
        )
    return json.dumps(out, ensure_ascii=False)


def _tool_list_matters_compact() -> str:
    rows = list_matters()[:50]
    out = [{"id": int(m["id"]), "title": m.get("title"), "doc_count": m.get("doc_count")} for m in rows]
    return json.dumps(out, ensure_ascii=False)


def _tool_list_persons_compact() -> str:
    rows = list_persons()
    out_p = [
        {
            "id": int(p["id"]),
            "name": p.get("name"),
            "role": p.get("role"),
            "relationship": p.get("relationship"),
            "is_primary": bool(p.get("is_primary")),
        }
        for p in rows
    ]
    return json.dumps({"persons": out_p}, ensure_ascii=False)


def _opt_pos_int(arguments: dict[str, Any], key: str) -> int | None:
    v = arguments.get(key)
    if v is None or v == "":
        return None
    try:
        i = int(v)
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def _tool_search_documents(arguments: dict[str, Any]) -> str:
    lim = int(arguments.get("limit") or 1)
    rows = search_documents(
        type=arguments.get("type"),
        category=arguments.get("category"),
        vendor=arguments.get("vendor"),
        date_from=arguments.get("date_from"),
        date_to=arguments.get("date_to"),
        nav_folder=arguments.get("nav_folder"),
        person_id=_opt_pos_int(arguments, "person_id"),
        person_name=arguments.get("person_name"),
        unassigned_only=bool(arguments.get("unassigned_only")),
        all_persons_scope=bool(arguments.get("all_persons_scope")),
        limit=lim,
        sort=arguments.get("sort") or "date_desc",
    )
    slim = documents_as_assistant_rows(rows)
    return json.dumps({"count": len(slim), "documents": slim}, ensure_ascii=False)


def _tool_show_document(arguments: dict[str, Any], tool_effects: list[dict[str, Any]]) -> str:
    doc_id = int(arguments["document_id"])
    raw_dev = str(arguments.get("target_device") or "pc").strip().lower()
    if raw_dev in ("fernseher", "tv", "television"):
        dev = "tv"
    elif raw_dev in ("tablet", "ipad"):
        dev = "tablet"
    else:
        dev = "pc"
    doc = get_document(doc_id)
    if not doc:
        return json.dumps(
            {"ok": False, "error": f"Dokument #{doc_id} nicht gefunden."},
            ensure_ascii=False,
        )
    tool_effects.append({"action": "show_document", "document_id": doc_id, "target_device": dev})
    return json.dumps(
        {
            "ok": True,
            "document_id": doc_id,
            "target_device": dev,
            "filename": doc.get("original_filename"),
            "hint": "Ausgabe an Gerät vorgemerkt — die App springt zur Vorschau, sofern möglich.",
        },
        ensure_ascii=False,
    )


def _tool_set_document_folder(arguments: dict[str, Any]) -> str:
    doc_id = int(arguments["document_id"])
    nav = str(arguments.get("nav_folder") or "").strip()
    if nav not in NAV_ALLOWED:
        return json.dumps({"ok": False, "error": f"Ungültiger nav_folder: {nav}"}, ensure_ascii=False)
    sub = arguments.get("folder_sub")
    if sub is not None:
        sub = str(sub).strip() or None
    ext = get_extraction(doc_id)
    if not ext:
        return json.dumps(
            {"ok": False, "error": "Keine Extraktion — bitte zuerst „Mit KI analysieren“ für dieses Dokument."},
            ensure_ascii=False,
        )
    ok = update_extraction_nav_folder(doc_id, nav_folder=nav, folder_sub=sub)
    return json.dumps(
        {"ok": bool(ok), "document_id": doc_id, "nav_folder": nav, "folder_sub": sub},
        ensure_ascii=False,
    )


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Strukturierte Suche in der Dokumentdatenbank (nur indexierte, nicht archivierte Dokumente). "
                "Immer zuerst nutzen, wenn der Nutzer nach Belegen, Beträgen, Absendern oder Zeiträumen fragt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Dokumentart / document_kind (z. B. invoice, reminder, payslip; auch deutsch: Rechnung, Mahnung).",
                    },
                    "category": {
                        "type": "string",
                        "description": "Kategorie oder Synonym (z. B. energy, legal, strom, anwalt).",
                    },
                    "vendor": {
                        "type": "string",
                        "description": "Teilstring Absender/Unternehmen (sender_name, auch Betreff/Dateiname).",
                    },
                    "date_from": {"type": "string", "description": "YYYY-MM-DD inklusive"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD inklusive"},
                    "nav_folder": {
                        "type": "string",
                        "enum": NAV_ALLOWED,
                        "description": "Optional: nur Dokumente in dieser Ablage.",
                    },
                    "person_id": {
                        "type": "integer",
                        "description": "Nur Dokumente dieser Person (id aus list_persons_compact)",
                    },
                    "all_persons_scope": {
                        "type": "boolean",
                        "description": "True = alle Personen zusammen (Haushalts-Gesamtansicht), keine personenbezogene Einschränkung",
                    },
                    "person_name": {
                        "type": "string",
                        "description": "Teilstring Name einer Person (wenn person_id unbekannt)",
                    },
                    "unassigned_only": {
                        "type": "boolean",
                        "description": "Nur Dokumente ohne Zuordnung",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max. Treffer (Standard 1 wenn keine Menge genannt, max. 50)",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["date_desc", "date_asc", "amount_desc", "amount_asc"],
                        "description": "Sortierung; Standard date_desc",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_document",
            "description": (
                "Dokument auf einem Zielgerät anzeigen: springt in der App zur Vorschau. "
                "Geräte: pc (Standard), tablet, tv (Fernseher)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "integer"},
                    "target_device": {
                        "type": "string",
                        "enum": ["pc", "tablet", "tv"],
                        "description": "Zielgerät",
                    },
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_persons_compact",
            "description": "Alle angelegten Personen (Hauptnutzer, Partner, Kinder) mit id für Suchfilter.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents_compact",
            "description": "Liste aller Dokumente mit Ablage (nav_folder), Art und Kurzinfos — nur wenn eine volle Übersicht nötig ist.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_matters_compact",
            "description": "Liste der Vorgänge (Themen) mit Dokumentanzahl.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_document_folder",
            "description": "Ablage-Ordner (nav_folder) und optional Unterordner (folder_sub, z.B. Stromanbieter-Name) setzen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "integer", "description": "Dokument-ID (# in der Liste)"},
                    "nav_folder": {
                        "type": "string",
                        "enum": NAV_ALLOWED,
                        "description": "Zielordner-Schlüssel",
                    },
                    "folder_sub": {
                        "type": "string",
                        "description": "Optional; z.B. Anbietername unter Stromanbieter",
                    },
                },
                "required": ["document_id", "nav_folder"],
            },
        },
    },
]


def _execute_tool(name: str, arguments: str, tool_effects: list[dict[str, Any]]) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "Ungültige Tool-Argumente"})
    if name == "search_documents":
        return _tool_search_documents(args)
    if name == "list_persons_compact":
        return _tool_list_persons_compact()
    if name == "show_document":
        return _tool_show_document(args, tool_effects)
    if name == "list_documents_compact":
        return _tool_list_documents_compact()
    if name == "list_matters_compact":
        return _tool_list_matters_compact()
    if name == "set_document_folder":
        return _tool_set_document_folder(args)
    return json.dumps({"error": f"Unbekanntes Tool: {name}"})


def run_organizer_chat(
    messages: list[dict[str, Any]],
    *,
    max_tool_rounds: int = 6,
    tool_effects: list[dict[str, Any]] | None = None,
) -> str:
    """messages: OpenAI-Format inkl. System als erste Nachricht. Letzte User-Nachricht wird verarbeitet."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt — Chat nicht verfügbar.")

    effects = tool_effects if tool_effects is not None else []
    client = OpenAI(api_key=api_key)
    work = [dict(m) for m in messages]
    rounds = 0
    while rounds < max_tool_rounds:
        rounds += 1
        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=work,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )
        except Exception as e:
            log_openai_error("run_organizer_chat", e)
            raise
        msg = resp.choices[0].message
        if msg.tool_calls:
            tool_calls_payload = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in msg.tool_calls
            ]
            work.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": tool_calls_payload,
                }
            )
            for tc in msg.tool_calls:
                result = _execute_tool(tc.function.name, tc.function.arguments or "{}", effects)
                work.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue
        return (msg.content or "").strip() or "(Keine Antwort)"

    return "Die KI hat zu viele Tool-Runden benötigt. Bitte Frage kürzen oder erneut versuchen."
