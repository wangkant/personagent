#!/usr/bin/env bash
# persona-llm-agent — one-click start (Linux/macOS)
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"

# Prefer the venv that quickstart.py creates; fall back to a global interpreter.
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="$(command -v python3 || command -v python || true)"
fi
if [ -z "$PY" ]; then
  echo "error: python3 not found. Run 'python quickstart.py' first." >&2
  exit 1
fi

if ! "$PY" -c "import fastapi, uvicorn, dotenv, httpx, PIL, ddgs" 2>/dev/null; then
  echo "installing dependencies..."
  "$PY" -m pip install -r requirements.txt -q
fi

echo "listen:  http://${HOST}:${PORT}"
echo "webhook: http://${HOST}:${PORT}/webhook/qq"
exec "$PY" -m uvicorn main:app --host "${HOST}" --port "${PORT}"
