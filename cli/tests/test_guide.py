"""The map of skills/harness-guide answers "which skill or command for this?" for both plugins: it
names every shipped skill and every top-level subcommand of both CLIs as a whole word, every tool its
"Use" and "Not this" cells name exists, and every path it points to leads somewhere. A skill or a
subcommand added without its line in the map fails here, so the guide cannot quietly fall behind."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUIDE = os.path.join(ROOT, "skills", "harness-guide")
MAP = os.path.join(GUIDE, "references", "map.md")
SKILL_ROOTS = ("skills", "plugins/ai-sdlc/skills")
CLIS = {"harness": "cli/harness.py", "ai_sdlc.py": "plugins/ai-sdlc/cli/ai_sdlc.py"}
HELP_TIMEOUT_SECONDS = 60
USAGE_CHOICES = re.compile(r"\{([a-z,-]+)\}")
CITED_SKILL = re.compile(r"`((?!harness-ai`)(?:harness|flow)-[a-z]+)`")   # `harness-ai` is the plugin
CITED_PATH = re.compile(r"`(?:\$\{CLAUDE_PLUGIN_ROOT\}/)?((?:cli|docs|skills|plugins|fixtures|app)/[^`\s]*)`")
TABLE_HEADER = "| You want to… | Use | Not this |"
TOOL_IN_CELL = re.compile(r"`([^`]+)`")


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def shipped_skills() -> list[str]:
    return sorted(name for root in SKILL_ROOTS for name in os.listdir(os.path.join(ROOT, root))
                  if os.path.isfile(os.path.join(ROOT, root, name, "SKILL.md")))


def top_level_subcommands(script: str) -> list[str]:
    """The first `{a,b,…}` of the usage line: the CLI's top-level subcommands, as argparse knows them."""
    done = subprocess.run([sys.executable, os.path.join(ROOT, script), "--help"], capture_output=True,
                          text=True, timeout=HELP_TIMEOUT_SECONDS, check=True)
    found = USAGE_CHOICES.search(done.stdout)
    if not found:
        raise AssertionError(f"no subcommand list in the usage of {script}")
    return found.group(1).split(",")


def tools_in_use_cells(text: str) -> set[str]:
    """The backticked names of the "Use" and "Not this" cells of every routing table of the map."""
    named, in_table = set(), False
    for line in text.splitlines():
        if line.startswith(TABLE_HEADER):
            in_table = True
        elif in_table and line.startswith("|") and not line.startswith("|---"):
            cells = line.strip("|").split("|")
            named |= {name for cell in cells[1:3] for name in TOOL_IN_CELL.findall(cell)}
        elif not line.startswith("|"):
            in_table = False
    return named


class GuideMapTest(unittest.TestCase):
    def test_the_guide_skill_and_its_map_exist(self):
        self.assertTrue(os.path.isfile(os.path.join(GUIDE, "SKILL.md")))
        self.assertTrue(os.path.isfile(MAP))

    def test_every_shipped_skill_has_its_line_in_the_map(self):
        text = read(MAP)
        for name in shipped_skills():
            with self.subTest(skill=name):
                self.assertIn(f"`{name}`", text)

    def test_every_top_level_subcommand_of_both_clis_is_in_the_map(self):
        text = read(MAP)
        for prefix, script in CLIS.items():
            names = top_level_subcommands(script)
            self.assertGreaterEqual(len(names), 10, script)
            for name in names:
                with self.subTest(cli=prefix, subcommand=name):
                    self.assertRegex(text, rf"{re.escape(prefix)} {re.escape(name)}(?![a-z-])")

    def test_every_skill_the_map_cites_exists(self):
        shipped = set(shipped_skills())
        for name in sorted(set(CITED_SKILL.findall(read(MAP)))):
            with self.subTest(skill=name):
                self.assertIn(name, shipped)

    def test_every_tool_named_in_a_use_or_not_this_cell_exists(self):
        shipped = set(shipped_skills())
        named = tools_in_use_cells(read(MAP))
        self.assertGreaterEqual(len(named), 16)
        for tool in sorted(named):
            with self.subTest(tool=tool):
                self.assertTrue(tool in shipped or tool.split()[0] in CLIS, tool)

    def test_every_path_the_guide_points_to_exists(self):
        cited = set(CITED_PATH.findall(read(MAP)) + CITED_PATH.findall(read(os.path.join(GUIDE, "SKILL.md"))))
        self.assertGreaterEqual(len(cited), 5)
        for path in sorted(cited):
            with self.subTest(path=path):
                self.assertTrue(os.path.exists(os.path.join(ROOT, path.rstrip("/"))), path)

    def test_the_reader_sees_a_missing_skill_and_a_dead_path(self):
        self.assertEqual(CITED_SKILL.findall("use `harness-nope` or `flow-why` from `harness-ai`"),
                         ["harness-nope", "flow-why"])
        self.assertEqual(CITED_PATH.findall("see `docs/nope.md`, `${CLAUDE_PLUGIN_ROOT}/docs/x.md` and `README.md`"),
                         ["docs/nope.md", "docs/x.md"])
        table = f"{TABLE_HEADER}\n|---|---|---|\n| Ship it | `deploy` | `review` |\n\nafter"
        self.assertEqual(tools_in_use_cells(table), {"deploy", "review"})
        self.assertIsNone(re.search(r"harness stat(?![a-z-])", "`harness status`"))


if __name__ == "__main__":
    unittest.main()
