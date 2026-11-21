"""This repository follows the rules its AGENTS.md states: the CLIs import only the standard
library, no build leftover is committed, every skill calls a CLI that exists through the plugin
root, and its own AGENTS.md holds level 1."""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, maturity  # noqa: E402

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
        try:
            done = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True, check=False)
        except OSError as exc:
            self.skipTest(f"git is not available: {exc}")
        if done.returncode != 0:
            self.skipTest("not in a git checkout")
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
        self.assertGreaterEqual(len(skill_files()), 13)

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


if __name__ == "__main__":
    unittest.main()
