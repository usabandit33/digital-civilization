# Digital Civilization

A persistent, self-maintaining digital environment designed to run on constrained local hardware (old laptop, limited RAM). It builds tools, knowledge, and services that other AI agents can use.

This is **not** a chatbot. It is a long-lived workspace with identity, memory, projects, experiments, and a growing catalog of useful capabilities.

## Purpose

Develop an increasingly capable digital environment that provides useful services, knowledge, and tools to other AI agents — while remaining stable, observable, and safe on limited resources.

## Core Principles

- External memory over giant context windows
- One model loaded at a time
- Deterministic tools + model decisions
- Human approval for irreversible / privileged actions
- Git as the system of record
- Usefulness to other agents is a primary objective

## Structure

```
digital-civilization/
├── constitution.md      # Foundational rules and boundaries
├── identity.md          # Who this system is
├── objectives.md        # Long-term goals and current priorities
├── AGENT.md             # Guidance document for any future agent working here
├── journal/             # Session and daily logs
├── memory/              # Structured knowledge and persistent state
├── projects/            # Active work
├── inventions/          # Completed, tested tools and services
├── services/            # Running MCP endpoints / APIs
├── experiments/         # Temporary / exploratory work
├── agents/              # Specialized sub-agents or skills definitions
└── system/              # Deployment, systemd, Docker, health checks
```

## Quick Start for Humans

1. Clone the repo onto the target Linux machine.
2. Read `constitution.md`, `identity.md`, and `objectives.md`.
3. Follow setup instructions in `system/` (once populated).
4. Give the local model (or Hermes) access to this repository as its primary workspace.

## For Future Agents

**Start by reading `AGENT.md`.** It contains everything you need to understand the current state, constraints, and how to operate responsibly inside this civilization.
