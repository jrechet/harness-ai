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


# The calls on the engine written in the plugin's own code. Session state goes through Claude Code's
# `read` and `update`, which `claude plugin validate` reports as `$.state.get` and `$.state.set`.
DIRECT_CALLS = {"fs.exists", "fs.read", "command.register", "ui.open", "ui.resolve"}
CALL = re.compile(r"\$\s*\??\.\s*([a-z]+)\s*\??\.\s*([A-Za-z]+)")
# `$` used any other way than `$.noun.method`: handed on, renamed or taken apart.
HANDED_ON = re.compile(r"\$(?!\s*\??\.\s*[a-z]+\s*\??\.\s*[A-Za-z]+)(?!\{)")
# The state read otherwise than by `owner.key`: brackets, destructuring, or walked whole.
SIDE_DOORS = re.compile(r"\b(?:state|raw|check)\b(?:\s+as\s+\w+)?\s*\)?\s*\[|\}\s*=\s*(?:state|raw|check)\b|Object\.\w+\((?:state|raw|check)\b")


def calls(source: str) -> set[str]:
    return {f"{noun}.{method}" for noun, method in CALL.findall(source)}


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
        cls.sources = {}
        for folder, _, names in os.walk(PLUGIN):
            for name in names:
                if name.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")) \
                        and ".test." not in name and not name.endswith(".d.ts") and ".claude-plugin" not in folder:
                    path = os.path.join(folder, name)
                    with open(path, encoding="utf-8") as fh:
                        cls.sources[os.path.relpath(path, PLUGIN).replace(os.sep, "/")] = fh.read()
        cls.source = cls.sources["hooks/summary.ts"]
        cls.everything = "\n".join(cls.sources.values())

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
        read = set(re.findall(r"\b(state\.level|state\.target|state|raw|check)\s*\??\.\s*([A-Za-z0-9_]+)\b", self.source))
        unknown = sorted(f"{owner}.{key}" for owner, key in read if key not in READ[owner])
        self.assertEqual(unknown, [])
        self.assertGreaterEqual(len(read), 15, "the plugin's source no longer reads the state the way this test looks for")

    def test_the_guard_on_keys_sees_the_spellings_it_must_refuse(self):
        self.assertEqual(SIDE_DOORS.findall(self.source), [])
        for spelling in ("state['facts']", "raw [ 'x' ]", "(state as any)['facts']", "const { facts } = state", "let {a, b}=check;", "Object.keys(state)"):
            with self.subTest(spelling=spelling):
                self.assertTrue(SIDE_DOORS.search(spelling))

    def test_the_state_file_is_parsed_in_one_place(self):
        self.assertEqual(self.sources["hooks/summary.ts"].count("JSON.parse("), 1)
        self.assertNotIn("JSON.parse", self.sources["hooks/register.tsx"])
        self.assertEqual(re.findall(r"\$\.fs\.read\(([^)]*)\)", self.sources["hooks/register.tsx"]), ["STATE_FILE"])
        self.assertEqual(re.findall(r"\$\.fs\.exists\(([^)]*)\)", self.sources["hooks/register.tsx"]), ["STATE_FILE"])
        self.assertIn("const STATE_FILE = '.harness/state.json'\n", self.sources["hooks/register.tsx"])
        self.assertIn("summarise(await $.fs.read(STATE_FILE))", self.sources["hooks/register.tsx"])

    def test_every_key_of_the_contract_is_read_by_the_plugin(self):
        for owner, keys in READ.items():
            for key in keys:
                with self.subTest(key=f"{owner}.{key}"):
                    self.assertRegex(self.source, rf"\b{re.escape(owner)}\.{key}\b")

    def test_the_plugin_runs_nothing_and_writes_nothing(self):
        """Every `$` call written in the plugin's code, whatever the spacing or the line breaks. What this
        cannot see: a call made by code the plugin does not hold; `claude plugin validate` lists those."""
        self.assertEqual(set(self.sources), {"hooks/register.tsx", "hooks/summary.ts"})
        self.assertEqual(calls(self.everything), DIRECT_CALLS)
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"modules": ["./register.tsx"]})

    def test_the_guard_on_calls_sees_the_spellings_that_hide_one(self):
        for spelling, expected in (("await $.process\n  .run(['x'])", "process.run"), ("$.fs\n.write('a','b')", "fs.write"),
                                   ("$.http.fetch ('u')", "http.fetch"), ("$ . fs . remove(p)", "fs.remove"),
                                   ("$?.shell?.exec(c)", "shell.exec")):
            with self.subTest(spelling=spelling):
                self.assertEqual(calls(spelling), {expected})
        for spelling in ("const { fs } = $", "const engine = $;", "helper($)", "[$]", "{ $ }"):
            with self.subTest(spelling=spelling):
                self.assertTrue(HANDED_ON.search(spelling))

    def test_the_engine_is_handed_only_to_the_functions_this_test_knows(self):
        """`$` passed whole to a function is how a call would escape the list above: each such hand-over
        is named here. `read` and `update` are Claude Code's session state; `refresh` is the plugin's own."""
        handed = set(re.findall(r"\b([A-Za-z_]+)\(\$[,)]", self.everything))
        self.assertEqual(handed, {"read", "update", "refresh"})
        rest = re.sub(r"\b(read|update|refresh)\(\$[,)]", "", self.everything)
        rest = re.sub(r"\(\$(: EngineInterface)?[,)]", "", rest)          # a hook's or a function's own parameter
        rest = re.sub(r"async \$ =>", "", rest)
        self.assertEqual(HANDED_ON.findall(rest), [])

    def test_the_plugin_imports_only_claude_code_and_its_own_files(self):
        imports = set(re.findall(r"from\s+'([^']+)'", self.everything))
        self.assertEqual(imports, {"claude-code", "../types", "./summary"})
        self.assertNotRegex(self.everything, r"\bimport\s*\(|\brequire\s*\(")

    def test_the_marketplace_lists_the_plugin_from_its_folder(self):
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
            plugins = {plugin["name"]: plugin["source"] for plugin in json.load(fh)["plugins"]}
        self.assertEqual(plugins["harness-hud"], "./plugins/harness-hud")
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["name"], "harness-hud")


if __name__ == "__main__":
    unittest.main()
