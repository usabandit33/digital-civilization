# Agents

Definitions, prompts, and configurations for specialized agents and reusable skills that operate inside the Digital Civilization.

## Available Agents

| Agent | File | Purpose |
|-------|------|---------|
| **Bootstrap Agent** | `bootstrap-agent.md` | Clones the repository and begins operating according to the constitution, identity, and objectives. Use this to hand the project to a new model or session. |

## How to add a new agent

1. Create a clear markdown file in this directory.
2. Include a ready-to-copy system prompt / instruction block.
3. Document how to invoke it (Hermes, Ollama, Claude, etc.).
4. Update this README with a one-line summary.
5. Prefer agents that respect the constitution and externalize state into the repository.

Keep agents lightweight, focused, and composable.
