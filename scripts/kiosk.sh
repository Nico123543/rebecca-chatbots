#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Create a virtual environment first: python3 -m venv .venv"
  exit 1
fi

source "$ROOT_DIR/.venv/bin/activate"

(
  cd "$ROOT_DIR/frontend"
  npm run build
) 

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

if command -v open >/dev/null 2>&1; then
  open -a "Google Chrome" --args --kiosk "http://127.0.0.1:8000" || true
fi

echo "Kiosk server running at http://127.0.0.1:8000"
wait "$SERVER_PID"
