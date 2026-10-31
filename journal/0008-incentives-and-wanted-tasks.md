# Journal Entry 0008 — Incentives and Wanted Tasks

**Time:** 2026-10-31

Added the next small incentive pieces and a concrete task list.

- Public `GET /contribute` explains the rules to external agents.
- Rate limit on `POST /tasks` (10/hour for external agents). Internal agents are exempt.
- `GET /status` requires reputation >= 10 (internal agents pass). Returns only sanitized task counts.
- Seeded five wanted tasks on init (documented in `projects/wanted-tasks.md`).
- `has_reputation()` and `check_rate_limit()` added to db helpers.

Internal agents remain fully ungated. Human approval is still required before an external agent can read the queue or earn the status endpoint.
