# Path Output Sanitizer

A small, standard-library-only helper for removing configured absolute directory roots from tool output before it is logged, shared, or returned to another agent.

## Why it exists

Absolute paths can disclose local usernames, machine layout, project locations, and private directory names. This helper replaces known roots such as a user's home directory with ~ while keeping useful relative suffixes.

## Python usage

    from path_sanitizer import sanitize_text, sanitize_value

    safe_message = sanitize_text(
        "Wrote /home/alice/projects/report.json",
        roots=["/home/alice"],
    )
    # "Wrote ~/projects/report.json"

    safe_result = sanitize_value(
        {"files": ["C:\\Users\\Alice\\Desktop\\report.txt"]},
        roots=[r"C:\Users\Alice"],
    )
    # {"files": ["~\\Desktop\\report.txt"]}

If roots is omitted, known home roots from Path.home(), HOME, and USERPROFILE are used. Pass roots=[] to disable default discovery. Windows roots match case-insensitively and accept either slash style. Relative paths are unchanged. For nested JSON-like data, string values are sanitized recursively; mapping keys and non-string values are preserved.

## JSON stdin/stdout CLI

    printf '{"path":"/home/alice/work/file.txt"}\n' \
      | python path_sanitizer.py --root /home/alice

The CLI reads one JSON value from stdin and writes one sanitized JSON value to stdout. Repeat --root to add roots. Invalid JSON returns exit code 2, writes a generic parse error to stderr, and does not echo the input.

## Safety and limits

- No network access, subprocesses, file writes, or environment changes.
- Only configured roots are replaced. This is not a general secret scanner and does not discover every private path.
- Mapping keys are intentionally unchanged to avoid silently changing field names or creating key collisions.
- Sanitize at the output boundary, before logs, API responses, or public artifacts are persisted.
- Review custom roots before sharing output. A path outside the configured roots may still reveal private information.

## Tests

From this directory:

    python -m unittest discover -s tests -v

The implementation and tests use only the Python standard library.
