#!/bin/bash
# Run Q-Wave GUI: project venv (pygame, qiskit, …) + PYTHONPATH for the qwave package layout.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PY=""
for candidate in "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/venv/bin/python"; do
  if [ -x "$candidate" ]; then
    VENV_PY=$candidate
    break
  fi
done

if [ -z "$VENV_PY" ]; then
  echo "Error: No virtualenv found at .venv or venv."
  echo "Create one (Python 3.12 recommended) and install deps, e.g.:"
  echo "  python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Repo root must be on PYTHONPATH so the `qwave` package directory resolves.
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

exec "$VENV_PY" qwave_gui.py
