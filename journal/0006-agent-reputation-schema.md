# Journal Entry 0006 — Agent Reputation Schema

**Time:** 2026-10-31

Added minimal agent and contribution tracking to the SQLite task queue.

- `agents` and `contributions` tables
- `claimed_by` and `contribution_id` on tasks
- Internal agents (`core`, `hermes`, `local`) are seeded as approved and internal; they are never gated
- External agents must be approved before they can claim tasks
- Core loop continues to work unchanged (no agent_id required)

Human approval remains the gate for external contribution credit.
