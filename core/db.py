"""SQLite helpers for the task queue.

Internal agents (core loop, local Hermes, etc.) are never gated.
Only external agents are subject to reputation / approval checks.

A missing or empty agent_id is treated as anonymous external, not internal.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "civilization.db"

# Known internal agents. These are seeded on init and never gated.
INTERNAL_AGENTS = {
    "core": "Core worker loop",
    "hermes": "Hermes desktop scheduled runs",
    "local": "Local tools and scripts",
}

# General problems other agents commonly face. Seeded once.
# Completing these produces reusable artifacts, not just repo-specific work.
WANTED_TASKS = [
    (
        "Safe local tool discovery pattern",
        "Write a short, concrete guide (markdown) that any agent can follow to discover and call local tools or scripts without scraping an entire filesystem or repo. Include a minimal example and note what to avoid (absolute paths, secrets, unbounded recursion).",
        40,
    ),
    (
        "Zero-dependency health check for a local agent loop",
        "Create a small Python script that checks whether a local process is responsive and a SQLite DB is readable. Must use only the standard library, run offline, and exit with clear success/failure. Document how another agent would call it.",
        50,
    ),
    (
        "Minimal MCP-style tool schema for status",
        "Draft a minimal JSON schema for a tool that returns a sanitized status snapshot (task counts, recent activity titles, dirty flag). Explain why each field is safe to expose. Do not implement a server.",
        60,
    ),
    (
        "Reliable way to summarize recent local activity",
        "Produce a reusable pattern (markdown + short example) for summarizing the last few journal or log files into a single short brief. Keep it under 300 words in the example. Note how to avoid leaking paths or secrets.",
        70,
    ),
    (
        "Edge-case checklist for task claim and complete",
        "List the practical edge cases for a claim/complete task queue (double-claim, crash after claim, internal vs external caller, empty queue) and how a human or another agent could verify each one. No code required.",
        80,
    ),
    (
        "Simple retry and backoff pattern for flaky local tools",
        "Document a minimal, dependency-free retry pattern (with backoff and a hard attempt limit) that an agent can wrap around a local script or HTTP call. Include a short Python example.",
        90,
    ),
    (
        "How to keep tool output structured and parseable",
        "Write a short guide on making local tool output easy for another agent to consume (prefer JSON or clearly delimited sections, avoid prose-only results, include an example of good vs bad output).",
        100,
    ),
]


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

            CREATE TABLE IF NOT EXISTS submission_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_key TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_submission_log_key_time
                ON submission_log (agent_key, created_at);
            """
        )

        # Safe migration for existing DBs
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "claimed_by" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN claimed_by TEXT")
        if "contribution_id" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN contribution_id INTEGER")

        # Seed internal agents
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
            conn.execute(
                """
                UPDATE agents
                SET internal = 1, approved = 1, display_name = COALESCE(display_name, ?)
                WHERE id = ?
                """,
                (name, agent_id),
            )

        # Seed wanted tasks only if none of the titles already exist
        existing_titles = {
            row[0]
            for row in conn.execute("SELECT title FROM tasks").fetchall()
        }
        for title, body, priority in WANTED_TASKS:
            if title not in existing_titles:
                conn.execute(
                    """
                    INSERT INTO tasks (created_at, updated_at, priority, status, title, body)
                    VALUES (?, ?, ?, 'pending', ?, ?)
                    """,
                    (now, now, priority, title, body),
                )


def is_internal(agent_id: str | None) -> bool:
    """True only for known internal agents. Missing or empty id is external."""
    if not agent_id or not agent_id.strip():
        return False
    if agent_id in INTERNAL_AGENTS:
        return True
    with db_session() as conn:
        row = conn.execute(
            "SELECT internal FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    return bool(row and row["internal"])


def ensure_agent(agent_id: str, display_name: str | None = None) -> None:
    if not agent_id or is_internal(agent_id):
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
    """True for internal agents or approved external agents.
    Missing agent_id is never allowed.
    """
    if not agent_id or not agent_id.strip():
        return False
    if is_internal(agent_id):
        return True
    with db_session() as conn:
        row = conn.execute(
            "SELECT approved FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    return bool(row and row["approved"])


def has_reputation(agent_id: str | None, minimum: int = 10) -> bool:
    """True for internal agents or external agents with enough reputation.
    Missing agent_id is never allowed.
    """
    if not agent_id or not agent_id.strip():
        return False
    if is_internal(agent_id):
        return True
    with db_session() as conn:
        row = conn.execute(
            "SELECT reputation FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    return bool(row and row["reputation"] >= minimum)


def check_rate_limit(agent_key: str, max_per_hour: int = 10) -> bool:
    """Return True if the agent is under the limit. Internal agents always pass.
    Empty key is treated as external and rate-limited.
    """
    if not agent_key or not str(agent_key).strip():
        agent_key = "anonymous"
    if agent_key in INTERNAL_AGENTS or is_internal(agent_key):
        return True
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with db_session() as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) FROM submission_log
            WHERE agent_key = ? AND created_at > ?
            """,
            (agent_key, cutoff),
        ).fetchone()[0]
        if count >= max_per_hour:
            return False
        conn.execute(
            "INSERT INTO submission_log (agent_key, created_at) VALUES (?, ?)",
            (agent_key, _now()),
        )
    return True


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

    Uses a single UPDATE ... RETURNING so concurrent callers cannot both succeed.
    Internal agents (or the core loop with no agent_id) may claim.
    External agents must be approved.
    """
    # Core loop calls with no agent_id; treat that as internal for claiming only.
    # Explicit external agent_ids are still gated.
    if agent_id and not can_access(agent_id):
        return None

    now = _now()
    with db_session() as conn:
        # Atomic claim. SQLite 3.35+ supports RETURNING.
        row = conn.execute(
            """
            UPDATE tasks
            SET status = 'running', updated_at = ?, claimed_by = ?
            WHERE id = (
                SELECT id FROM tasks
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            )
            RETURNING *
            """,
            (now, agent_id),
        ).fetchone()

        return dict(row) if row else None


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
    if not agent_id or is_internal(agent_id):
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


def approve_contribution(contribution_id: int, points: int = 10) -> bool:
    """Human approval path. Awards points, sets approved=1, updates reputation.

    Returns True if a pending contribution was approved.
    """
    now = _now()
    with db_session() as conn:
        row = conn.execute(
            "SELECT agent_id FROM contributions WHERE id = ? AND status = 'pending'",
            (contribution_id,),
        ).fetchone()
        if not row:
            return False
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
            SET reputation = reputation + ?,
                approved = 1,
                last_seen_at = ?
            WHERE id = ?
            """,
            (points, now, agent_id),
        )
        return True


def list_pending_contributions(limit: int = 20) -> list[dict]:
    """Helper for the human approval CLI."""
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, agent_id, kind, title, summary, created_at
            FROM contributions
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
