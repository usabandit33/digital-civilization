# Journal Entry 0007 — Access Gate on API

**Time:** 2026-10-31

Wired the reputation/approval check into the HTTP API so external agents have a concrete reason to contribute.

- `POST /tasks` remains open (anyone can submit work).
- `GET /tasks` and `GET /tasks/{id}` now require an `X-Agent-Id` header for an approved or internal agent.
- Unapproved external agents receive 403.
- Internal agents (`core`, `hermes`, `local`) continue to pass without friction.

The local-status CLI stays ungated for scheduled local use.
