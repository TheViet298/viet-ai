# Install git pre-push hook for AI log submission (Windows PowerShell).
# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

param([switch]$Watch)

$ErrorActionPreference = 'Stop'

$RepoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $RepoRoot
$HookFile = (git rev-parse --git-path hooks/pre-push).Trim()

# Git for Windows runs hooks via its POSIX shell.
$HookBody = @'
#!/bin/sh
# Pre-push: recover saved Codex and Antigravity activity, then drain AI logs.
cd "$(git rev-parse --show-toplevel)" || exit 0
scripts/_pyrun.cmd scripts/log_codex.py --auto || true
scripts/_pyrun.cmd scripts/log_antigravity.py --auto || true
scripts/_pyrun.cmd scripts/submit_log.py --all || true
exit 0
'@

[System.IO.File]::WriteAllText(
	$HookFile,
	$HookBody,
	[System.Text.UTF8Encoding]::new($false)
)
Write-Host "[ai-log] Git pre-push hook installed."

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
