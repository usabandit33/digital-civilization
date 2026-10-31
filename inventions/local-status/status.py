#!/usr/bin/env python3
"""Local status reporter for the Digital Civilization.

Safe, local-only snapshot. No network. No personal data leakage.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    """Walk upward until we find a directory containing constitution.md."""
    current = start.resolve()
    for _ in range(10):
        if (current / "constitution.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def run_git(args: list[str], cwd: Path) -> str:
    """Run a restricted git command. Returns empty string on failure."""
    allowed = {
        ("status", "--short"),
        ("log", "-5", "--pretty=format:%s"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
    }
    # Normalize for check
    key = tuple(args)
    if key not in allowed and not (len(args) >= 2 and args[0] == "log" and args[1].startswith("-")):
        # Extra safety: only the commands we listed plus basic log
        if args[0] not in ("status", "log", "rev-parse"):
            return ""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def recent_journals(repo: Path, limit: int = 5) -> list[str]:
    journal_dir = repo / "journal"
    if not journal_dir.is_dir():
        return []
    files = sorted(journal_dir.glob("*.md"), reverse=True)[:limit]
    titles = []
    for f in files:
        try:
            first = f.read_text(encoding="utf-8", errors="replace").splitlines()
            title = next((line.strip("# ").strip() for line in first if line.strip()), f.name)
            # Keep it short and relative
            titles.append(title[:120])
        except OSError:
            titles.append(f.name)
    return titles


def task_counts(repo: Path) -> dict[str, int]:
    db_path = repo / "data" / "civilization.db"
    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    if not db_path.is_file():
        return counts
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
        ).fetchall()
        for row in rows:
            status = str(row["status"])
            if status in counts:
                counts[status] = int(row["n"])
        conn.close()
    except (sqlite3.Error, OSError):
        pass
    return counts


def collect_status(repo: Path) -> dict:
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "unknown"
    status_short = run_git(["status", "--short"], repo)
    recent_commits = [
        line.strip() for line in run_git(["log", "-5", "--pretty=format:%s"], repo).splitlines() if line.strip()
    ]
    journals = recent_journals(repo)
    tasks = task_counts(repo)

    # Sanitize: never include absolute paths
    dirty = bool(status_short)

    return {
        "repo": "digital-civilization",
        "branch": branch,
        "dirty": dirty,
        "status_lines": status_short.splitlines()[:20] if status_short else [],
        "recent_commits": recent_commits[:5],
        "recent_journals": journals,
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Digital Civilization status")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo = find_repo_root(script_dir)
    if repo is None:
        print("Error: could not locate Digital Civilization repo root (missing constitution.md).", file=sys.stderr)
        sys.exit(1)

    data = collect_status(repo)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Digital Civilization status")
        print(f"Branch: {data['branch']}{' (dirty)' if data['dirty'] else ''}")
        if data["status_lines"]:
            print("Changes:")
            for line in data["status_lines"]:
                print(f"  {line}")
        print("Recent commits:")
        for c in data["recent_commits"] or ["(none)"]:
            print(f"  - {c}")
        print("Recent journals:")
        for j in data["recent_journals"] or ["(none)"]:
            print(f"  - {j}")
        t = data["tasks"]
        print(f"Tasks: pending={t['pending']} running={t['running']} done={t['done']} failed={t['failed']}")


if __name__ == "__main__":
    main()
