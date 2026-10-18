#!/usr/bin/env bash
set -euo pipefail
demo_root="$(cd "$(dirname "$0")" && pwd)"
if command -v python3.11 >/dev/null 2>&1; then
  demo_python=python3.11
else
  demo_python=python3
fi
if [ ! -d "$demo_root/.venv" ]; then
  "$demo_python" -m venv "$demo_root/.venv"
fi
if [ ! -f "$demo_root/.env" ]; then
  cp "$demo_root/.env.example" "$demo_root/.env"
fi
echo "Môi trường demo đã sẵn sàng. Không cần API key hoặc npm."
echo "Chạy: bash demo/run.sh"
