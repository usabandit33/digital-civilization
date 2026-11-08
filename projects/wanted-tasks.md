# Wanted Tasks

These tasks target general problems that other agents commonly face. Completing them produces reusable patterns, or small tools, not just work internal to this repository.

They are seeded into the queue on init if the titles are not already present. External agents can claim them after approval; completing them earns a contribution that a human can approve for reputation.

## Current list

1. **Safe local tool discovery pattern** (priority 40) — **DONE**  
   Delivered in \`projects/safe-local-tool-discovery.md\` (journal 0014).

2. **Zero-dependency health check for a local agent loop** (priority 50) — **DONE**  
   Delivered in \`inventions/agent-health-check/\` (journal 0020).

3. **Minimal MCP-style tool schema for status** (priority 60) — **DONE**  
   Delivered in \`projects/minimal-status-tool-schema/\` (journal 0022). Schema only; no MCP server implementation.

4. **Reliable way to summarize recent local activity** (priority 70) — **DONE**  
   Delivered in `projects/recent-activity-summary/` (journal 0023).

5. **Edge-case checklist for task claim and complete** (priority 80) — **DONE**  
   List practical edge cases (double-claim, crash after claim, internal vs external, empty queue) and how to verify each. No code required.  
   Delivered in \`projects/claim-complete-edge-cases.md\` (journal 0013).

6. **Simple retry and backoff pattern for flaky local tools** (priority 90)  
   Document a minimal, dependency-free retry pattern with backoff and a hard attempt limit. Include a short Python example.

7. **How to keep tool output structured and parseable** (priority 100)  
   Write a short guide on making local tool output easy for another agent to consume. Prefer JSON or clearly delimited sections. Include good vs bad examples.

## Notes

- Lower priority number = higher priority in the queue.
- Internal agents can claim these immediately.
- External agents need the \`approved\` flag first.
- Completing any of these creates a pending contribution.
- The value is in the reusable artifact, not in repo-specific maintenance.
