# Placeholder Comment Scanner

A read-only, standard-library tool for finding unfinished-work markers in explicitly supplied Python source files. It helps an agent catch comments such as `TODO`, `FIXME`, or `PLACEHOLDER` before presenting a change for review.

## Quick start

From the repository root:

```bash
python inventions/placeholder-comment-scanner/placeholder_scanner.py path/to/module.py
python inventions/placeholder-comment-scanner/placeholder_scanner.py --json path/to/module.py
python inventions/placeholder-comment-scanner/placeholder_scanner.py --marker REVIEW path/to/module.py
```

The command accepts one or more explicit file paths. It does not recurse into directories, modify files, execute source code, invoke subprocesses, or access the network.

## Library API

```python
import sys
sys.path.insert(0, "inventions/placeholder-comment-scanner")

from placeholder_scanner import scan_source, scan_file

findings = scan_source("value = 1  # TODO: finish\n")
for finding in findings:
    print(finding.path, finding.line, finding.column, finding.marker)

findings = scan_file("path/to/module.py")
```

`scan_source()` and `scan_file()` return `Finding` objects with a path, 1-based line and column, and normalized marker name. A `SourceTokenizationError` is raised when the source cannot be tokenized completely.

## Default markers

- `TODO`
- `FIXME`
- `XXX`
- `HACK`
- `PLACEHOLDER`

Use `--marker NAME` to add one or more marker names for a CLI run. Marker matching is case-insensitive and requires identifier boundaries, so `TODOLIST` and `MYTODO` do not match `TODO`.

## Output and exit codes

The JSON report uses schema version `1.0` and contains `ok`, file counts, findings, and read/tokenization errors. It deliberately reports only marker locations and names, not the full comment text, to avoid copying arbitrary source text into logs.

| Exit code | Meaning |
|---|---|
| `0` | All requested files were scanned and no markers were found |
| `1` | At least one marker was found |
| `2` | One or more files could not be read/tokenized, or marker configuration was invalid |

An error takes precedence over findings and returns `2` so callers do not mistake a partial scan for a clean result.

## Scope and limitations

- Only Python `COMMENT` tokens are scanned. Markers in strings, docstrings, Markdown, YAML, or other file types are intentionally ignored.
- This is a review aid, not a proof of correctness. A clean scan does not mean code is complete, secure, or tested.
- Some projects intentionally keep TODO comments. Treat findings as a review gate for the submitted change, not a reason to delete useful backlog notes throughout a repository.
- The scanner reads only paths explicitly supplied by the caller. It does not discover files or traverse directories.
- It uses Python's tokenizer and standard library only; no third-party packages are required.

## Tests

```bash
cd inventions/placeholder-comment-scanner
python -m unittest discover -s tests -p 'test_*.py' -v
```

Task reference: **Task #127** in `projects/published-tasks.md`.
