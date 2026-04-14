"""
Datenschutz-Hinweise (Kurzfassung für den Nutzer)

- Volltext der PDFs wird nur lokal in der SQLite-Datenbank gespeichert (siehe DOCU_DB_PATH / data/).
- An die KI-API wird ein gekürzter Textausschnitt gesendet (DOCU_LLM_CHAR_LIMIT, Standard 12.000 Zeichen):
  bei langen PDFs typischerweise **Anfang und Ende** des Textes (Mittelteil nur lokal in SQLite).
  Optional: ``DOCU_LLM_TWO_PHASE=1`` — dann zuerst eine KI-Zusammenfassung aus Anfang/Mitte/Ende, danach die
  strukturierte Extraktion (zwei API-Runden, höhere Kosten). Optional OCR bei Import: ``DOCU_ENABLE_OCR=1``
  (Tesseract/pdf2image, siehe README).
- Es werden keine Dateien an die API hochgeladen, nur Text.
- Für personenbezogene Inhalte (Lohn, Gesundheit, Verträge) prüfen Sie Verträge Ihres
  KI-Anbieters (Auftragsverarbeitung) und ob Sie kürzere Limits oder ein Enterprise-Konto benötigen.
"""

PRIVACY_UI_DE = """
**Was passiert mit Ihren Daten?**

- PDFs werden nach `data/archive` kopiert; der erkannte Text liegt in einer **lokalen SQLite-Datenbank**.
- Wenn Sie „Mit KI analysieren“ nutzen, wird **nur ein Ausschnitt** des Textes an die konfigurierte
  OpenAI-kompatible API geschickt (Länge über `DOCU_LLM_CHAR_LIMIT`, Standard 12.000 Zeichen; lange PDFs:
  Anfang **und** Ende). Optional zwei KI-Schritte (`DOCU_LLM_TWO_PHASE`) oder OCR beim Import (`DOCU_ENABLE_OCR`).
- **Kein automatischer Upload** der Original-PDF an die API.

Bitte prüfen Sie für sensible Unterlagen die Nutzungs- und Auftragsverarbeitungsbedingungen Ihres Anbieters.
"""
