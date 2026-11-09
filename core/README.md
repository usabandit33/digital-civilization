# Core — Minimal Task Queue, Worker & HTTP API

Lightweight foundation for the Digital Civilization.

## Components

| Module | Purpose |
|--------|---------|
| `db.py` | SQLite task queue |
| `llm.py` | Thin Ollama client |
| `main.py` | Worker loop (processes tasks) |
| `api.py` + `serve.py` | HTTP API so other agents can submit work |
| `add_task.py` | CLI helper |
| `init_db.py` | Database initialization |
| `queue_integrity.py` | Read-only queue integrity diagnostics |

## Quick start

```bash
# from repository root, with venv activated
pip install -r core/requirements.txt
python -m core.init_db

# Terminal 1 — worker
python -m core.main

# Terminal 2 — API
python -m core.serve
```

API listens on `http://127.0.0.1:8741` by default.

## HTTP API

### Submit a task
```bash
curl -X POST http://127.0.0.1:8741/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Summarize Phase 1 objectives", "priority": 10}'
```

### Check status / result
```bash
curl http://127.0.0.1:8741/tasks/1
```

### List recent tasks
```bash
curl http://127.0.0.1:8741/tasks
curl "http://127.0.0.1:8741/tasks?status=done"
```

### Health
```bash
curl http://127.0.0.1:8741/health
```

## CLI alternatives

```bash
python -m core.add_task "Research lightweight MCP patterns" --priority 10
python -m core.main --once
```

## Queue integrity

Run a read-only consistency report against the queue database:

```bash
python -m core.queue_integrity
python -m core.queue_integrity --json
python -m core.queue_integrity --db /path/to/civilization.db --json
```

The checker verifies SQLite integrity, required task columns and values, unique task IDs, and supported statuses. It never initializes, repairs, or modifies the queue. See [queue-integrity.md](queue-integrity.md) for checks, output fields, exit codes, and limitations.

## Design notes

- One model at a time
- Tasks start as plain text (structured tool calling comes later)
- API is bound to localhost by default for safety
- Worker and API are separate processes so either can restart independently
- Queue diagnostics are read-only and do not replace backups or human review
- Ready for a future MCP wrapper around the same queue
