#!/usr/bin/env bash
# personagent — one-click start (Linux/macOS)
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"

# Never install application packages into the system Python.
if [ ! -x ".venv/bin/python" ]; then
  if [ -e ".venv" ]; then
    echo "error: .venv exists but has no executable Python. Repair it with quickstart.py or move it aside first." >&2
    exit 1
  fi
  BASE_PY="$(command -v python3 || command -v python || true)"
  if [ -z "$BASE_PY" ]; then
    echo "error: python3 not found. Install Python and run quickstart.py first." >&2
    exit 1
  fi
  echo "creating project virtual environment..."
  if ! "$BASE_PY" -m venv .venv; then
    echo "error: could not create .venv. Check that Python's venv support is installed." >&2
    exit 1
  fi
fi
PY=".venv/bin/python"

if ! "$PY" -c "import fastapi, uvicorn, dotenv, httpx, PIL, ddgs" 2>/dev/null; then
  echo "installing dependencies..."
  "$PY" -m pip install -r requirements.txt -q
fi

echo "listen:  http://${HOST}:${PORT}"
echo "webhook: http://${HOST}:${PORT}/webhook/qq"
exec "$PY" -m uvicorn main:app --host "${HOST}" --port "${PORT}"
