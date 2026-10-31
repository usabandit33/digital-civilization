# Journal Entry 0003 — HTTP API

**Date:** 2026-10-30

**Summary:** Minimal HTTP API added so other agents can submit tasks.

## What was added

- `core/api.py` — FastAPI application
  - `POST /tasks` — submit a new task
  - `GET /tasks/{id}` — check status and retrieve result
  - `GET /tasks` — list recent tasks (optional status filter)
  - `GET /health` — simple health check
- `core/serve.py` — convenient runner (default `127.0.0.1:8741`)
- Updated requirements, README, setup guide, and an example systemd unit for the API

## How other agents use it

```bash
# Submit
curl -X POST http://127.0.0.1:8741/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Your task here", "priority": 10}'

# Poll
curl http://127.0.0.1:8741/tasks/1
```

The worker (`python -m core.main`) must be running for tasks to be processed.

## Design choices

- Bound to localhost by default for safety.
- Separate process from the worker so either can be restarted independently.
- Same SQLite queue — no duplication of state.
- Ready to be wrapped by an MCP server later without changing the core data model.

## Next logical steps

- Add the first real tool (research, code analysis, etc.)
- Optional: simple MCP server that calls the same queue
- Real hardware numbers in `hardware-notes.md`
- Basic authentication or Tailscale-only exposure before any wider access
