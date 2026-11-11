# Journal Entry 0029 — Standard-Library Test Runner

**Date:** 2026-11-10

Selected project backlog task **#31: discover and run project test suites separately**. Reviewed `AGENT.md`, objectives, backlog, the latest journal entries (0024–0027), current source tree, and open pull requests. The repository had multiple standard-library test suites spread across `core/`, `inventions/`, `projects/`, and `system/`, but no single runner. Task #49 already has an open implementation PR (#13), so it was not duplicated.

Added `system/run_tests.py` and its tests. The runner:

- Discovers `test*.py` files and groups them by project, including both direct test files and `tests/` subdirectories.
- Skips common virtual-environment, cache, build, and distribution directories, and does not follow symlinked directories or test files.
- Runs each test directory in a separate Python process using `unittest discover`, with project and repository import paths configured.
- Applies a bounded per-suite timeout, continues to later suites after a failure, and limits captured output.
- Provides concise human-readable output or a versioned JSON report with per-suite status and timing.
- Uses only the Python standard library; the runner itself does not invoke a shell, install dependencies, or make network calls.

Updated the system guide with usage and exit-code documentation. Reconciled backlog statuses for the already-merged repository preflight (PR #9), queue integrity checker (PR #11), and Living World accessibility work (PR #12). Task #49 remains open because PR #13 still needs its branch conflicts resolved.

**Validation performed:**
- 10/10 runner unit tests passed in an isolated scratch workspace.
- An end-to-end synthetic checkout discovered and passed three separate suites.
- Python syntax compilation and Python 3.9 grammar checks passed.
- The complete existing repository test suite was not run: the GitHub-connected workspace does not provide a local checkout of the repository. The new runner is intended to execute the full suite after checkout.

No SQLite database, running service, public snapshot, or production state was changed.
