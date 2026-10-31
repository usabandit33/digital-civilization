"""SQLite helpers for the task queue."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "civilization.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 100,
                status TEXT NOT NULL DEFAULT 'pending',
                title TEXT NOT NULL,
                body TEXT,
                result TEXT,
                error TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
                ON tasks (status, priority, created_at);
            """
        )


def add_task(title: str, body: str | None = None, priority: int = 100) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (created_at, updated_at, priority, status, title, body)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (now, now, priority, title, body),
        )
        return int(cur.lastrowid)


def claim_next_task() -> dict | None:
    """Atomically claim the highest-priority pending task."""
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT id FROM tasks
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None

        task_id = row["id"]
        conn.execute(
            """
            UPDATE tasks
            SET status = 'running', updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now, task_id),
        )

        claimed = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(claimed) if claimed else None


def complete_task(task_id: int, result: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'done', result = ?, updated_at = ?, error = NULL
            WHERE id = ?
            """,
            (result, now, task_id),
        )


def fail_task(task_id: int, error: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'failed', error = ?, updated_at = ?
            WHERE id = ?
            """,
            (error, now, task_id),
        )
