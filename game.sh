#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONUTF8=1

find_bootstrap_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

ensure_venv() {
  if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    return 0
  fi

  if ! bootstrap_python="$(find_bootstrap_python)"; then
    echo "Python not found in WSL. Install python3 or python." >&2
    exit 127
  fi

  echo "Creating local virtual environment in .venv..." >&2
  "$bootstrap_python" -m venv "$SCRIPT_DIR/.venv"
}

ensure_requirements() {
  if "$SCRIPT_DIR/.venv/bin/python" -c "import dotenv, openai" >/dev/null 2>&1; then
    return 0
  fi

  echo "Installing Python dependencies into .venv..." >&2
  "$SCRIPT_DIR/.venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$SCRIPT_DIR/.venv/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
}

ensure_venv
ensure_requirements
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [ "$#" -eq 0 ]; then
  exec "$PYTHON_BIN" ./play_match.py --mode openrouter --rounds 2
fi

exec "$PYTHON_BIN" ./play_match.py "$@"
