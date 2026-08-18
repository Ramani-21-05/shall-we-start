#!/usr/bin/env bash
set -e

echo "=== Upgrading pip ==="
python -m pip install --upgrade pip

echo "=== Installing dependencies without cache ==="
python -m pip install --no-cache-dir -r requirements.txt

echo "=== Initializing Databases ==="
python init_auth_db.py || true
python init_hackathon_db.py || true
