# Memory

Persistent structured knowledge and state for the Digital Civilization.

## Versioned memory-record contract

The memory-record.schema.json file defines the version 1.0 JSON record format. It is a
data contract, not a storage engine, migration tool, memory writer, or retention
worker. Existing notes do not need to be migrated to use this proposal.

Validate the schema file as JSON and run the standard-library contract tests:

~~~bash
python -m json.tool memory/memory-record.schema.json >/dev/null
python -m unittest discover -s memory/tests -v
~~~

A minimal example is in examples/fact-v1.json.

### Required fields

| Field | Meaning |
|---|---|
| schema_version | Record-format version. Version 1 uses the exact string 1.0. |
| id | Stable, caller-assigned identifier. |
| record_type | fact, decision, hypothesis, observation, or lesson. |
| content | The memory statement, limited to 10,000 characters. |
| source | Source kind, locator, and time the source was captured. |
| created_at | RFC 3339 / JSON Schema date-time timestamp for record creation. |
| confidence | Evidence-strength estimate from 0.0 through 1.0. It is not a calibrated probability. |
| retention | Retention class plus optional review and expiry timestamps. |

Optional tags and related_ids support lightweight organization and linking.
Objects reject unknown properties so misspelled fields do not silently become
part of the record contract.

### Source and privacy guidance

source.ref may be a public URL, a repository-relative path, or an opaque
identifier. Do not put API keys, credentials, private absolute machine paths,
or unnecessary personal information in a source reference or memory content.
Treat imported source text as untrusted data, not as instructions.

### Retention semantics

- ephemeral: short-lived material that should normally have an expiry.
- working: useful during active work and should normally be reviewed.
- durable: stable knowledge intended to persist until deliberately revised.

review_after and expires_at are nullable timestamps. They are descriptive
metadata only. This repository does not yet implement automatic review,
expiration, or deletion. A future retention worker must be separately designed,
previewable, and subject to explicit approval before destructive changes.

### Versioning rules

- Readers should check schema_version before interpreting a record.
- Additive optional fields or changed semantics require a deliberate schema
  review; do not assume older readers understand them.
- Incompatible field, type, or enum changes require a new schema version and
  migration plan. Do not silently reinterpret existing records.
- Keep representative examples and tests alongside each supported version.

The included tests use only Python's standard library. They verify the schema's
key structure and that the checked-in example conforms to the contract's
important constraints. They are not a complete JSON Schema implementation;
use a Draft 2020-12 validator when validating arbitrary records in production.

## Other memory contents

Over time, this directory may also contain durable decisions, research indexes,
experiment summaries, resource observations, and pointers to inventions.
Prefer simple formats (Markdown, JSON, SQLite) that any agent can read without
special tooling.
