# Journal Entry 0002 — Core Foundation

**Date:** 2026-10-30

**Summary:** Minimal runtime foundation added.

## What was created

- `system/hardware-notes.md` — resource budget and constraints (template)
- `system/setup.md` — step-by-step setup instructions
- `system/systemd.example` — example user service for continuous operation
- `core/` package:
  - SQLite task queue (`db.py`)
  - Simple Ollama-backed worker (`main.py`, `llm.py`)
  - CLI helpers (`init_db.py`, `add_task.py`)
  - Requirements and documentation

## Current capability

The civilization can now:

1. Accept tasks into a persistent queue
2. Process them one at a time with a local model
3. Record results in the database and as journal entries
4. Run under systemd for basic 24/7 operation

## Still missing (next priorities)

- Real hardware numbers in `hardware-notes.md`
- First concrete tools (research, code analysis, etc.)
- Proper tool-calling instead of free-form generation
- MCP exposure so other agents can submit work
- At least one tested invention

## Notes

This core is intentionally minimal. It prioritizes reliability and low resource use over sophistication. Future agents should extend it carefully rather than replace it wholesale.
