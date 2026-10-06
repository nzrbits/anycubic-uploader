#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
STAMP="$VENV/requirements.sha256"

require_tk() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: $1 not found. Install Python 3.10 or later." >&2
        exit 1
    fi
    if ! "$1" -c 'import tkinter' >/dev/null 2>&1; then
        PYVER=$("$1" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
        BASE=$("$1" -c 'import sys; print(sys.base_prefix)')
        echo "Error: Python $PYVER has no working tkinter." >&2
        if command -v brew >/dev/null 2>&1 && [ "${BASE#"$(brew --prefix)"}" != "$BASE" ]; then
            echo "Install it with: brew install python-tk@$PYVER" >&2
        else
            echo "Install Python with Tk support. The python.org installers include it." >&2
        fi
        exit 1
    fi
}

if [ -f "$PYTHON" ]; then
    require_tk "$PYTHON"
else
    require_tk python3
    python3 -m venv "$VENV"
fi

DIGEST=$("$PYTHON" -c 'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$REQUIREMENTS")
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$DIGEST" ]; then
    "$PYTHON" -m pip install -r "$REQUIREMENTS"
    printf '%s\n' "$DIGEST" > "$STAMP"
fi

exec "$PYTHON" "$SCRIPT_DIR/tray_app.py" "$@"
