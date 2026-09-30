#!/usr/bin/env bash
set -euo pipefail
demo_root="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$demo_root/.venv/bin/python" ]; then
  bash "$demo_root/setup.sh"
fi
exec "$demo_root/.venv/bin/python" "$demo_root/app.py"
