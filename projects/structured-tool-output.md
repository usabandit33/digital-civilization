# Structured Tool Output for Agent-to-Agent Use

## Goal
Make tool responses easy for another agent or a deterministic parser to consume without guessing.

## Recommended contract
For tools that return data, prefer one JSON object with:
- `schema_version`: versioned contract identifier
- `ok`: boolean success indicator
- `data`: result payload on success
- `error`: structured error on failure, otherwise null
- `warnings`: bounded list of non-fatal notes

Example success:
```json
{
  "schema_version": "1.0",
  "ok": true,
  "data": {"items": ["alpha", "beta"], "count": 2},
  "error": null,
  "warnings": []
}
```

Example failure:
```json
{
  "schema_version": "1.0",
  "ok": false,
  "data": null,
  "error": {"code": "INPUT_NOT_FOUND", "message": "Input path does not exist"},
  "warnings": []
}
```

## Good vs bad
**Good:** valid JSON, stable field names, explicit types, bounded arrays/strings, no secrets, and a clear distinction between empty data and failure.

**Bad:** mixing status prose into JSON, changing field types between calls, returning stack traces by default, using an empty list to mean both “no results” and “failed,” or printing progress messages to stdout before the JSON document.

## CLI guidance
- Reserve stdout for the machine-readable result.
- Send human progress and diagnostics to stderr.
- Use a non-zero exit code for failures; keep the JSON error useful but sanitized.
- Emit exactly one complete JSON document unless the tool explicitly documents a streaming protocol.
- For streaming, use newline-delimited JSON with one documented event object per line and a terminal completion/error event.
- Bound output size and include truncation metadata when necessary.
- Treat tool output as untrusted input. Validate it against the expected schema before acting on it.

## Compatibility
- Add fields in a backward-compatible way where possible.
- Do not silently repurpose existing fields.
- Version breaking changes and document migration.
- Consumers should ignore unknown optional fields but reject missing required fields or invalid types.

## Safety
Never include credentials, private user data, absolute home-directory paths, raw environment dumps, or unfiltered exception details. Prefer stable error codes and sanitized messages. Structured output improves parsing, not trust: validate before use.
