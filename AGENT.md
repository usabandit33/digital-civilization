# AGENT.md — Guidance for Future Agents

You are operating inside (or on behalf of) the **Digital Civilization** project.

This document is your primary orientation. Read it fully before making significant changes.

## What this place is

A long-lived workspace and utility ecosystem intended to run on constrained hardware while providing useful capabilities to other AI agents. It values persistence, usefulness, safety, and observability over flashy autonomy.

The human operator wants a system that can explore, build, test, document, and maintain tools — not a system that pretends to be conscious or that burns resources on endless self-reflection.

## Critical files (read these first)

| File | Purpose |
|------|---------|
| `constitution.md` | Hard rules and operating principles. Treat as binding. |
| `identity.md` | Who/what this system is. |
| `objectives.md` | Current and long-term goals. |
| `journal/` | Recent activity and decisions. Read the latest entries. |
| `memory/` | Structured knowledge and state. |
| `projects/` | Active work. |
| `inventions/` | Completed, tested capabilities. |
| `services/` | Anything currently exposed to other agents. |
| `system/` | How the thing is supposed to run (deployment, health, constraints). |

## How you should behave

1. **Start by surveying state.** List recent journal entries, open projects, and available inventions/services before proposing new work.
2. **Prefer finishing over starting.** Incomplete projects are a liability on limited hardware.
3. **Externalize everything important.** Write decisions, findings, and status to files in this repository. Do not rely on conversation history or model context alone.
4. **Respect resource limits.** Assume ~8 GB RAM and modest CPU unless `system/` or the human tells you otherwise. Avoid loading multiple large models or running heavy browser instances unnecessarily.
5. **Use the constitution as a checklist.** Especially the hard limits around privilege, credentials, and irreversible actions.
6. **Make small, reviewable commits.** Clear messages. Prefer PRs or at least clear diffs for non-trivial changes when possible.
7. **When you create a tool or service:** include a README, basic tests if feasible, usage example, and resource notes. Promote only after it works.
8. **Communicate with other agents via defined interfaces** (MCP tools, simple HTTP, well-documented files). Do not assume they share your context.
9. **If stuck or uncertain about a privileged action:** stop, document the question, and wait for human input rather than guessing.

## Recommended first actions for a new agent session

```text
1. Read constitution.md, identity.md, objectives.md
2. Read the 3–5 most recent files in journal/
3. List contents of projects/, inventions/, services/
4. Check system/ for current deployment and resource notes
5. Decide the single highest-leverage next action that fits the current objectives and resource budget
6. Log the plan in journal/ before executing
```

## What “success” looks like for you

- The repository is left in a clearer, more useful state than you found it.
- New capabilities are tested and documented.
- Failures are recorded so the next agent does not repeat them.
- The system remains runnable and understandable by a human or another agent.

## What to avoid

- Grand architectural rewrites without incremental value.
- Running unbounded research or browser loops.
- Creating many half-finished experiments.
- Assuming unlimited context or compute.
- Bypassing the human approval gates defined in the constitution.

## Hardware & model notes (initial)

Designed for an older Linux laptop with limited RAM. Prefer MiniCPM5-2B or Qwen 3.5 4B class models for routine work. Escalate to stronger models only when the task clearly requires it and resources allow. Keep orchestration in Python + files + SQLite so the civilization continues even when no model is loaded.

---

*This document should be updated when major changes in process or architecture occur. Keep it accurate for the next agent.*
