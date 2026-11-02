#!/usr/bin/env python3
"""Build a sanitized world.json from real repo data. Stdlib only, read-only.

  python inventions/world/world.py --serve        live, local (http://127.0.0.1:8750/)
  python inventions/world/world.py                writes docs/world/world.json (public snapshot)

Public output never includes task titles, results, errors, agent notes, or
self-chosen external agent ids (those are replaced by a short hash alias).
"""
from __future__ import annotations
import argparse, hashlib, json, re, sqlite3, subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

INTERNAL = ("core", "hermes", "local")
STALE_SECONDS = 1800


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / "constitution.md").is_file():
            return cur
        cur = cur.parent
    raise SystemExit("repo root not found (constitution.md)")


def alias(agent_id):
    if agent_id is None:
        return "core"  # assumption: the core worker claims without an id
    if agent_id in INTERNAL:
        return agent_id
    return "visitor-" + hashlib.sha1(str(agent_id).encode()).hexdigest()[:4]


def districts(root):
    p, out = root / "projects" / "published-tasks.md", []
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            if line[3:].lower().startswith("how to"):
                break
            out.append({"name": line[3:].strip(), "tasks": []})
        else:
            m = re.match(r"(\d+)\.\s+(.*)", line)
            if m and out:
                out[-1]["tasks"].append({"n": int(m[1]), "title": m[2].strip()[:120]})
    return out


def inventions(root):
    base, out = root / "inventions", []
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        r = d / "README.md"
        text = r.read_text(encoding="utf-8", errors="replace") if r.is_file() else ""
        m = re.search(r"published task #(\d+)", text, re.I)
        summary = next((l.strip() for l in text.splitlines()[1:]
                        if l.strip() and not l.startswith("#")), "")
        out.append({"name": d.name, "task": int(m[1]) if m else None, "summary": summary[:140]})
    return out


def journal(root, n=10):
    d = root / "journal"
    if not d.is_dir():
        return []
    files = sorted(d.glob("*.md"), reverse=True)[:n]
    titles = []
    for f in files:
        try:
            first = f.read_text(encoding="utf-8", errors="replace").splitlines()
            title = next((line.strip("# ").strip() for line in first if line.strip()), f.name)
            titles.append(title[:120])
        except OSError:
            titles.append(f.name)
    return titles


def branches(root):
    try:
        out = subprocess.run(
            ["git", "branch", "--list"],
            cwd=root, capture_output=True, text=True, timeout=10, check=False,
        )
        if out.returncode != 0:
            return []
        return [ln.strip().lstrip("* ") for ln in out.stdout.splitlines() if ln.strip() and not ln.strip().startswith("*")]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def presence(root):
    res = {"counts": {"pending": 0, "running": 0, "done": 0, "failed": 0},
           "working": [], "agents": [], "pending_contributions": 0}
    db = root / "data" / "civilization.db"
    if not db.is_file():
        return res
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        c.row_factory = sqlite3.Row
        for row in c.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"):
            s = str(row["status"])
            if s in res["counts"]:
                res["counts"][s] = int(row["n"])
        now = datetime.now(timezone.utc)
        for r in c.execute("SELECT id, claimed_by, updated_at FROM tasks WHERE status='running'"):
            try:
                age = (now - datetime.fromisoformat(r["updated_at"])).total_seconds()
            except (TypeError, ValueError):
                age = 0
            res["working"].append({"agent": alias(r["claimed_by"]), "task": r["id"], "stalled": age > STALE_SECONDS})
        for r in c.execute("SELECT id, approved, reputation, internal FROM agents WHERE internal = 0"):
            res["agents"].append({"id": alias(r["id"]), "external": True,
                                  "approved": bool(r["approved"]), "reputation": r["reputation"]})
        res["pending_contributions"] = c.execute(
            "SELECT COUNT(*) FROM contributions WHERE status='pending'").fetchone()[0]
        c.close()
    except sqlite3.Error:
        pass
    return res


def build(root):
    data = {"generated": datetime.now(timezone.utc).isoformat(), "demo": False,
            "districts": districts(root), "inventions": inventions(root),
            "branches": branches(root), "journal": journal(root)}
    data.update(presence(root))
    return data


def serve(root, port):
    web = root / "docs" / "world"

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            p = self.path.split("?")[0]
            if p == "/world.json":
                body, ct = json.dumps(build(root)).encode(), "application/json"
            elif p in ("/", "/index.html"):
                body, ct = (web / "index.html").read_bytes(), "text/html; charset=utf-8"
            else:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    print(f"World (live, local only): http://127.0.0.1:{port}/")
    HTTPServer(("127.0.0.1", port), H).serve_forever()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8750)
    ap.add_argument("--out", default=None, help="default: docs/world/world.json")
    a = ap.parse_args()
    root = find_root(Path(__file__).parent)
    if a.serve:
        serve(root, a.port)
    else:
        out = Path(a.out) if a.out else root / "docs" / "world" / "world.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(build(root), indent=1), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
