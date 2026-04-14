# Dokumenten-Organizer (MVP)

Lokaler Posteingang für PDFs, Textextraktion, strukturierte KI-Analyse (OpenAI API) und Vorgänge mit Verknüpfung über gemeinsame Kennungen.

## Voraussetzungen

- Python 3.10+
- `OPENAI_API_KEY` für die KI-Analyse

## Installation und Start

| Schritt | Aktion |
|--------|--------|
| 1 | Repository klonen bzw. Ordner öffnen |
| 2 | Virtuelle Umgebung anlegen und aktivieren |
| 3 | Abhängigkeiten installieren: `pip install -r requirements.txt` |
| 4 | `.env` aus Vorlage: `copy .env.example .env` (PowerShell) bzw. `cp .env.example .env` — `OPENAI_API_KEY` setzen |
| 5 | App starten (siehe unten: lokal **Streamlit** vs. **ASGI**) |

**Lokal (Streamlit, schnell):**

```powershell
cd C:\Users\Bianc\docu-organizer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env bearbeiten: OPENAI_API_KEY=...
streamlit run app.py
```

Unter `streamlit run app.py` laufen **PWA-Routen** (Manifest, Service Worker unter `/manifest.json`, `/sw.js` usw.) anders bzw. fehlen im Vergleich zum **ASGI**-Start mit `uvicorn asgi:app` — für ein Setup wie in Produktion lokal `uvicorn` nutzen (siehe nächster Abschnitt).

PDFs in `data\inbox` legen oder **in der Sidebar per PDF-Upload** — dann **Posteingang → Jetzt einlesen**. In der App: Tabs **Posteingang**, **Dokumente**, **Vorgänge**; auf der Startseite das **Finanz-Dashboard**. PWA: in **Chrome oder Edge** „App installieren“ / Installationsprompt nutzen.

### Production / Railway

**Produktion (ASGI, empfohlen):** PWA-Assets und Streamlit laufen über eine gemeinsame App — Start wie in `asgi.py`:

```bash
uvicorn asgi:app --host 0.0.0.0 --port $PORT
```

**Railway:** Der effektive Startbefehl steht in `railway.toml` und erweitert den Aufruf u. a. um Proxy-Header und Lifespan:

`uvicorn asgi:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=* --lifespan on`

| Thema | Hinweis |
|-------|---------|
| PWA | Installation in Chrome/Edge; Upload und Tabs wie oben |
| Version sichtbar | Optional `DOCU_APP_VERSION` in `.env` (z. B. Git-Tag) für Deploy-Sichtbarkeit in der Oberfläche |

### Checkliste: URL öffentlich / Railway

1. **`DOCU_BASIC_AUTH_USER`** und **`DOCU_BASIC_AUTH_PASSWORD`** in den **Railway Variables** setzen (beide nötig). Ohne diese Paarung ist die App im Browser für jeden erreichbar, der die URL kennt — inklusive PWA-Routen.
2. **Passwort** stark wählen (nicht wiederverwenden aus anderen Diensten).
3. **Backup** einplanen: `python scripts/backup_data.py` erzeugt eine ZIP mit `documents.db`, **`archive/`** (importierte PDFs) und **`inbox/`** (noch nicht eingelesene Uploads). Auf dem Server z. B. per geplantem Job ausführen und die Datei zusätzlich **extern** ablegen (S3, Nextcloud, anderer Speicher). Lokal funktioniert dasselbe Skript, wenn `DOCU_DATA_DIR` / `DOCU_DB_PATH` auf deine Daten zeigen.

Lokal ASGI mit Hot-Reload (laut `asgi.py`): `uvicorn asgi:app --reload --host 127.0.0.1 --port 8501`

## Konfiguration (optional)

| Umgebungsvariable | Bedeutung |
|-------------------|-----------|
| `DOCU_DATA_DIR` | Basisordner (Standard: `./data`) |
| `DOCU_LLM_CHAR_LIMIT` | Max. Zeichen an die KI (Standard: 12000) |
| `DOCU_LLM_TWO_PHASE` | `1` / `true`: bei sehr langem Text zuerst KI-Komprimierung (Anfang/Mitte/Ende), dann Extraktion — **zwei** API-Runden |
| `DOCU_OPENAI_MODEL` | Modellname (Standard: `gpt-4o-mini`) |
| `DOCU_APP_VERSION` | Optional: z. B. Git-Tag, nur Anzeige/Deploy-Transparenz |
| `DOCU_EMAIL_DRAFT_MODEL` | Optional: Modell für E-Mail-Entwürfe; nicht gesetzt = gleiches Modell wie Extraktion (`DOCU_OPENAI_MODEL`) |
| `DOCU_BASIC_AUTH_USER` / `DOCU_BASIC_AUTH_PASSWORD` | Optional: HTTP-Basic-Auth vor der gesamten ASGI-App (nur wenn **beide** gesetzt) |
| `DOCU_SMTP_HOST`, `DOCU_SMTP_PORT` (Standard 587), `DOCU_SMTP_USER`, `DOCU_SMTP_PASSWORD`, `DOCU_SMTP_FROM` | Optional: E-Mail-Versand aus der App (Tab **Dokumente** → Aktionen); siehe **Gmail** unten |

#### Gmail (empfohlen, wenn du nur Gmail nutzt)

Google erlaubt SMTP nur mit **App-Passwort** (wenn die Bestätigung in zwei Schritten aktiv ist) oder mit einem passenden Kontotyp — siehe [Google: App-Passwörter](https://support.google.com/accounts/answer/185833).

| Variable | Typischer Wert |
|----------|----------------|
| `DOCU_SMTP_HOST` | `smtp.gmail.com` |
| `DOCU_SMTP_PORT` | `587` (STARTTLS, Standard in der App) oder `465` (SSL) |
| `DOCU_SMTP_USER` | Deine vollständige Gmail-Adresse |
| `DOCU_SMTP_PASSWORD` | **16-stelliges App-Passwort** (kein normales Google-Passwort) |
| `DOCU_SMTP_FROM` | Meist dieselbe Adresse wie `DOCU_SMTP_USER` |
| `DOCU_SMTP_TIMEOUT` | Optional: Timeout in Sekunden (Standard `60`) |
| `DOCU_SMTP_ADDRESS_FAMILY` | Optional: `ipv4` oder `ipv6` — bei Fehler **„Network is unreachable“** (errno 101) hilft oft `ipv4`, wenn der Server keine IPv6-Route nach außen hat |

**Railway:** dieselben fünf Variablen unter **Variables** setzen; danach neu deployen bzw. Dienst neu starten.

| `DOCU_JSON_LOGS` | `1` / `true`: strukturierte Log-Zeilen auf stdout (Railway) |
| `DOCU_PWA_NOTIFY` | `1` / `true`: nach KI-Analyse Browser-**Notification** (nur wenn Nutzer die Berechtigung erteilt hat) |
| `DOCU_ENABLE_OCR` | `1` / `true`: bei sehr wenig PDF-Text optional Tesseract versuchen (benötigt `pytesseract`, `pdf2image`, installiertes **Tesseract** und unter Windows **Poppler**) |

### Weitere Funktionen in der App

- **Suche** (Sidebar): Treffer in Dateiname, Absender, Betreff, Kurzfassung, Kennungen; springt zum Dokument.
- **Export** (Tab **Dokumente**): ZIP mit Original-PDFs und CSV-Metadaten für ausgewählte Belege.
- **Archiv / Papierkorb**: Dokument archivieren (Aktionen) oder in der Sidebar wiederherstellen.
- **E-Mail**: KI-Entwurf (Mehrfachauswahl) und optionaler SMTP-Versand nach Bestätigung.
- **Gleiche Kennung**: Sidebar-Expander listet mehrere Dokumente mit derselben extrahierten Referenz (Hinweis auf Dubletten).

### Backup

Datenbank, **Archiv** und **Posteingang** als ZIP sichern (nutzt dieselben Pfade wie die App):

```powershell
python scripts/backup_data.py
python scripts\backup_data.py C:\Backups\docu_export.zip
```

### Railway: tägliches Backup per Cron

Railway kann einen **eigenen kurzlebigen Dienst** nach Cron-Plan starten (Startbefehl läuft durch und beendet sich). Offizielle Doku: [Cron Jobs | Railway](https://docs.railway.com/cron-jobs) — Zeitpläne in **UTC**, minimal alle **5 Minuten**.

**Wichtig:** Den Cron-**nicht** auf dem gleichen Service wie `uvicorn` aktivieren. Stattdessen:

1. Im **gleichen Projekt** einen **zweiten Service** anlegen (dieselbe Repo-Root / dasselbe Build wie die Web-App).
2. **Dasselbe Volume** wie bei der App an denselben Mount-Pfad hängen (z. B. `/dokumente`), damit `documents.db`, `archive/` und `inbox/` sichtbar sind.
3. Dieselben Variablen wie bei der App setzen, mindestens **`DOCU_DATA_DIR`** (bzw. Standard `/dokumente` auf Railway) und bei Bedarf **`DOCU_DB_PATH`**.
4. Unter **Settings → Cron Schedule** z. B. täglich um 04:15 UTC: `15 4 * * *`
5. **Custom Start Command** (überschreibt den Web-Start für diesen Service nur hier) z. B.:

```bash
sh -c 'python scripts/backup_data.py /dokumente/backups/backup_$(date -u +%Y%m%d_%H%M%S).zip'
```

Die ZIP liegt dann **auf dem Volume** unter `backups/` und überlebt Deploys. Regelmäßig zusätzlich herunterladen oder per eigenem Upload (S3, rclone, …) auslagern — das Skript selbst lädt nirgends hoch.

**Hinweis:** Wenn ein Cron-Lauf noch läuft und der nächste Termin fällig ist, kann Railway den neuen Start auslassen; das Backup-Skript sollte also schnell fertig sein (typisch Sekunden bis wenige Minuten).

Datenschutzkurzinfo: siehe Sidebar in der App und `privacy_notes.py`.
