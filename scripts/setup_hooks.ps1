# Install git hooks for AI log submission and branch protection (Windows PowerShell).
# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

param([switch]$Watch)

$ErrorActionPreference = 'Stop'

$RepoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $RepoRoot

# 1. Install pre-push hook (Codex & Antigravity sweep + submit)
$PrePushFile = (git rev-parse --git-path hooks/pre-push).Trim()
$PrePushBody = @'
#!/bin/sh
# Pre-push: recover saved Codex and Antigravity activity, then drain AI logs.
cd "$(git rev-parse --show-toplevel)" || exit 0
scripts/_pyrun.cmd scripts/log_codex.py --auto || true
scripts/_pyrun.cmd scripts/log_antigravity.py --auto || true
scripts/_pyrun.cmd scripts/submit_log.py --all || true
exit 0
'@

[System.IO.File]::WriteAllText(
    $PrePushFile,
    $PrePushBody,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "[ai-log] Git pre-push hook installed."

# 2. Install pre-commit hook (Confine agent hooks & AI log files to feature/ai-khoi)
$PreCommitFile = (git rev-parse --git-path hooks/pre-commit).Trim()
$PreCommitBody = @'
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
'@

[System.IO.File]::WriteAllText(
    $PreCommitFile,
    $PreCommitBody,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "[ai-log] Git pre-commit hook (branch protection) installed."

if (-not (Test-Path .ai-log)) { New-Item -ItemType Directory -Path .ai-log | Out-Null }
if (-not (Test-Path .ai-log/.gitkeep)) { New-Item -ItemType File -Path .ai-log/.gitkeep | Out-Null }

if ($Watch) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c scripts\_pyrun.cmd scripts\log_codex.py --watch --submit' `
        -WorkingDirectory $RepoRoot -WindowStyle Hidden `
        -RedirectStandardOutput '.ai-log/codex-watch.stdout.log' `
        -RedirectStandardError '.ai-log/codex-watch.log'
    Write-Host '[ai-log] Background Codex capture requested; see .ai-log/codex-watch.log.'
}

Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
