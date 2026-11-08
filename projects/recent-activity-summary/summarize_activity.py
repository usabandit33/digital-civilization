#!/usr/bin/env python3
"""Create a bounded, privacy-conscious brief from recent local text files."""
import argparse
import re
from pathlib import Path

MAX_FILE_BYTES = 32_000
MAX_TOTAL_BYTES = 96_000
MAX_EXCERPT_CHARS = 320
PATTERNS = (
    re.compile(r"(?i)(api[_ -]?key|access[_ -]?token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(authorization\s*:\s*bearer)\s+[^\s]+"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
)

def redact(text):
    for pattern in PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) + "= [REDACTED]") if m.lastindex else "[REDACTED]", text)
    return text

def summarize(directory: Path, limit=5):
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not directory.exists() or not directory.is_dir():
        raise ValueError("input must be an existing directory")
    candidates = []
    for path in directory.iterdir():
        try:
            if path.is_symlink() or not path.is_file():
                continue
            candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    candidates.sort(key=lambda item: item[0], reverse=True)
    entries, total = [], 0
    for _, path in candidates:
        if len(entries) >= limit or total >= MAX_TOTAL_BYTES:
            break
        try:
            raw = path.read_bytes()[:MAX_FILE_BYTES]
        except OSError:
            continue
        total += len(raw)
        lines = [line.strip() for line in raw.decode("utf-8", errors="replace").splitlines() if line.strip()]
        if not lines:
            continue
        excerpt = re.sub(r"\s+", " ", redact(" ".join(lines)))[:MAX_EXCERPT_CHARS]
        entries.append(f"- {path.name}: {excerpt}")
    if not entries:
        return "Recent activity: no readable text files found."
    return f"Recent activity ({len(entries)} files)\n" + "\n".join(entries)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        print(summarize(args.directory, args.limit))
    except ValueError as exc:
        parser.error(str(exc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
