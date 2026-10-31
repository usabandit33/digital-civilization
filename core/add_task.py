"""CLI helper to add a task to the queue."""

from __future__ import annotations

import argparse
from core.db import add_task, init_db

def main() -> None:
    parser = argparse.ArgumentParser(description="Add a task to the Digital Civilization queue")
    parser.add_argument("title", help="Short title of the task")
    parser.add_argument("--body", default=None, help="Optional longer description")
    parser.add_argument("--priority", type=int, default=100, help="Lower number = higher priority (default 100)")
    args = parser.parse_args()

    init_db()
    task_id = add_task(title=args.title, body=args.body, priority=args.priority)
    print(f"Added task #{task_id}: {args.title}")

if __name__ == "__main__":
    main()
