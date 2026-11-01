# Journal Entry 0011 — Gate, Approval, and Claim Fixes

**Time:** 2026-11-01

Fixed three critical issues from the review:

1. **Access gate** — Missing or empty `agent_id` is now treated as anonymous external, not internal. Only known internal IDs (`core`, `hermes`, `local`) or DB-marked internal agents bypass checks.
2. **Approval** — `approve_contribution()` now sets `approved = 1` in addition to adding reputation. Added `python -m core.approve` CLI so a human can list and approve pending contributions.
3. **Claim race** — `claim_next_task()` now uses a single atomic `UPDATE ... RETURNING` so concurrent callers cannot both succeed on the same task.

The core loop can still claim with no agent_id (treated as internal for claiming only). External agents must present a real ID and be approved before they can read the queue or claim.
