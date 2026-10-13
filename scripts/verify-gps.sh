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
check_timeout="${GPS_CHECK_TIMEOUT_SECONDS:-300}"
[[ "$check_timeout" =~ ^[1-9][0-9]*$ ]] || { echo "GPS_CHECK_TIMEOUT_SECONDS phải là số giây > 0" >&2; exit 2; }
command -v timeout >/dev/null || { echo "Thiếu timeout (coreutils)" >&2; exit 2; }
run_check() {
  local label="$1"
  shift
  printf '\n=== %s ===\n' "$label"
  if timeout --signal=TERM --kill-after=10s "${check_timeout}s" "$@"; then
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
run_check "Backend location tests" env PYTHONDONTWRITEBYTECODE=1 LANGFUSE_TRACING_ENABLED=false LANGCHAIN_TRACING_V2=false AGENT_LLM_ENABLED=false "$python_bin" -m pytest -p no:cacheprovider tests/test_agents/test_location_and_memory.py tests/test_agents/test_location_extraction.py
run_check "Backend location API regression" env PYTHONDONTWRITEBYTECODE=1 LANGFUSE_TRACING_ENABLED=false LANGCHAIN_TRACING_V2=false AGENT_LLM_ENABLED=false "$python_bin" -m pytest -p no:cacheprovider tests/test_api/test_aligned_spec.py -k customer_location_and_service_points
run_check "Backend nearby API and privacy" env PYTHONDONTWRITEBYTECODE=1 LANGFUSE_TRACING_ENABLED=false LANGCHAIN_TRACING_V2=false AGENT_LLM_ENABLED=false "$python_bin" -m pytest -p no:cacheprovider tests/test_api/test_nearby_service_points.py tests/test_api/test_location_log_privacy.py
run_check "Frontend build" npm --prefix frontend run build

exit "$result"
