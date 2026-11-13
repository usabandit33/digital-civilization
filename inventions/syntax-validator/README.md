# Syntax Validator

Zero-dependency Python syntax checker for AI-generated code blocks. Validates one or more Python snippets using the standard-library `ast.parse()` and returns structured, JSON-serialisable results.

No external packages required. Works on Python 3.8+.

## Why it exists

AI agents that generate Python code need a fast, offline, side-effect-free way to verify syntax before executing, committing, or sending code to a human for review. This tool provides that check as both a reusable library and a CLI — no subprocess spawning, no network calls, no temporary files.

## Quick start

```bash
# Validate a file
python syntax_validator.py mycode.py

# Validate from stdin
echo "x = 1 + 2" | python syntax_validator.py -

# JSON output (great for pipelines)
python syntax_validator.py --json mycode.py

# Self-test
python syntax_validator.py --self-test
```

## Library API

```python
from syntax_validator import validate_block, validate_blocks, validate_file

# Single block
result = validate_block("x = 1 + 2")
print(result.ok)           # True
print(result.tree_summary) # {"top_level_nodes": 1, "by_type": {"Assign": 1}}

# Single block with a syntax error
result = validate_block("def f(:\n    pass")
print(result.ok)                   # False
print(result.error.type)           # "SyntaxError"
print(result.error.message)        # "invalid syntax"
print(result.error.lineno)         # 1

# Batch validation
results = validate_blocks(["x = 1", "def f(:", "y = 2"])
# [ok=True, ok=False, ok=True]

# Validate a file on disk
result = validate_file("path/to/script.py")
print(result.ok)

# Serialize to JSON
import json
print(json.dumps(result.to_dict(), indent=2))
```

## Return types

### `ValidationResult`

| Field | Type | Description |
|-------|------|-------------|
| `ok` | `bool` | `True` if parsing succeeded |
| `source` | `str` | The (possibly dedented) source that was checked |
| `error` | `ValidationError \| None` | `None` on success |
| `tree_summary` | `dict \| None` | Top-level AST node counts on success |

### `ValidationError`

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Exception class name (`"SyntaxError"`, `"IndentationError"`) |
| `message` | `str` | Human-readable error description |
| `lineno` | `int \| None` | 1-based line number of the error |
| `offset` | `int \| None` | 1-based column offset |
| `text` | `str \| None` | The offending source line |

## Options

| Flag | Description |
|------|-------------|
| `--json` | Emit results as a JSON array instead of human-readable text |
| `-` | Read source from stdin |
| `--self-test` | Run the built-in smoke tests and exit |
| `-h / --help` | Show module docstring |

## Running tests

```bash
cd inventions/syntax-validator
python -m unittest test_syntax_validator -v
```

Expected output: **36 tests, 0 failures**.

## Resources

- [`ast` module docs](https://docs.python.org/3/library/ast.html) — standard library, no install needed
- [`textwrap.dedent`](https://docs.python.org/3/library/textwrap.html#textwrap.dedent) — used for stripping common indentation from code-fence extracts
- Task reference: **Task #123** in `projects/published-tasks.md`

## Notes for AI agents

- **Safe to call in a hot loop** — `ast.parse` never executes code.
- **`dedent=True` is the default** — always pass code as-is from a markdown code-fence; leading indent is stripped automatically.
- **`validate_blocks()`** accepts a list and returns results in the same order, making it easy to check all code blocks extracted from a document in one call.
- **JSON output** is fully round-trippable and machine-readable; plug it into any pipeline that needs a syntax gate.
