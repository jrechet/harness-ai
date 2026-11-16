"""Tests of `harness serve`: history from git and HTTP API, without a browser."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import serve, status  # noqa: E402

TODAY = date(2026, 11, 9)


def git(repo, *args, when="2026-10-01T10:00:00Z"):
    env = {**os.environ, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when}
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True, env=env)


def write(repo, rel, content):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = self.dir.name
        git(self.repo, "init", "-q", "-b", "main")

    def tearDown(self):
        self.dir.cleanup()

    def commit_state(self, when):
        status.main([self.repo, "--today", when[:10]])
        git(self.repo, "add", "-A", when=when)
        git(self.repo, "commit", "-q", "-m", f"state {when[:10]}", when=when)

    def test_no_git_history_gives_current_only(self):
        entries = serve.history(self.repo, today=TODAY)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]["sha"])
        self.assertEqual(entries[0]["level"], 0)

    def test_history_follows_commits_then_current(self):
        self.commit_state("2026-09-01T10:00:00Z")                      # level 0
        write(self.repo, "AGENTS.md", "# r\n\nMode : **délégation**.\n\n## Règles\n- a\n\n## Interdits\n- b\n")
        self.commit_state("2026-10-01T10:00:00Z")                      # level 1
        entries = serve.history(self.repo, today=TODAY)
        self.assertEqual([e["date"] for e in entries[:2]], ["2026-09-01", "2026-10-01"])
        self.assertEqual([e["level"] for e in entries[:2]], [0, 1])
        self.assertTrue(all(e["sha"] for e in entries[:2]))
        # the current state is identical to the last commit: no extra "current" entry
        self.assertEqual(len(entries), 2)
        # an uncommitted change adds the current state
        write(self.repo, "AGENTS.md", "# r\n")
        entries = serve.history(self.repo, today=TODAY)
        self.assertEqual(len(entries), 3)
        self.assertIsNone(entries[-1]["sha"])
        self.assertEqual(entries[-1]["level"], 0)

    def test_summary_fields(self):
        e = serve.history(self.repo, today=TODAY)[0]
        self.assertEqual(set(e), {"sha", "date", "level", "checks_passed", "checks_total", "levels", "layers",
                                  "layers_source", "health_score"})
        self.assertEqual(len(e["levels"]), 4)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        write(self.dir.name, "AGENTS.md", "# r\n\nMode : **assistance**.\n")
        self.server, self.thread = serve.serve_in_thread(self.dir.name, today=TODAY)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.dir.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()

    def test_state_endpoint(self):
        code, ctype, body = self.get("/api/state")
        self.assertEqual(code, 200)
        self.assertIn("application/json", ctype)
        state = json.loads(body)
        self.assertEqual(state["schema"], "harness-state/1")
        self.assertEqual(state["facts"]["instructions"]["source"]["mode"], "assistance")

    def test_history_endpoint(self):
        code, _, body = self.get("/api/history")
        self.assertEqual(code, 200)
        self.assertEqual(len(json.loads(body)), 1)

    def test_app_is_served(self):
        code, ctype, body = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b'id="app"', body)
        code, ctype, _ = self.get("/app.js")
        self.assertEqual(code, 200)
        self.assertIn("javascript", ctype)
        code, _, _ = self.get("/vendor/vue.esm-browser.prod.js")
        self.assertEqual(code, 200)

    def test_unknown_path_is_404(self):
        try:
            self.get("/nope.txt")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            self.fail("404 expected")


if __name__ == "__main__":
    unittest.main()
