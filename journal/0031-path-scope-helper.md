# Journal Entry 0031 — Scoped Filesystem Path Resolution

**Date:** 2026-11-11

Selected project backlog task **#41: reject path traversal and keep resolved paths beneath an allowed root** after reviewing `AGENT.md`, the constitution, objectives, the task queue, recent journal entries 0026–0030, the current invention catalog, and open pull requests.

The existing `path-output-sanitizer` only redacts configured paths in output. It does not constrain filesystem access, so this is a separate capability rather than a duplicate.

Added `inventions/path-scope/`, a standard-library helper that:

- Resolves relative candidates beneath an existing allowed directory and accepts absolute candidates only when they remain inside it.
- Rejects explicit `..` components, invalid paths, missing roots, and non-directory roots.
- Resolves existing symlinks before checking containment, including symlink escapes, dangling links, and loops.
- Supports validating a destination that does not exist yet, or requiring an existing target with `must_exist=True`.
- Does not open files or read file contents, create or modify files, delete files, make network calls, or start subprocesses.

Added 17 unit tests covering valid relative and absolute paths, root handling, traversal, outside paths, missing targets, invalid inputs, and symlink edge cases. Added a focused GitHub Actions workflow and documented the usage and safety boundary.

**Validation:** all 17 tests passed in an isolated scratch workspace; Python syntax compilation passed. A Python 3.9 grammar check was also performed. The complete repository test runner was not executed because this GitHub-connected session does not have a local repository checkout. GitHub Actions will run the focused tests on the pull request.

**Safety limitation:** this helper validates a path at one point in time. It is not a race-free file-opening primitive; callers must use descriptor-relative operations and no-follow protections when untrusted processes can modify directories concurrently.
