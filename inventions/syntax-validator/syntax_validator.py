"""
syntax_validator.py — Zero-dependency Python syntax checker for AI-generated code.

Validates one or more Python code blocks using the standard-library `ast.parse()`
function and returns structured JSON-serialisable results.

No external packages required. Works on Python 3.8+.

Usage (CLI):
    python syntax_validator.py <file.py>          # validate a file
    python syntax_validator.py -                  # read code from stdin
    python syntax_validator.py --self-test        # run built-in smoke tests

Usage (library):
    from syntax_validator import validate_block, validate_blocks

    result = validate_block("x = 1 + 2")
    # {"ok": True, "source": "x = 1 + 2", "error": null}

    results = validate_blocks(["x = 1", "def f(:\n  pass"])
    # [{"ok": True, ...}, {"ok": False, "error": {"type": "SyntaxError", ...}}]
"""

from __future__ import annotations

import ast
import json
import sys
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------

@dataclass
class ValidationError:
    type: str          # e.g. "SyntaxError", "IndentationError"
    message: str
    lineno: Optional[int] = None
    offset: Optional[int] = None
    text: Optional[str] = None   # the offending source line, if available

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "message": self.message,
            "lineno": self.lineno,
            "offset": self.offset,
            "text": self.text,
        }


@dataclass
class ValidationResult:
    ok: bool
    source: str
    error: Optional[ValidationError] = field(default=None)
    # Populated only on success
    tree_summary: Optional[dict] = field(default=None)

    def to_dict(self) -> dict:
        d: dict = {
            "ok": self.ok,
            "source": self.source,
            "error": self.error.to_dict() if self.error else None,
        }
        if self.tree_summary is not None:
            d["tree_summary"] = self.tree_summary
        return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_block(source: str, *, dedent: bool = True, filename: str = "<string>") -> ValidationResult:
    """
    Validate a single Python code block.

    Parameters
    ----------
    source : str
        Python source code to validate.
    dedent : bool
        If True (default), strip common leading whitespace before parsing.
        Useful when the code was extracted from a markdown code-fence and
        is indented relative to the surrounding prose.
    filename : str
        Filename shown in error messages (cosmetic only).

    Returns
    -------
    ValidationResult
        .ok       — True if the code parses without errors.
        .source   — The (possibly dedented) source that was checked.
        .error    — None on success, ValidationError on failure.
        .tree_summary — dict with top-level statement counts on success.
    """
    if dedent:
        source = textwrap.dedent(source)

    try:
        tree = ast.parse(source, filename=filename, mode="exec")
    except SyntaxError as exc:
        # IndentationError is a subclass of SyntaxError
        return ValidationResult(
            ok=False,
            source=source,
            error=ValidationError(
                type=type(exc).__name__,
                message=exc.msg,
                lineno=exc.lineno,
                offset=exc.offset,
                text=exc.text.rstrip("\n") if exc.text else None,
            ),
        )

    return ValidationResult(
        ok=True,
        source=source,
        error=None,
        tree_summary=_summarise_tree(tree),
    )


def validate_blocks(sources: List[str], **kwargs) -> List[ValidationResult]:
    """
    Validate multiple Python code blocks.

    Parameters
    ----------
    sources : list[str]
        List of source strings to validate, one per block.
    **kwargs
        Forwarded to :func:`validate_block`.

    Returns
    -------
    list[ValidationResult]
        One result per input block, in the same order.
    """
    return [validate_block(s, **kwargs) for s in sources]


def validate_file(path: str) -> ValidationResult:
    """
    Validate a Python source file on disk.

    Parameters
    ----------
    path : str
        File path to read and validate.

    Returns
    -------
    ValidationResult
        Result of parsing the file's contents.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        return ValidationResult(
            ok=False,
            source="",
            error=ValidationError(
                type="IOError",
                message=str(exc),
            ),
        )
    return validate_block(source, dedent=False, filename=path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _summarise_tree(tree: ast.Module) -> dict:
    """Return a lightweight count of top-level AST node types."""
    counts: dict[str, int] = {}
    for node in ast.iter_child_nodes(tree):
        name = type(node).__name__
        counts[name] = counts.get(name, 0) + 1
    return {"top_level_nodes": len(list(ast.iter_child_nodes(tree))), "by_type": counts}


# ---------------------------------------------------------------------------
# Built-in smoke tests
# ---------------------------------------------------------------------------

_SMOKE_TESTS = [
    # (description, source, expect_ok)
    ("empty string",           "",                                       True),
    ("simple assignment",      "x = 1",                                  True),
    ("function definition",    "def f():\n    return 42",                True),
    ("class definition",       "class A:\n    pass",                     True),
    ("import statement",       "import os\nimport sys",                  True),
    ("syntax error",           "def f(:\n    pass",                      False),
    ("indentation error",      "if True:\npass",                         False),
    ("unclosed paren",         "x = (1 + 2",                             False),
    ("missing colon",          "def f()\n    pass",                      False),
    ("multi-statement ok",     "x = 1\ny = 2\nz = x + y",               True),
]


def _run_smoke_tests() -> bool:
    """Run built-in smoke tests. Returns True if all pass."""
    failures = 0
    for desc, src, expect_ok in _SMOKE_TESTS:
        result = validate_block(src)
        if result.ok != expect_ok:
            print(f"FAIL  [{desc}]: expected ok={expect_ok}, got ok={result.ok}")
            if result.error:
                print(f"       Error: {result.error.type}: {result.error.message}")
            failures += 1
        else:
            status = "PASS"
            detail = ""
            if not result.ok and result.error:
                detail = f"  ({result.error.type}: {result.error.message})"
            print(f"{status}  [{desc}]{detail}")

    if failures:
        print(f"\n{failures}/{len(_SMOKE_TESTS)} smoke tests FAILED.")
    else:
        print(f"\nAll {len(_SMOKE_TESTS)} smoke tests passed.")
    return failures == 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv[0] == "--self-test":
        return 0 if _run_smoke_tests() else 1

    if argv[0] == "--json":
        # --json <file>  or  --json -  (stdin)
        targets = argv[1:]
    else:
        targets = argv
        json_mode = False

    json_mode = "--json" in argv or argv[0] == "--json"

    results = []
    for target in [t for t in targets if t != "--json"]:
        if target == "-":
            source = sys.stdin.read()
            result = validate_block(source, dedent=False, filename="<stdin>")
        else:
            result = validate_file(target)
        results.append(result)

    if json_mode:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        exit_code = 0
        for r in results:
            if r.ok:
                name = r.source.splitlines()[0][:60] if r.source else "(empty)"
                print(f"OK   {name!r}...")
            else:
                exit_code = 1
                err = r.error
                loc = f" (line {err.lineno}, col {err.offset})" if err.lineno else ""
                print(f"ERR  {err.type}: {err.message}{loc}")
                if err.text:
                    print(f"     >>> {err.text}")
        return exit_code

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
