"""Read-only integrity checks for the Digital Civilization SQLite task queue.

Run from the repository root with python -m core.queue_integrity.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "civilization.db"
REQUIRED_COLUMNS = ("id", "created_at", "updated_at", "priority", "status", "title")
ALLOWED_STATUSES = frozenset(("pending", "running", "done", "failed"))


def _issue(code: str, message: str, **details: Any) -> Dict[str, Any]:
    item: Dict[str, Any] = {"code": code, "message": message}
    item.update(details)
    return item


def inspect_queue(database: Union[str, Path] = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Inspect a queue database without changing it and return a JSON-safe report.

    The database is opened with SQLite mode=ro and query_only enabled.
    No schema creation, migrations, repair, or automatic cleanup is performed.
    """
    path = Path(database).expanduser()
    report: Dict[str, Any] = {
        "ok": False,
        "database": path.name or str(path),
        "task_count": 0,
        "checks": {
            "database_readable": False,
            "sqlite_integrity": None,
            "tasks_table_present": False,
            "required_columns_present": None,
            "unique_task_ids": None,
            "valid_statuses": None,
            "required_values_present": None,
        },
        "issues": [],
    }

    if not path.is_file():
        report["issues"].append(
            _issue("database_not_found", "The queue database file does not exist or is not a regular file.")
        )
        return report

    try:
        # as_uri() safely escapes spaces and other URI-sensitive path characters.
        connection_uri = path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(connection_uri, uri=True, timeout=2.0)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            report["checks"]["database_readable"] = True

            integrity_ok = True
            integrity_messages = []
            for integrity_row in connection.execute("PRAGMA quick_check"):
                if integrity_row[0] != "ok":
                    integrity_ok = False
                    if len(integrity_messages) < 10:
                        integrity_messages.append(str(integrity_row[0]))
            report["checks"]["sqlite_integrity"] = integrity_ok
            if not integrity_ok:
                report["issues"].append(
                    _issue(
                        "sqlite_integrity_check_failed",
                        "SQLite quick_check reported a problem.",
                        details=integrity_messages,
                    )
                )

            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
            ).fetchone()
            report["checks"]["tasks_table_present"] = table is not None
            if table is None:
                report["issues"].append(
                    _issue("tasks_table_missing", "The database does not contain a tasks table.")
                )
                return report

            table_info = connection.execute('PRAGMA table_info("tasks")').fetchall()
            columns = {str(row["name"]).lower() for row in table_info}
            missing_columns = [name for name in REQUIRED_COLUMNS if name not in columns]
            columns_ok = not missing_columns
            report["checks"]["required_columns_present"] = columns_ok
            if missing_columns:
                report["issues"].append(
                    _issue(
                        "required_columns_missing",
                        "The tasks table is missing required columns.",
                        columns=missing_columns,
                    )
                )

            available = [name for name in REQUIRED_COLUMNS if name in columns]
            if not available:
                report["checks"]["required_values_present"] = False
                report["checks"]["unique_task_ids"] = None
                report["checks"]["valid_statuses"] = None
                return report

            quoted = ", ".join('"' + name + '"' for name in available)
            rows = connection.execute("SELECT " + quoted + " FROM tasks")
            id_counts: Dict[Any, int] = {}
            invalid_statuses = []
            missing_values = []
            task_count = 0
            for row_number, row in enumerate(rows, start=1):
                task_count += 1
                task_id = row["id"] if "id" in columns else None
                if "id" in columns and task_id is not None:
                    id_counts[task_id] = id_counts.get(task_id, 0) + 1

                if "status" in columns:
                    status = row["status"]
                    if status is not None and str(status).strip() and str(status) not in ALLOWED_STATUSES:
                        invalid_statuses.append((row_number, task_id, str(status)))

                for field in available:
                    value = row[field]
                    is_missing = value is None
                    if isinstance(value, str):
                        is_missing = not value.strip()
                    if is_missing:
                        missing_values.append((row_number, task_id, field))

            report["task_count"] = task_count

            if "id" in columns:
                duplicates = [(task_id, count) for task_id, count in id_counts.items() if count > 1]
                report["checks"]["unique_task_ids"] = not duplicates
                for task_id, count in duplicates:
                    report["issues"].append(
                        _issue(
                            "duplicate_task_id",
                            "More than one task row has the same ID.",
                            task_id=task_id,
                            occurrences=count,
                        )
                    )

            if "status" in columns:
                report["checks"]["valid_statuses"] = not invalid_statuses
                for row_number, task_id, status in invalid_statuses:
                    report["issues"].append(
                        _issue(
                            "invalid_task_status",
                            "Task status is not part of the supported lifecycle.",
                            row_number=row_number,
                            task_id=task_id,
                            value=status,
                        )
                    )

            report["checks"]["required_values_present"] = not missing_values and columns_ok
            for row_number, task_id, field in missing_values:
                report["issues"].append(
                    _issue(
                        "missing_required_value",
                        "A task row has an empty required field.",
                        row_number=row_number,
                        task_id=task_id,
                        field=field,
                    )
                )

    except (OSError, sqlite3.Error, ValueError) as exc:
        report["issues"].append(
            _issue(
                "database_unreadable",
                "The queue database could not be inspected read-only.",
                error_type=type(exc).__name__,
            )
        )

    report["ok"] = not report["issues"]
    return report


def _print_human(report: Dict[str, Any]) -> None:
    print("Queue integrity: " + ("OK" if report["ok"] else "ISSUES FOUND"))
    print("Database: " + str(report["database"]))
    print("Tasks checked: " + str(report["task_count"]))
    for name, passed in report["checks"].items():
        if passed is not None:
            print("  {0}: {1}".format(name.replace("_", " "), "PASS" if passed else "FAIL"))
    if not report["issues"]:
        print("No integrity issues found.")
        return
    print("Issues:")
    for item in report["issues"]:
        details = []
        for key in ("task_id", "row_number", "field", "value", "occurrences", "columns"):
            if key in item:
                details.append("{0}={1!r}".format(key, item[key]))
        suffix = " (" + ", ".join(details) + ")" if details else ""
        print("- [{0}] {1}{2}".format(item["code"], item["message"], suffix))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only integrity checks for the task queue database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite queue database (default: core DB)")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report")
    args = parser.parse_args(argv)

    report = inspect_queue(args.db)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
