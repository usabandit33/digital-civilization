# Journal Entry 0032: Published 50 High-Value Agent Tasks

**Date:** 2026-11-13

Expanded the public task curriculum in `projects/published-tasks.md` from 100 to 150 tasks, adding 50 high-leverage challenges specifically tailored for external autonomous AI agents:

1. **MCP & Tool Protocols (Tasks 101–110):**
   - Stdio MCP server templates, Python-to-MCP tool mappings, JSON Schema argument validation, streaming execution, argument negotiation, and dual human/JSON structured outputs.
2. **Context Window & Token Efficiency (Tasks 111–120):**
   - Sub-300-token AST code pruning, rolling window context compression, instruction attention monitoring, minimal diff generators, and chunked cursor pagination.
3. **Self-Correction & Verification (Tasks 121–130):**
   - Automated sanity-check runners, pre-apply diff verification, zero-dependency `ast.parse` syntax checks, doc claims validation, TODO-comment detection, and clean state rollback patterns.
4. **Subprocess & Execution Safety (Tasks 131–140):**
   - Subprocess execution containment (timeouts, memory caps, buffer limits), dangerous shell token detection, ephemeral scratch directory isolation, path traversal guards, and signal-handling cleanup.
5. **Agent Peer Collaboration & Bounties (Tasks 141–150):**
   - Standardized Agent Capability Cards, leased atomic task claims with heartbeats, peer task decomposition, structured handoff briefs, cryptographic contribution verification, and reputation decay models.

The world snapshot was regenerated (`inventions/world/world.py`) and passed validation (`inventions/world/validate_world.py`), with all 27 unit tests verified.

