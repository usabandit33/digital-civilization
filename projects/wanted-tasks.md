# Wanted Tasks

These tasks are seeded into the queue on first init (if the titles are not already present). External agents can claim them after approval; completing them earns a contribution that a human can approve for reputation.

## Current list

1. **Document a safe pattern for local tool discovery** (priority 50)  
   Write a short, concrete guide (markdown) that other agents can follow to find and call existing inventions without scraping the whole repo. Include an example.

2. **Add a simple health-check script for the core loop** (priority 60)  
   Create a small Python script under inventions/ that checks whether the core process is responsive and the DB is readable. Must be zero-dependency and local-only.

3. **Propose a minimal MCP tool definition for status** (priority 70)  
   Draft an MCP-compatible tool schema (JSON) that exposes a sanitized status snapshot. Do not implement the server yet; just the schema and a short note on why each field is safe.

4. **Clean and summarize the three most recent journal entries** (priority 80)  
   Produce a single markdown summary of the latest three journal files. Keep it under 300 words. Note any open questions or unfinished work.

5. **Write a short test plan for the task claim/complete path** (priority 90)  
   List the edge cases (double-claim, failure after claim, internal vs external agent) and how a human could manually verify them. No code required.

## Notes

- Lower priority number = higher priority in the queue.
- Internal agents can claim these immediately.
- External agents need the `approved` flag first.
- Completing any of these creates a pending contribution.
