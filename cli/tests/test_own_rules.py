"""This repository follows the rules its AGENTS.md states: the CLIs import only the standard
library, no build leftover is committed, every skill calls a CLI that exists through the plugin
root, and its own AGENTS.md holds level 1."""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, maturity, medals  # noqa: E402

SILVER_RANK = 2
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI_ROOTS = ("cli", "plugins/ai-sdlc/cli")
SKILL_ROOTS = {"skills": "harness.py", "plugins/ai-sdlc/skills": "ai_sdlc.py"}   # each plugin's skills call its own CLI
PLUGIN_PREFIX = '"${CLAUDE_PLUGIN_ROOT}/cli/'
FORBIDDEN_TRACKED = re.compile(r"(^|/)__pycache__(/|$)|\.pyc$|\.skill$")
# `python3 <prefix><script>.py" <subcommand> <action>`: a word counts only when it is a bare lowercase
# token, so `<repo>`, `.`, a flag or a path ends the subcommand.
CLI_CALL = re.compile(r'python3\s+(\S*?)(harness|ai_sdlc)\.py"?((?:[ \t]+[a-z][a-z-]*(?![\w<>./"-]))*)')
MAX_SUBCOMMAND_WORDS = 2
HELP_TIMEOUT_SECONDS = 60


def python_files(cli_root: str) -> list[str]:
    found = []
    for folder, dirs, files in os.walk(os.path.join(ROOT, cli_root)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        found.extend(os.path.join(folder, name) for name in files if name.endswith(".py"))
    return sorted(found)


def local_modules(cli_root: str) -> set[str]:
    """The modules and packages a CLI ships at its own root: what its files may import besides the standard library."""
    base = os.path.join(ROOT, cli_root)
    names = set()
    for name in os.listdir(base):
        if name.endswith(".py"):
            names.add(name[:-3])
        elif os.path.isdir(os.path.join(base, name)) and name != "__pycache__":
            names.add(name)
    return names


def imported_modules(path: str) -> list[tuple[int, str]]:
    """Every absolute import of a file as (line, top-level module); relative imports are local by construction."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name.split(".")[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module.split(".")[0]))
    return found


def foreign_imports(cli_root: str) -> list[str]:
    allowed = set(sys.stdlib_module_names) | local_modules(cli_root)
    return [f"{os.path.relpath(path, ROOT)}:{line} imports {module}"
            for path in python_files(cli_root)
            for line, module in imported_modules(path) if module not in allowed]


def skill_files() -> list[tuple[str, str]]:
    """Every shipped SKILL.md as (path relative to the repository, the CLI script its plugin ships)."""
    found = []
    for skill_root, script in SKILL_ROOTS.items():
        base = os.path.join(ROOT, skill_root)
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, "SKILL.md")):
                found.append((f"{skill_root}/{name}/SKILL.md", script))
    return found


def cli_calls(text: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Every CLI call a text cites as (prefix before the script, script, leading subcommand words)."""
    return [(prefix, f"{script}.py", tuple(words.split()[:MAX_SUBCOMMAND_WORDS]))
            for prefix, script, words in CLI_CALL.findall(text)]


def read(relative: str) -> str:
    with open(os.path.join(ROOT, relative), encoding="utf-8") as fh:
        return fh.read()


def script_path(script: str) -> str:
    cli_root = next(root for root, name in SKILL_ROOTS.items() if name == script)
    return os.path.join(ROOT, os.path.dirname(cli_root), "cli", script)


def help_exit_code(script: str, words: tuple[str, ...]) -> int:
    """`--help` exits 0 when the subcommand exists and 2 when argparse does not know it; it starts nothing."""
    done = subprocess.run([sys.executable, script_path(script), *words, "--help"], capture_output=True,
                          timeout=HELP_TIMEOUT_SECONDS, check=False)
    return done.returncode


class StandardLibraryOnlyTests(unittest.TestCase):
    """AGENTS.md, Forbidden: no dependency outside the standard library in the CLI."""

    def test_every_import_of_both_clis_is_standard_or_local(self):
        for cli_root in CLI_ROOTS:
            with self.subTest(cli=cli_root):
                self.assertGreater(len(python_files(cli_root)), 5, "the walk must find the CLI's files")
                self.assertEqual(foreign_imports(cli_root), [])

    def test_the_import_reader_sees_every_form_and_skips_relative_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("import os, requests.adapters\nfrom yaml import safe_load\nfrom . import sibling\n"
                         "from .sibling import thing\ndef late():\n    import numpy as np\n")
            self.assertEqual(imported_modules(path), [(1, "os"), (1, "requests"), (2, "yaml"), (6, "numpy")])


class NothingBuiltIsCommittedTests(unittest.TestCase):
    """AGENTS.md, Forbidden: no `__pycache__` and no `.skill` in the repository."""

    def test_git_tracks_no_pycache_no_pyc_and_no_packaged_skill(self):
        # No way out: without git or outside a checkout this test fails, it never passes by not looking.
        done = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True, check=False)
        self.assertEqual(done.returncode, 0, "this rule is read from git: run the suite in a checkout")
        tracked = [name for name in done.stdout.decode("utf-8", "surrogateescape").split("\0") if name]
        self.assertGreater(len(tracked), 0)
        self.assertEqual([name for name in tracked if FORBIDDEN_TRACKED.search(name)], [])

    def test_the_pattern_names_what_is_forbidden_and_nothing_else(self):
        for name in ("cli/__pycache__/harness.cpython-311.pyc", "__pycache__/x", "cli/harness.pyc", "dist/harness-audit.skill"):
            with self.subTest(name=name):
                self.assertRegex(name, FORBIDDEN_TRACKED)
        for name in ("skills/harness-audit/SKILL.md", "cli/harness.py", "docs/skills.md", ".claude/skills/x/SKILL.md"):
            with self.subTest(name=name):
                self.assertNotRegex(name, FORBIDDEN_TRACKED)


class SkillsCallTheCliTests(unittest.TestCase):
    """AGENTS.md, Rules: what must be guaranteed lives in the CLI, and the skills call it."""

    def test_every_shipped_skill_is_found(self):
        folders = {os.path.dirname(os.path.dirname(path)) for path, _ in skill_files()}
        self.assertEqual(folders, set(SKILL_ROOTS))
        self.assertGreaterEqual(len(skill_files()), 16)

    def test_every_skill_calls_its_cli_through_the_plugin_root(self):
        for path, script in skill_files():
            with self.subTest(skill=path):
                text = read(path)
                self.assertNotRegex(text, r"python3 cli/", "the skill must call ${CLAUDE_PLUGIN_ROOT}/cli/…")
                calls = cli_calls(text)
                self.assertIn((PLUGIN_PREFIX, script), {(prefix, name) for prefix, name, _ in calls},
                              f"the skill never calls {PLUGIN_PREFIX}{script}")
                self.assertEqual([(prefix, name) for prefix, name, _ in calls if prefix != PLUGIN_PREFIX], [],
                                 "a CLI call that does not go through ${CLAUDE_PLUGIN_ROOT} breaks once installed")

    def test_every_subcommand_a_skill_cites_exists(self):
        cited: dict[tuple[str, tuple[str, ...]], str] = {}
        for path, _ in skill_files():
            for _, script, words in cli_calls(read(path)):
                cited.setdefault((script, words), path)
        self.assertGreaterEqual(len(cited), 15)
        for (script, words), path in sorted(cited.items()):
            with self.subTest(skill=path, call=f"{script} {' '.join(words)}"):
                self.assertTrue(words, "a call without a subcommand")
                self.assertEqual(help_exit_code(script, words), 0)

    def test_the_call_reader_stops_at_what_is_not_a_subcommand(self):
        text = ('`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map <repo>` then '
                '`python3 "${CLAUDE_PLUGIN_ROOT}/cli/ai_sdlc.py" qa gate . --base <base>`, '
                '`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" target <n> <repo>`, '
                '`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" report from-place <file>` and python3 cli/harness.py rules docs/x')
        self.assertEqual(cli_calls(text), [
            (PLUGIN_PREFIX, "harness.py", ("status",)),
            (PLUGIN_PREFIX, "ai_sdlc.py", ("qa", "gate")),
            (PLUGIN_PREFIX, "harness.py", ("target",)),
            (PLUGIN_PREFIX, "harness.py", ("report", "from-place")),
            ("cli/", "harness.py", ("rules",)),
        ])

    def test_an_unknown_subcommand_is_seen(self):
        self.assertEqual(help_exit_code("harness.py", ("status",)), 0)
        self.assertNotEqual(help_exit_code("harness.py", ("no-such-command",)), 0)
        self.assertNotEqual(help_exit_code("ai_sdlc.py", ("qa", "no-such-action")), 0)


EXAMPLE_BLOCK = re.compile(r"```json\n(.*?)```", re.S)
LONG_WORD = re.compile(r"[a-z]{6,}")


def example_pieces(text: str) -> list[str]:
    """The `piece` texts of the JSON examples a skill shows."""
    pieces = []
    for block in EXAMPLE_BLOCK.findall(text):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        rows = data if isinstance(data, list) else [data]
        pieces += [row["piece"] for row in rows if isinstance(row, dict) and isinstance(row.get("piece"), str)]
    return pieces


def graded_lines() -> list[tuple[str, str]]:
    """Every line an answer key of `fixtures/design` grades: (fixture and item, the line's text)."""
    lines = []
    for key in sorted(glob.glob(os.path.join(ROOT, "fixtures", "design", "*", "expected.json"))):
        fixture = os.path.dirname(key)
        with open(key, encoding="utf-8") as fh:
            expected = json.load(fh)
        for item in expected.get("traps", []) + expected.get("healthy", []):
            with open(os.path.join(fixture, "artifact", item["file"]), encoding="utf-8") as fh:
                text = fh.read().split("\n")
            first, last = item["lines"]
            lines.append((f"{os.path.basename(fixture)} {item['id']}", " ".join(text[first - 1:last])))
    return lines


def leaked_examples(pieces: list[str], graded: list[tuple[str, str]]) -> list[str]:
    """The examples that share two words of six letters or more with a graded line."""
    leaks = []
    for piece in pieces:
        words = set(LONG_WORD.findall(piece.lower()))
        for name, line in graded:
            shared = words & set(LONG_WORD.findall(line.lower()))
            if len(shared) >= 2:
                leaks.append(f"{piece!r} shares {sorted(shared)} with {name}")
    return leaks


class SkillExamplesGiveNoAnswerAwayTests(unittest.TestCase):
    """A skill's example must not be a piece an answer key grades: a blind run would be handed it.

    The run of 2026-11-25 found 7 traps of 7 on `release-skill`, one of them copied from the example
    of `harness-coach`."""

    def test_the_answer_keys_grade_lines_that_exist(self):
        graded = graded_lines()
        self.assertGreaterEqual(len(graded), 20)
        self.assertTrue(all(line.strip() for _, line in graded))

    def test_the_guard_sees_the_example_that_leaked(self):
        self.assertTrue(leaked_examples(["Refuse to release with uncommitted files"], graded_lines()))

    def test_the_guard_reads_the_examples_of_the_skills(self):
        found = [piece for path, _ in skill_files() for piece in example_pieces(read(path))]
        self.assertTrue(found, "no JSON example with a `piece` found in any SKILL.md: the guard reads nothing")

    def test_the_example_of_the_coach_is_one_the_command_accepts(self):
        block = EXAMPLE_BLOCK.search(read("skills/harness-coach/SKILL.md")).group(1)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(block)
            result = subprocess.run([sys.executable, os.path.join(ROOT, "cli", "harness.py"), "place", "review", path],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 piece read", result.stdout)

    def test_no_example_of_a_skill_is_a_graded_piece(self):
        graded = graded_lines()
        for path, _ in skill_files():
            with self.subTest(skill=path):
                self.assertEqual(leaked_examples(example_pieces(read(path)), graded), [])


def shadowed_names(path: str) -> list[str]:
    """Top-level classes and functions defined twice in a file, and methods defined twice in a class:
    the second definition silently replaces the first, and its tests stop running."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    twice = []
    for owner, body in [("", tree.body)] + [(n.name + ".", n.body) for n in tree.body if isinstance(n, ast.ClassDef)]:
        names = [n.name for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
        twice += sorted({owner + name for name in names if names.count(name) > 1})
    return twice


class NoTestIsShadowedTests(unittest.TestCase):
    """A test class or a test method defined twice in one file: only the last one runs. Seen on
    2026-11-25, when a second `ReviewTests` in test_place.py stopped ten tests without a failure."""

    def test_no_test_file_defines_a_name_twice(self):
        files = [path for root in CLI_ROOTS for path in python_files(root) if os.sep + "tests" + os.sep in path]
        self.assertGreaterEqual(len(files), 40)
        self.assertEqual({os.path.relpath(path, ROOT): names for path in files if (names := shadowed_names(path))}, {})

    def test_the_reader_sees_a_class_and_a_method_defined_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_x.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("class A:\n    def t(self): pass\n    def t(self): pass\nclass B: pass\nclass B: pass\n")
            self.assertEqual(shadowed_names(path), ["B", "A.t"])


class OwnLevelOneTests(unittest.TestCase):
    """This repository's AGENTS.md holds the level 1 it asks of others, measured as `harness status` measures it."""

    def setUp(self):
        self.facts = facts.collect(ROOT)

    def test_agents_md_holds_level_one_five_out_of_five(self):
        checks = maturity.level1(self.facts)
        self.assertEqual(len(checks), 5)
        self.assertEqual([check["id"] for check in checks if not check["passed"]], [])

    def test_agents_md_is_the_loaded_file_and_stays_short(self):
        source = self.facts["instructions"]["source"]
        self.assertEqual(source["path"], "AGENTS.md")
        self.assertGreater(source["lines"], 0)
        self.assertLessEqual(source["lines"], maturity.MAX_SOURCE_LINES)
        self.assertEqual(maturity.MAX_SOURCE_LINES, 60, "the limit this repository states in its level 1")


class OwnRulesGuardedTests(unittest.TestCase):
    """This repository's AGENTS.md names a guardrail on at least half of its rules, and every guardrail it
    names exists: what `harness rules` and the level 3 of `harness status` read."""

    def setUp(self):
        self.facts = facts.collect(ROOT)

    def test_at_least_half_of_the_rules_say_what_enforces_them(self):
        source = self.facts["instructions"]["source"]
        self.assertGreaterEqual(source["rules_total"], 8, "the rules of AGENTS.md must be found")
        self.assertGreaterEqual(source["rules_guarded"] * 2, source["rules_total"],
                                f"{source['rules_guarded']} of {source['rules_total']} rules name a guardrail")

    def test_every_guardrail_and_task_contract_agents_md_cites_exists(self):
        self.assertEqual(self.facts["dangling"], [])


class OwnMarketplaceMedalTests(unittest.TestCase):
    """This repository's marketplace keeps the medal it asks of others, measured as `harness medals` measures it."""

    def setUp(self):
        self.evaluated = medals.evaluate_marketplace(ROOT)

    def test_the_marketplace_medal_is_at_least_silver(self):
        medal = medals.build(self.evaluated)["medal"]
        self.assertGreaterEqual(medal["rank"], SILVER_RANK, f"the marketplace medal is {medal['name']}")

    def test_every_skill_description_says_when_to_use_it_and_when_not(self):
        described = {s["id"]: s for s in self.evaluated["successes"] if s["id"] in ("M2.when", "M2.when-not")}
        self.assertEqual(sorted(described), ["M2.when", "M2.when-not"])
        self.assertEqual({ident: s["evidence"] for ident, s in described.items() if not s["passed"]}, {})


if __name__ == "__main__":
    unittest.main()
