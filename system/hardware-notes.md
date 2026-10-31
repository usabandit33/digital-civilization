# Hardware & Resource Notes

**This file is intentionally generic.**

Do not commit machine-specific diagnostics, hostnames, usernames, IP addresses, or other personal environment details to the public repository.

## Design Constraints (public)

The Digital Civilization is designed to remain viable on constrained hardware:

- Limited RAM (target class: ~8 GB)
- Modest CPU (older dual-core / low single-thread performance)
- CPU-only inference expected
- Prefer one model loaded at a time
- Prefer SQLite + files over large in-memory stores
- Queue work instead of running many heavy tasks concurrently
- Keep context windows modest

## Local (private) notes

If you need to record real machine details for your own use, keep them outside the public repo (for example in a private local file that is gitignored, or in a private fork).

Suggested local-only file name: `system/hardware-notes.local.md` (already covered by common ignore patterns if you add it).

## Runtime Rules

- One model at a time when resources are tight
- Monitor memory before launching browser automation or multiple services
- Prefer small, tested tools over large always-on processes
- Re-evaluate limits whenever the host machine changes
