#!/usr/bin/env bash
# personagent - open local setup and chat from a checkout (Linux/macOS)
set -e
cd "$(dirname "$0")"

if [ ! -t 0 ] && [ ! -f ".env" ] && [ -z "${LLM_API_KEY:-}" ]; then
  echo "error: setup is needed. Run python3 quickstart.py in a terminal to open the welcome page." >&2
  exit 1
fi

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

if [ ! -x ".venv/bin/python" ]; then
  echo "creating project virtual environment..."
  if ! "$BASE_PY" -m venv .venv; then
    echo "error: could not create .venv. Check that Python's venv support is installed." >&2
    exit 1
  fi
fi
PY=".venv/bin/python"

if ! "$PY" -c "import fastapi, uvicorn, dotenv, httpx, PIL, ddgs, websockets, qrcode, cryptography" 2>/dev/null; then
  echo "installing dependencies..."
  "$PY" -m pip install -r requirements.txt -q
fi

if [ -t 0 ] && [ "$#" -eq 0 ]; then
  exec "$PY" -m persona_agent start
fi
exec "$PY" main.py "$@"
