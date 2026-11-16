"""Le README ne promet que ce qui tourne : ses liens mènent quelque part, ses exemples passent dans les
commandes qu'il cite, et chaque sous-commande qu'il nomme existe."""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def readme() -> str:
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def run(*argv: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            return harness.main(list(argv))
        except SystemExit as exc:
            return int(exc.code or 0)


class ReadmeTests(unittest.TestCase):
    def test_every_relative_link_leads_somewhere(self):
        for target in re.findall(r"\]\(([^)#\s]+)", readme()):
            if "://" not in target:
                with self.subTest(target=target):
                    self.assertTrue(os.path.exists(os.path.join(ROOT, target)), target)

    def test_every_subcommand_it_names_exists(self):
        names = set(re.findall(r"harness\.py ([a-z]+)", readme()))
        self.assertGreaterEqual(len(names), 8)
        for name in sorted(names):
            with self.subTest(name=name):
                self.assertEqual(run(name, "--help"), 0)

    def test_the_examples_run_through_the_commands_it_cites(self):
        with tempfile.TemporaryDirectory() as tmp:
            examples = os.path.join(ROOT, "docs", "exemples")
            page = os.path.join(tmp, "p.html")
            self.assertEqual(run("report", "build", os.path.join(examples, "rapport.json"), "-o", page), 0)
            self.assertEqual(run("report", "from-place", os.path.join(examples, "morceaux.json"), "--kind", "skill",
                                 "--name", "release", "-o", page), 0)
            self.assertEqual(run("place", "plan", os.path.join(examples, "morceaux.json")), 0)

    def test_every_skill_it_names_is_shipped_and_finds_its_cli_once_installed(self):
        for name in re.findall(r"^\| [^|]+ \| `([a-z-]+)`", readme(), re.MULTILINE):
            in_sdlc = os.path.isdir(os.path.join(ROOT, "plugins/ai-sdlc/skills", name))   # un skill est dans un plugin ou l'autre
            folder = "plugins/ai-sdlc/skills" if in_sdlc else "skills"
            path = os.path.join(ROOT, folder, name, "SKILL.md")
            with self.subTest(name=name):
                self.assertTrue(os.path.isfile(path), path)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotRegex(text, r"python3 cli/", "le skill doit appeler ${CLAUDE_PLUGIN_ROOT}/cli/…")


if __name__ == "__main__":
    unittest.main()
