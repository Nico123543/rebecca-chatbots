# Online-Installationsanleitung

Diese Anleitung ist nur für den `Online-Modus`.

Das bedeutet:

- beide Chat-Agenten laufen über `OpenRouter`
- `LM Studio` wird nicht gebraucht
- es müssen keine lokalen Modelle installiert werden

Diese Anleitung ist für jemanden gedacht, der das Projekt frisch über `git clone` startet.

## 1. Was du brauchst

Auf dem Rechner sollten diese Programme vorhanden sein:

- `Python 3.12` oder neuer
- `Git`
- `Node.js`
- `npm`

Du kannst das im Terminal prüfen:

```bash
python3 --version
git --version
node --version
npm --version
```

Wenn bei `git`, `node` oder `npm` `command not found` steht, müssen diese Programme erst installiert werden.

Downloads:

- Git: [https://git-scm.com/downloads](https://git-scm.com/downloads)
- Node.js: [https://nodejs.org/](https://nodejs.org/)

Bei Node.js bitte die aktuelle `LTS`-Version nehmen.

## 2. Projekt herunterladen

Im Terminal:

```bash
git clone <REPOSITORY-URL>
cd "<PROJEKT-ORDNER>"
```

Dabei:

- `<REPOSITORY-URL>` durch die echte Git-Adresse ersetzen
- `<PROJEKT-ORDNER>` durch den Namen des geklonten Ordners ersetzen

## 3. Python-Umgebung anlegen

Im Projektordner ausführen:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

Wichtig:

- Wenn später ein neues Terminal geöffnet wird, muss die Umgebung wieder aktiviert werden:

```bash
source .venv/bin/activate
```

## 4. Frontend installieren

Danach ausführen:

```bash
cd frontend
npm install
npm run build
cd ..
```

Dieser Schritt baut die Weboberfläche, die später im Browser angezeigt wird.

## 5. `.env`-Datei anlegen

Im Hauptordner des Projekts eine Datei mit dem Namen `.env` anlegen.

Inhalt:

```env
KIOSK_MODEL_MODE=online
OPENROUTER_API_KEY=HIER_DEN_ECHTEN_OPENROUTER_KEY_EINFUEGEN
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=Reciprocal Drift
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
```

Wichtig:

- `HIER_DEN_ECHTEN_OPENROUTER_KEY_EINFUEGEN` durch den echten Schlüssel ersetzen
- `KIOSK_MODEL_MODE=online` genau so stehen lassen
- `LMSTUDIO_BASE_URL` darf drin bleiben, auch wenn der Online-Modus es nicht benutzt

## 6. Projekt starten

Im Projektordner:

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

Danach im Browser öffnen:

```text
http://127.0.0.1:8000
```

## 7. Was dann passieren sollte

Auf der Seite:

- auf `Start fresh` klicken
- danach sollten die zwei Agenten anfangen, miteinander zu sprechen
- in das Eingabefeld kann ein kurzer Text geschrieben werden
- dieser Text sollte im Verlauf erscheinen und spätere Antworten beeinflussen

## 8. Projekt stoppen

Im Terminal, in dem der Server läuft:

- `Ctrl + C` drücken

## 9. Wenn etwas nicht funktioniert

### Wenn `git` fehlt

Git installieren:

- [https://git-scm.com/downloads](https://git-scm.com/downloads)

### Wenn `node` oder `npm` fehlt

Node.js LTS installieren:

- [https://nodejs.org/](https://nodejs.org/)

### Wenn die Seite alt aussieht oder Änderungen nicht auftauchen

Dann das Frontend neu bauen:

```bash
cd frontend
npm run build
cd ..
```

Danach den Server neu starten:

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

### Wenn die Python-Pakete nicht installiert werden

Zuerst sicherstellen, dass die virtuelle Umgebung aktiv ist:

```bash
source .venv/bin/activate
```

Dann erneut:

```bash
python3 -m pip install -e .
```

### Wenn die Chats nicht starten

Prüfen:

- ob die Datei `.env` existiert
- ob in `.env` wirklich `KIOSK_MODEL_MODE=online` steht
- ob der OpenRouter-Key richtig eingetragen ist
- ob Internet vorhanden ist

### Wenn OpenRouter einen Fehler meldet

Das kann passieren, wenn:

- der API-Key falsch ist
- das Modell gerade kurzfristig begrenzt ist
- die Internetverbindung instabil ist

Dann:

- Server mit `Ctrl + C` stoppen
- Server neu starten
- nochmal `Start fresh` klicken

## 10. Kurzversion zum Kopieren

Nach dem Klonen des Repos:

```bash
cd "<PROJEKT-ORDNER>"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
cd frontend
npm install
npm run build
cd ..
uvicorn backend.app.main:app --reload
```

Dann im Browser öffnen:

```text
http://127.0.0.1:8000
```
