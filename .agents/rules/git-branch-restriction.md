---
description: "Branch Restriction: AI logging and agent hook files must ONLY be committed to branch feature/ai-khoi"
activation: always-on
---

# Git Branch Restriction: AI Logging & Agent Hook Files

## 1. Core Rule & Policy
All files and configurations related to agent hooks, AI activity logging, and automated log submissions **MUST ONLY** be committed to the branch `feature/ai-khoi`.
**NEVER** commit, merge, or push any of these files to other branches on GitHub (including `main`, `develop`, `feature/ai-long`, or any other branch).

## 2. Restricted File Paths
The following files and directories are strictly confined to `feature/ai-khoi`:
- `.agents/**` (e.g., `.agents/hooks.json`, `.agents/rules/**`, `.agents/workflows/**`)
- `.ai-log/**`
- `scripts/setup_hooks.sh`
- `scripts/setup_hooks.ps1`
- `scripts/log_antigravity.py`
- `scripts/log_codex.py`
- `scripts/log_hook.py`
- `scripts/log_manual.py`
- `scripts/ai_log_store.py`
- `scripts/submit_log.py`
- `scripts/_pyrun.sh`
- `scripts/_pyrun.cmd`
- `tests/test_ai_logging.py`

## 3. Strict Operating Rules for AI Agents and Developers

### A. Pre-Commit Verification
- Always check the active git branch before staging (`git add`) or committing (`git commit`):
  ```bash
  git branch --show-current
  ```
- If the current branch is **NOT** `feature/ai-khoi`:
  - **DO NOT** stage or commit any restricted files.
  - If any restricted file has been staged accidentally, unstage it immediately:
    ```bash
    git restore --staged <file>
    ```

### B. Pre-Push Verification
- When pushing to GitHub (`origin`), verify the destination branch:
  - Only push restricted files to `origin feature/ai-khoi`.
  - **NEVER** push these files to `origin main`, `origin develop`, or any other team branch.

### C. Branch Switching & Merging
- When switching away from `feature/ai-khoi` (e.g., to work on `develop` or `main`), ensure uncommitted changes in AI logging files remain stashed or isolated on `feature/ai-khoi`.
- When creating pull requests or merging into shared branches (`develop`, `main`), ensure commits containing AI logging or agent hooks are not merged into the shared codebase.

