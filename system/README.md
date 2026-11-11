# System

Deployment, operations, and constraints for the Digital Civilization.

## Current contents

| File | Purpose |
|------|---------|
| `hardware-notes.md` | Authoritative resource budget and machine constraints |
| `setup.md` | Step-by-step setup instructions |
| `repo_preflight.py` | Read-only checkout readiness checks |
| `run_tests.py` | Discovers and runs each standard-library test suite separately |
| `systemd.example` | Example user systemd unit for continuous operation |

## Repository preflight

Run from any working directory by invoking the script with Python:

~~~bash
python system/repo_preflight.py
python system/repo_preflight.py --json
~~~

The command checks that Python 3.9 or newer is running, Git is installed and recognizes this checkout, the expected top-level directories exist, and the checkout root plus Git metadata directory appear writable.

- Exit code `0`: all checks passed.
- Exit code `1`: one or more checks failed, or the repository root could not be located.
- `--json`: emits a machine-readable object with an overall `ok` flag and individual check results.

The preflight uses only the Python standard library. It does not access the network, invoke a shell, create files, or modify the repository. Writable-state detection uses operating-system permission checks only. It is advisory and deliberately does not perform a write probe, so it cannot guarantee that every future file operation will succeed (for example, filesystem quotas or ACL changes may still intervene).

Run its tests from the repository root:

~~~bash
python -m unittest discover -s system/tests -v
~~~


## Repository test runner

Run from the repository root or another working directory:

~~~bash
python system/run_tests.py
python system/run_tests.py --json
python system/run_tests.py --timeout 180
~~~

The runner discovers Python files named `test*.py` and reports each project suite separately. Files directly inside a project directory belong to that directory's suite; files inside a directory named `tests` belong to the parent project suite. Known virtual environments, caches, build directories, and symlinked directories are skipped.

Each discovered test directory runs in its own Python process through `unittest discover`. The runner adds the project and repository roots to that process's import path, uses no shell, installs no packages, and makes no network calls itself. A suite has a 120-second timeout by default; `--timeout` accepts 1 to 3600 seconds. Captured output is bounded to the last 8,000 characters per suite.

- Exit code `0`: every discovered suite passed.
- Exit code `1`: one or more suites failed or timed out.
- Exit code `2`: the repository root could not be found or no test suites were discovered.
- `--json`: emits suite names, test-file counts, statuses, durations, return codes, and bounded output.

The runner does not modify repository files. Individual tests may create temporary files or start local-only test fixtures; review test code before running tests from an untrusted repository. The runner's own tests are included in the `system` suite.

## Design goals

- Stay runnable on ~8 GB RAM
- Survive reboots via systemd (user service preferred)
- Keep the core loop simple and observable
- Make it easy for a new agent to understand the runtime state
