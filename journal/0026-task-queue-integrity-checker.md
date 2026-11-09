# Journal Entry 0026 — Task Queue Integrity Checker

**Date:** 2026-11-08

Selected project backlog task **#11: queue integrity checks** after reviewing the current core SQLite schema, worker, API status counts, latest journal entries, and open pull requests. No existing read-only queue validator or core test suite was present.

Added a standard-library CLI that opens the configured SQLite database in read-only mode and checks SQLite integrity, the `tasks` table and required columns, duplicate task IDs, supported lifecycle statuses, and empty required values. It emits human-readable or JSON output and never repairs or mutates the queue.

Validation: 11 isolated unit tests cover a clean queue, duplicate IDs, invalid status, missing values, missing columns/table/database, corrupt input, unchanged database bytes, and both CLI formats. See the pull request for the recorded local validation results.

**Boundary:** This is a report-only diagnostic. It does not initialize or migrate the database, claim tasks, modify rows, or assess whether a `running` task still has a live worker.
