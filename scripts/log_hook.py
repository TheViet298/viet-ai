#!/usr/bin/env python3
"""
Shared AI hook logger — works with Claude Code, Gemini CLI, Codex, Cursor, Copilot.
Reads JSON from stdin, normalizes to common format, appends to .ai-log/session.jsonl
"""
import json
import os
import sys
import subprocess
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ai_log_store import append_entries, entry_id, log_dir, repo_root

VN_TZ = timezone(timedelta(hours=7))


def git(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def detect_tool(data: dict) -> str:
    """Detect which AI tool sent this hook event.

    Priority:
      1. --tool=NAME CLI argument (cross-platform: works in cmd.exe, PowerShell, bash)
      2. AI_TOOL_NAME env var (legacy, bash-only when set inline)
      3. Heuristics from payload shape
    """
    for arg in sys.argv[1:]:
        if arg.startswith("--tool="):
            return arg.split("=", 1)[1].lower()
    tool_env = os.environ.get("AI_TOOL_NAME", "").lower()
    if tool_env:
        return tool_env
    # Heuristics
    if "transcript_path" in data:
        return "codex"
    if data.get("hook_event_name", "").startswith(("Before", "After", "Session", "Pre", "Notification")):
        return "gemini"
    if data.get("hook_event_name", "")[0:1].islower():
        # camelCase event names → Cursor or Copilot
        if "workspace_roots" in data:
            return "cursor"
        if "toolName" in data:
            return "copilot"
    if "hook_event_name" in data:
        return "claude"
    return "unknown"


def normalize(data: dict, tool: str) -> dict | None:
    """Normalize tool-specific payload to common log entry."""
    event = data.get("hook_event_name") or data.get("event", "")
    ts = datetime.now(VN_TZ).isoformat()

    # Resolve repo from git origin. When cwd is not a git working tree (or
    # origin isn't set), skip the event entirely — these entries can't be
    # tied back to a team on the server and would just clutter the pending
    # queue forever.
    origin = git("git remote get-url origin")
    if not origin:
        return None
    repo = origin.rstrip("/").split("/")[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    base = {
        "ts": ts,
        "tool": tool,
        "event": event,
        "session_id": (
            data.get("session_id") or
            data.get("conversation_id") or
            data.get("generation_id") or ""
        ),
        "model": data.get("model", ""),
        "repo": repo,
        "branch": git("git rev-parse --abbrev-ref HEAD"),
        "commit": git("git rev-parse --short HEAD"),
        "student": git("git config user.email"),
    }

    if tool == "claude":
        if event != "UserPromptSubmit":
            return None
        prompt = data.get("prompt", "")[:1000]
        base.update({"prompt": prompt})

    elif tool == "gemini":
        if event == "BeforeAgent":
            prompt = data.get("prompt", "")[:1000]
        else:
            req = data.get("request", {})
            contents = req.get("contents", [])
            prompt = ""
            for c in reversed(contents):
                for part in c.get("parts", []):
                    if part.get("text"):
                        prompt = part["text"][:1000]
                        break
                if prompt:
                    break
        if not prompt:
            return None
        base.update({"prompt": prompt})

    elif tool == "codex":
        if event not in {"UserPromptSubmit", "UserPrompt"}:
            return None
        prompt = data.get("prompt") or ""
        if not prompt:
            return None
        base.update({"turn_id": data.get("turn_id", ""),
                     "transcript_path": data.get("transcript_path", ""),
                     "capture_method": "native_hook",
                     "prompt": prompt})
        identifier = [base["turn_id"], prompt]
        base["entry_id"] = entry_id(base["session_id"], "UserPrompt", identifier)

    elif tool == "cursor":
        prompt = data.get("prompt", "")[:1000]
        if not prompt:
            return None
        base.update({"prompt": prompt})

    elif tool == "copilot":
        prompt = data.get("prompt", "")[:1000]
        if not prompt:
            return None
        base.update({"prompt": prompt})

    else:
        prompt = data.get("prompt", "")
        if not prompt:
            return None
        base.update({"prompt": prompt})

    if not base.get("prompt"):
        return None

    base["event"] = "UserPrompt"
    return base



def main():
    # Read stdin as UTF-8 explicitly. On Windows, sys.stdin defaults to the
    # system code page (e.g. cp1252), which corrupts non-Latin1 prompts
    # (Vietnamese, CJK, emoji) into mojibake. The hook payload is always UTF-8.
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
    if not raw:
        sys.exit(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)
    tool = detect_tool(data)
    entry = normalize(data, tool)
    try:
        root = repo_root(data.get("cwd"))
    except (OSError, subprocess.CalledProcessError):
        if tool == "codex":
            print("{}")
        return
    directory = log_dir(root)
    if tool == "codex":
        if entry:
            append_entries(directory, [entry])
        transcript = Path(data.get("transcript_path") or "")
        if transcript.is_file():
            from log_codex import capture
            capture(root, [transcript])
        if data.get("hook_event_name") == "Stop":
            from submit_log import submit_all
            with redirect_stdout(sys.stderr):
                submit_all()
        print("{}")
        return
    if not entry:
        if tool == "codex":
            print("{}")
        sys.exit(0)

    append_entries(directory, [entry])

    # Codex expects a hook-output object; do not inject log text into context.
    print("{}" if tool == "codex" else json.dumps({"status": "logged"}))


if __name__ == "__main__":
    main()
