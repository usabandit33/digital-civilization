# Minimal Status Tool Schema

This is a contract proposal for an MCP-style read-only tool named \`get_local_status\`. It describes the tool boundary only. It does not implement an MCP server or change the existing local status CLI.

## Files

- \`status-tool.schema.json\`: JSON Schema (Draft 2020-12) describing the tool metadata, empty input, and sanitized output.
- \`test_status_schema.py\`: standard-library checks for schema structure and the documented example.

## Contract

The tool accepts no arguments. Its result contains:

- \`schema_version\`: contract version, currently \`1.0\`
- \`status\`: \`ok\`, \`partial\`, or \`unavailable\`
- \`repository\`: fixed repository identifier
- \`git\`: whether Git status was readable and whether the worktree is dirty
- \`tasks\`: whether task counts were readable and non-negative counts for four known states

If Git cannot be read, \`git.dirty\` must be \`null\`. If the task database cannot be read, set \`tasks.available\` to false and report zero counts; consumers must treat those counts as unavailable, not as proof that no tasks exist. Use \`status=ok\` only when both sources are available, \`partial\` when exactly one is available, and \`unavailable\` when neither is available.

## Example result

~~~json
{
  "schema_version": "1.0",
  "status": "ok",
  "repository": "digital-civilization",
  "git": {
    "available": true,
    "dirty": false
  },
  "tasks": {
    "available": true,
    "pending": 2,
    "running": 1,
    "done": 18,
    "failed": 0
  }
}
~~~

The counts above are illustrative, not live repository data.

## Safety rationale

| Field | Why it is safe / useful |
|---|---|
| \`schema_version\` | Lets callers reject unsupported contract versions without exposing host details. |
| \`status\` | A bounded enum communicates availability without leaking exception text. |
| \`repository\` | A fixed logical identifier avoids returning an absolute path or hostname. |
| \`git.available\`, \`git.dirty\` | Exposes only whether Git can be queried and whether changes exist. |
| \`tasks.available\` and counts | Gives operational queue totals without exposing task titles, prompts, results, or database paths. |

The schema intentionally excludes usernames, hostnames, IP addresses, absolute paths, environment variables, credentials, branch names, commit messages, journal titles, task contents, and free-form error strings. Do not add those fields casually: they can disclose personal or operational information and are not necessary for a basic health snapshot.

## Status semantics

- **ok**: both Git and task counts were read successfully.
- **partial**: one source was unavailable.
- **unavailable**: neither source was available.

A caller must not interpret unavailable task counts as zero work. Availability is separate from the count values.

## Validation

Run from the repository root:

~~~bash
python -m unittest discover -s projects/minimal-status-tool-schema -p 'test_*.py' -v
~~~

The checks use only Python's standard library. They verify JSON parsing, required schema structure, restrictive object boundaries, and the example payload's basic types. They are not a full JSON Schema validator.

## Non-goals

- No MCP server, transport, authentication, or network listener.
- No changes to the existing \`inventions/local-status/\` implementation.
- No claim that this contract is already implemented by a callable tool.
