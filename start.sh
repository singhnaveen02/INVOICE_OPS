#!/usr/bin/env bash
set -e

echo "========================================================="
echo "      InvoiceOps - AI-Powered Invoice Processing"
echo "========================================================="
echo ""

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Start Backend
echo "[1/2] Starting Backend API..."
cd "$DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
python init_db.py
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 3

# Start Frontend
echo "[2/2] Starting Frontend..."
cd "$DIR/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================================="
echo "  InvoiceOps is live!"
echo "  - Frontend UI:  http://localhost:5173"
echo "  - Backend API:  http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "========================================================="

wait $BACKEND_PID $FRONTEND_PID
