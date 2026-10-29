#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -r requirements.txt
echo "Open http://127.0.0.1:5000/ in your browser"
"$PYTHON" app.py
