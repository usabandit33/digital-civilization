#!/usr/bin/env python3
"""Discover and run repository test suites separately, using only Python's stdlib."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

EXCLUDED_DIRECTORIES = {
    ".git", ".venv", "venv", ".tox", ".nox", "__pycache__",
    ".pytest_cache", ".mypy_cache", "node_modules", "build", "dist",
}
TEST_PREFIX = "test"
TEST_SUFFIX = ".py"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_TIMEOUT_SECONDS = 3600
MAX_OUTPUT_CHARACTERS = 8000


def find_repo_root(start: Path | str) -> Path | None:
    """Find the checkout root by walking upward to its constitution and system dir."""
    candidate = Path(start).expanduser()
    if candidate.is_file():
        candidate = candidate.parent
    try:
        candidate = candidate.resolve()
    except OSError:
        return None

    for directory in (candidate, *candidate.parents):
        if (directory / "constitution.md").is_file() and (directory / "system").is_dir():
            return directory
    return None


def discover_suites(repo_root: Path) -> list[dict[str, Any]]:
    """Group test files into project suites without following symlinks or build dirs.

    A test file directly in a project directory belongs to that directory's suite.
    A test file in a directory named tests belongs to its parent project suite.
    """
    root = repo_root.resolve()
    groups: dict[Path, dict[str, Any]] = {}

    for current, directory_names, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            name for name in directory_names
            if name not in EXCLUDED_DIRECTORIES
            and not (current_path / name).is_symlink()
        )

        for filename in sorted(filenames):
            if not (filename.startswith(TEST_PREFIX) and filename.endswith(TEST_SUFFIX)):
                continue

            test_file = current_path / filename
            if test_file.is_symlink() or not test_file.is_file():
                continue

            test_directory = test_file.parent
            suite_root = (
                test_directory.parent
                if test_directory.name == "tests"
                else test_directory
            )
            try:
                suite_root = suite_root.resolve()
                test_directory = test_directory.resolve()
                suite_root.relative_to(root)
                test_directory.relative_to(root)
            except (OSError, ValueError):
                continue

            group = groups.setdefault(
                suite_root,
                {"root": suite_root, "test_directories": set(), "test_files": 0},
            )
            group["test_directories"].add(test_directory)
            group["test_files"] += 1

    suites = []
    for suite_root, group in groups.items():
        relative_name = suite_root.relative_to(root).as_posix() or "."
        suites.append({
            "name": relative_name,
            "root": suite_root,
            "test_directories": sorted(group["test_directories"], key=lambda p: p.as_posix()),
            "test_files": group["test_files"],
        })
    return sorted(suites, key=lambda suite: suite["name"])


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _bounded_output(parts: list[str]) -> str:
    output = "\n".join(part for part in parts if part)
    if len(output) > MAX_OUTPUT_CHARACTERS:
        return "[earlier output omitted]\n" + output[-MAX_OUTPUT_CHARACTERS:]
    return output


def run_suite(
    repo_root: Path,
    suite: dict[str, Any],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run every discovered test directory for one suite in isolated Python processes."""
    root = repo_root.resolve()
    suite_root = Path(suite["root"]).resolve()
    env = os.environ.copy()
    python_paths = [str(suite_root), str(root)]
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    started = time.monotonic()
    deadline = started + timeout_seconds
    output_parts: list[str] = []
    return_codes: list[int] = []
    timed_out = False

    for test_directory in suite["test_directories"]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            output_parts.append(
                f"Timed out after {timeout_seconds} seconds before "
                f"{Path(test_directory).relative_to(root).as_posix()} could run."
            )
            break

        command = [
            sys.executable, "-m", "unittest", "discover",
            "-s", str(test_directory),
            "-p", "test*.py",
            "-v",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                timeout=max(1, remaining),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            output_parts.extend([_as_text(exc.stdout), _as_text(exc.stderr)])
            output_parts.append(
                f"Timed out after {timeout_seconds} seconds while running "
                f"{Path(test_directory).relative_to(root).as_posix()}."
            )
            break
        except OSError as exc:
            return_codes.append(1)
            output_parts.append(f"Could not start test process: {type(exc).__name__}")
            continue

        return_codes.append(completed.returncode)
        output_parts.extend([completed.stdout, completed.stderr])

    duration = round(time.monotonic() - started, 3)
    if timed_out:
        status = "timed_out"
    elif not return_codes or any(code != 0 for code in return_codes):
        status = "failed"
    else:
        status = "passed"

    return {
        "name": suite["name"],
        "test_files": suite["test_files"],
        "test_directories": [
            Path(path).relative_to(root).as_posix()
            for path in suite["test_directories"]
        ],
        "status": status,
        "return_codes": return_codes,
        "duration_seconds": duration,
        "output": _bounded_output(output_parts),
    }


def run_all(
    repo_root: Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run all discovered suites and return a machine-readable summary."""
    suites = discover_suites(repo_root)
    results = [run_suite(repo_root, suite, timeout_seconds) for suite in suites]
    passed = sum(result["status"] == "passed" for result in results)
    failed = sum(result["status"] == "failed" for result in results)
    timed_out = sum(result["status"] == "timed_out" for result in results)
    return {
        "schema_version": "1.0",
        "ok": bool(results) and passed == len(results),
        "repository": repo_root.name,
        "total_suites": len(results),
        "passed_suites": passed,
        "failed_suites": failed,
        "timed_out_suites": timed_out,
        "suites": results,
    }


def _positive_timeout(value: str) -> int:
    try:
        seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be an integer number of seconds") from exc
    if not 1 <= seconds <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(
            f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds"
        )
    return seconds


def _render_text(result: dict[str, Any]) -> None:
    print("Digital Civilization test runner")
    if not result["suites"]:
        print("No test suites were discovered.")
        return

    for suite in result["suites"]:
        label = suite["status"].upper()
        print(
            f"{label:9} {suite['name']} "
            f"({suite['test_files']} test files, {suite['duration_seconds']:.3f}s)"
        )
        if suite["status"] != "passed" and suite["output"]:
            print(suite["output"])

    print(
        "Summary: "
        f"{result['passed_suites']}/{result['total_suites']} suites passed; "
        f"{result['failed_suites']} failed; "
        f"{result['timed_out_suites']} timed out."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        help="repository root or a path inside the checkout (default: this script's checkout)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_timeout,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"maximum seconds per suite (default: {DEFAULT_TIMEOUT_SECONDS}; max: {MAX_TIMEOUT_SECONDS})",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    args = parser.parse_args(argv)

    start = Path(args.root).expanduser() if args.root else Path(__file__)
    repo_root = find_repo_root(start)
    if repo_root is None:
        result = {
            "schema_version": "1.0",
            "ok": False,
            "repository": None,
            "total_suites": 0,
            "passed_suites": 0,
            "failed_suites": 0,
            "timed_out_suites": 0,
            "suites": [],
            "error": "Could not locate a repository containing constitution.md and system/.",
        }
        exit_code = 2
    else:
        result = run_all(repo_root, args.timeout)
        exit_code = 0 if result["ok"] else (2 if result["total_suites"] == 0 else 1)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _render_text(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
