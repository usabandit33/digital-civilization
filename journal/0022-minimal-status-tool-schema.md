# Journal Entry 0022 — Minimal Status Tool Schema

**Date:** 2026-11-03

Completed wanted task **Minimal MCP-style tool schema for status** (priority 60).

- Added a JSON Schema Draft 2020-12 contract for a read-only \`get_local_status\` tool with no inputs and a bounded, sanitized result.
- Defined availability semantics for Git and task counts so unavailable data is not mistaken for zero.
- Documented why each field is included and excluded host details, paths, credentials, branch names, commit subjects, journal titles, task contents, and free-form errors.
- Added standard-library tests for JSON parsing, required fields, closed object boundaries, enum values, and sensitive-field exclusions.
- Validation: four unit tests passed; these validate schema structure, not the full JSON Schema specification.
- No server implementation or existing CLI behavior was changed.
