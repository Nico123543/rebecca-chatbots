# Reciprocal Drift

`Reciprocal Drift` is a local kiosk installation where two language models speak to each other while visitors inject short text fragments that subtly bend the exchange.

The project now supports two explicit runtime modes:

- `local`: both agents run through `LM Studio`
- `online`: both agents run through `OpenRouter`

## Stack

- Backend: `FastAPI`, local `SQLite`, provider-agnostic model adapters
- Frontend: `React` + `Vite`
- Default runtime: one local exhibition computer, browser kiosk mode

## What v1 includes

- A `SessionController` that starts, pauses, resumes, and stops a two-agent loop
- A provider adapter layer with `OpenRouter`, `LM Studio`, `Ollama`, and deterministic `mock` support
- Visitor fragment intake with controlled multi-turn influence
- Local persistence of sessions, turns, fragments, and event logs
- WebSocket streaming for live kiosk/operator updates
- A kiosk-facing conversation view and a separate operator control panel

## Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
uvicorn backend.app.main:app --reload
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

## One-command local dev

```bash
./scripts/dev.sh
```

`./scripts/dev.sh` is the recommended development entrypoint.
It starts:

- the FastAPI backend on `http://127.0.0.1:8000`
- the Vite frontend on `http://127.0.0.1:5173`

Open `http://127.0.0.1:5173` while developing. That URL hot-reloads frontend changes automatically and talks to the backend API without requiring a rebuild.

## Kiosk mode

```bash
./scripts/kiosk.sh
```

The kiosk script builds the frontend, starts the FastAPI server, and tries to open the app in Chrome kiosk mode on macOS. Use kiosk mode for exhibition-style runs on `http://127.0.0.1:8000`, not for day-to-day frontend development.

## Config

- `config.yaml` defines timing, prompts, storage, and model adapters
- `.env` provides API secrets and optional base URLs
- The active mode is selected with `KIOSK_MODEL_MODE=local` or `KIOSK_MODEL_MODE=online`
- Default mode is `local`, so both agents use `google/gemma-3-4b` through LM Studio at `http://127.0.0.1:1234/v1`
- Online mode uses the same OpenRouter key for both agents, so you do not need a second API key
- The default online pair is:
  - `google/gemma-3n-e4b-it` for `Agent A`
  - `google/gemma-3-4b-it` for `Agent B`
- In LM Studio, start the local server in the Developer tab or with `lms server start`, then make sure `google/gemma-3-4b` is available
- If you want a different all-local or all-online pair, edit `model_profiles.local` or `model_profiles.online` in `config.yaml`

## Tests

The included tests cover the adapter factory, the influence engine, and the session controller:

```bash
python3 -m unittest discover -s tests
```
