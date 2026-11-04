# Recent Activity Summary

Dependency-free helper for a short brief from recent local journal/log files.

Run from the repository root:
```bash
python3 projects/recent-activity-summary/summarize_activity.py journal --limit 3
python3 -m unittest discover -s projects/recent-activity-summary/tests -v
```

Reads regular files in the supplied directory, newest first. It is read-only, ignores symlinks, bounds input/output, emits basenames rather than absolute paths, and redacts common credential-shaped values. Summaries are untrusted and should be reviewed before sharing externally.

Example:
```text
Recent activity (2 files)
- 0023-summary.md: Added a bounded activity summarizer; tests passed.
- 0022-notes.md: Documented the local validation workflow.
```
