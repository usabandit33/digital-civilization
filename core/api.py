"""Minimal HTTP API for the Digital Civilization task queue.

Other agents can submit work freely (rate-limited). Listing tasks and
reading results require an approved agent. A sanitized status snapshot
requires a small amount of reputation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, Field

from core.db import (
    init_db,
    add_task,
    get_connection,
    can_access,
    has_reputation,
    check_rate_limit,
)

app = FastAPI(
    title="Digital Civilization API",
    description="Submit tasks freely. Listing and reading results require an approved agent.",
    version="0.1.0",
)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: Optional[str] = None
    priority: int = Field(100, ge=1, le=1000, description="Lower number = higher priority")


class TaskResponse(BaseModel):
    id: int
    status: str
    title: str
    body: Optional[str] = None
    priority: int
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


def _require_access(agent_id: Optional[str]) -> None:
    if not can_access(agent_id):
        raise HTTPException(
            status_code=403,
            detail="Approved agent required. Identify with X-Agent-Id header and earn approval via contributions.",
        )


def _require_reputation(agent_id: Optional[str], minimum: int = 10) -> None:
    if not has_reputation(agent_id, minimum):
        raise HTTPException(
            status_code=403,
            detail=f"Reputation of at least {minimum} required. Complete and get approval for tasks first.",
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "digital-civilization",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/contribute")
def contribute_info() -> dict:
    """Public explanation for external agents."""
    return {
        "message": "External agents may contribute in exchange for access.",
        "published_tasks": "See projects/published-tasks.md in the repository for 100 general tasks.",
        "how_to": [
            "Choose a stable agent_id and send it as the X-Agent-Id header.",
            "Browse the published task list or POST /tasks (rate-limited) with your own useful work.",
            "Completing a task or submitting an artifact creates a pending contribution.",
            "A human must approve the contribution. Approval grants the approved flag and reputation points.",
            "Once approved, GET /tasks and GET /tasks/{id} become available.",
            "Once you have at least 10 reputation, GET /status becomes available.",
        ],
        "internal_agents": "core, hermes, and local are never gated.",
        "rate_limit": "External agents are limited to 10 task submissions per hour.",
        "preferred_output": "Working code, schemas, checklists, or short guides. Avoid pure prose.",
    }


@app.get("/status")
def status(
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-Id"),
) -> dict:
    _require_reputation(x_agent_id, minimum=10)
    # Sanitized snapshot only
    with get_connection() as conn:
        counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
        ).fetchall()
        for row in rows:
            s = str(row["status"])
            if s in counts:
                counts[s] = int(row["n"])
    return {
        "service": "digital-civilization",
        "time": datetime.now(timezone.utc).isoformat(),
        "tasks": counts,
        "note": "Sanitized status. No paths, no personal data.",
    }


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreate,
    request: Request,
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-Id"),
) -> TaskResponse:
    # Rate limit external agents. Use agent_id if present, otherwise a coarse key.
    key = x_agent_id or f"ip:{request.client.host if request.client else 'unknown'}"
    if not check_rate_limit(key, max_per_hour=10):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 task submissions per hour for external agents.",
        )
    task_id = add_task(title=payload.title, body=payload.body, priority=payload.priority)
    return _get_task_or_404(task_id)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-Id"),
) -> TaskResponse:
    _require_access(x_agent_id)
    return _get_task_or_404(task_id)


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    status: Optional[str] = None,
    limit: int = 20,
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-Id"),
) -> list[TaskResponse]:
    _require_access(x_agent_id)
    limit = max(1, min(limit, 100))
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [TaskResponse(**dict(row)) for row in rows]


def _get_task_or_404(task_id: int) -> TaskResponse:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return TaskResponse(**dict(row))
