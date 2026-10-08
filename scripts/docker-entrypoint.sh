#!/bin/sh
set -e

echo "[+] Starting VinFast ServiceFlow Backend..."

# Ensure embedding models exist
python scripts/download_models.py

echo "[+] Launching FastAPI application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 "$@"
