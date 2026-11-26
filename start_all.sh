#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================================="
echo "  🚀 Starting DelhiMove AI Full-Stack Platform"
echo "  Problem 2: Real-Time Bus Traffic Prediction & Journey Planner"
echo "=========================================================="

"$DIR/start_backend.sh" &
BACKEND_PID=$!

"$DIR/start_frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "  Backend API:  http://127.0.0.1:5001"
echo "  Frontend App: http://127.0.0.1:5174"
echo ""
echo "Press Ctrl+C to terminate both servers."

cleanup() {
    echo "Stopping DelhiMove AI services..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT
wait
