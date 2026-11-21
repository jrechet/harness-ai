"""The README promises only what runs: its links lead somewhere, its examples pass in the
commands it cites, and every subcommand it names exists."""
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
            examples = os.path.join(ROOT, "docs", "examples")
            page = os.path.join(tmp, "p.html")
            self.assertEqual(run("report", "build", os.path.join(examples, "report.json"), "-o", page), 0)
            self.assertEqual(run("report", "from-place", os.path.join(examples, "pieces.json"), "--kind", "skill",
                                 "--name", "release", "-o", page), 0)
            self.assertEqual(run("place", "plan", os.path.join(examples, "pieces.json")), 0)

    def test_every_skill_it_names_is_shipped_and_finds_its_cli_once_installed(self):
        for name in re.findall(r"^\| [^|]+ \| `([a-z-]+)`", readme(), re.MULTILINE):
            in_sdlc = os.path.isdir(os.path.join(ROOT, "plugins/ai-sdlc/skills", name))   # a skill lives in one plugin or the other
            folder = "plugins/ai-sdlc/skills" if in_sdlc else "skills"
            path = os.path.join(ROOT, folder, name, "SKILL.md")
            with self.subTest(name=name):
                self.assertTrue(os.path.isfile(path), path)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotRegex(text, r"python3 cli/", "the skill must call ${CLAUDE_PLUGIN_ROOT}/cli/…")

    def test_the_first_command_it_gives_is_the_plain_words_map(self):
        blocks = re.findall(r"```bash\n(.*?)```", readme(), re.DOTALL)
        first = next(block for block in blocks if "harness.py" in block)
        self.assertIn("status", first)
        self.assertIn("--map", first)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("status", tmp, "--map"), 0)

    def test_the_cli_table_lists_the_map(self):
        rows = [line for line in readme().splitlines() if line.startswith("| ") and "harness.py status" in line]
        self.assertTrue(any("--map" in row for row in rows), rows)

    def test_it_says_the_repository_is_private_next_to_the_clone_and_the_install(self):
        text = readme()
        for command in ("git clone https://github.com/jrechet/harness-ai.git", "/plugin marketplace add jrechet/harness-ai"):
            with self.subTest(command=command):
                at = text.index(command)
                nearby = text[at:at + 700]
                self.assertIn("private", nearby)
        at = text.index("/plugin marketplace add jrechet/harness-ai")
        self.assertIn("claude plugin marketplace add <clone folder>", text[at:at + 700])

    def test_it_shows_the_by_hand_road_to_the_template_blocks(self):
        text = readme()
        self.assertIn("](skills/harness-init/references/agents-template.md)", text)
        paragraph = next(p for p in text.split("\n\n") if "agents-template.md" in p)
        for word in ("By hand", "Step 1", "Step 2", "Step 4"):
            with self.subTest(word=word):
                self.assertIn(word, paragraph)
        with open(os.path.join(ROOT, "skills/harness-init/references/agents-template.md"), encoding="utf-8") as fh:
            template = fh.read()
        for step in re.findall(r"Step \d", paragraph):
            with self.subTest(step=step):
                self.assertRegex(template, rf"(?m)^## {step} ")

    def test_it_says_what_to_commit_and_what_to_ignore_in_the_harness_folder(self):
        sentence = next(p for p in readme().split("\n\n") if "state.html" in p and "Commit" in p)
        for name in ("config.json", "state.json", "audit.json", "harvest.json"):
            with self.subTest(name=name):
                self.assertIn(name, sentence)
        self.assertRegex(sentence, r"Ignore `\.harness/state\.html`")

    def test_it_says_the_review_loop_needs_github_and_that_is_still_true(self):
        self.assertRegex(readme(), r"review loop needs GitHub")
        self.assertEqual(run("harvest", "github", "--help"), 0)
        self.assertNotEqual(run("harvest", "gitlab", "--help"), 0)


if __name__ == "__main__":
    unittest.main()
