#!/bin/bash
set -e

echo "=== Initializing Local SQLite & Seed Databases ==="
python init_auth_db.py || true
python init_hackathon_db.py || true

echo "=== Starting FastAPI Backend on Port $PORT ==="
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
