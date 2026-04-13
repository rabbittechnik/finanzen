# Dokumenten-Organizer (MVP)

Lokaler Posteingang für PDFs, Textextraktion, strukturierte KI-Analyse (OpenAI API) und Vorgänge mit Verknüpfung über gemeinsame Kennungen.

## Voraussetzungen

- Python 3.10+
- `OPENAI_API_KEY` für die KI-Analyse

## Installation und Start

```powershell
cd C:\Users\Bianc\docu-organizer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env bearbeiten: OPENAI_API_KEY=...
streamlit run app.py
```

PDFs in `data\inbox` legen, dann in der App **Posteingang → Jetzt einlesen** wählen.

## Konfiguration (optional)

| Umgebungsvariable | Bedeutung |
|-------------------|-----------|
| `DOCU_DATA_DIR` | Basisordner (Standard: `./data`) |
| `DOCU_LLM_CHAR_LIMIT` | Max. Zeichen an die KI (Standard: 12000) |
| `DOCU_OPENAI_MODEL` | Modellname (Standard: `gpt-4o-mini`) |

Datenschutzkurzinfo: siehe Sidebar in der App und `privacy_notes.py`.
