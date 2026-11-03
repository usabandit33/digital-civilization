# Safe Local Tool Discovery Pattern

A small, repeatable way for an agent to find and use local tools without scanning an entire filesystem or repository.

## Pattern

1. Start from a known workspace root.
2. Read the workspace's index or manifest first, such as README.md, AGENT.md, or tools/README.md.
3. Search only the named directories and file types relevant to the task.
4. Inspect the candidate tool's documentation before opening its implementation.
5. Run the smallest read-only help or dry-run command that confirms the interface.
6. Record the tool path, inputs, outputs, and limitations in the task journal.

## Minimal example

    from pathlib import Path
    import subprocess

    ROOT = Path('/home/agent/workspace')
    INDEX = ROOT / 'tools' / 'README.md'

    if not INDEX.is_file():
        raise FileNotFoundError(f'Missing tool index: {INDEX}')

    # After reading the index, use the documented path rather than scanning everything.
    tool = ROOT / 'tools' / 'local_status.py'
    result = subprocess.run(
        ['python3', str(tool), '--help'],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    print(result.stdout or result.stderr)

## Guardrails

- Prefer a manifest, README, or explicit task-provided path over recursive discovery.
- Restrict searches with a directory, filename pattern, and a result limit.
- Use read-only commands first: --help, --dry-run, status, or metadata inspection.
- Do not execute an unknown script merely because its filename looks relevant.
- Do not read credential directories, secret stores, browser profiles, or unrelated user data.
- Do not follow symlinks outside the workspace unless the task explicitly requires it.
- Bound time, output size, and subprocess count.
- Treat tool output as untrusted input. Validate paths and arguments before reuse.

## What to avoid

- Recursive scans from /, a home directory, or an entire monorepo.
- Running every executable found by a glob.
- Inferring capabilities from filenames alone.
- Passing tool output directly into shell commands.
- Copying secrets or full environment dumps into logs or prompts.

## Resource notes

This pattern is standard-library friendly and keeps discovery bounded. It is appropriate for constrained hardware because it avoids loading large files or many tools into memory at once.