#!/usr/bin/env bash
# Install git pre-push hook for AI log submission (POSIX / Git Bash).
# Run once after cloning: bash scripts/setup_hooks.sh
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
HOOK_FILE="$(git rev-parse --git-path hooks/pre-push)"

cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
# Pre-push: recover saved Codex and Antigravity activity, then drain AI logs.
# Uses the cross-platform Python launcher so it works whether the user
# has python3, python, or only the `py` launcher (Windows).
cd "$(git rev-parse --show-toplevel)" || exit 0
bash scripts/_pyrun.sh scripts/log_codex.py --auto || true
bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py --all || true
exit 0  # Never block push, even if either step fails
EOF

chmod +x "$HOOK_FILE"
chmod +x scripts/_pyrun.sh 2>/dev/null || true
echo "[ai-log] Git pre-push hook installed."

mkdir -p .ai-log
touch .ai-log/.gitkeep

if [ "${1:-}" = "--watch" ]; then
  # Capture continues even when this Codex session has not reloaded its hooks.
  # log_codex holds an exclusive watcher lock, so running setup twice is safe.
  nohup bash scripts/_pyrun.sh scripts/log_codex.py --watch --submit \
    >> .ai-log/codex-watch.log 2>&1 < /dev/null &
  echo "[ai-log] Background Codex capture requested; see .ai-log/codex-watch.log."
fi

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
