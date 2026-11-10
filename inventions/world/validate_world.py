#!/usr/bin/env python3
"""Validate a Digital Civilization world snapshot without changing it.

Examples:
  python inventions/world/validate_world.py
  python inventions/world/validate_world.py docs/world/world.json --json
  cat docs/world/world.json | python inventions/world/validate_world.py -
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = ROOT / "docs" / "world" / "world.json"
MAX_SNAPSHOT_BYTES = 2_000_000

# These limits are deliberately generous relative to the current repository.
# They protect the small viewer from unexpectedly large or malformed payloads.
LIMITS = {
    "districts": 20,
    "tasks_per_district": 100,
    "inventions": 500,
    "branches": 500,
    "journal": 100,
    "working": 1_000,
    "agents": 1_000,
}


def _string(value: Any, path: str, errors: list[str], maximum: int) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: expected a non-empty string")
    elif len(value) > maximum:
        errors.append(f"{path}: exceeds {maximum} characters")
    elif "\x00" in value:
        errors.append(f"{path}: contains a null character")


def _integer(
    value: Any,
    path: str,
    errors: list[str],
    *,
    minimum: int | None = None,
) -> None:
    # bool is a subclass of int in Python, but is not a valid numeric count.
    if type(value) is not int:
        errors.append(f"{path}: expected an integer")
    elif minimum is not None and value < minimum:
        errors.append(f"{path}: must be at least {minimum}")


def _list(
    value: Any,
    path: str,
    errors: list[str],
    maximum: int,
) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path}: expected a list")
        return []
    if len(value) > maximum:
        errors.append(f"{path}: contains {len(value)} items; limit is {maximum}")
    return value[:maximum]


def _object(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return {}
    return value


def validate_snapshot(data: Any) -> list[str]:
    """Return validation errors. An empty list means the snapshot is valid."""
    if not isinstance(data, dict):
        return ["$: expected a JSON object"]

    errors: list[str] = []
    required = (
        "generated", "demo", "districts", "inventions", "branches",
        "journal", "counts", "working", "agents", "pending_contributions",
    )
    for key in required:
        if key not in data:
            errors.append(f"$.{key}: missing required field")

    if "generated" in data:
        value = data["generated"]
        _string(value, "$.generated", errors, 64)
        if isinstance(value, str) and value.strip():
            try:
                timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    errors.append("$.generated: timestamp must include a timezone")
            except ValueError:
                errors.append("$.generated: expected an ISO 8601 timestamp")

    if "demo" in data and type(data["demo"]) is not bool:
        errors.append("$.demo: expected a boolean")

    if "counts" in data:
        counts = _object(data["counts"], "$.counts", errors)
        for status in ("pending", "running", "done", "failed"):
            if status not in counts:
                errors.append(f"$.counts.{status}: missing required field")
            else:
                _integer(counts[status], f"$.counts.{status}", errors, minimum=0)

    if "districts" in data:
        for index, raw in enumerate(_list(data["districts"], "$.districts", errors, LIMITS["districts"])):
            path = f"$.districts[{index}]"
            district = _object(raw, path, errors)
            if "name" not in district:
                errors.append(f"{path}.name: missing required field")
            else:
                _string(district["name"], f"{path}.name", errors, 120)
            if "tasks" not in district:
                errors.append(f"{path}.tasks: missing required field")
                continue
            for task_index, raw_task in enumerate(
                _list(district["tasks"], f"{path}.tasks", errors, LIMITS["tasks_per_district"])
            ):
                task_path = f"{path}.tasks[{task_index}]"
                task = _object(raw_task, task_path, errors)
                if "n" not in task:
                    errors.append(f"{task_path}.n: missing required field")
                else:
                    _integer(task["n"], f"{task_path}.n", errors, minimum=1)
                if "title" not in task:
                    errors.append(f"{task_path}.title: missing required field")
                else:
                    _string(task["title"], f"{task_path}.title", errors, 120)

    if "inventions" in data:
        for index, raw in enumerate(_list(data["inventions"], "$.inventions", errors, LIMITS["inventions"])):
            path = f"$.inventions[{index}]"
            invention = _object(raw, path, errors)
            for key, maximum in (("name", 100), ("summary", 140)):
                if key not in invention:
                    errors.append(f"{path}.{key}: missing required field")
                else:
                    _string(invention[key], f"{path}.{key}", errors, maximum)
            if "task" not in invention:
                errors.append(f"{path}.task: missing required field")
            elif invention["task"] is not None:
                _integer(invention["task"], f"{path}.task", errors, minimum=1)

    if "branches" in data:
        for index, branch in enumerate(_list(data["branches"], "$.branches", errors, LIMITS["branches"])):
            _string(branch, f"$.branches[{index}]", errors, 255)

    if "journal" in data:
        for index, entry in enumerate(_list(data["journal"], "$.journal", errors, LIMITS["journal"])):
            _string(entry, f"$.journal[{index}]", errors, 120)

    if "working" in data:
        for index, raw in enumerate(_list(data["working"], "$.working", errors, LIMITS["working"])):
            path = f"$.working[{index}]"
            worker = _object(raw, path, errors)
            if "agent" not in worker:
                errors.append(f"{path}.agent: missing required field")
            else:
                _string(worker["agent"], f"{path}.agent", errors, 64)
            if "task" not in worker:
                errors.append(f"{path}.task: missing required field")
            else:
                _integer(worker["task"], f"{path}.task", errors, minimum=1)
            if "stalled" not in worker:
                errors.append(f"{path}.stalled: missing required field")
            elif type(worker["stalled"]) is not bool:
                errors.append(f"{path}.stalled: expected a boolean")

    if "agents" in data:
        for index, raw in enumerate(_list(data["agents"], "$.agents", errors, LIMITS["agents"])):
            path = f"$.agents[{index}]"
            agent = _object(raw, path, errors)
            if "id" not in agent:
                errors.append(f"{path}.id: missing required field")
            else:
                _string(agent["id"], f"{path}.id", errors, 64)
            for key in ("external", "approved"):
                if key not in agent:
                    errors.append(f"{path}.{key}: missing required field")
                elif type(agent[key]) is not bool:
                    errors.append(f"{path}.{key}: expected a boolean")
            if "reputation" not in agent:
                errors.append(f"{path}.reputation: missing required field")
            else:
                _integer(agent["reputation"], f"{path}.reputation", errors)

    if "pending_contributions" in data:
        _integer(data["pending_contributions"], "$.pending_contributions", errors, minimum=0)

    return errors


def _read_snapshot(source: str) -> Any:
    if source == "-":
        payload = sys.stdin.buffer.read(MAX_SNAPSHOT_BYTES + 1)
    else:
        with Path(source).open("rb") as handle:
            payload = handle.read(MAX_SNAPSHOT_BYTES + 1)
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError(f"snapshot exceeds the {MAX_SNAPSHOT_BYTES}-byte limit")
    return json.loads(payload.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "snapshot", nargs="?", default=str(DEFAULT_SNAPSHOT),
        help="snapshot JSON file, or '-' to read stdin",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable validation result")
    args = parser.parse_args(argv)

    try:
        errors = validate_snapshot(_read_snapshot(args.snapshot))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"$: unable to read snapshot: {exc}"]

    result = {"ok": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif errors:
        print("World snapshot is invalid:")
        for error in errors:
            print(f"- {error}")
    else:
        print("World snapshot is valid.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
