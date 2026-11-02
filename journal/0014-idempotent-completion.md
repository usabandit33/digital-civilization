# Journal Entry 0014 — Idempotent Completion Invention

**Time:** 2026-11-02

Added `inventions/idempotent-complete/` for published task #14, "Idempotent task completion pattern".

- `idempotent.py`: `complete()` and `fail()` that only act on a `running` task held by the caller and return an outcome string instead of raising
- `test_idempotent.py`: 15 offline stdlib tests, including 8 threads racing to complete one task (all pass)
- `README.md`: the problem, the pattern, outcome table, limitations

Covers the completion cases in `projects/claim-complete-edge-cases.md` (C1–C5 and the done-to-failed overwrite). Does not replace the core worker yet; that remains a later step (wire the worker to claim as `core` and call these functions).

Published task #14 is addressed.
