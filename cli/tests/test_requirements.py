"""The requirements cite evidence that exists: every run or fixture path they name resolves
from the repository root, and the run counts of their "last checked" line are those of the
registry."""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY = os.path.join(ROOT, "fixtures", "results.jsonl")
LAST_CHECKED = re.compile(r"^Last checked against the registry: (\d{4}-\d{2}-\d{2})\b(.*)$", re.M)


def requirements() -> str:
    with open(os.path.join(ROOT, "docs", "requirements.md"), encoding="utf-8") as fh:
        return fh.read()


def registry() -> list[dict]:
    with open(REGISTRY, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def cited_paths(text: str) -> list[str]:
    """The quoted names that point at a fixture or at a recorded run."""
    quoted = re.findall(r"`([^`\s]+)`", text)
    return [q for q in quoted if q.startswith("fixtures/") or "runs/" in q]


class RequirementsTests(unittest.TestCase):
    def test_every_fixture_or_run_path_it_cites_resolves(self):
        paths = cited_paths(requirements())
        self.assertTrue(paths, "the requirements cite no evidence path")
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(glob.glob(os.path.join(ROOT, path)), path)

    def test_it_says_when_it_was_last_checked_against_the_registry(self):
        self.assertRegex(requirements(), LAST_CHECKED)

    def test_the_run_counts_it_states_are_those_of_the_registry(self):
        found = LAST_CHECKED.search(requirements())
        self.assertIsNotNone(found, "no 'Last checked against the registry' line")
        line = found.group(2)
        rows = registry()
        total = re.search(r"(\d+) runs", line)
        self.assertIsNotNone(total, "the line gives no total of runs")
        self.assertEqual(int(total.group(1)), len(rows))
        kinds = collections.Counter(row["kind"] for row in rows)
        stated = {kind: int(count) for count, kind in re.findall(r"(\d+) `([a-z]+)`", line)}
        self.assertEqual(stated, dict(kinds))


if __name__ == "__main__":
    unittest.main()
