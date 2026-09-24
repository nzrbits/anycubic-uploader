#!/usr/bin/env bash
# Anycubic Cloud Auto-Uploader — macOS / Linux Launcher
# Sets up Python venv (once) and starts the tray app.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"

# The tray app and token setup need tkinter. Homebrew Python ships without it.
require_tk() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: $1 not found. Install Python 3.10 or later." >&2
        exit 1
    fi
    if ! "$1" -c "import tkinter" >/dev/null 2>&1; then
        PYVER=$("$1" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null) || PYVER=""
        BASE=$("$1" -c 'import sys; print(sys.base_prefix)' 2>/dev/null) || BASE=""
        echo "Error: Python ${PYVER:-?} ($1) has no working tkinter." >&2
        if [ -n "$PYVER" ] && command -v brew >/dev/null 2>&1 \
            && [ "${BASE#"$(brew --prefix)"}" != "$BASE" ]; then
            echo "Install it with: brew install python-tk@$PYVER" >&2
        else
            echo "Install Tk support for this Python (python.org installers include it)." >&2
        fi
        exit 1
    fi
}

if [ -f "$PYTHON" ]; then
    require_tk "$PYTHON"
else
    require_tk python3
fi

# Create venv and install dependencies (first run only)
if [ ! -f "$PYTHON" ]; then
    echo "Setting up Python environment..."
    python3 -m venv "$VENV"
    "$PYTHON" -m pip install --quiet --upgrade pip
    "$PYTHON" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
    echo "Done."
fi

# Run token setup if config.json is missing or has the placeholder token
CONFIG="$SCRIPT_DIR/config.json"
NEEDS_TOKEN=false

if [ ! -f "$CONFIG" ]; then
    NEEDS_TOKEN=true
else
    TOKEN=$(python3 -c "
import json, sys
try:
    t = json.load(open('$CONFIG')).get('token','')
    print('empty' if not t or t == 'YOUR_ANYCUBIC_TOKEN_HERE' else 'ok')
except:
    print('empty')
")
    if [ "$TOKEN" = "empty" ]; then
        NEEDS_TOKEN=true
    fi
fi

if [ "$NEEDS_TOKEN" = "true" ]; then
    echo "No token found — running token setup..."
    "$PYTHON" "$SCRIPT_DIR/setup_token.py"
fi

echo "Starting Anycubic Auto-Uploader..."
"$PYTHON" "$SCRIPT_DIR/tray_app.py"
