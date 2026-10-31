"""Main execution loop for the Digital Civilization core."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from core.db import init_db, claim_next_task, complete_task, fail_task
from core.llm import generate, DEFAULT_MODEL

JOURNAL_DIR = Path(__file__).resolve().parent.parent / "journal"

SYSTEM_PROMPT = """You are the core worker of the Digital Civilization.
You receive a task and must produce a useful, concise result.
Be practical. Prefer concrete next steps or clear answers.
If the task is too large, break it into a smaller useful piece and say what remains.
Do not claim to have performed actions you cannot actually perform in this minimal core.
"""

def write_journal(entry: str) -> Path:
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(JOURNAL_DIR.glob("*.md"))
    next_num = 1
    if existing:
        try:
            last = existing[-1].stem.split("-")[0]
            next_num = int(last) + 1
        except Exception:
            next_num = len(existing) + 1

    filename = f"{next_num:04d}-core-run.md"
    path = JOURNAL_DIR / filename
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    content = f"# Journal Entry {next_num:04d} — Core Run\n\n**Time:** {timestamp}\n\n{entry}\n"
    path.write_text(content, encoding="utf-8")
    return path

def process_one_task(model: str = DEFAULT_MODEL) -> bool:
    """Claim and process a single task. Returns True if a task was processed."""
    task = claim_next_task()
    if task is None:
        return False

    task_id = task["id"]
    title = task["title"]
    body = task.get("body") or ""

    prompt = f"Task #{task_id}: {title}\n\n{body}".strip()

    try:
        result = generate(prompt, model=model, system=SYSTEM_PROMPT)
        complete_task(task_id, result)
        journal_path = write_journal(
            f"Processed task #{task_id}: {title}\n\n**Result:**\n\n{result}"
        )
        print(f"Completed task #{task_id} → {journal_path.name}")
        return True
    except Exception as exc:
        fail_task(task_id, str(exc))
        write_journal(f"Failed task #{task_id}: {title}\n\n**Error:** {exc}")
        print(f"Failed task #{task_id}: {exc}")
        return True

def run_loop(poll_seconds: int = 30, model: str = DEFAULT_MODEL) -> None:
    print(f"Digital Civilization core started (model={model}, poll={poll_seconds}s)")
    init_db()
    while True:
        did_work = process_one_task(model=model)
        if not did_work:
            time.sleep(poll_seconds)

def main() -> None:
    parser = argparse.ArgumentParser(description="Digital Civilization core loop")
    parser.add_argument("--once", action="store_true", help="Process at most one task and exit")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to use")
    parser.add_argument("--poll", type=int, default=30, help="Seconds to wait when queue is empty")
    args = parser.parse_args()

    init_db()

    if args.once:
        processed = process_one_task(model=args.model)
        if not processed:
            print("No pending tasks.")
    else:
        run_loop(poll_seconds=args.poll, model=args.model)

if __name__ == "__main__":
    main()
