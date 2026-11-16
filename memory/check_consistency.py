#!/usr/bin/env python3
"""Read-only consistency checks for Digital Civilization memory records (schema v1.0)."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SUPPORTED_SCHEMA_VERSION = "1.0"
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
MAX_SCHEMA_BYTES = 262_144
MAX_RECORD_BYTES = 1_048_576
MAX_RECORD_FILES = 10_000
SCHEMA_FILENAME = "memory-record.schema.json"
DEFAULT_RECORDS_DIR = Path(__file__).resolve().parent / "records"
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent / SCHEMA_FILENAME

RECORD_KEYS = {
    "schema_version", "id", "record_type", "content", "source",
    "created_at", "confidence", "retention", "tags", "related_ids",
}
REQUIRED_RECORD_KEYS = {
    "schema_version", "id", "record_type", "content", "source",
    "created_at", "confidence", "retention",
}
SOURCE_KEYS = {"kind", "ref", "captured_at"}
RETENTION_KEYS = {"class", "review_after", "expires_at"}
RECORD_TYPES = {"fact", "decision", "hypothesis", "observation", "lesson"}
SOURCE_KINDS = {
    "conversation", "repository_file", "tool_output",
    "web_page", "human_input", "system_event",
}
RETENTION_CLASSES = {"ephemeral", "working", "durable"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _reject_constant(value: str) -> None:
    raise ValueError("non-standard JSON numeric constant")


def _read_json(path: Path, limit: int) -> Any:
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise OverflowError
    return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not DATETIME_PATTERN.fullmatch(value):
        return False
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except (ValueError, OverflowError):
        return False


def _add(findings: list[dict[str, str]], code: str, field: str) -> None:
    findings.append({"code": code, "field": field})


def validate_record(record: Any) -> list[dict[str, str]]:
    """Validate the checked-in memory-record v1.0 contract without dependencies."""
    findings: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [{"code": "record_root_not_object", "field": "$"}]

    for key in sorted(REQUIRED_RECORD_KEYS - set(record)):
        _add(findings, "missing_required_field", f"$.{key}")
    for key in sorted(set(record) - RECORD_KEYS):
        _add(findings, "unknown_field", f"$.{key}")

    if record.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        _add(findings, "unsupported_schema_version", "$.schema_version")

    record_id = record.get("id")
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 128 or not ID_PATTERN.fullmatch(record_id):
        _add(findings, "invalid_id", "$.id")

    record_type = record.get("record_type")
    if not isinstance(record_type, str) or record_type not in RECORD_TYPES:
        _add(findings, "unsupported_record_type", "$.record_type")

    content = record.get("content")
    if not isinstance(content, str):
        _add(findings, "type_mismatch", "$.content")
    elif not 1 <= len(content) <= 10_000:
        _add(findings, "invalid_length", "$.content")

    if not _valid_timestamp(record.get("created_at")):
        _add(findings, "invalid_timestamp", "$.created_at")

    confidence = record.get("confidence")
    try:
        valid_confidence = (
            not isinstance(confidence, bool)
            and isinstance(confidence, (int, float))
            and math.isfinite(float(confidence))
            and 0 <= confidence <= 1
        )
    except OverflowError:
        valid_confidence = False
    if not valid_confidence:
        _add(findings, "invalid_confidence", "$.confidence")

    source = record.get("source")
    if not isinstance(source, dict):
        _add(findings, "type_mismatch", "$.source")
    else:
        for key in sorted(SOURCE_KEYS - set(source)):
            _add(findings, "missing_required_field", f"$.source.{key}")
        for key in sorted(set(source) - SOURCE_KEYS):
            _add(findings, "unknown_field", f"$.source.{key}")
        source_kind = source.get("kind")
        if not isinstance(source_kind, str) or source_kind not in SOURCE_KINDS:
            _add(findings, "unsupported_source_kind", "$.source.kind")
        ref = source.get("ref")
        if not isinstance(ref, str):
            _add(findings, "type_mismatch", "$.source.ref")
        elif not 1 <= len(ref) <= 2048:
            _add(findings, "invalid_length", "$.source.ref")
        if not _valid_timestamp(source.get("captured_at")):
            _add(findings, "invalid_timestamp", "$.source.captured_at")

    retention = record.get("retention")
    if not isinstance(retention, dict):
        _add(findings, "type_mismatch", "$.retention")
    else:
        for key in sorted(RETENTION_KEYS - set(retention)):
            _add(findings, "missing_required_field", f"$.retention.{key}")
        for key in sorted(set(retention) - RETENTION_KEYS):
            _add(findings, "unknown_field", f"$.retention.{key}")
        retention_class = retention.get("class")
        if not isinstance(retention_class, str) or retention_class not in RETENTION_CLASSES:
            _add(findings, "unsupported_retention_class", "$.retention.class")
        for key in ("review_after", "expires_at"):
            value = retention.get(key)
            if value is not None and not _valid_timestamp(value):
                _add(findings, "invalid_timestamp", f"$.retention.{key}")

    for key, maximum, item_maximum in (("tags", 20, 64), ("related_ids", 50, 128)):
        if key not in record:
            continue
        values = record[key]
        if not isinstance(values, list):
            _add(findings, "type_mismatch", f"$.{key}")
            continue
        if len(values) > maximum:
            _add(findings, "too_many_items", f"$.{key}")
        string_values = [value for value in values if isinstance(value, str)]
        if len(string_values) != len(set(string_values)):
            _add(findings, "duplicate_item", f"$.{key}")
        for index, value in enumerate(values):
            valid = (
                isinstance(value, str)
                and 1 <= len(value) <= item_maximum
                and (key != "related_ids" or bool(ID_PATTERN.fullmatch(value)))
            )
            if not valid:
                _add(findings, "invalid_item", f"$.{key}[{index}]")

    return findings


def _label(path: Path, parent: Path | None = None) -> str:
    if parent is not None:
        try:
            return (parent.name + "/" + path.relative_to(parent).as_posix()).lstrip("./")
        except (ValueError, OSError):
            pass
    return path.name


def _collect_files(
    paths: Iterable[Path], allow_missing_default: bool
) -> tuple[list[tuple[Path, str]], list[dict[str, str]]]:
    files: list[tuple[Path, str]] = []
    errors: list[dict[str, str]] = []
    seen: set[Path] = set()
    for supplied in paths:
        path = Path(supplied).expanduser()
        if path.is_symlink():
            errors.append({"path": path.name, "code": "symlink_input"})
            continue
        if not path.exists():
            if not allow_missing_default:
                errors.append({"path": path.name, "code": "input_not_found"})
            continue
        if path.is_dir():
            entries: list[Path] = []
            too_many = False
            try:
                with os.scandir(path) as iterator:
                    for item in iterator:
                        if item.is_symlink() or not item.is_file(follow_symlinks=False):
                            continue
                        if Path(item.name).suffix.lower() != ".json" or item.name == SCHEMA_FILENAME:
                            continue
                        if len(files) + len(entries) >= MAX_RECORD_FILES:
                            too_many = True
                            break
                        entries.append(Path(item.path))
            except OSError:
                errors.append({"path": path.name, "code": "directory_read_error"})
                continue
            if too_many:
                errors.append({"path": path.name, "code": "too_many_record_files"})
            for entry in sorted(entries, key=lambda item: item.name):
                label = _label(entry, path)
                try:
                    resolved = entry.resolve(strict=True)
                except OSError:
                    errors.append({"path": label, "code": "path_resolution_error"})
                    continue
                if resolved not in seen:
                    seen.add(resolved)
                    files.append((resolved, label))
        elif path.is_file():
            if path.suffix.lower() != ".json" or path.name == SCHEMA_FILENAME:
                errors.append({"path": path.name, "code": "unsupported_file"})
                continue
            try:
                resolved = path.resolve(strict=True)
            except OSError:
                errors.append({"path": path.name, "code": "path_resolution_error"})
                continue
            if resolved not in seen:
                seen.add(resolved)
                files.append((resolved, path.name))
        else:
            errors.append({"path": path.name, "code": "unsupported_input"})
    if len(files) > MAX_RECORD_FILES:
        errors.append({"path": ".", "code": "too_many_record_files"})
        files = files[:MAX_RECORD_FILES]
    return files, errors


def _schema_supports_v1(schema: dict[str, Any]) -> bool:
    """Ensure the checked-in schema still matches the constraints this checker enforces."""
    try:
        props = schema["properties"]
        defs = schema["$defs"]
        identifier = defs["id"]
        if set(defs) != {"id", "source", "retention"}:
            return False
        source = defs["source"]
        source_props = source["properties"]
        retention = defs["retention"]
        retention_props = retention["properties"]
        tags = props["tags"]
        related = props["related_ids"]
        return (
            schema.get("type") == "object"
            and schema.get("additionalProperties") is False
            and set(schema["required"]) == REQUIRED_RECORD_KEYS
            and set(props) == RECORD_KEYS
            and props["schema_version"].get("const") == SUPPORTED_SCHEMA_VERSION
            and props["id"].get("$ref") == "#/$defs/id"
            and props["record_type"].get("type") == "string"
            and set(props["record_type"]["enum"]) == RECORD_TYPES
            and props["content"].get("type") == "string"
            and props["content"].get("minLength") == 1
            and props["content"].get("maxLength") == 10_000
            and props["source"].get("$ref") == "#/$defs/source"
            and props["created_at"].get("type") == "string"
            and props["created_at"].get("format") == "date-time"
            and props["confidence"].get("type") == "number"
            and props["confidence"].get("minimum") == 0
            and props["confidence"].get("maximum") == 1
            and identifier.get("type") == "string"
            and identifier.get("minLength") == 1
            and identifier.get("maxLength") == 128
            and identifier.get("pattern") == ID_PATTERN.pattern
            and props["retention"].get("$ref") == "#/$defs/retention"
            and props["tags"].get("type") == "array"
            and props["related_ids"].get("type") == "array"
            and source.get("type") == "object"
            and source.get("additionalProperties") is False
            and set(source["required"]) == SOURCE_KEYS
            and set(source_props) == SOURCE_KEYS
            and source_props["kind"].get("type") == "string"
            and set(source_props["kind"]["enum"]) == SOURCE_KINDS
            and source_props["ref"].get("type") == "string"
            and source_props["ref"].get("minLength") == 1
            and source_props["ref"].get("maxLength") == 2048
            and source_props["captured_at"].get("type") == "string"
            and source_props["captured_at"].get("format") == "date-time"
            and retention.get("type") == "object"
            and retention.get("additionalProperties") is False
            and set(retention["required"]) == RETENTION_KEYS
            and set(retention_props) == RETENTION_KEYS
            and retention_props["class"].get("type") == "string"
            and set(retention_props["class"]["enum"]) == RETENTION_CLASSES
            and retention_props["review_after"].get("type") == ["string", "null"]
            and retention_props["expires_at"].get("type") == ["string", "null"]
            and retention_props["review_after"].get("format") == "date-time"
            and retention_props["expires_at"].get("format") == "date-time"
            and tags.get("maxItems") == 20
            and tags.get("uniqueItems") is True
            and tags["items"].get("type") == "string"
            and tags["items"].get("minLength") == 1
            and tags["items"].get("maxLength") == 64
            and related.get("maxItems") == 50
            and related.get("uniqueItems") is True
            and related["items"].get("$ref") == "#/$defs/id"
        )
    except (KeyError, TypeError, AttributeError):
        return False


def check_records(
    paths: Iterable[Path],
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    *,
    allow_missing_default: bool = False,
) -> tuple[dict[str, Any], int]:
    """Scan records and cross-references; return (report, process exit code)."""
    try:
        schema_file = Path(schema_path)
        if schema_file.is_symlink() or not schema_file.is_file():
            raise OSError
        schema = _read_json(schema_file, MAX_SCHEMA_BYTES)
        if (
            not isinstance(schema, dict)
            or schema.get("$schema") != DRAFT_2020_12
            or schema.get("properties", {}).get("schema_version", {}).get("const")
            != SUPPORTED_SCHEMA_VERSION
            or not _schema_supports_v1(schema)
        ):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError, OverflowError, AttributeError):
        return ({
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "ok": False,
            "files_checked": 0,
            "files": [],
            "records_valid": 0,
            "records_invalid": 0,
            "findings": [],
            "scan_errors": [{"path": "schema", "code": "schema_unavailable_or_invalid"}],
        }, 2)

    files, scan_errors = _collect_files(paths, allow_missing_default)
    findings: list[dict[str, Any]] = []
    parsed: list[tuple[str, dict[str, Any], bool]] = []
    records_valid = 0
    records_invalid = 0

    for path, label in files:
        try:
            record = _read_json(path, MAX_RECORD_BYTES)
        except OverflowError:
            findings.append({"file": label, "severity": "error", "code": "record_too_large"})
            records_invalid += 1
            continue
        except json.JSONDecodeError as exc:
            findings.append({
                "file": label, "severity": "error", "code": "invalid_json",
                "line": exc.lineno, "column": exc.colno,
            })
            records_invalid += 1
            continue
        except UnicodeDecodeError:
            findings.append({"file": label, "severity": "error", "code": "invalid_utf8"})
            records_invalid += 1
            continue
        except ValueError:
            findings.append({"file": label, "severity": "error", "code": "invalid_json_value"})
            records_invalid += 1
            continue
        except OSError:
            scan_errors.append({"path": label, "code": "file_read_error"})
            continue

        record_findings = validate_record(record)
        valid = not record_findings
        records_valid += int(valid)
        records_invalid += int(not valid)
        for item in record_findings:
            findings.append({
                "file": label, "severity": "error",
                "code": item["code"], "field": item["field"],
            })
        if isinstance(record, dict):
            parsed.append((label, record, valid))
        else:
            parsed.append((label, {}, False))

    first_by_id: dict[str, str] = {}
    all_ids: set[str] = set()
    for label, record, _valid in parsed:
        record_id = record.get("id")
        if isinstance(record_id, str):
            if record_id in first_by_id:
                findings.append({
                    "file": label, "severity": "error",
                    "code": "duplicate_id", "record_id": record_id,
                })
            else:
                first_by_id[record_id] = label
            all_ids.add(record_id)

    for label, record, valid in parsed:
        if not valid:
            continue
        for related_id in record.get("related_ids", []):
            if related_id not in all_ids:
                findings.append({
                    "file": label, "severity": "warning",
                    "code": "unresolved_related_id",
                    "record_id": record["id"], "related_id": related_id,
                })

    findings.sort(key=lambda item: (
        str(item.get("file", "")), str(item.get("field", "")),
        str(item.get("code", "")), str(item.get("record_id", "")),
    ))
    scan_errors.sort(key=lambda item: (item.get("path", ""), item.get("code", "")))
    result = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "ok": not findings and not scan_errors,
        "files_checked": len(files),
        "files": [label for _path, label in files],
        "records_valid": records_valid,
        "records_invalid": records_invalid,
        "findings": findings,
        "scan_errors": scan_errors,
    }
    if not files and not scan_errors:
        result["message"] = "No JSON memory records were found in the supplied location."
    return result, 2 if scan_errors else (1 if findings else 0)


def _render_text(result: dict[str, Any], exit_code: int) -> None:
    print("Digital Civilization memory consistency check")
    print(
        f"Files checked: {result['files_checked']}; "
        f"valid records: {result['records_valid']}; "
        f"invalid records: {result['records_invalid']}"
    )
    if result.get("message"):
        print(result["message"])
    for finding in result["findings"]:
        field = f" ({finding['field']})" if finding.get("field") else ""
        print(f"{finding['severity'].upper()} {finding['file']}: {finding['code']}{field}")
    for error in result["scan_errors"]:
        print(f"ERROR {error['path']}: {error['code']}")
    print("Result: " + ("CLEAN" if exit_code == 0 else "FINDINGS" if exit_code == 1 else "SCAN ERROR"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*",
        help="JSON record files or directories (direct children only; default: memory/records)",
    )
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH), help="memory-record schema path")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    args = parser.parse_args(argv)
    paths = [Path(item) for item in args.paths] if args.paths else [DEFAULT_RECORDS_DIR]
    result, exit_code = check_records(paths, Path(args.schema), allow_missing_default=not args.paths)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _render_text(result, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
