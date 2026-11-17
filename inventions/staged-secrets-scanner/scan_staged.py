#!/usr/bin/env python3
"""Scan staged Git blobs for common credential patterns without printing secrets."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any

SCHEMA_VERSION = "1.0"
MAX_STAGED_FILES = 500
MAX_CHANGED_PATH_BYTES = 2_048_000
MAX_FILE_BYTES = 1_048_576
MAX_TOTAL_BYTES = 10_485_760
MAX_ALLOWLIST_BYTES = 65_536
GIT_TIMEOUT_SECONDS = 10
DEFAULT_ALLOWLIST = Path(__file__).with_name("allowlist.json")

# These are deliberately high-confidence token formats. Generic assignments such
# as PASSWORD=... are omitted because they create too many false positives.
PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key_id": re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    "github_classic_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    "github_fine_grained_token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,255}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,255}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "stripe_live_secret": re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,255}\b"),
    "npm_token": re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"),
    "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


class ScanError(ValueError):
    """A scan could not be completed safely."""


def _git(root: Path, args: list[str], *, input_data: bytes | None = None) -> bytes:
    """Run a fixed Git subcommand without a shell or user-controlled arguments."""
    env = os.environ.copy()
    # Ignore environment overrides that can redirect Git to another index,
    # object store, executable, or work tree.
    for key in tuple(env):
        if key.startswith("GIT_"):
            env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(root),
            env=env,
            input=input_data,
            stdin=subprocess.DEVNULL if input_data is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScanError("git_unavailable_or_timed_out") from exc
    if completed.returncode != 0:
        raise ScanError("git_command_failed")
    return completed.stdout


def _repo_root(start: Path) -> Path:
    try:
        supplied = start.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ScanError("repository_path_unavailable") from exc
    if not supplied.is_dir():
        raise ScanError("repository_path_not_directory")
    output = _git(supplied, ["rev-parse", "--show-toplevel"])
    try:
        root = Path(os.fsdecode(output.rstrip(b"\r\n"))).resolve(strict=True)
    except OSError as exc:
        raise ScanError("repository_root_unavailable") from exc
    if not root.is_dir():
        raise ScanError("repository_root_not_directory")
    return root


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        bool(path.parts)
        and not path.is_absolute()
        and all(part not in ("", ".", "..") for part in path.parts)
        and not any(character in value for character in "*?[]")
        and path.as_posix() == value
    )


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_allowlist(path: Path) -> dict[str, set[str]]:
    """Load exact path/rule suppressions; wildcard and parent paths are forbidden."""
    try:
        if path.is_symlink() or not path.is_file():
            raise ScanError("allowlist_unavailable")
        if path.stat().st_size > MAX_ALLOWLIST_BYTES:
            raise ScanError("allowlist_too_large")
        raw = path.read_bytes()
        if len(raw) > MAX_ALLOWLIST_BYTES:
            raise ScanError("allowlist_too_large")
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except ScanError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ScanError("allowlist_invalid") from exc

    if not isinstance(document, dict) or set(document) != {"version", "entries"}:
        raise ScanError("allowlist_invalid")
    version = document.get("version")
    if type(version) is not int or version != 1 or not isinstance(document.get("entries"), list):
        raise ScanError("allowlist_invalid")
    if len(document["entries"]) > 100:
        raise ScanError("allowlist_too_many_entries")

    result: dict[str, set[str]] = {}
    for entry in document["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "rules", "reason"}:
            raise ScanError("allowlist_invalid")
        path_value = entry["path"]
        rules = entry["rules"]
        reason = entry["reason"]
        if not _safe_relative_path(path_value):
            raise ScanError("allowlist_path_must_be_exact_relative_path")
        if (
            not isinstance(rules, list)
            or not rules
            or any(not isinstance(rule, str) or rule not in PATTERNS for rule in rules)
            or len(rules) != len(set(rules))
        ):
            raise ScanError("allowlist_rules_invalid")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 200:
            raise ScanError("allowlist_reason_invalid")
        allowed = result.setdefault(path_value, set())
        if allowed.intersection(rules):
            raise ScanError("allowlist_duplicate_rule")
        allowed.update(rules)
    return result


def scan_text(
    source: str,
    path: str,
    allowlist: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return detected and allowlisted locations without returning matched text."""
    findings: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        for rule, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                item = {
                    "path": path,
                    "line": line_number,
                    "column": match.start() + 1,
                    "rule": rule,
                }
                if rule in allowlist.get(path, set()):
                    suppressed.append(item)
                else:
                    findings.append(item)
    return findings, suppressed


def _parse_index(raw: bytes) -> dict[str, list[tuple[str, str, int]]]:
    entries: dict[str, list[tuple[str, str, int]]] = {}
    for record in raw.split(b"\x00"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            path = os.fsdecode(raw_path)
            stage_number = int(stage)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ScanError("git_index_unreadable") from exc
        entries.setdefault(path, []).append((mode, oid, stage_number))
    return entries


def _parse_batch(raw: bytes, expected: int) -> list[bytes]:
    blobs: list[bytes] = []
    cursor = 0
    for _ in range(expected):
        newline = raw.find(b"\n", cursor)
        if newline < 0:
            raise ScanError("git_blob_batch_truncated")
        header = raw[cursor:newline].split()
        if len(header) != 3 or header[1] != b"blob":
            raise ScanError("git_index_object_not_blob")
        try:
            size = int(header[2])
        except ValueError as exc:
            raise ScanError("git_blob_size_invalid") from exc
        start = newline + 1
        end = start + size
        if size < 0 or end >= len(raw) or raw[end:end + 1] != b"\n":
            raise ScanError("git_blob_batch_truncated")
        blobs.append(raw[start:end])
        cursor = end + 1
    if cursor != len(raw):
        raise ScanError("git_blob_batch_unexpected_data")
    return blobs


def scan_staged(repo: Path, allowlist_path: Path = DEFAULT_ALLOWLIST) -> tuple[dict[str, Any], int]:
    """Scan changed regular-file blobs from the Git index, not working-tree files."""
    empty: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "files_checked": 0,
        "binary_or_non_utf8_skipped": 0,
        "findings": [],
        "suppressed": [],
        "scan_errors": [],
    }
    try:
        root = _repo_root(repo)
        allowlist = load_allowlist(allowlist_path)
        unmerged = _git(root, ["ls-files", "--unmerged", "-z"])
        if unmerged:
            raise ScanError("unmerged_index_entries")
        changed_raw = _git(root, ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", "--"])
        if len(changed_raw) > MAX_CHANGED_PATH_BYTES:
            raise ScanError("staged_path_list_too_large")
        changed_paths = [os.fsdecode(item) for item in changed_raw.split(b"\x00") if item]
        if len(changed_paths) > MAX_STAGED_FILES:
            raise ScanError("too_many_staged_files")
        if not changed_paths:
            empty.update({"ok": True, "message": "No staged added or modified files to scan."})
            return empty, 0

        index = _parse_index(_git(root, ["ls-files", "--stage", "-z"]))
        selected: list[tuple[str, str]] = []
        for path in changed_paths:
            entries = index.get(path, [])
            if len(entries) != 1 or entries[0][2] != 0:
                raise ScanError("unmerged_or_missing_index_entry")
            mode, oid, _stage = entries[0]
            if mode not in {"100644", "100755"}:
                continue
            selected.append((path, oid))

        if not selected:
            empty.update({"ok": True, "message": "No staged regular text files to scan."})
            return empty, 0

        size_input = b"".join(oid.encode("ascii") + b"\n" for _path, oid in selected)
        size_output = _git(
            root,
            ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
            input_data=size_input,
        )
        size_lines = size_output.splitlines()
        if len(size_lines) != len(selected):
            raise ScanError("git_blob_size_response_invalid")
        sizes: list[int] = []
        total_size = 0
        for line in size_lines:
            fields = line.split()
            if len(fields) != 3 or fields[1] != b"blob":
                raise ScanError("git_index_object_not_blob")
            try:
                size = int(fields[2])
            except ValueError as exc:
                raise ScanError("git_blob_size_invalid") from exc
            if size < 0 or size > MAX_FILE_BYTES:
                raise ScanError("staged_file_too_large")
            sizes.append(size)
            total_size += size
        if total_size > MAX_TOTAL_BYTES:
            raise ScanError("staged_total_too_large")

        blob_input = b"".join(oid.encode("ascii") + b"\n" for _path, oid in selected)
        blob_output = _git(root, ["cat-file", "--batch"], input_data=blob_input)
        blobs = _parse_batch(blob_output, len(selected))

        findings: list[dict[str, Any]] = []
        suppressed: list[dict[str, Any]] = []
        skipped = 0
        checked = 0
        for (path, _oid), blob, expected_size in zip(selected, blobs, sizes):
            if len(blob) != expected_size:
                raise ScanError("git_blob_size_mismatch")
            if b"\x00" in blob:
                skipped += 1
                continue
            try:
                source = blob.decode("utf-8-sig")
            except UnicodeDecodeError:
                skipped += 1
                continue
            checked += 1
            found, ignored = scan_text(source, path, allowlist)
            findings.extend(found)
            suppressed.extend(ignored)

        findings.sort(key=lambda item: (item["path"], item["line"], item["column"], item["rule"]))
        suppressed.sort(key=lambda item: (item["path"], item["line"], item["column"], item["rule"]))
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": not findings,
            "files_checked": checked,
            "binary_or_non_utf8_skipped": skipped,
            "findings": findings,
            "suppressed": suppressed,
            "scan_errors": [],
        }
        return report, 1 if findings else 0
    except ScanError as exc:
        empty["scan_errors"].append({"code": str(exc)})
        return empty, 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository path (default: current directory)")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST), help="exact-path allowlist JSON")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    report, exit_code = scan_staged(Path(args.repo), Path(args.allowlist))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for finding in report["findings"]:
            print(
                f"{finding['path']}:{finding['line']}:{finding['column']}: "
                f"possible credential pattern ({finding['rule']})"
            )
        for item in report["suppressed"]:
            print(
                f"ALLOWLISTED {item['path']}:{item['line']}:{item['column']}: "
                f"{item['rule']}"
            )
        for error in report["scan_errors"]:
            print(f"ERROR: {error['code']}", file=sys.stderr)
        if exit_code == 0 and not report["suppressed"]:
            print(report.get("message", f"No credential patterns found in {report['files_checked']} staged text file(s)."))
        elif exit_code == 1:
            print(f"Found {len(report['findings'])} possible credential pattern(s).", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
