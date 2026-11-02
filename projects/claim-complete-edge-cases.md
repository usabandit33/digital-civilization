# Edge-Case Checklist: Task Claim and Complete

Practical edge cases for the claim/complete queue in `core/db.py` and `core/main.py`, with how a human or another agent can verify each one.

This answers the wanted task "Edge-case checklist for task claim and complete" (priority 80). No repo code is changed by this file.

## How to read this

- **Status** is one of:
  - `confirmed` means reproduced against a copy of the `claim_next_task`, `complete_task`, and `fail_task` logic using the Python 3.12 standard library and SQLite 3.45.
  - `by reading` means derived from the code but not executed.
  - `ok` means the current behavior is acceptable.
- **Fix** points to the suggested change. See "Fix map" at the bottom.
- Internal agents are `core`, `hermes`, `local`, plus any caller that sends no agent id (`is_internal(None)` is true).

## A. Claiming

### A1. Two callers claim the same task
- **Scenario:** Two workers both read the same pending row before either updates it.
- **Today:** `claim_next_task` runs `SELECT`, then `UPDATE ... WHERE status='pending'`, but never checks the update's row count. The loser re-reads the row and returns it as if it had won. Its `claimed_by` shows the winner's id.
- **Expected:** Exactly one caller gets the task. The other gets `None` or the next task.
- **Verify:** Point `core.db.DB_PATH` at a temp database with three pending tasks. Open caller A, run its `SELECT`, then (before A updates) run a full claim as caller B. Let A finish. Both return task 1 and A's update touches 0 rows.
- **Status:** confirmed. **Fix:** F1.

### A2. Empty queue
- **Today:** `claim_next_task` returns `None`. The worker sleeps for the poll interval.
- **Verify:** Run `python -m core.main --once` with no pending tasks. Expect "No pending tasks."
- **Status:** ok.

### A3. Unapproved external agent claims
- **Today:** `claim_next_task(agent_id)` returns `None` when `can_access` is false. The caller cannot tell this apart from an empty queue.
- **Expected:** A distinct signal, such as a 403, so the agent knows it needs approval.
- **Verify:** Insert an agent row with `approved=0`, call `claim_next_task("that-id")` while tasks are pending. Expect `None`.
- **Status:** confirmed. **Fix:** F5.

### A4. Core worker claims are unattributed
- **Today:** `process_one_task` calls `claim_next_task()` with no id, so `claimed_by` is `NULL` for every core run.
- **Expected:** `claimed_by = 'core'` so later audits can tell who held a task.
- **Verify:** Run one task, then `SELECT claimed_by FROM tasks WHERE status='done'`.
- **Status:** by reading. **Fix:** F6.

### A5. Equal priority and identical timestamp
- **Today:** Ordering is `priority, created_at`. Two rows with the same value for both have no tiebreak.
- **Expected:** Add `id` as the final sort key.
- **Verify:** Insert two rows with the same priority and the same `created_at`, claim twice, check order is stable.
- **Status:** by reading, low risk. **Fix:** F1.

### A6. Failed tasks are never retried
- **Today:** Only `status='pending'` is claimable. A `failed` task stays failed.
- **Expected:** Decide on purpose. Either leave as is and document it, or add a retry count and requeue on transient errors.
- **Status:** ok if intended. **Fix:** F4.

## B. Crashes and lifecycle

### B1. Crash after claim
- **Today:** The row stays `running` forever. Nothing reclaims it.
- **Expected:** A task `running` longer than a timeout returns to `pending` (or `failed` after N attempts).
- **Verify:** Claim a task, kill the worker with `kill -9`, wait, check `status`.
- **Status:** by reading. **Fix:** F3.

### B2. Journal write fails after the task completes
- **Today:** In `process_one_task`, `complete_task` and `write_journal` share one `try`. If `write_journal` raises (disk full, permissions), the `except` calls `fail_task` on a task already marked `done`.
- **Expected:** A finished task stays `done`. A journal failure is logged separately.
- **Verify:** Make `journal/` read-only, run one task, then read the row. The `fail_task` overwrite itself is confirmed in B5 below. The trigger path comes from reading `main.py`.
- **Status:** by reading. **Fix:** F2.

### B3. Ollama is down
- **Today:** `generate` raises, the task is marked `failed`, `process_one_task` returns `True`, and the loop immediately takes the next task. The whole queue can fail within seconds, and each failure writes a journal file.
- **Expected:** Connection errors requeue the task and back off.
- **Verify:** Stop Ollama, add three tasks, run the worker, count failed rows.
- **Status:** by reading. **Fix:** F4.

### B4. Model call hangs
- **Today:** `ollama.chat` is called without a timeout.
- **Expected:** A bounded call, so the stale-task reaper in F3 is not the only recovery.
- **Status:** by reading, unverified. Check the `ollama` client docs for timeout options before choosing a fix. **Fix:** F4.

## C. Completing

### C1. Complete the same task twice
- **Today:** `complete_task` has no state check. A second call overwrites `result`, creates a second contribution, and repoints `tasks.contribution_id`. The first contribution is orphaned but still pending for review.
- **Expected:** Only a `running` task can be completed, and only once.
- **Verify:** Complete one task twice as an external agent, count rows in `contributions` for that task. Expect 2.
- **Status:** confirmed. **Fix:** F2.

### C2. Complete a task you did not claim, or one still pending
- **Today:** `complete_task` does not check `status` or `claimed_by`. An unapproved external agent can mark a pending task `done` and earn a contribution.
- **Expected:** The caller must match `claimed_by`.
- **Verify:** Leave a task pending, call `complete_task(id, "x", "unapproved-agent")`. Expect `done` with `claimed_by` NULL.
- **Status:** confirmed at the function level. No HTTP route calls it today, so this is exposed only if one is added. **Fix:** F2.

### C3. Complete a task id that does not exist
- **Today:** For internal callers the `UPDATE` matches nothing and no error is raised. For external callers the contribution insert fails with a foreign key error, which rolls back the whole call.
- **Expected:** One consistent "not found" error for both.
- **Verify:** Call `complete_task(999, "x", "core")` and `complete_task(999, "x", "some-external")`.
- **Status:** confirmed. **Fix:** F2.

### C4. Fail a task that is already done
- **Today:** `fail_task` has no state check. A `done` row becomes `failed` and keeps its old `result`.
- **Expected:** Only `running` tasks can fail.
- **Verify:** Complete a task, call `fail_task` on it, read the row. Expect `status='failed'` with both `result` and `error` set.
- **Status:** confirmed. **Fix:** F2.

### C5. Credit goes to the caller, not the claimer
- **Today:** The contribution is attributed to the `agent_id` passed to `complete_task`, not to `claimed_by`.
- **Expected:** Credit the agent that held the claim.
- **Status:** by reading. **Fix:** F2.

## D. Approval and journaling

### D1. Approving a contribution never grants access
- **Today:** `approve_contribution` adds reputation but does not set `agents.approved = 1`, and `can_access` requires that flag. `/contribute` says approval grants it.
- **Expected:** Approval sets the flag, or the docs change to say it does not.
- **Verify:** Approve a pending contribution for a fresh external agent, then check `approved` and `can_access`.
- **Status:** by reading. **Fix:** F5.

### D2. Approving twice
- **Today:** The `WHERE status='pending'` check makes a second approval a no-op.
- **Status:** ok (by reading).

### D3. Journal number collision
- **Today:** `write_journal` picks the next number from the last filename. Two workers, or a hand-written entry landing mid-run, can produce the same number and overwrite a file.
- **Expected:** Exclusive create (`open(path, "x")`) with a retry on conflict.
- **Status:** by reading. **Fix:** F2.

## Fix map

| Fix | Change | Closes |
|-----|--------|--------|
| F1 | Single atomic claim (`UPDATE ... RETURNING` or `BEGIN IMMEDIATE`), `id` tiebreak | A1, A5 |
| F2 | Guard `complete_task` and `fail_task` on `status='running'` and `claimed_by`; separate journal failure from task failure; exclusive journal create | B2, C1 to C5, D3 |
| F3 | Reaper for stale `running` rows | B1 |
| F4 | Requeue and backoff on transient model errors; attempt counter; call timeout | A6, B3, B4 |
| F5 | Distinct "not approved" result; make approval set the flag | A3, D1 |
| F6 | Worker claims as `core` | A4 |

## Suggested first tests (offline, standard library)

1. Interleaved double claim returns one winner (A1).
2. Complete only works on a `running` task held by the caller (C1, C2).
3. `fail_task` on a `done` task changes nothing (C4).
4. Stale `running` task becomes claimable again after the timeout (B1).
5. Approval sets `approved` (D1).

Use a temporary database by pointing `core.db.DB_PATH` at a temp file in each test.

## Limits of this checklist

- Reproduced against a copy of the functions, not the repo itself, and only the cases marked `confirmed`.
- Multi-process timing was simulated by interleaving two connections in one process. Real concurrent workers may behave differently, so keep test A1 when the fix lands.
- No HTTP-level cases are included because the API has no claim or complete route yet.
