# Task Queue Integrity Checks

The task queue integrity checker provides a read-only diagnostic for the SQLite `tasks` table. It is intended for maintenance, troubleshooting, and preflight checks. It does not repair data or change the queue.

## Run it

From the repository root:

```bash
python -m core.queue_integrity
python -m core.queue_integrity --json
python -m core.queue_integrity --db /path/to/civilization.db --json
```

The default database is `data/civilization.db`, matching `core.db.DB_PATH`.

## What it checks

- SQLite's `quick_check` result.
- Presence of the `tasks` table and the required columns: `id`, `created_at`, `updated_at`, `priority`, `status`, and `title`.
- Duplicate non-null task IDs, including databases whose schema does not enforce a primary key.
- Status values against the queue lifecycle used by the core API and worker: `pending`, `running`, `done`, and `failed`.
- Null or blank required row values.

The report contains a stable `ok` flag, a task count, named check results, and an `issues` array with machine-readable issue codes. It does not include task titles, result bodies, or full database paths.

## Exit codes

- `0`: all checks passed.
- `1`: one or more integrity issues were found, or the database could not be inspected.

## Safety and limitations

- The database is opened using SQLite URI `mode=ro`; `PRAGMA query_only=ON` adds a second read-only guard.
- The checker does not initialize the database, run migrations, acquire task claims, update rows, or attempt repairs.
- It reports the first ten SQLite `quick_check` messages to keep output bounded.
- It validates the queue table only. It does not audit foreign-key consistency across agents and contributions, business-level timestamp ordering, or whether a `running` task has a live worker.
- A clean report is a point-in-time observation, not a guarantee that another process will not change the database immediately afterward.

Run its tests from the repository root:

```bash
python -m unittest core.tests.test_queue_integrity -v
```
