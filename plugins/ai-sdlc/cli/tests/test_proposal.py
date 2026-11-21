"""Tests of the proposal's "As built" section: the proposal is the initial design and is not
rewritten, so its last section says what the plugin ships today. Its two tables are compared with
points.json, the file the CLI reads: a point or a phase added there without its row here fails."""
from __future__ import annotations

import json
import os
import re
import unittest

CLI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CLI)))
PROPOSAL = os.path.join(ROOT, "docs", "ai-sdlc", "proposal.md")
POINTS = os.path.join(CLI, "aisdlclib", "points.json")
HEADING = re.compile(r"^## As built \((\d{4}-\d{2}-\d{2})\)$")
BRANCHES = {"base": "base branch", "current": "current branch"}


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _as_built(text: str) -> list[str]:
    """The lines of the "As built" section, heading included; empty if the section is missing."""
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if HEADING.match(line)]
    if not starts:
        return []
    rest = lines[starts[0] + 1:]
    end = next((index for index, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return [lines[starts[0]], *rest[:end]]


def _tables(lines: list[str]) -> list[list[list[str]]]:
    """The Markdown tables of a section, each as its rows of cells, the separator row dropped."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*lines, ""]:
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(set(cell) <= set("-: ") for cell in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def _table(lines: list[str], first_header: str) -> list[list[str]]:
    """The body rows of the table whose first header cell is the given one."""
    for table in _tables(lines):
        if table[0][0] == first_header:
            return table[1:]
    return []


def _code(name: str) -> str:
    return f"`{name}`"


class AsBuiltSection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(PROPOSAL)
        cls.section = _as_built(cls.text)
        cls.config = json.loads(_read(POINTS))

    def test_the_proposal_says_at_its_top_that_it_is_the_initial_proposal(self) -> None:
        top = self.text.split("\n## ", 1)[0]
        self.assertIn("initial proposal", top)
        self.assertIn("(#as-built-", top)

    def test_the_as_built_section_is_dated_and_closes_the_document(self) -> None:
        self.assertTrue(self.section, "no '## As built (YYYY-MM-DD)' section in the proposal")
        headings = [line for line in self.text.splitlines() if line.startswith("## ")]
        self.assertEqual(headings[-1], self.section[0])

    def test_the_points_table_matches_points_json(self) -> None:
        expected = [
            [
                _code(name),
                ", ".join(_code("/" + phase) for phase in point["read_by"]),
                "yes" if point["replaceable"] else "no",
                BRANCHES[point["branch"]],
            ]
            for name, point in self.config["points"].items()
        ]
        self.assertEqual(len(expected), 8)
        self.assertEqual(_table(self.section, "Point"), expected)

    def test_the_levels_table_matches_points_json(self) -> None:
        expected = [[_code("/" + name), str(phase["min_level"])] for name, phase in self.config["phases"].items()]
        self.assertEqual(len(expected), 7)
        self.assertEqual(_table(self.section, "Phase"), expected)

    def test_the_section_names_the_plugin_s_own_cli(self) -> None:
        self.assertIn("plugins/ai-sdlc/cli/ai_sdlc.py", "\n".join(self.section))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "plugins", "ai-sdlc", "cli", "ai_sdlc.py")))


class Parsing(unittest.TestCase):
    def test_a_missing_section_gives_no_line(self) -> None:
        self.assertEqual(_as_built("# Title\n\n## Other\n\ntext\n"), [])

    def test_the_section_stops_at_the_next_heading(self) -> None:
        text = "## As built (2026-01-02)\n\n| Point | A |\n|---|---|\n| `x` | y |\n\n## Next\n\n| Point | A |\n"
        section = _as_built(text)
        self.assertEqual(section[0], "## As built (2026-01-02)")
        self.assertEqual(_table(section, "Point"), [["`x`", "y"]])
        self.assertEqual(_table(section, "Phase"), [])


if __name__ == "__main__":
    unittest.main()
