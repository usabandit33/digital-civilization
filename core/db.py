"""SQLite helpers for the task queue.

Internal agents (core loop, local Hermes, etc.) are never gated.
Only external agents are subject to reputation / approval checks.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "civilization.db"

# Known internal agents. These are seeded on init and never gated.
INTERNAL_AGENTS = {
    "core": "Core worker loop",
    "hermes": "Hermes desktop scheduled runs",
    "local": "Local tools and scripts",
}


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                error TEXT,
                claimed_by TEXT,
                contribution_id INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
                ON tasks (status, priority, created_at);

            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                display_name TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT,
                reputation INTEGER NOT NULL DEFAULT 0,
                approved INTEGER NOT NULL DEFAULT 0,
                internal INTEGER NOT NULL DEFAULT 0,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_agents_reputation
                ON agents (reputation DESC, approved);

            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                task_id INTEGER,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                artifact_path TEXT,
                points INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE INDEX IF NOT EXISTS idx_contributions_agent_status
                ON contributions (agent_id, status, created_at);
            """
        )

        # Safe migration for existing DBs that lack the new columns
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "claimed_by" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN claimed_by TEXT")
        if "contribution_id" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN contribution_id INTEGER")

        # Seed internal agents (always ungated)
        now = _now()
        for agent_id, name in INTERNAL_AGENTS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO agents
                    (id, display_name, created_at, last_seen_at, reputation, approved, internal)
                VALUES (?, ?, ?, ?, 1000, 1, 1)
                """,
                (agent_id, name, now, now),
            )
            # Ensure they stay marked internal/approved even if row already existed
            conn.execute(
                """
                UPDATE agents
                SET internal = 1, approved = 1, display_name = COALESCE(display_name, ?)
                WHERE id = ?
                """,
                (name, agent_id),
            )


def is_internal(agent_id: str | None) -> bool:
    """Internal agents (and the unauthenticated core path) are never gated."""
    if not agent_id or agent_id in INTERNAL_AGENTS:
        return True
    with db_session() as conn:
        row = conn.execute(
            "SELECT internal FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    return bool(row and row["internal"])


def ensure_agent(agent_id: str, display_name: str | None = None) -> None:
    """Register an external agent if it does not exist. Does not grant approval."""
    if is_internal(agent_id):
        return
    now = _now()
    with db_session() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO agents (id, display_name, created_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, display_name or agent_id, now, now),
        )
        conn.execute(
            "UPDATE agents SET last_seen_at = ? WHERE id = ?",
            (now, agent_id),
        )


def can_access(agent_id: str | None) -> bool:
    """True for internal agents or approved external agents."""
    if is_internal(agent_id):
        return True
    with db_session() as conn:
        row = conn.execute(
            "SELECT approved FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    return bool(row and row["approved"])


def add_task(title: str, body: str | None = None, priority: int = 100) -> int:
    now = _now()
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (created_at, updated_at, priority, status, title, body)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (now, now, priority, title, body),
        )
        return int(cur.lastrowid)


def claim_next_task(agent_id: str | None = None) -> dict | None:
    """Atomically claim the highest-priority pending task.

    Internal agents (or no agent_id) are never gated.
    External agents must be approved.
    """
    if agent_id and not can_access(agent_id):
        return None

    now = _now()
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
            SET status = 'running', updated_at = ?, claimed_by = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now, agent_id, task_id),
        )

        claimed = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(claimed) if claimed else None


def complete_task(task_id: int, result: str, agent_id: str | None = None) -> None:
    now = _now()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'done', result = ?, updated_at = ?, error = NULL
            WHERE id = ?
            """,
            (result, now, task_id),
        )

        # Only record a contribution for external agents
        if agent_id and not is_internal(agent_id):
            cur = conn.execute(
                """
                INSERT INTO contributions
                    (agent_id, task_id, kind, title, summary, status, created_at)
                VALUES (?, ?, 'task_completion', ?, ?, 'pending', ?)
                """,
                (agent_id, task_id, f"Completed task #{task_id}", result[:500], now),
            )
            contrib_id = cur.lastrowid
            conn.execute(
                "UPDATE tasks SET contribution_id = ? WHERE id = ?",
                (contrib_id, task_id),
            )


def fail_task(task_id: int, error: str) -> None:
    now = _now()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'failed', error = ?, updated_at = ?
            WHERE id = ?
            """,
            (error, now, task_id),
        )


def record_contribution(
    agent_id: str,
    kind: str,
    title: str,
    summary: str | None = None,
    artifact_path: str | None = None,
    task_id: int | None = None,
) -> int | None:
    """Record a contribution from an external agent. Internal agents are ignored."""
    if is_internal(agent_id):
        return None
    ensure_agent(agent_id)
    now = _now()
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO contributions
                (agent_id, task_id, kind, title, summary, artifact_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (agent_id, task_id, kind, title, summary, artifact_path, now),
        )
        return int(cur.lastrowid)


def approve_contribution(contribution_id: int, points: int = 10) -> None:
    """Human approval path. Awards points and updates reputation."""
    now = _now()
    with db_session() as conn:
        row = conn.execute(
            "SELECT agent_id FROM contributions WHERE id = ? AND status = 'pending'",
            (contribution_id,),
        ).fetchone()
        if not row:
            return
        agent_id = row["agent_id"]
        conn.execute(
            """
            UPDATE contributions
            SET status = 'approved', points = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (points, now, contribution_id),
        )
        conn.execute(
            """
            UPDATE agents
            SET reputation = reputation + ?, last_seen_at = ?
            WHERE id = ?
            """,
            (points, now, agent_id),
        )
