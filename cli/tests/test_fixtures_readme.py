"""fixtures/README.md leads to every fixture family, its links lead somewhere and the
commands of its 'Running' block pass as written."""
from __future__ import annotations

import contextlib
import io
import os
import re
import shlex
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "fixtures")
CLI_PREFIX = "python3 cli/harness.py "


def page() -> str:
    with open(os.path.join(FIXTURES, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def families() -> list[str]:
    return sorted(name for name in os.listdir(FIXTURES) if os.path.isdir(os.path.join(FIXTURES, name)))


def family_rows() -> dict[str, str]:
    """The rows of the table that opens the page, before its first section, by family."""
    opening = page().split("\n## ", 1)[0]
    return {match.group(1): match.group(0) for match in re.finditer(r"^\| `([a-z]+)/` \|.*$", opening, re.MULTILINE)}


def running_commands() -> list[str]:
    block = re.search(r"^## Running\n+```bash\n(.*?)```", page(), re.MULTILINE | re.DOTALL)
    return [line.strip() for line in block.group(1).splitlines() if line.strip()] if block else []


def run(command: str) -> int:
    argv = shlex.split(command[len(CLI_PREFIX):])
    here = os.getcwd()
    os.chdir(ROOT)   # the page writes its paths from the root of the repository
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return harness.main(argv)
            except SystemExit as exc:
                return int(exc.code or 0)
    finally:
        os.chdir(here)


class FixturesReadmeTests(unittest.TestCase):
    def test_every_family_has_its_row_at_the_top(self):
        rows = family_rows()
        self.assertGreaterEqual(len(families()), 9)
        self.assertEqual(sorted(rows), families())

    def test_every_row_gives_a_grader_command_and_a_link(self):
        for family, row in family_rows().items():
            with self.subTest(family=family):
                self.assertRegex(row, r"`[a-z_./0-9 -]+\.py [a-z -]+`", "no grader command")
                self.assertRegex(row, r"\]\([^)]+\)", "no link")

    def test_a_family_with_its_own_page_is_linked_to_it_and_shares_its_grader(self):
        for family, row in family_rows().items():
            own = os.path.join(FIXTURES, family, "README.md")
            if not os.path.isfile(own):
                continue
            with open(own, encoding="utf-8") as fh:
                text = fh.read()
            with self.subTest(family=family):
                self.assertIn(f"]({family}/README.md)", row)
                commands = re.findall(r"`([a-z_./0-9 -]+\.py [a-z -]+)`", row)
                self.assertTrue(commands)
                for command in commands:
                    self.assertIn(command.strip(), text, "the family's page does not give this command")

    def test_every_relative_link_leads_somewhere(self):
        targets = [t for t in re.findall(r"\]\(([^)#\s]+)", page()) if "://" not in t]
        self.assertTrue(targets)
        for target in targets:
            with self.subTest(target=target):
                self.assertTrue(os.path.exists(os.path.join(FIXTURES, target)), target)

    def test_every_anchor_link_leads_to_a_heading(self):
        headings = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
                    for h in re.findall(r"^#+ (.+)$", page(), re.MULTILINE)}
        for anchor in re.findall(r"\]\(#([^)]+)\)", page()):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, headings)

    def test_the_running_block_passes_as_written(self):
        commands = running_commands()
        self.assertGreaterEqual(len(commands), 3)
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(command.startswith(CLI_PREFIX), command)
                self.assertEqual(run(command), 0)


if __name__ == "__main__":
    unittest.main()
