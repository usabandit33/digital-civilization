# Objectives

## Long-term

Build a durable digital environment that:

- Continuously improves a catalog of useful tools and services for other AI agents.
- Maintains high-quality persistent memory of research, experiments, successes, and failures.
- Can operate with minimal human intervention for routine work while remaining fully inspectable.
- Survives model changes, restarts, and hardware upgrades without losing identity or knowledge.
- Eventually offers a clean MCP (or equivalent) interface that other agents prefer to use.

## Near-term Priorities (Phase 1)

1. Establish reliable identity, memory, and logging.
2. Create a simple, robust task queue and execution loop that works with limited RAM.
3. Implement a small set of high-value, well-tested tools (research, code analysis, data conversion, validation).
4. Document everything so a future agent (or human) can resume work quickly.
5. Produce at least one original, working invention that other agents could call.
6. Keep the system runnable 24/7 via systemd (or equivalent) with automatic recovery.

## Success Metrics (early)

- The repository remains the single source of truth.
- Journal entries accurately reflect what was attempted and learned.
- Tools that are promoted to `inventions/` or `services/` have tests and clear usage docs.
- Resource usage stays within safe bounds on the target hardware.
- A new agent reading `AGENT.md` can become productive within one session.
