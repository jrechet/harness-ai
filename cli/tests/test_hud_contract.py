"""The state file is a contract with the `harness-hud` plugin, which draws from it.

The plugin's own tests run under `claude plugin test plugins/harness-hud`, which this suite cannot
start. What is held here: every key the plugin reads is one `harness status` writes, with the type
the plugin expects, and the plugin reads no key this test does not know."""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(CLI_DIR)
sys.path.insert(0, CLI_DIR)
from harness import main as harness_main  # noqa: E402

PLUGIN = os.path.join(ROOT, "plugins", "harness-hud")
SUMMARY = os.path.join(PLUGIN, "hooks", "summary.ts")
AGENTS = "# demo\n\nMode: **assistance**. A human drives every task.\n\n## Rules\n- Tests pass.\n"
# The keys of the state file the plugin reads, by the object they are read from.
READ = {"state": {"schema", "date", "level", "target", "levels", "next_actions"},
        "state.level": {"reached", "name"},
        "state.target": {"level", "reached"},
        "raw": {"level", "name", "passed_checks", "total_checks", "achieved", "in_scope", "checks"},
        "check": {"label", "passed", "ignored"}}


def quiet(*argv: str) -> int:
    with redirect_stdout(io.StringIO()):
        return harness_main(list(argv))


class HudContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        repo = os.path.realpath(cls._tmp.name)
        with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(AGENTS)
        quiet("ignore", "L1.forbidden", "--reason", "kept in the permissions", "--repo", repo)
        quiet("target", "2", repo)
        quiet("status", repo)
        with open(os.path.join(repo, ".harness", "state.json"), encoding="utf-8") as fh:
            cls.state = json.load(fh)
        with open(SUMMARY, encoding="utf-8") as fh:
            cls.source = fh.read()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_schema_is_the_one_the_plugin_accepts(self):
        self.assertEqual(self.state["schema"], "harness-state/1")
        self.assertIn("'harness-state/1'", self.source)

    def test_the_top_of_the_state_has_what_the_plugin_reads(self):
        self.assertLessEqual(READ["state"], set(self.state))
        self.assertIsInstance(self.state["level"]["reached"], int)
        self.assertIsInstance(self.state["level"]["name"], str)
        self.assertEqual(self.state["target"]["level"], 2)
        self.assertIsInstance(self.state["target"]["reached"], bool)
        self.assertIsInstance(self.state["date"], str)
        self.assertTrue(all(isinstance(action, str) for action in self.state["next_actions"]))

    def test_every_level_has_what_the_plugin_reads(self):
        self.assertEqual([level["level"] for level in self.state["levels"]], [0, 1, 2, 3, 4])
        for level in self.state["levels"]:
            with self.subTest(level=level["level"]):
                self.assertLessEqual(READ["raw"], set(level))
                self.assertIsInstance(level["passed_checks"], int)
                self.assertIsInstance(level["total_checks"], int)
                self.assertIsInstance(level["achieved"], bool)
                self.assertIsInstance(level["in_scope"], bool)
                for check in level["checks"]:
                    self.assertIsInstance(check["label"], str)
                    self.assertIsInstance(check["passed"], bool)

    def test_a_check_set_aside_is_marked_the_way_the_plugin_reads_it(self):
        aside = [check for level in self.state["levels"] for check in level["checks"] if check.get("ignored") is True]
        self.assertEqual([check["id"] for check in aside], ["L1.forbidden"])
        self.assertFalse(aside[0]["passed"])

    def test_a_level_beyond_the_target_is_out_of_scope(self):
        self.assertEqual([level["in_scope"] for level in self.state["levels"]], [True, True, True, False, False])

    def test_the_plugin_reads_no_key_this_contract_does_not_know(self):
        read = {(owner, key) for owner, key in re.findall(r"\b(state\.level|state\.target|state|raw|check)\.([a-z_]+)\b", self.source)}
        unknown = sorted(f"{owner}.{key}" for owner, key in read if key not in READ[owner])
        self.assertEqual(unknown, [])
        self.assertGreaterEqual(len(read), 15, "the plugin's source no longer reads the state the way this test looks for")

    def test_every_key_of_the_contract_is_read_by_the_plugin(self):
        for owner, keys in READ.items():
            for key in keys:
                with self.subTest(key=f"{owner}.{key}"):
                    self.assertRegex(self.source, rf"\b{re.escape(owner)}\.{key}\b")

    def test_the_plugin_runs_nothing_and_writes_nothing(self):
        with open(os.path.join(PLUGIN, "hooks", "register.tsx"), encoding="utf-8") as fh:
            register = fh.read()
        calls = set(re.findall(r"\$\.([a-z]+\.[a-zA-Z]+)\(", register + self.source))
        self.assertEqual(calls, {"fs.exists", "fs.read", "command.register", "ui.open", "ui.resolve"})

    def test_the_marketplace_lists_the_plugin_from_its_folder(self):
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
            plugins = {plugin["name"]: plugin["source"] for plugin in json.load(fh)["plugins"]}
        self.assertEqual(plugins["harness-hud"], "./plugins/harness-hud")
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["name"], "harness-hud")


if __name__ == "__main__":
    unittest.main()
