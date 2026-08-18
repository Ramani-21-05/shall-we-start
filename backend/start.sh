#!/bin/bash
# Render.com startup script for PharmaCast Backend

set -e

echo "🔄 Initializing database..."
python init_hackathon_db.py

echo "🚀 Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
