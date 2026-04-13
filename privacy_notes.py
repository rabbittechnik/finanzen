"""
Datenschutz-Hinweise (Kurzfassung für den Nutzer)

- Volltext der PDFs wird nur lokal in der SQLite-Datenbank gespeichert (siehe DOCU_DB_PATH / data/).
- An die KI-API wird ausschließlich ein gekürzter Textausschnitt gesendet (DOCU_LLM_CHAR_LIMIT,
  Standard 12.000 Zeichen), siehe extract_llm._truncate und config.LLM_TEXT_CHAR_LIMIT.
- Es werden keine Dateien an die API hochgeladen, nur Text.
- Für personenbezogene Inhalte (Lohn, Gesundheit, Verträge) prüfen Sie Verträge Ihres
  KI-Anbieters (Auftragsverarbeitung) und ob Sie kürzere Limits oder ein Enterprise-Konto benötigen.
"""

PRIVACY_UI_DE = """
**Was passiert mit Ihren Daten?**

- PDFs werden nach `data/archive` kopiert; der erkannte Text liegt in einer **lokalen SQLite-Datenbank**.
- Wenn Sie „Mit KI analysieren“ nutzen, wird **nur ein Ausschnitt** des Textes an die konfigurierte
  OpenAI-kompatible API geschickt (Länge über Umgebungsvariable `DOCU_LLM_CHAR_LIMIT`, Standard 12.000 Zeichen).
- **Kein automatischer Upload** der Original-PDF an die API.

Bitte prüfen Sie für sensible Unterlagen die Nutzungs- und Auftragsverarbeitungsbedingungen Ihres Anbieters.
"""
