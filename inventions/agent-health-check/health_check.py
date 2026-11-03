#!/usr/bin/env python3
"""Offline-friendly process and SQLite health check; standard library only."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def check_http(url: str, timeout: float) -> dict[str, Any]:
    """Check a configured HTTP health endpoint without sending credentials."""
    request = urllib.request.Request(url, headers={"User-Agent": "agent-health-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            ok = 200 <= status < 300
            return {"name": "process", "ok": ok, "detail": f"HTTP {status}"}
    except urllib.error.HTTPError as exc:
        return {"name": "process", "ok": False, "detail": f"HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", None)
        detail = type(reason).__name__ if reason is not None else type(exc).__name__
        return {"name": "process", "ok": False, "detail": detail}


def check_sqlite(db_path: Path) -> dict[str, Any]:
    """Open an existing SQLite database read-only and perform a minimal read."""
    if not db_path.is_file():
        return {"name": "sqlite", "ok": False, "detail": "database file not found"}
    try:
        # URI mode=ro prevents accidental database creation or modification.
        uri = db_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        try:
            connection.execute("SELECT 1").fetchone()
            connection.execute("PRAGMA schema_version").fetchone()
        finally:
            connection.close()
        return {"name": "sqlite", "ok": True, "detail": "read-only query succeeded"}
    except (sqlite3.Error, OSError, ValueError) as exc:
        return {"name": "sqlite", "ok": False, "detail": type(exc).__name__}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check an HTTP process endpoint and an existing SQLite database."
    )
    parser.add_argument("--url", required=True, help="HTTP(S) health endpoint URL")
    parser.add_argument("--db", required=True, type=Path, help="Existing SQLite database path")
    parser.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds (0.1-30)")
    parser.add_argument("--json", action="store_true", help="Emit a JSON status object")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.1 <= args.timeout <= 30:
        build_parser().error("--timeout must be between 0.1 and 30 seconds")
    if not args.url.startswith(("http://", "https://")):
        build_parser().error("--url must use http:// or https://")

    checks = [check_http(args.url, args.timeout), check_sqlite(args.db)]
    healthy = all(item["ok"] for item in checks)
    result = {"ok": healthy, "checks": checks}
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for item in checks:
            print(f"{'OK' if item['ok'] else 'FAIL'} {item['name']}: {item['detail']}")
        print("Overall: " + ("HEALTHY" if healthy else "UNHEALTHY"))
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
