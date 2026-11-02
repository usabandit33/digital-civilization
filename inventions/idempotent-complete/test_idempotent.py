"""Offline tests for idempotent.py. Standard library only.

Run from this folder:   python -m unittest -v
Or from the repo root:  python -m unittest discover -s inventions/idempotent-complete -v
"""

import os
import sqlite3
import tempfile
import threading
import unittest

import idempotent as idem

SCHEMA = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'pending',
    title TEXT,
    result TEXT,
    error TEXT,
    claimed_by TEXT,
    updated_at TEXT
);
CREATE TABLE contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    agent_id TEXT NOT NULL
);
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "t.db")
        self.conn = self.connect()
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def add(self, status="running", claimed_by="a", result=None):
        cur = self.conn.execute(
            "INSERT INTO tasks (status, title, claimed_by, result) VALUES (?, 't', ?, ?)",
            (status, claimed_by, result),
        )
        self.conn.commit()
        return cur.lastrowid

    def row(self, task_id):
        return self.conn.execute(
            "SELECT status, result, error, claimed_by FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()


class CompleteTests(Base):
    def test_owner_completes_running_task(self):
        t = self.add()
        self.assertEqual(idem.complete(self.conn, t, "ok", owner="a"), idem.COMPLETED)
        self.conn.commit()
        self.assertEqual(self.row(t), ("done", "ok", None, "a"))

    def test_repeat_by_owner_is_idempotent_and_keeps_first_result(self):
        t = self.add()
        idem.complete(self.conn, t, "first", owner="a")
        self.assertEqual(idem.complete(self.conn, t, "second", owner="a"), idem.ALREADY_DONE)
        self.conn.commit()
        self.assertEqual(self.row(t)[1], "first")

    def test_pending_task_cannot_be_completed_by_stranger(self):
        t = self.add(status="pending", claimed_by=None)
        self.assertEqual(idem.complete(self.conn, t, "x", owner="stranger"), idem.NOT_RUNNING)
        self.assertEqual(self.row(t)[0], "pending")

    def test_wrong_owner_cannot_complete_running_task(self):
        t = self.add(claimed_by="a")
        self.assertEqual(idem.complete(self.conn, t, "x", owner="b"), idem.NOT_OWNER)
        self.assertEqual(self.row(t)[0], "running")

    def test_null_owner_matches_null_claim_only(self):
        t = self.add(claimed_by=None)
        self.assertEqual(idem.complete(self.conn, t, "ok", owner=None), idem.COMPLETED)

    def test_stale_worker_cannot_overwrite_newer_result(self):
        t = self.add()
        idem.complete(self.conn, t, "fresh", owner="a")
        self.conn.commit()
        self.assertEqual(idem.complete(self.conn, t, "stale", owner="a"), idem.ALREADY_DONE)
        self.assertEqual(self.row(t)[1], "fresh")

    def test_missing_task_returns_not_found(self):
        self.assertEqual(idem.complete(self.conn, 999, "x", owner="a"), idem.NOT_FOUND)

    def test_failed_task_is_not_completed(self):
        t = self.add(status="failed", claimed_by="a")
        self.assertEqual(idem.complete(self.conn, t, "x", owner="a"), idem.NOT_RUNNING)


class FailTests(Base):
    def test_owner_fails_running_task(self):
        t = self.add()
        self.assertEqual(idem.fail(self.conn, t, "boom", owner="a"), idem.FAILED)
        self.conn.commit()
        self.assertEqual(self.row(t)[0], "failed")

    def test_repeat_fail_is_idempotent(self):
        t = self.add()
        idem.fail(self.conn, t, "first", owner="a")
        self.assertEqual(idem.fail(self.conn, t, "second", owner="a"), idem.ALREADY_FAILED)

    def test_wrong_owner_cannot_fail_running_task(self):
        t = self.add(claimed_by="a")
        self.assertEqual(idem.fail(self.conn, t, "x", owner="b"), idem.NOT_OWNER)

    def test_done_task_is_never_turned_into_failure(self):
        t = self.add()
        idem.complete(self.conn, t, "ok", owner="a")
        self.conn.commit()
        self.assertEqual(idem.fail(self.conn, t, "late", owner="a"), idem.NOT_RUNNING)
        self.assertEqual(self.row(t)[0], "done")

    def test_missing_task_returns_not_found(self):
        self.assertEqual(idem.fail(self.conn, 999, "x", owner="a"), idem.NOT_FOUND)


class PatternTests(Base):
    def test_concurrent_completion_has_exactly_one_winner(self):
        t = self.add()
        results = []

        def try_complete():
            c = self.connect()
            out = idem.complete(c, t, "ok", owner="a")
            c.commit()
            c.close()
            results.append(out)

        threads = [threading.Thread(target=try_complete) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        self.assertEqual(results.count(idem.COMPLETED), 1)
        self.assertEqual(self.row(t)[0], "done")

    def test_side_effect_runs_once_when_gated_on_outcome(self):
        t = self.add()
        called = []

        def complete_with_side_effect():
            if idem.complete(self.conn, t, "ok", owner="a") == idem.COMPLETED:
                called.append(1)

        complete_with_side_effect()
        complete_with_side_effect()
        self.assertEqual(len(called), 1)
