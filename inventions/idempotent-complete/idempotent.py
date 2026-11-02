"""Idempotent, claim-aware completion for a SQLite task queue.

Standard library only. No network. Never commits: the caller owns the
transaction, so completion and any side effects (such as recording a
contribution) can succeed or fail together.

Required table: tasks(id, status, result, error, claimed_by, updated_at).
Statuses used: 'running', 'done', 'failed'.

Every function returns one outcome string instead of raising, so a caller
can retry safely and branch on what actually happened.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

# complete() outcomes
COMPLETED = "completed"        # this call moved running -> done
ALREADY_DONE = "already_done"  # same owner retried; nothing changed

# fail() outcomes
FAILED = "failed"              # this call moved running -> failed
ALREADY_FAILED = "already_failed"  # same owner retried; nothing changed

# shared outcomes
NOT_OWNER = "not_owner"        # someone else holds (or held) the claim
NOT_RUNNING = "not_running"    # task is pending, or in a state this call cannot change
NOT_FOUND = "not_found"        # no such task id

_REPEAT = {"done": ALREADY_DONE, "failed": ALREADY_FAILED}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _diagnose(conn: sqlite3.Connection, task_id: int, owner: Optional[str], target: str) -> str:
    """Explain why the guarded UPDATE changed nothing. Read-only."""
    row = conn.execute(
        "SELECT status, claimed_by FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return NOT_FOUND
    status, claimed_by = row[0], row[1]
    # A stranger touching a running task, or a task already finished in this
    # target state, is a stale or foreign caller.
    if status in ("running", target) and claimed_by != owner:
        return NOT_OWNER
    if status == target:
        return _REPEAT[target]
    return NOT_RUNNING


def complete(
    conn: sqlite3.Connection,
    task_id: int,
    result: str,
    owner: Optional[str] = None,
    now: Optional[str] = None,
) -> str:
    """Mark a running task done, only if `owner` holds the claim.

    `owner=None` matches a NULL `claimed_by` (for example a worker that
    claims without an id). A different owner never matches it.
    """
    cur = conn.execute(
        """
        UPDATE tasks
        SET status = 'done', result = ?, error = NULL, updated_at = ?
        WHERE id = ? AND status = 'running' AND claimed_by IS ?
        """,
        (result, now or _now(), task_id, owner),
    )
    if cur.rowcount == 1:
        return COMPLETED
    return _diagnose(conn, task_id, owner, "done")


def fail(
    conn: sqlite3.Connection,
    task_id: int,
    error: str,
    owner: Optional[str] = None,
    now: Optional[str] = None,
) -> str:
    """Mark a running task failed, only if `owner` holds the claim.

    A done task is never turned into a failure by a later caller.
    """
    cur = conn.execute(
        """
        UPDATE tasks
        SET status = 'failed', error = ?, updated_at = ?
        WHERE id = ? AND status = 'running' AND claimed_by IS ?
        """,
        (error, now or _now(), task_id, owner),
    )
    if cur.rowcount == 1:
        return FAILED
    return _diagnose(conn, task_id, owner, "failed")
