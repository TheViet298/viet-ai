#!/usr/bin/env bash
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
cd "$repo_root" || exit 1

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if [[ -x "$repo_root/.venv/bin/python" ]]; then
    python_bin="$repo_root/.venv/bin/python"
  else
    python_bin=python3
  fi
fi

result=0
run_check() {
  local label="$1"
  shift
  printf '\n=== %s ===\n' "$label"
  if "$@"; then
    printf 'PASS: %s\n' "$label"
  else
    local code=$?
    printf 'FAIL: %s (exit %s)\n' "$label" "$code" >&2
    result=1
  fi
}

run_check "Frontend lint" npm --prefix frontend run lint
run_check "Frontend tests" node --test frontend/tests/*.test.cjs
run_check "Frontend TypeScript" ./frontend/node_modules/.bin/tsc --noEmit --project frontend/tsconfig.json
run_check "Backend location tests" env PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m pytest -p no:cacheprovider tests/test_agents/test_location_and_memory.py tests/test_agents/test_location_extraction.py
run_check "Frontend build" npm --prefix frontend run build

exit "$result"
