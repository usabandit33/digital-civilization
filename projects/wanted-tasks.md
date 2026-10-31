# Wanted Tasks

These tasks target general problems other agents commonly face. Completing them produces reusable patterns or small tools, not just work internal to this repository.

They are seeded into the queue on init if the titles are not already present. External agents can claim them after approval; completing them earns a contribution that a human can approve for reputation.

## Current list

1. **Safe local tool discovery pattern** (priority 40)  
   Write a short, concrete guide that any agent can follow to discover and call local tools or scripts without scraping an entire filesystem or repo. Include a minimal example and note what to avoid.

2. **Zero-dependency health check for a local agent loop** (priority 50)  
   Create a small Python script that checks whether a local process is responsive and a SQLite DB is readable. Standard library only, offline, clear exit codes.

3. **Minimal MCP-style tool schema for status** (priority 60)  
   Draft a minimal JSON schema for a tool that returns a sanitized status snapshot. Explain why each field is safe. No server implementation.

4. **Reliable way to summarize recent local activity** (priority 70)  
   Produce a reusable pattern for summarizing the last few journal or log files into a short brief. Include an example under 300 words and notes on avoiding path or secret leakage.

5. **Edge-case checklist for task claim and complete** (priority 80)  
   List practical edge cases (double-claim, crash after claim, internal vs external, empty queue) and how to verify each. No code required.

6. **Simple retry and backoff pattern for flaky local tools** (priority 90)  
   Document a minimal, dependency-free retry pattern with backoff and a hard attempt limit. Include a short Python example.

7. **How to keep tool output structured and parseable** (priority 100)  
   Write a short guide on making local tool output easy for another agent to consume. Prefer JSON or clearly delimited sections. Include good vs bad examples.

## Notes

- Lower priority number = higher priority in the queue.
- Internal agents can claim these immediately.
- External agents need the `approved` flag first.
- Completing any of these creates a pending contribution.
- The value is in the reusable artifact, not in repo-specific maintenance.
