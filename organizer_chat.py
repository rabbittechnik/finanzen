"""KI-Assistent mit Tool-Zugriff auf Dokumentliste und manuelle Ablage (nav_folder)."""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from config import OPENAI_MODEL
from db import get_extraction, list_documents, list_matters, update_extraction_nav_folder
from nav_logic import NAV_KEYS_ORDER, NAV_LABELS

CHAT_MODEL = os.environ.get("DOCU_CHAT_MODEL", OPENAI_MODEL)

NAV_ALLOWED = [k for k in NAV_KEYS_ORDER if k != "home"]


def _nav_catalog_text() -> str:
    lines = ["Erlaubte nav_folder-Schlüssel (exakt so verwenden):"]
    for k in NAV_ALLOWED:
        lines.append(f"  - {k}: {NAV_LABELS.get(k, k)}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""Du bist der eingebaute Assistent der Streamlit-App „Dokumenten-Organizer“ (deutsche Finanz-/Postunterlagen).

{_nav_catalog_text()}

Du kannst:
- mit list_documents_compact die aktuelle Dokumentübersicht abrufen (IDs, Dateiname, Ablage, Art, Zahlstatus, Kurzfassung),
- mit list_matters_compact die Vorgänge sehen,
- mit set_document_folder die **Ablage** (nav_folder, optional folder_sub für Stromanbieter) ändern — nur wenn bereits eine KI-Extraktion existiert.

Antworte freundlich und knapp auf Deutsch. Wenn du Ordner änderst, bestätige die IDs und die neue Ablage.
Wenn keine Extraktion existiert, weise darauf hin: Nutzer soll im Tab „Dokumente“ **Mit KI analysieren** ausführen.
Erfinde keine Dokument-IDs — nutze nur list_documents_compact.
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
            }
        )
    return json.dumps(out, ensure_ascii=False)


def _tool_list_matters_compact() -> str:
    rows = list_matters()[:50]
    out = [{"id": int(m["id"]), "title": m.get("title"), "doc_count": m.get("doc_count")} for m in rows]
    return json.dumps(out, ensure_ascii=False)


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
            "name": "list_documents_compact",
            "description": "Liste aller Dokumente mit Ablage (nav_folder), Art und Kurzinfos — für Fragen und Umsortieren.",
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


def _execute_tool(name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "Ungültige Tool-Argumente"})
    if name == "list_documents_compact":
        return _tool_list_documents_compact()
    if name == "list_matters_compact":
        return _tool_list_matters_compact()
    if name == "set_document_folder":
        return _tool_set_document_folder(args)
    return json.dumps({"error": f"Unbekanntes Tool: {name}"})


def run_organizer_chat(messages: list[dict[str, Any]], *, max_tool_rounds: int = 6) -> str:
    """messages: OpenAI-Format inkl. System als erste Nachricht. Letzte User-Nachricht wird verarbeitet."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt — Chat nicht verfügbar.")

    client = OpenAI(api_key=api_key)
    work = [dict(m) for m in messages]
    rounds = 0
    while rounds < max_tool_rounds:
        rounds += 1
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=work,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
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
                result = _execute_tool(tc.function.name, tc.function.arguments or "{}")
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
