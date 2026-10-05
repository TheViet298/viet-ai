#!/usr/bin/env bash
# Install git hooks for AI log submission and branch protection (POSIX / Git Bash).
# Run once after cloning: bash scripts/setup_hooks.sh
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 1. Install pre-push hook (Codex & Antigravity sweep + submit)
PRE_PUSH_FILE="$(git rev-parse --git-path hooks/pre-push)"
cat > "$PRE_PUSH_FILE" <<'EOF'
#!/usr/bin/env bash
# Pre-push: recover saved Codex and Antigravity activity, then drain AI logs.
# Uses the cross-platform Python launcher so it works whether the user
# has python3, python, or only the `py` launcher (Windows).
cd "$(git rev-parse --show-toplevel)" || exit 0
bash scripts/_pyrun.sh scripts/log_codex.py --auto || true
bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py --all || true
exit 0  # Never block push, even if any step fails
EOF
chmod +x "$PRE_PUSH_FILE"
echo "[ai-log] Git pre-push hook installed."

# 2. Install pre-commit hook (Confine agent hooks & AI log files to feature/ai-khoi)
PRE_COMMIT_FILE="$(git rev-parse --git-path hooks/pre-commit)"
cat > "$PRE_COMMIT_FILE" <<'EOF'
#!/bin/sh
# Pre-commit hook: ensure agent hooks and ai-log files are only committed to feature/ai-khoi

BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || git branch --show-current 2>/dev/null)

if [ "$BRANCH" != "feature/ai-khoi" ]; then
    RESTRICTED_FILES=$(git diff --cached --name-only | grep -E '^(\.agents/|\.ai-log/|scripts/(setup_hooks\.|log_|ai_log_store\.py|submit_log\.py|_pyrun\.)|tests/test_ai_logging\.py)')
    if [ -n "$RESTRICTED_FILES" ]; then
        echo "======================================================================" >&2
        echo "[ERROR] COMMIT REJECTED BY PRE-COMMIT HOOK:" >&2
        echo "AI logging and agent hook files can ONLY be committed to 'feature/ai-khoi'!" >&2
        echo "Current branch: '$BRANCH'" >&2
        echo "The following staged files are restricted:" >&2
        echo "$RESTRICTED_FILES" | while IFS= read -r f; do echo "  - $f" >&2; done
        echo "" >&2
        echo "To unstage these files, run:" >&2
        echo "  git restore --staged <file>" >&2
        echo "======================================================================" >&2
        exit 1
    fi
fi

exit 0
EOF
chmod +x "$PRE_COMMIT_FILE"
echo "[ai-log] Git pre-commit hook (branch protection) installed."

chmod +x scripts/_pyrun.sh 2>/dev/null || true
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
