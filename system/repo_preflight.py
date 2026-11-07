#!/usr/bin/env python3
"""Read-only preflight checks for a Digital Civilization checkout."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

MIN_PYTHON = (3, 9)
REQUIRED_DIRECTORIES = (
    "agents", "core", "data", "experiments", "inventions",
    "journal", "memory", "projects", "services", "system",
)


def find_repo_root(start: Path) -> Optional[Path]:
    """Find the checkout root by walking upward for its constitution file."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / "constitution.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def check_python(minimum: tuple[int, int] = MIN_PYTHON) -> dict:
    """Report whether the running interpreter meets the supported baseline."""
    current = tuple(sys.version_info[:3])
    ok = current[:2] >= minimum
    implementation = platform.python_implementation()
    version = ".".join(str(part) for part in current)
    required = ".".join(str(part) for part in minimum)
    return {
        "name": "python",
        "ok": ok,
        "detail": f"{implementation} {version}; minimum {required}",
    }


def check_git(repo: Path) -> tuple[dict, Optional[Path]]:
    """Check Git availability and confirm repo is the current checkout."""
    executable = shutil.which("git")
    if executable is None:
        return {
            "name": "git",
            "ok": False,
            "detail": "git executable not found on PATH",
        }, None

    try:
        version = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if version.returncode != 0:
            return {"name": "git", "ok": False, "detail": "git --version failed"}, None

        top_level = subprocess.run(
            [executable, "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if top_level.returncode != 0:
            return {
                "name": "git",
                "ok": False,
                "detail": "repository directory is not a Git working tree",
            }, None

        actual_root = Path(top_level.stdout.strip()).resolve()
        if actual_root != repo.resolve():
            return {
                "name": "git",
                "ok": False,
                "detail": "Git working-tree root does not match the detected repository root",
            }, None

        git_dir_result = subprocess.run(
            [executable, "-C", str(repo), "rev-parse", "--absolute-git-dir"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        git_dir = None
        if git_dir_result.returncode == 0 and git_dir_result.stdout.strip():
            git_dir = Path(git_dir_result.stdout.strip()).resolve()

        return {
            "name": "git",
            "ok": True,
            "detail": version.stdout.strip() or "Git is available",
        }, git_dir
    except (OSError, subprocess.TimeoutExpired):
        return {
            "name": "git",
            "ok": False,
            "detail": "Git command could not be completed",
        }, None


def check_required_directories(repo: Path) -> dict:
    """Check that the expected top-level project directories exist."""
    missing = [name for name in REQUIRED_DIRECTORIES if not (repo / name).is_dir()]
    detail = "all required directories are present"
    if missing:
        detail = "missing: " + ", ".join(missing)
    return {
        "name": "required_directories",
        "ok": not missing,
        "detail": detail,
        "missing": missing,
    }


def check_writable_state(repo: Path, git_dir: Optional[Path]) -> dict:
    """Check directory permissions without creating or changing any files."""
    targets = [("repository root", repo)]
    if git_dir is not None:
        targets.append(("Git metadata", git_dir))

    unavailable = [
        label
        for label, path in targets
        if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK)
    ]
    if unavailable:
        detail = "not writable or not accessible: " + ", ".join(unavailable)
    elif git_dir is not None:
        detail = "repository and Git metadata directories appear writable (permission check only)"
    else:
        detail = "repository root appears writable (permission check only)"

    return {"name": "writable_state", "ok": not unavailable, "detail": detail}


def run_preflight(repo: Path) -> dict:
    """Run all checks and return a path-sanitized result object."""
    git_check, git_dir = check_git(repo)
    checks = [
        check_python(),
        git_check,
        check_required_directories(repo),
        check_writable_state(repo, git_dir),
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "repository": repo.name,
        "checks": checks,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight checks for a Digital Civilization checkout."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    repo = find_repo_root(Path(__file__).resolve().parent)
    if repo is None:
        result = {
            "ok": False,
            "repository": None,
            "checks": [{
                "name": "repository_root",
                "ok": False,
                "detail": "could not find constitution.md above the script location",
            }],
        }
    else:
        result = run_preflight(repo)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Digital Civilization repository preflight")
        print(f"Repository: {result['repository'] or 'not found'}")
        for item in result["checks"]:
            print(f"{'OK' if item['ok'] else 'FAIL'} {item['name']}: {item['detail']}")
        print("Overall: " + ("READY" if result["ok"] else "NOT READY"))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
