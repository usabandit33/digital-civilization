# Path Scope Helper

A dependency-free helper for resolving a filesystem path beneath an allowed directory.

## Usage

```python
from path_scope import PathScopeError, resolve_scoped_path

try:
    destination = resolve_scoped_path(
        "/srv/agent-data",
        "reports/daily.json",
    )
except PathScopeError:
    # Reject the request without logging the untrusted path input.
    raise

# destination is an absolute, resolved pathlib.Path.
```

Relative paths are interpreted beneath the allowed root. Absolute paths are accepted only when their resolved destination remains beneath it. Explicit `..` components are rejected, and existing symlinks are resolved before the containment check. The root must already exist and be a directory. The destination may be missing by default; pass `must_exist=True` when it must already exist. The helper raises `PathScopeError` for invalid roots, invalid paths, missing required targets, symlink loops, and paths that escape the root.

## Validation

Run from this directory:

```bash
python -m unittest discover -s tests -v
```

The implementation and tests use only the Python standard library. Tests use temporary directories and do not touch user data.

## Safety boundary

This helper does not open files or read their contents, and it does not create, modify, or delete files. It only checks filesystem metadata and resolves paths. It validates a path at one point in time. It does **not** make a later check-then-open sequence race-free: another process could replace a symlink after validation. Do not rely on it alone when untrusted processes can modify directories concurrently. In that threat model, use descriptor-relative filesystem operations and platform-specific no-follow protections.

Path parsing follows the host operating system. This is a local filesystem helper, not a URL decoder or archive-extraction sanitizer. Callers must separately handle encoded paths and archive member names before converting them to filesystem paths.
