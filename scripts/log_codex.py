#!/usr/bin/env python3
"""
OpenAI Codex CLI / Desktop log scanner — extracts user prompts from
local Codex session rollout files into .ai-log/session.jsonl.

Source of truth:
    ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows console encoding so VN diacritics in prompts print cleanly.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VN_TZ = timezone(timedelta(hours=7))

IGNORED_PROMPT_PREFIXES = (
    "<",
    ">>>",
    "[",
    "{",
    "The active permission profile",
    "Reviewed Codex session",
    "Host notice:",
    "The following is the Codex agent",
    "The Codex agent has requested",
    "Assess the exact planned action",
    "Planned action JSON:",
    "Some conversation entries were omitted.",
    "Retained source order",
)


def git(cmd: str, cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL,
            cwd=cwd,
        ).strip()
    except Exception:
        return ""


def repo_context(cwd: Path | None = None) -> tuple[str, str, str, str]:
    root = cwd or Path.cwd()
    repo = git("git remote get-url origin", cwd).rstrip("/").split("/")[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return (
        repo or root.name,
        git("git rev-parse --abbrev-ref HEAD", cwd),
        git("git rev-parse --short HEAD", cwd),
        git("git config user.email", cwd)
        or os.environ.get("USERNAME", os.environ.get("USER", "unknown")),
    )


def _normalize(p: str) -> str:
    if not p:
        return ""
    return p.strip().lower().replace("/", "\\").rstrip("\\")


def _session_matches_repo(cwds: set[str], repo_root_n: str) -> bool:
    if not repo_root_n or not cwds:
        return False
    for cwd in cwds:
        if cwd == repo_root_n:
            return True
        if cwd.startswith(repo_root_n + "\\"):
            return True
        if repo_root_n.startswith(cwd + "\\"):
            return True
        # Also include Downloads/New folder if user operated project copies there
        if "downloads\\new folder" in cwd:
            return True
    return False


def get_logged_entry_ids(log_dir: Path) -> set[str]:
    logged: set[str] = set()
    files_to_check = []
    live_file = log_dir / "session.jsonl"
    if live_file.exists():
        files_to_check.append(live_file)
    archive_dir = log_dir / "archive"
    if archive_dir.exists():
        files_to_check.extend(archive_dir.glob("*.jsonl"))

    for f in files_to_check:
        try:
            with open(f, encoding="utf-8-sig") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        eid = entry.get("entry_id")
                        if eid:
                            logged.add(eid)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    return logged


def parse_session_file(session_file: Path, repo_root_n: str, no_repo_filter: bool):
    """Parse one rollout-*.jsonl session file, returning (cwds, model, list of prompt dicts)."""
    try:
        with open(session_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = [json.loads(line) for line in f if line.strip()]
    except Exception:
        return set(), "", []

    cwds: set[str] = set()
    model = ""
    session_id = session_file.stem
    if session_id.startswith("rollout-"):
        parts = session_id.split("-", 4)
        if len(parts) >= 5:
            session_id = parts[4]

    for d in lines:
        payload = d.get("payload", {})
        if d.get("type") == "turn_context":
            cwd = payload.get("cwd")
            if cwd:
                cwds.add(_normalize(cwd))
            if not model:
                model = payload.get("model", "")
        elif payload.get("role") == "user":
            for item in payload.get("content", []):
                t = item.get("text", "")
                if "<cwd>" in t:
                    m = re.search(r"<cwd>(.*?)</cwd>", t)
                    if m:
                        cwds.add(_normalize(m.group(1)))

    if not no_repo_filter and not _session_matches_repo(cwds, repo_root_n):
        return cwds, model, []

    if not model:
        model = "gpt-6.1-sol"

    prompts = []
    for d in lines:
        payload = d.get("payload", {})
        if payload.get("role") == "user":
            for item in payload.get("content", []):
                if item.get("type") == "input_text":
                    text = item.get("text", "").strip()
                    if not text or any(text.startswith(pref) for pref in IGNORED_PROMPT_PREFIXES):
                        continue
                    ts = d.get("timestamp")
                    ordinal = d.get("ordinal", 0)
                    prompts.append({
                        "session_id": session_id,
                        "ordinal": ordinal,
                        "timestamp": ts,
                        "prompt": text,
                        "model": model,
                    })

    return cwds, model, prompts


def build_entry(item: dict, repo: str, branch: str, commit: str, student: str) -> dict:
    ts = item["timestamp"] or ""
    if ts.endswith("Z"):
        try:
            ts = (
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                .astimezone(VN_TZ)
                .isoformat()
            )
        except ValueError:
            pass
    if not ts:
        ts = datetime.now(VN_TZ).isoformat()

    return {
        "ts": ts,
        "tool": "codex",
        "event": "UserPrompt",
        "entry_id": f"codex-{item['session_id']}-{item['ordinal']:05d}",
        "session_id": item["session_id"],
        "model": item["model"],
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "student": student,
        "prompt": item["prompt"],
        "response_summary": "",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract user prompts from OpenAI Codex CLI/Desktop sessions into .ai-log/session.jsonl."
    )
    parser.add_argument("--auto", action="store_true",
                        help="Default mode: scan recent sessions.")
    parser.add_argument("--hours", type=int, default=72,
                        help="Window in hours when scanning (default: 72).")
    parser.add_argument("--all", action="store_true",
                        help="Ignore time cutoff; scan all sessions.")
    parser.add_argument("--no-repo-filter", action="store_true",
                        help="Don't filter sessions by current repo.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be logged without writing.")
    args = parser.parse_args()

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        print(f"[codex-log] No Codex sessions directory found at {sessions_dir}.", file=sys.stderr)
        sys.exit(0)

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "session.jsonl"
    logged_ids = get_logged_entry_ids(log_dir)

    cutoff = None
    if not args.all:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    repo_root_n = "" if args.no_repo_filter else _normalize(str(Path.cwd()))
    repo, branch, commit, student = repo_context()

    new_entries = []
    for session_file in sorted(sessions_dir.glob("**/*.jsonl")):
        if cutoff:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                continue

        cwds, model, prompts = parse_session_file(session_file, repo_root_n, args.no_repo_filter)
        for p in prompts:
            entry = build_entry(p, repo, branch, commit, student)
            if entry["entry_id"] in logged_ids:
                continue
            new_entries.append(entry)
            logged_ids.add(entry["entry_id"])

    if not new_entries:
        scope = "all" if args.all else f"{args.hours}h"
        print(f"[codex-log] No new prompts (window={scope}).", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print(f"\n[codex-log] DRY RUN — would log {len(new_entries)} entries:\n")
        for e in new_entries:
            preview = e["prompt"].replace("\n", " ")[:100]
            print(f"  [{e['ts'][:19]}] {preview}")
        sys.exit(0)

    with open(log_file, "a", encoding="utf-8") as f:
        for e in new_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"[codex-log] Logged {len(new_entries)} prompt(s) from Codex.", file=sys.stderr)


if __name__ == "__main__":
    main()
