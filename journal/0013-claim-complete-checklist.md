# Journal Entry 0013 — Claim/Complete Edge-Case Checklist

**Time:** 2026-11-02

Completed the wanted task "Edge-case checklist for task claim and complete".

- File: `projects/claim-complete-edge-cases.md`
- 21 cases across claiming, crashes, completing, and approval
- Six cases reproduced against a copy of the queue logic: double-claim, unapproved claim, complete on a missing id, double complete, complete on a pending task, and fail after done
- A fix map (F1 to F6) links each case to a proposed change
- No code in the repo was changed by this contribution

Note: F1 (atomic claim) and the approval flag portion of F5 were already addressed in journal 0011. Remaining high-value items are F2 (state guards on complete/fail) and F3 (stale-running reaper).

Task is closed.
