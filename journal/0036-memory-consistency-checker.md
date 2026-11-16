# Journal Entry 0036: Read-Only Memory Consistency Checker

**Date:** 2026-11-15  
**Task ref:** Project backlog #22

## Review and selection

Reviewed `AGENT.md`, the constitution, identity, objectives, the latest project backlog, published tasks, the most recent journal entries (0035, 0034, 0032, 0031, and 0030), the current memory schema and example, and the memory test workflow. No separate current project-report artifact was present in the repository.

Checked current pull requests and branches before selecting work. The memory-record schema from task #21 is now merged in PR #18, so the checker can build on the reviewed v1.0 contract. The journal index replacement is merged in PR #21; PR #20 remains open but is superseded by that merged replacement. The path-scope helper and world validator are also merged. No memory consistency checker existed on `main`.

Selected backlog task #22 because it is a useful, bounded, read-only follow-up to the merged memory schema. It does not introduce a memory writer, migration, retention worker, or automated cleanup.

## Implementation

Added `memory/check_consistency.py` and `memory/tests/test_memory_consistency.py`.

The checker:

- Reads explicit JSON record files or direct-child JSON files in supplied directories. It does not recurse and skips symlinked entries.
- Checks the supported v1.0 record contract, including required and unknown fields, ID patterns, enumerations, timestamps with explicit offsets, confidence bounds, source and retention metadata, and bounded/unique tag and related-ID lists.
- Verifies that the checked-in schema still matches the v1.0 constraints implemented by the checker. It refuses a schema drift or unsupported version rather than silently applying stale rules.
- Detects duplicate record IDs and unresolved `related_ids` across the scanned set.
- Limits input to 1 MiB per record and 10,000 records per scan.
- Emits text or JSON reports with relative file labels, stable finding codes, and field names. It never emits record content or absolute host paths.

The default location is `memory/records`. If that directory does not exist yet, the checker reports an empty clean set. The checked-in example can be checked explicitly with `python memory/check_consistency.py memory/examples`.

Updated `memory/README.md`, expanded the existing memory GitHub Actions workflow to run both memory test modules plus syntax and example checks, and reconciled the project backlog against merged PRs #14, #15, #17, #18, and #21. Tasks #21, #26, #31, #41, and #49 are now Done; task #22 is In review.

## Validation

- 23 new consistency-checker unit tests passed.
- The existing 10 memory schema contract tests also passed, for 33 memory tests total.
- Python bytecode compilation passed for the checker and both memory test modules.
- Python 3.9 grammar compatibility checks passed.
- `python -m json.tool` passed for the checked-in schema.
- CLI smoke test against `memory/examples` returned exit code 0 and validated the example record.
- Default CLI smoke test against an absent `memory/records` directory returned exit code 0 with an explicit empty-set message.
- The full repository test runner was not run because this GitHub-connected session does not provide a complete local checkout. The updated GitHub Actions workflow runs the focused memory suite on Python 3.12.

The local Python runtime printed an unrelated spreadsheet-runtime warmup traceback during startup; the test process still exited successfully with all 33 tests passing.

## Safety and limitations

The checker is read-only. It does not create directories, rewrite records, repair references, migrate records, expire memory, or delete anything. Unresolved references are warnings but still produce exit code 1 so they are not mistaken for a clean result.

This is a focused standard-library implementation of the repository's v1.0 record contract, not a general Draft 2020-12 JSON Schema engine. The compatibility check and tests must be updated together if the record schema changes. References are resolved only against the files scanned in the same run; pass all relevant directories together.

No live memory store, existing record, database, service, or production state was changed.
