#!/usr/bin/env bash
# Anycubic Cloud Auto-Uploader — macOS / Linux Launcher
# Sets up Python venv (once) and starts the tray app.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"

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
