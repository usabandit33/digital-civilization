# Core — Minimal Task Queue & Execution Loop

Lightweight foundation for the Digital Civilization.

## What it does

- SQLite-backed task queue
- Simple execution loop that can call a local Ollama model
- Writes basic journal entries
- Designed to run under systemd and survive restarts
- Intentionally minimal so it fits constrained hardware

## Quick start

```bash
# from repository root, with venv activated
python -m core.init_db
python -m core.main --once          # process one task or idle
python -m core.main                 # run continuously (poll loop)
```

## Adding a task manually

```bash
python -m core.add_task "Research lightweight MCP server patterns" --priority 10
```

## Design notes

- One model at a time
- Tasks are plain text for now (structured tools come later)
- Results and status live in the SQLite database and in `journal/`
- No browser automation or heavy tools in this first version
