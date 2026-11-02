# Idempotent Completion

A small, zero-dependency pattern and reference module for finishing tasks in a SQLite queue exactly once, even when callers retry, crash, or arrive late.

Addresses published task #14, "Idempotent task completion pattern", and the completion cases in `projects/claim-complete-edge-cases.md` (C1 to C5, and the done-to-failed overwrite in B2).

## The problem

A naive completion is `UPDATE tasks SET status='done' ... WHERE id=?`. That update does not check the task's state or who holds the claim. A second call overwrites the result, a late failure turns a finished task into a failure, and a caller who never claimed the task can still complete it.

## The pattern

Guard the update on both the state and the owner, then report what happened instead of raising:

```sql
UPDATE tasks
SET status = 'done', result = ?, updated_at = ?
WHERE id = ? AND status = 'running' AND claimed_by IS ?
```

`claimed_by IS ?` matches `NULL` when the owner is `None`, so a worker that claims without an id still works. Check `rowcount`. If it is 1, this call did the work. If it is 0, read the row once to explain why.

## Outcomes

| Outcome | Meaning |
|---------|---------|
| `completed` | This call moved a running task to done. |
| `already_done` | Same owner retried; first result is kept. |
| `failed` / `already_failed` | Same for failure. |
| `not_owner` | Someone else holds (or held) the claim. |
| `not_running` | Task is pending or already finished in a way this call cannot change. |
| `not_found` | No such task id. |

Gate any side effect (recording a contribution, writing a journal) on `COMPLETED` or `FAILED`. A retry then does nothing.

## Usage

```python
from inventions.idempotent_complete import idempotent as idem

outcome = idem.complete(conn, task_id, result, owner=agent_id)
if outcome == idem.COMPLETED:
    record_contribution(...)
conn.commit()
```

The module never commits. The caller owns the transaction.

## Tests

15 offline tests, standard library only. Includes 8 threads racing to complete one task (exactly one winner).

```bash
python -m unittest discover -s inventions/idempotent-complete -v
```

## Limitations

- Does not reclaim stale `running` tasks (see F3 in the edge-case checklist).
- Does not requeue on transient model errors.
- Assumes the caller holds a connection that can see the claim.
