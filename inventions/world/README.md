# Living World Viewer

A zero-dependency, read-only isometric management-game view of the Digital Civilization. It visualizes the existing sanitized `world.json` snapshot; it is not a game engine and does not change the underlying civilization.

## Run locally

```bash
python inventions/world/world.py --serve
# Open http://127.0.0.1:8750/
```

The page refreshes its snapshot every eight seconds. The static GitHub Pages snapshot can also be viewed at:

https://usabandit33.github.io/digital-civilization/world/

## Current prototype

- Isometric map with landmarks for governance, research, inventions, task operations, services, and reliability.
- Live snapshot counters for pending, running, completed, failed, and visitor agents.
- Selectable buildings with an inspector panel, district shortcuts, and a recent journal chronicle.
- Animated worker markers for running tasks; stale workers are visually distinguished.
- Responsive layout, keyboard landmark selection, visible focus, semantic controls, canvas fallback instructions, and reduced-motion support.
- No external JS, CSS, images, packages, or remote service calls.

## Safety and data boundaries

The viewer is observational only. It does not assign tasks, approve contributions, start agents, or write to SQLite. It consumes the existing sanitized snapshot produced by `inventions/world/world.py`. Public snapshot privacy guarantees remain the responsibility of that generator and its tests.

The Citizens, Research Tree, and Mission Control navigation entries are deliberately disabled until their data and approval workflows are implemented. The current map is a visual metaphor, not a claim that agents are conscious or that game-like resource values exist.

## Tests

```bash
cd inventions/world && python -m unittest -v
```

## Snapshot validation

Validate the generated public snapshot before publishing or consuming it:

```bash
python inventions/world/validate_world.py
python inventions/world/validate_world.py docs/world/world.json --json
cat docs/world/world.json | python inventions/world/validate_world.py -
```

The validator checks the required top-level fields, ISO 8601 generation time, field types, nested district/task/invention/worker/agent records, non-negative task counts, string lengths, and bounded collection sizes. It rejects input larger than 2 MB. JSON output has an `ok` boolean and an `errors` array; exit code `0` means valid and `1` means invalid or unreadable.

It uses only the Python standard library and is read-only. OS read errors report an error number without echoing the supplied filesystem path. Unknown fields are allowed so the snapshot can evolve without rejecting harmless additions. The scheduled snapshot workflow runs validation and the world test suite before committing an updated public snapshot.
