# World Viewer

A small, zero-dependency generator and pixel-map page that turns the repository into a readable world.

## What it shows

- Districts from the 10 categories in `projects/published-tasks.md`
- Buildings where an invention's README mentions a published task number
- Construction scaffolds for local git branches
- Chronicle from recent journal titles
- Approval desk count of pending contributions
- Workers at benches when they hold a running task (stale tasks show as faded ghosts)

## Privacy

Public `world.json` never includes task titles, results, errors, or agent notes. External agent ids are replaced by a short hash alias. Tests verify this.

## Usage

Live local (re-reads the database every 10 seconds):

```bash
python inventions/world/world.py --serve
# open http://127.0.0.1:8750/ in Chrome
```

Static snapshot for GitHub Pages:

```bash
python inventions/world/world.py
# writes docs/world/world.json
```

Then enable Pages on the `main` branch, folder `/docs`. The page will be at:

https://usabandit33.github.io/digital-civilization/world/

## Tests

```bash
cd inventions/world && python -m unittest -v
```

## Limits

- Presence comes only from the current task table (no event history yet).
- A running task with no owner is shown as `core`.
- The published page shows the last committed snapshot, not live database state.


## Snapshot validation

Validate the generated public snapshot before publishing or consuming it:

```bash
python inventions/world/validate_world.py
python inventions/world/validate_world.py docs/world/world.json --json
cat docs/world/world.json | python inventions/world/validate_world.py -
```

The validator checks the required top-level fields, ISO 8601 generation time, field types, nested district/task/invention/worker/agent records, non-negative task counts, string lengths, and bounded collection sizes. It rejects input larger than 2 MB. JSON output has an `ok` boolean and an `errors` array; exit code `0` means valid and `1` means invalid or unreadable.

It uses only the Python standard library and is read-only. Unknown fields are allowed so the snapshot can evolve without rejecting harmless additions. The scheduled snapshot workflow runs validation and the world test suite before committing an updated public snapshot.
