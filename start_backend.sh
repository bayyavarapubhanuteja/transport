#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Starting DelhiMove AI Flask REST API on http://127.0.0.1:5001..."
cd "$DIR/backend"
export FLASK_DEBUG=True
export PORT=5001
export HOST=127.0.0.1
PYTHONPATH=. /Users/apple/Desktop/transport/Bheedbus/venv/bin/python3 app.py
