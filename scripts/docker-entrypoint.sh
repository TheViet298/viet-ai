#!/bin/sh
set -e

echo "[+] Starting VinFast ServiceFlow Backend..."

# Seed verified catalog snapshots into /app/data/verified if mounted volume is empty
mkdir -p /app/data/verified
for f in vehicle_facts.json catalog_colors.json; do
    if [ ! -f "/app/data/verified/$f" ] && [ -f "/app/fixtures/$f" ]; then
        cp "/app/fixtures/$f" "/app/data/verified/$f"
    fi
done
if [ ! -f "/app/data/verified/public_prices.json" ] && [ -f "/app/fixtures/verified_public_prices.json" ]; then
    cp "/app/fixtures/verified_public_prices.json" "/app/data/verified/public_prices.json"
fi

# Ensure embedding models exist
python scripts/download_models.py

echo "[+] Launching FastAPI application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 "$@"
