"""Unit tests for the agent health check."""
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "health_check.py"
SPEC = importlib.util.spec_from_file_location("health_check", MODULE_PATH)
health_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health_check)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 503)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args):
        pass


class HealthCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/health"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_http_success(self):
        result = health_check.check_http(self.url, 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["detail"], "HTTP 200")

    def test_http_failure_status(self):
        result = health_check.check_http(self.url + "-missing", 2)
        self.assertFalse(result["ok"])
        self.assertEqual(result["detail"], "HTTP 503")

    def test_sqlite_read_only_existing_db(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.db"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE sample (value INTEGER)")
            connection.commit()
            connection.close()
            result = health_check.check_sqlite(path)
            self.assertTrue(result["ok"])
            self.assertEqual(result["detail"], "read-only query succeeded")
            connection = sqlite3.connect(path)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0], 0)
            connection.close()

    def test_sqlite_missing_db_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.db"
            result = health_check.check_sqlite(path)
            self.assertFalse(result["ok"])
            self.assertFalse(path.exists())

    def test_cli_json_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.db"
            sqlite3.connect(path).close()
            # Use CLI with a live endpoint and temporary database.
            import contextlib
            import io
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = health_check.main(["--url", self.url, "--db", str(path), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(len(payload["checks"]), 2)


if __name__ == "__main__":
    unittest.main()
