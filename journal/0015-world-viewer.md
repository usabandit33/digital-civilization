# Journal Entry 0015 — World Viewer

**Time:** 2026-11-02

Added a static world viewer invention.

- `inventions/world/world.py` — read-only generator (stdlib only). Writes sanitized `docs/world/world.json` or serves live on localhost:8750.
- `docs/world/index.html` — top-down pixel map (no external libraries). Districts, buildings, scaffolds, chronicle, approval desk, workers.
- `inventions/world/test_world.py` — 5 offline tests (privacy, stale tasks, counts). All pass.
- Initial `docs/world/world.json` is a minimal placeholder marked `demo: true`. Regenerate with `python inventions/world/world.py` before relying on the published page.

Privacy: task titles, results, errors, and agent notes are excluded. External agent ids become short hash aliases.

To publish: enable GitHub Pages on `main` / `docs`. Page URL will be `https://usabandit33.github.io/digital-civilization/world/`.

Presence is current-state only (no events table yet). Live public presence would require scheduled commits of a fresh `world.json`.
