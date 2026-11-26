#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "⚡ Starting DelhiMove AI React Frontend on http://127.0.0.1:5174..."
cd "$DIR/frontend"
npm run dev -- --host 127.0.0.1
