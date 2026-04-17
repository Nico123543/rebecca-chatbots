#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"

cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Create a virtual environment first: python3 -m venv .venv"
  exit 1
fi

source "$ROOT_DIR/.venv/bin/activate"

(
  cd "$ROOT_DIR/frontend"
  VITE_API_BASE="http://${API_HOST}:${API_PORT}" npm run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
FRONTEND_PID=$!

uvicorn backend.app.main:app --reload --host "$API_HOST" --port "$API_PORT" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
  kill "$FRONTEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Dev frontend: http://${WEB_HOST}:${WEB_PORT}"
echo "Dev backend:  http://${API_HOST}:${API_PORT}"
echo "Open the frontend URL above during development. It hot-reloads automatically."

wait -n "$FRONTEND_PID" "$BACKEND_PID"
