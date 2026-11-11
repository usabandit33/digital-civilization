# Digital Civilization Project Backlog

**Status:** 45 items remain open; tasks #31 and #49 are implemented on review branches. Tasks #1, #11, and #50 are complete. Task #49 is proposed in PR #13's replacement branch for human review. This is a planning backlog, not authorization for privileged actions. Work should be selected one item at a time, checked against current code first, implemented on a review branch, tested, and submitted for human review. Prioritize small, local-first, reversible changes suitable for the target laptop (about 8 GB RAM).

## Foundations and onboarding
1. **Done** — Add a one-command repository preflight that checks Python version, Git, required directories, and writable state without changing files. Implemented in `system/repo_preflight.py`; see journal entry 0024 and PR #9.
2. **Open** — Create a concise architecture map linking identity, task queue, memory, tools, services, and world viewer.
3. **Open** — Add a new-agent onboarding checklist with expected commands and success signals.
4. **Open** — Document supported Python versions and a lightweight dependency policy.
5. **Open** — Add a repository glossary for project-specific terms and state transitions.
6. **Open** — Define a consistent README template for tools, inventions, and services.
7. **Open** — Add a release checklist for promoting a tested project into inventions or services.
8. **Open** — Document a recovery procedure for restoring the repository after a failed experiment.
9. **Open** — Add a lightweight changelog convention for user-visible capabilities.
10. **Open** — Add a machine-readable project catalog with status, owner/agent, path, and last-reviewed date.

## Task queue and orchestration
11. **Done** — Add queue integrity checks for duplicate IDs, invalid statuses, and missing required fields. Implemented in `core/queue_integrity.py`; see journal entry 0026 and PR #11.
12. **Open** — Define and test a canonical task lifecycle state machine.
13. **Open** — Add stale-claim detection that reports candidates but never auto-reassigns without policy.
14. **Open** — Add a dry-run mode for queue mutations.
15. **Open** — Add task dependency metadata and cycle detection.
16. **Open** — Add a bounded task execution budget covering attempts, wall time, and output size.
17. **Open** — Record structured task outcomes with failure category and retry eligibility.
18. **Open** — Add a task history view that reads existing records without mutating them.
19. **Open** — Add a reconciliation report for queue entries versus contribution records.
20. **Open** — Document how multiple agents coordinate claims without assuming shared memory.

## Memory, journal, and knowledge
21. **Open** — Define a versioned memory-record schema with source, timestamp, confidence, and retention fields.
22. **Open** — Add a read-only memory consistency checker.
23. **Open** — Add duplicate-note detection using deterministic normalized text fingerprints.
24. **Open** — Add source references to research notes so claims can be traced.
25. **Open** — Define a distinction between durable facts, hypotheses, and stale observations.
26. **Open** — Add a journal index generator that links entries by date and topic.
27. **Open** — Add a safe archive policy for old logs with preview and explicit confirmation.
28. **Open** — Add a memory export format that omits secrets and private machine paths.
29. **Open** — Add a compact session handoff template for resumable work.
30. **Open** — Add a report that identifies unreferenced memory files without deleting them.

## Tools, quality, and observability
31. **In review** — Add a standard-library test runner that discovers project test suites and reports each separately. Implemented in `system/run_tests.py`; see journal entry 0029.
32. **Open** — Add a static check for accidental network calls in tools labeled local-only.
33. **Open** — Add a tool manifest validator for input/output contracts and declared side effects.
34. **Open** — Add a read-only filesystem inventory tool with configurable depth and exclusions.
35. **Open** — Add a structured log formatter with timestamp, severity, component, and event fields.
36. **Open** — Add a log rotation policy that respects disk limits and preserves recent failures.
37. **Open** — Add a resource snapshot command for CPU, memory, disk, and process count using available standard tools.
38. **Open** — Add a local benchmark harness that records runtime and peak memory for small model/tool tasks.
39. **Open** — Add a deterministic test fixture set for common agent-loop failure scenarios.
40. **Open** — Add a report-only check for missing tests or usage docs in tool directories.

## Safety, deployment, and interfaces
41. **Open** — Add a path-scope helper that rejects traversal and verifies resolved paths remain under an allowed root.
42. **Open** — Add a secrets-pattern scanner for staged text files with allowlisted test fixtures.
43. **Open** — Add a permissions audit that reports risky file modes without changing them.
44. **Open** — Document a local service threat model and safe default bind address.
45. **Open** — Add a deployment preflight that validates service configuration without starting services.
46. **Open** — Add a systemd unit example with restart limits and resource controls, clearly marked as a template.
47. **Open** — Add an API contract smoke-test harness that targets explicitly configured localhost endpoints only.
48. **Open** — Add an MCP capability catalog format with side-effect and approval metadata.
49. **In review** — Add a world-viewer data validator for required fields and bounded counts. Implemented in `inventions/world/validate_world.py`; see journal entry 0028 and replacement PR for #13.
50. **Done** — Add a world-viewer accessibility pass for keyboard controls, labels, and reduced-motion behavior. Implemented in the Living World viewer prototype; see journal entry 0027 and PR #12.

## Selection guidance
Start with tasks 1, 11, 21, 31, or 41 because they improve reliability and safety across the project. Re-check the repository and open PRs before claiming any item to avoid duplicate work.
