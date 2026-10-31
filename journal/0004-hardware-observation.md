# Journal Entry 0004 — Hardware Observation

**Date:** 2026-10-31

**Summary:** First real diagnostics captured (from Windows + Git Bash).

## Findings

- The commands were executed in Git Bash on Windows, not on the intended old Linux laptop.
- Ollama is present (v0.40.13) with multiple models, including `qwen3.5:4b` (3.3 GB).
- Standard Linux resource tools are unavailable in this environment.
- Python 3.14.6 is available.

## Implications

- Development and early testing are currently happening on a stronger Windows machine.
- The architecture must still target the constrained Linux laptop as the eventual always-on host.
- `system/hardware-notes.md` has been updated to record both the observed Windows environment and the original Linux target constraints.

## Next

- When the Linux laptop is available, re-run full diagnostics and update the hardware notes with real RAM/CPU/swap figures.
- Continue Phase 1 work (first real invention / tools) using `qwen3.5:4b` as a sensible default model.
