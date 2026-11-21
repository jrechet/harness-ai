"""The recorded pull-request histories of the sample projects: `harvest github --from` replays
them offline and finds what `history-expected.json` says, no more; and replaying the history
of go-hexa on top of its level-2 step is what takes the repository from level 1 to level 2."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS = os.path.join(ROOT, "cli", "harness.py")
REPOS = os.path.join(ROOT, "fixtures", "repos")
WITH_HISTORY = ("go-hexa", "microservices")
REAL_SIGNALS = ("S1", "S2", "S3", "S4")
LEVEL2_OVERLAY = os.path.join(REPOS, "go-hexa", "runs", "2026-11-14-step-target2", "overlay")
TODAY = "2026-11-21"   # one week after the harvest marker the level-2 step wrote


def harness(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, HARNESS, *args], capture_output=True, text=True, timeout=60, cwd=cwd)


def expected(fixture: str) -> dict:
    with open(os.path.join(REPOS, fixture, "history-expected.json"), encoding="utf-8") as fh:
        return json.load(fh)


def replay(fixture: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """The harvest of the fixture's history, with the options its expected file gives."""
    return harness("harvest", "github", *expected(fixture)["options"],
                   "--from", os.path.join(REPOS, fixture, "history"), cwd=cwd)


def status(repo: str) -> dict:
    proc = harness("status", repo, "--format", "json", "--no-write", "--today", TODAY)
    return json.loads(proc.stdout)


def checks(state: dict, level: int) -> dict[str, bool]:
    return {c["id"]: c["passed"] for c in state["levels"][level]["checks"]}


class RecordedHistory(unittest.TestCase):
    def test_replay_gives_the_expected_harvest_and_reads_every_source(self):
        for fixture in WITH_HISTORY:
            with self.subTest(fixture=fixture):
                proc = replay(fixture)

                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), expected(fixture)["result"])

    def test_replay_does_not_depend_on_the_folder_it_runs_from(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            for fixture in WITH_HISTORY:
                with self.subTest(fixture=fixture):
                    proc = replay(fixture, cwd=elsewhere)

                    self.assertEqual(json.loads(proc.stdout), expected(fixture)["result"])

    def test_history_holds_a_rule_comment_and_a_correction_on_an_agent_pr(self):
        for fixture in WITH_HISTORY:
            with self.subTest(fixture=fixture):
                result = expected(fixture)["result"]

                self.assertGreaterEqual(result["counts"].get("S1", 0), 1)
                self.assertGreaterEqual(result["counts"].get("S2", 0), 1)
                self.assertGreaterEqual(result["agent_prs"], 1)
                self.assertEqual(result["errors"], [])

    def test_noise_is_in_the_history_and_not_in_the_harvest(self):
        for fixture in WITH_HISTORY:
            with self.subTest(fixture=fixture):
                wanted = expected(fixture)
                recorded = self.recorded_text(fixture)
                harvested = json.dumps(json.loads(replay(fixture).stdout)["evidence"])

                self.assertGreaterEqual(len(wanted["noise"]), 3)
                for noise in wanted["noise"]:
                    self.assertTrue(noise["why"].strip(), noise)
                    self.assertIn(json.dumps(noise["url"]), recorded, "the noise is not in the history")
                    self.assertNotIn(json.dumps(noise["url"]), harvested, f"counted: {noise['why']}")

    def test_every_recorded_answer_is_read_by_the_replay(self):
        """A file the replay never opens is a call the harvest no longer makes: stale history."""
        for fixture in WITH_HISTORY:
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as tmp:
                history = os.path.join(REPOS, fixture, "history")
                answers = sorted(n for n in os.listdir(history) if not n.startswith("_"))

                for name in answers:
                    copy = os.path.join(tmp, name[:-len(".json")])
                    shutil.copytree(history, copy)
                    os.remove(os.path.join(copy, name))
                    proc = harness("harvest", "github", *expected(fixture)["options"], "--from", copy)

                    self.assertEqual(proc.returncode, 2, f"{name} is never read")
                    self.assertIn(name, proc.stderr)

    def test_history_records_its_window(self):
        for fixture in WITH_HISTORY:
            with self.subTest(fixture=fixture):
                with open(os.path.join(REPOS, fixture, "history", "_window.json"), encoding="utf-8") as fh:
                    window = json.load(fh)

                self.assertEqual(window["since"][:10], expected(fixture)["result"]["since"])
                self.assertNotIn("--since", expected(fixture)["options"])

    def test_readme_documents_the_history(self):
        with open(os.path.join(ROOT, "fixtures", "README.md"), encoding="utf-8") as fh:
            readme = fh.read()

        self.assertIn("history/", readme)
        self.assertIn("history-expected.json", readme)
        self.assertIn("--from fixtures/repos/go-hexa/history", readme)

    @staticmethod
    def recorded_text(fixture: str) -> str:
        history = os.path.join(REPOS, fixture, "history")
        parts = []
        for name in sorted(os.listdir(history)):
            with open(os.path.join(history, name), encoding="utf-8") as fh:
                parts.append(json.dumps(json.load(fh)))
        return "\n".join(parts)


class GoHexaLeavesLevelOne(unittest.TestCase):
    """The repository, the files of its level-2 step, then one harvest of its history."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = os.path.join(tmp.name, "ledger")
        shutil.copytree(os.path.join(REPOS, "go-hexa", "repo"), self.repo)
        shutil.copytree(LEVEL2_OVERLAY, self.repo, dirs_exist_ok=True)

    def harvest(self) -> dict:
        proc = replay("go-hexa", cwd=self.repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        os.makedirs(os.path.join(self.repo, ".harness"))
        with open(os.path.join(self.repo, ".harness", "harvest.json"), "w", encoding="utf-8") as fh:
            fh.write(proc.stdout)
        return json.loads(proc.stdout)

    def test_before_the_harvest_only_the_signal_is_missing(self):
        state = status(self.repo)

        self.assertEqual(state["level"]["reached"], 1)
        self.assertEqual([c for c, passed in checks(state, 2).items() if not passed], ["L2.signal"])

    def test_replaying_the_history_takes_the_repository_to_level_two(self):
        before = status(self.repo)["level"]["reached"]

        harvest = self.harvest()
        state = status(self.repo)

        self.assertEqual(before, 1)
        self.assertGreater(sum(harvest["counts"].get(s, 0) for s in REAL_SIGNALS), 0)
        self.assertEqual(state["level"]["reached"], 2)
        self.assertTrue(all(checks(state, 2).values()), checks(state, 2))
        self.assertEqual(state["facts"]["harvest"]["errors"], 0)


if __name__ == "__main__":
    unittest.main()
