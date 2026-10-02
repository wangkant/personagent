#!/usr/bin/env bash
# personagent - start the service from a checkout (Linux/macOS)
set -e
cd "$(dirname "$0")"

# Never install application packages into the system Python.
if [ ! -x ".venv/bin/python" ]; then
  if [ -e ".venv" ]; then
    echo "error: .venv exists but has no executable Python. Repair it with quickstart.py or move it aside first." >&2
    exit 1
  fi
  BASE_PY="$(command -v python3 || command -v python || true)"
  if [ -z "$BASE_PY" ]; then
    echo "error: python3 not found. Install Python 3.10 or newer, then run: python3 quickstart.py" >&2
    exit 1
  fi
fi

# Not set up yet: run the setup wizard instead of a server that cannot answer.
if [ ! -f ".env" ] && [ -z "${LLM_API_KEY:-}" ]; then
  if [ ! -t 0 ]; then
    echo "error: personagent is not set up here yet (no .env). Run: python3 quickstart.py" >&2
    exit 1
  fi
  echo "No .env yet: starting the setup wizard (quickstart.py)."
  if [ -x ".venv/bin/python" ]; then SETUP_PY=".venv/bin/python"; else SETUP_PY="$BASE_PY"; fi
  "$SETUP_PY" quickstart.py
  if [ ! -f ".env" ]; then
    exit 1
  fi
fi

if [ ! -x ".venv/bin/python" ]; then
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

# main.py loads .env before resolving SERVER_HOST / SERVER_PORT.
exec "$PY" main.py
