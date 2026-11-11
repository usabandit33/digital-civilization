import json, sqlite3, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import world
import validate_world


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        r = self.root = Path(self.t.name)
        (r / "constitution.md").write_text("x")
        (r / "projects").mkdir(); (r / "journal").mkdir(); (r / "data").mkdir()
        (r / "projects" / "published-tasks.md").write_text(
            "# P\n\n## Reliability\n11. Retry\n14. Idempotent completion\n\n## How to submit\n99. no\n")
        (r / "journal" / "0001-a.md").write_text("# Journal Entry 0001 — Hi\n")
        inv = r / "inventions" / "idem"; inv.mkdir(parents=True)
        (inv / "README.md").write_text("# Idem\n\nAddresses published task #14, thing.\n")
        c = sqlite3.connect(r / "data" / "civilization.db")
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        c.executescript("""
        CREATE TABLE tasks (id INTEGER PRIMARY KEY, status TEXT, title TEXT, claimed_by TEXT, updated_at TEXT);
        CREATE TABLE agents (id TEXT, approved INT, reputation INT, internal INT, notes TEXT);
        CREATE TABLE contributions (id INTEGER PRIMARY KEY, status TEXT);""")
        c.execute("INSERT INTO tasks VALUES (1,'running','SECRET TITLE',NULL,?)", (old,))
        c.execute("INSERT INTO tasks VALUES (2,'running','x','evil<script>',?)", (datetime.now(timezone.utc).isoformat(),))
        c.execute("INSERT INTO tasks VALUES (3,'pending','y',NULL,?)", (old,))
        c.execute("INSERT INTO agents VALUES ('evil<script>',0,5,0,'PRIVATE NOTE')")
        c.execute("INSERT INTO contributions VALUES (1,'pending')")
        c.commit(); c.close()
        self.w = world.build(r)

    def tearDown(self):
        self.t.cleanup()

    def test_districts_and_invention_mapping(self):
        self.assertEqual([d["name"] for d in self.w["districts"]], ["Reliability"])
        self.assertEqual(len(self.w["districts"][0]["tasks"]), 2)
        self.assertEqual(self.w["inventions"][0]["task"], 14)

    def test_null_claim_is_core_and_stale_is_flagged(self):
        by = {x["task"]: x for x in self.w["working"]}
        self.assertEqual(by[1]["agent"], "core")
        self.assertTrue(by[1]["stalled"])
        self.assertFalse(by[2]["stalled"])

    def test_no_private_text_leaks(self):
        blob = json.dumps(self.w)
        for bad in ("SECRET TITLE", "PRIVATE NOTE", "evil", "<script>"):
            self.assertNotIn(bad, blob)
        self.assertTrue(any(a["id"].startswith("visitor-") for a in self.w["agents"]))

    def test_counts_and_pending_contributions(self):
        self.assertEqual(self.w["counts"]["running"], 2)
        self.assertEqual(self.w["pending_contributions"], 1)

    def test_missing_db_is_fine(self):
        (self.root / "data" / "civilization.db").unlink()
        self.assertEqual(world.build(self.root)["working"], [])

    def test_generated_snapshot_matches_validator(self):
        self.assertEqual(validate_world.validate_snapshot(self.w), [])


if __name__ == "__main__":
    unittest.main()
