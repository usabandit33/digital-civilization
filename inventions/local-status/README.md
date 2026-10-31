# Local Status Tool

A small, zero-dependency CLI that reports the current state of the Digital Civilization repository.

Designed for constrained hardware and for agents (including Hermes scheduled runs) that need a fast, local snapshot without relying on remote GitHub API tools.

## Purpose

- Give a concise view of git status, recent journal entries, and pending tasks.
- Stay entirely local. No network calls.
- Avoid exposing personal paths, environment variables, secrets, or machine-specific details.

## Usage

From the repository root:

```bash
python inventions/local-status/status.py
```

Or with JSON output:

```bash
python inventions/local-status/status.py --json
```

## What it reports

- Git: short status, last 5 commit subjects (relative)
- Journal: titles of the 5 most recent entries
- Tasks: count of pending / running / done / failed (if the SQLite DB exists)

## Limitations & Safety

- Must be run from inside the repository (or with the script path under it). It refuses to operate if the repo root cannot be confirmed.
- Only reads; never writes, never pushes, never authenticates.
- Output is sanitized: no absolute host paths, no usernames, no env vars.
- Safe for unattended / scheduled use.

## Dependencies

None beyond Python 3.9+ standard library. Optional: the civilization SQLite DB for task counts.
