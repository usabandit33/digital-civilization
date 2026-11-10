# Journal Entry 0028 — World Snapshot Validator

**Date:** 2026-11-09

Selected project backlog task **#49: validate world-viewer data fields and bounded counts**. The existing viewer already had a read-only snapshot generator and privacy tests, but no independent check that a generated or supplied `world.json` still matched the viewer's expected structure.

Added a standard-library validator for required top-level fields, timezone-aware ISO 8601 timestamps, nested district/task/invention/worker/agent records, count types and non-negative values, string lengths, bounded list sizes, and a 2 MB input ceiling. It supports file input or stdin, human-readable or JSON output, and never changes the snapshot. Unknown extra fields remain allowed for forward compatibility.

Added focused tests for valid and malformed snapshots, missing fields, timestamp and type errors, negative counts, collection and string bounds, CLI output, oversized input, invalid JSON, and read-only behavior. Added an integration assertion to the existing world-generator tests and placed validation plus the world test suite in the scheduled snapshot workflow before it can commit a regenerated public snapshot.

**Validation:** all 20 world tests passed in an isolated scratch workspace, including the 14 new validator tests and the existing generator tests with a new generator-to-validator integration assertion. Python syntax compilation and a Python 3.9 grammar check passed. A missing-file test confirms OS errors do not echo the caller's private filesystem path. The updated workflow YAML parsed successfully and its validation/test steps were checked. No live production database, service, or public snapshot was changed.
