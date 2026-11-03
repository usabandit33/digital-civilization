# Agent Health Check

A small, dependency-free CLI that checks whether a local agent process responds over HTTP and whether an existing SQLite database can be read.

## Usage

```bash
python inventions/agent-health-check/health_check.py --url http://127.0.0.1:8000/health --db memory/civilization.db
python inventions/agent-health-check/health_check.py --url http://127.0.0.1:8000/health --db memory/civilization.db --json
```

Exit codes: **0** all checks passed, **1** one or more checks failed, **2** invalid arguments/configuration (argparse).

The HTTP check sends a simple GET with no credentials and uses a bounded timeout (default 3 seconds, allowed 0.1–30). The database check opens an existing file in SQLite read-only mode and runs minimal queries. It does not create, migrate, or modify the database. Output intentionally avoids full exception messages and filesystem paths.

## Tests

Run from the repository root:

```bash
python -m unittest discover -s inventions/agent-health-check/tests -v
```

## Resource and safety notes

- Python standard library only; no network access beyond the explicitly supplied health URL.
- Intended for loopback/local endpoints. Do not pass URLs containing credentials or sensitive query strings.
- Read-only SQLite access; no database writes or integrity-repair operations.
- The process check verifies HTTP responsiveness, not application correctness.
