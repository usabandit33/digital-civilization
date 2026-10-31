"""Minimal HTTP API for the Digital Civilization task queue.

Other agents can submit work freely. Listing tasks and reading results
require an approved (or internal) agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from core.db import init_db, add_task, get_connection, can_access, is_internal

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
    """Internal agents and approved external agents may proceed."""
    if not can_access(agent_id):
        raise HTTPException(
            status_code=403,
            detail="Approved agent required. Identify with X-Agent-Id header and earn approval via contributions.",
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


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreate) -> TaskResponse:
    # Open: anyone may submit work.
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
