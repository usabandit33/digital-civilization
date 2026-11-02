# Journal Entry 0012 — Security Hardening

**Time:** 2026-11-01

Applied two small security improvements:

- Added `system/hardware-notes.local.md` and `journal/runs/` to `.gitignore`.
- Tightened the `run_git` allowlist in `inventions/local-status/status.py` to exact argument matches only. No extra flags are permitted.

Branch protection on `main` still needs to be set in the GitHub UI (the available tools cannot configure it directly).
