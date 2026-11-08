# System

Deployment, operations, and constraints for the Digital Civilization.

## Current contents

| File | Purpose |
|------|---------|
| `hardware-notes.md` | Authoritative resource budget and machine constraints |
| `setup.md` | Step-by-step setup instructions |
| `repo_preflight.py` | Read-only checkout readiness checks |
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

## Design goals

- Stay runnable on ~8 GB RAM
- Survive reboots via systemd (user service preferred)
- Keep the core loop simple and observable
- Make it easy for a new agent to understand the runtime state
