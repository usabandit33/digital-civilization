#!/usr/bin/env python3
"""Generate a deterministic Markdown index for numbered journal entries."""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


ENTRY_NAME_RE = re.compile(
    r"^(?P<number>\d{4})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md$",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^\s*#\s+(.+?)\s*$")
DATE_FIELD_RE = re.compile(
    r"^\s*\*{0,2}Date\s*:?\*{0,2}\s*:?\s*(.*?)\s*$", re.IGNORECASE
)
TOPICS_FIELD_RE = re.compile(
    r"^\s*\*{0,2}Topics?\s*:?\*{0,2}\s*:?\s*(.*?)\s*$", re.IGNORECASE
)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


@dataclass(frozen=True)
class JournalEntry:
    """Small, display-safe description of one journal entry."""

    number: int
    filename: str
    title: str
    entry_date: Optional[date]
    topics: Tuple[str, ...]


def _field_value(text: str, pattern: re.Pattern) -> Optional[str]:
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    match = ISO_DATE_RE.search(value)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _parse_topics(value: Optional[str], slug: str) -> Tuple[str, ...]:
    candidates = (
        [part.strip() for part in re.split(r"[,;|]", value) if part.strip()]
        if value
        else [slug.replace("-", " ").title()]
    )
    unique = []
    seen = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def _escape_inline(value: str) -> str:
    """Escape Markdown punctuation in metadata and heading text."""
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>])", r"\\\1", " ".join(value.split()))


def _read_entry(path: Path, number: int, slug: str) -> JournalEntry:
    content = path.read_text(encoding="utf-8")
    title = None
    for line in content.splitlines():
        match = HEADING_RE.match(line)
        if match:
            title = match.group(1).strip()
            break
    if not title:
        title = slug.replace("-", " ").title()

    raw_date = _field_value(content, DATE_FIELD_RE)
    raw_topics = _field_value(content, TOPICS_FIELD_RE)
    return JournalEntry(
        number=number,
        filename=path.name,
        title=title,
        entry_date=_parse_date(raw_date),
        topics=_parse_topics(raw_topics, slug),
    )


def collect_entries(journal_dir: Path) -> List[JournalEntry]:
    """Read numbered Markdown entries directly inside journal_dir.

    Non-entry files, directories, and symlinks are ignored. No files are
    created, changed, or removed.
    """
    journal_dir = Path(journal_dir)
    if not journal_dir.exists() or not journal_dir.is_dir():
        raise ValueError("journal directory does not exist or is not a directory")

    entries = []
    for path in journal_dir.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        match = ENTRY_NAME_RE.fullmatch(path.name)
        if not match:
            continue
        entries.append(
            _read_entry(path, int(match.group("number")), match.group("slug"))
        )

    # Dated entries first, newest first. Undated entries follow by sequence.
    entries.sort(
        key=lambda entry: (
            entry.entry_date is not None,
            entry.entry_date or date.min,
            entry.number,
            entry.filename.casefold(),
        ),
        reverse=True,
    )
    return entries


def render_index(entries: Sequence[JournalEntry]) -> str:
    """Render a stable Markdown index grouped by date and by topic."""
    lines = [
        "# Journal Index",
        "",
        "Generated from numbered journal entries by "
        "`inventions/journal-index/journal_index.py`.",
        "",
        "## By date",
        "",
        "| Date | Topic(s) | Entry |",
        "| --- | --- | --- |",
    ]

    if not entries:
        lines.extend(["", "_No numbered journal entries found._", ""])
        return "\n".join(lines)

    for entry in entries:
        shown_date = entry.entry_date.isoformat() if entry.entry_date else "Undated"
        topics = ", ".join(_escape_inline(topic) for topic in entry.topics)
        title = _escape_inline(entry.title)
        lines.append(
            "| {0} | {1} | [{2}]({3}) |".format(
                shown_date, topics, title, entry.filename
            )
        )

    topic_entries = {}
    topic_labels = {}
    for entry in entries:
        for topic in entry.topics:
            key = topic.casefold()
            topic_entries.setdefault(key, []).append(entry)
            topic_labels.setdefault(key, topic)

    lines.extend(["", "## By topic", ""])
    for key in sorted(topic_entries):
        lines.append("### " + _escape_inline(topic_labels[key]))
        for entry in topic_entries[key]:
            shown_date = entry.entry_date.isoformat() if entry.entry_date else "Undated"
            title = _escape_inline(entry.title)
            lines.append("- {0} · [{1}]({2})".format(shown_date, title, entry.filename))
        lines.append("")

    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a read-only Markdown index of numbered journal entries."
    )
    default_dir = Path(__file__).resolve().parents[2] / "journal"
    parser.add_argument(
        "--journal-dir",
        type=Path,
        default=default_dir,
        help="journal directory to scan (default: repository journal/)",
    )
    args = parser.parse_args(argv)

    try:
        entries = collect_entries(args.journal_dir)
        sys.stdout.write(render_index(entries))
    except (OSError, UnicodeError, ValueError) as exc:
        print("journal-index: {0}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
