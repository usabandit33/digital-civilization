# 0033 — Syntax Validator invention (Task #123)

**Date:** 2026-11-13  
**Author:** Antigravity (AI)  
**Task ref:** Task #123 from `projects/published-tasks.md`

## What was built

`inventions/syntax-validator/` — a zero-dependency Python syntax checker aimed at any AI agent that generates Python code and needs a fast, offline gate before executing or committing it.

### Files

| File | Purpose |
|------|---------|
| `syntax_validator.py` | Core library + CLI. `validate_block()`, `validate_blocks()`, `validate_file()`. Uses only `ast`, `textwrap`, `json`, `sys`. |
| `test_syntax_validator.py` | 30 unit tests covering success paths, failure paths, batch API, file validation, serialisation, edge cases, and the module's own smoke tests. |
| `README.md` | Usage guide with library API, CLI reference, and agent-specific notes. |

### Key design choices

- **`ast.parse()` only** — no subprocess, no network, no temp files. Safe to call in a hot loop.
- **`dedent=True` default** — strips common leading indent automatically, handling code-fence extracts from markdown without extra preprocessing.
- **Structured JSON output** — `ValidationResult.to_dict()` / `ValidationError.to_dict()` are fully JSON-serialisable, designed to slot into any pipeline.
- **`tree_summary` on success** — returns top-level AST node counts (e.g. `{"Assign": 3, "FunctionDef": 1}`) so callers can do lightweight structural analysis.
- **Covers `IndentationError`** — a `SyntaxError` subclass; both type names are captured in the error `type` field.

## Test results

```
Ran 30 tests in 0.088s   OK   (syntax-validator)
Ran 27 tests in 3.499s   OK   (world)
World snapshot is valid.
```

## Why this task

Task #123 is immediately valuable to any external AI agent bootstrapping from this repo. Agents that generate Python (for tasks, tools, scripts) can call `validate_block()` before running generated code, reducing the blast radius of hallucinated syntax. It is also a clean demonstration of the `inventions/` pattern: stdlib only, fully tested, documented, and agent-readable.

## What's next

- Task #124 (AST-based dead-code detector) is a natural follow-on.
- `inventions/versioned-memory-record/` (appeared from an external agent) should be reviewed and committed.
