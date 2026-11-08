#!/usr/bin/env python3
"""Sanitize configured absolute path roots in text or JSON-compatible values.

The module is deliberately standard-library-only and performs no I/O except
when its optional stdin/stdout CLI is used.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


def default_home_roots() -> list[str]:
    """Return known absolute home-directory roots for the current user."""
    candidates: list[str] = []
    try:
        candidates.append(str(Path.home()))
    except (RuntimeError, OSError):
        pass
    for key in ("HOME", "USERPROFILE"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)

    roots: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        root = _validated_root(candidate)
        if not root:
            continue
        identity = _root_identity(root)
        if identity not in seen:
            roots.append(root)
            seen.add(identity)
    return roots


def _validated_root(value: os.PathLike[str] | str) -> str | None:
    """Normalize an absolute root while rejecting empty and filesystem roots."""
    raw = os.fspath(value).strip()
    if not raw or not (os.path.isabs(raw) or ntpath.isabs(raw)):
        return None
    root = raw.rstrip("\\/")
    if not root or root == "/" or re.fullmatch(r"[A-Za-z]:", root):
        return None
    return root


def _root_identity(root: str) -> str:
    if ntpath.splitdrive(root)[0] or root.startswith("\\\\"):
        return ntpath.normcase(ntpath.normpath(root))
    return root


def _compile_roots(roots: Iterable[os.PathLike[str] | str]) -> list[re.Pattern[str]]:
    normalized: dict[str, str] = {}
    for candidate in roots:
        root = _validated_root(candidate)
        if root:
            normalized.setdefault(_root_identity(root), root)

    patterns: list[re.Pattern[str]] = []
    # Longest roots first so a nested private root is not partially replaced.
    for root in sorted(normalized.values(), key=len, reverse=True):
        pieces = re.split(r"[\\/]", root)
        root_pattern = r"[\\/]".join(re.escape(piece) for piece in pieces)
        is_windows = bool(ntpath.splitdrive(root)[0]) or root.startswith("\\\\")
        flags = re.IGNORECASE if is_windows else 0
        patterns.append(re.compile(
            r"(?<![A-Za-z0-9_.-])" + root_pattern + r"(?=$|[\\/]|[\s\"'<>),;])",
            flags,
        ))
    return patterns


def sanitize_text(
    text: str,
    roots: Iterable[os.PathLike[str] | str] | None = None,
    replacement: str = "~",
) -> str:
    """Replace configured absolute roots in text, preserving path suffixes.

    If roots is omitted, known home-directory roots are used. Passing an
    empty iterable disables replacement. Windows roots are matched without
    regard to case and accept either slash style. Relative paths are untouched.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    selected_roots = default_home_roots() if roots is None else roots
    return _sanitize_with_patterns(text, _compile_roots(selected_roots), replacement)


def _sanitize_with_patterns(
    text: str, patterns: list[re.Pattern[str]], replacement: str
) -> str:
    result = text
    for pattern in patterns:
        result = pattern.sub(lambda match: replacement, result)
    return result


def sanitize_value(
    value: Any,
    roots: Iterable[os.PathLike[str] | str] | None = None,
    replacement: str = "~",
) -> Any:
    """Recursively sanitize string values in JSON-compatible data.

    Mapping keys and non-string scalar values are preserved to avoid changing
    field names or data types. Lists and tuples retain their container type.
    """
    selected_roots = default_home_roots() if roots is None else roots
    patterns = _compile_roots(selected_roots)

    def visit(item: Any) -> Any:
        if isinstance(item, str):
            return _sanitize_with_patterns(item, patterns, replacement)
        if isinstance(item, list):
            return [visit(child) for child in item]
        if isinstance(item, tuple):
            return tuple(visit(child) for child in item)
        if isinstance(item, dict):
            return {key: visit(child) for key, child in item.items()}
        return item

    return visit(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", action="append", default=[],
        help="additional absolute path root to replace (repeatable)",
    )
    parser.add_argument("--replacement", default="~", help="replacement for each root (default: ~)")
    args = parser.parse_args(argv)

    roots = [*default_home_roots(), *args.root]
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON input: {exc.msg}", file=sys.stderr)
        return 2

    sanitized = sanitize_value(payload, roots=roots, replacement=args.replacement)
    json.dump(sanitized, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
