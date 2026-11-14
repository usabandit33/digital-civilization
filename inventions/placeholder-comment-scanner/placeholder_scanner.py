"""Find unfinished-work markers in Python comments without executing code."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import io
import json
from pathlib import Path
import re
import sys
import tokenize
from typing import Iterable

DEFAULT_MARKERS = ("TODO", "FIXME", "XXX", "HACK", "PLACEHOLDER")
_MARKER_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class Finding:
    """One placeholder marker found in a Python comment."""

    path: str
    line: int
    column: int
    marker: str


class SourceTokenizationError(ValueError):
    """Raised when Python source cannot be tokenized completely."""


def _compile_markers(markers: Iterable[str]) -> re.Pattern[str]:
    if isinstance(markers, (str, bytes)):
        raise ValueError("markers must be an iterable of marker names, not a string")

    try:
        values = tuple(markers)
    except TypeError as exc:
        raise ValueError("markers must be an iterable of marker names") from exc

    if not values:
        raise ValueError("at least one marker is required")

    normalized: list[str] = []
    seen: set[str] = set()
    for marker in values:
        if not isinstance(marker, str) or not _MARKER_NAME.fullmatch(marker):
            raise ValueError("each marker must be a non-empty identifier-like string")
        upper = marker.upper()
        if upper not in seen:
            normalized.append(re.escape(marker))
            seen.add(upper)

    alternatives = "|".join(sorted(normalized, key=len, reverse=True))
    return re.compile(
        rf"(?<![A-Za-z0-9_])(?:{alternatives})(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )


def scan_source(
    source: str,
    *,
    path: str = "<string>",
    markers: Iterable[str] = DEFAULT_MARKERS,
) -> list[Finding]:
    """Return placeholder markers found in COMMENT tokens in ``source``.

    Strings and docstrings are intentionally ignored. Line and column numbers
    in findings are 1-based. The function parses tokens only; it never executes
    or imports the supplied source.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(path, str):
        raise TypeError("path must be a string")

    pattern = _compile_markers(markers)
    findings: list[Finding] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT:
                continue
            for match in pattern.finditer(token.string):
                findings.append(
                    Finding(
                        path=path,
                        line=token.start[0],
                        column=token.start[1] + match.start() + 1,
                        marker=match.group(0).upper(),
                    )
                )
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise SourceTokenizationError(str(exc)) from exc

    return findings


def scan_file(
    path: str | Path,
    *,
    markers: Iterable[str] = DEFAULT_MARKERS,
) -> list[Finding]:
    """Read one explicitly supplied Python file and scan its comment tokens."""
    display_path = str(path)
    with tokenize.open(display_path) as handle:
        source = handle.read()
    return scan_source(source, path=display_path, markers=markers)


def _build_report(paths: list[str], markers: Iterable[str]) -> dict:
    findings: list[Finding] = []
    errors: list[dict[str, str]] = []
    scanned = 0

    for path in paths:
        try:
            findings.extend(scan_file(path, markers=markers))
            scanned += 1
        except (OSError, UnicodeError, SourceTokenizationError, ValueError) as exc:
            errors.append({
                "path": path,
                "type": type(exc).__name__,
                "message": str(exc),
            })

    return {
        "schema_version": "1.0",
        "ok": not findings and not errors,
        "files_requested": len(paths),
        "files_scanned": scanned,
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "errors": errors,
    }


def _positive_markers(values: list[str] | None) -> tuple[str, ...]:
    """Append CLI markers to the built-in defaults."""
    return DEFAULT_MARKERS + tuple(values or ())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="explicit Python source files to scan")
    parser.add_argument(
        "--marker",
        action="append",
        dest="markers",
        help="additional marker name; may be repeated (defaults: TODO, FIXME, XXX, HACK, PLACEHOLDER)",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    args = parser.parse_args(argv)

    report = _build_report(args.paths, _positive_markers(args.markers))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for finding in report["findings"]:
            print(
                f"{finding['path']}:{finding['line']}:{finding['column']}: "
                f"placeholder marker {finding['marker']}"
            )
        for error in report["errors"]:
            print(
                f"ERROR {error['path']}: {error['type']}: {error['message']}",
                file=sys.stderr,
            )
        if not report["findings"] and not report["errors"]:
            print(f"No placeholder comments found in {report['files_scanned']} file(s).")
        elif report["findings"]:
            print(f"Found {report['finding_count']} placeholder marker(s).", file=sys.stderr)

    if report["errors"]:
        return 2
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
