"""The guardrail against a corpus of commands it did not grow up with: `fixtures/guard/commands.json` was written
from the README's description of the hook, before its author read `guard.py`. Each command carries the verdict
expected of the guardrail; this test runs the guardrail on each, and holds the README's list of known limits to
the corpus. Nothing here is tuned to the code: when a verdict changes, the corpus entry and the README change."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import guard  # noqa: E402

CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_sdlc.py")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
CORPUS = os.path.join(ROOT, "fixtures", "guard", "commands.json")
README = os.path.join(ROOT, "README.md")

DELIVER, BENIGN, PASS_THROUGH, FALSE_REFUSAL = "deliver", "benign", "pass-through", "false-refusal"
REFUSED_TODAY = {DELIVER: True, BENIGN: False, PASS_THROUGH: False, FALSE_REFUSAL: True}
MIN_COMMANDS = 60
MIN_PER_VERDICT = {DELIVER: 20, BENIGN: 20, PASS_THROUGH: 3}


def _corpus() -> list[dict[str, str]]:
    with open(CORPUS, encoding="utf-8") as handle:
        return json.load(handle)["commands"]


def _of(verdict: str) -> list[dict[str, str]]:
    return [entry for entry in _corpus() if entry["expected"] == verdict]


def _readme_block(name: str) -> list[str]:
    with open(README, encoding="utf-8") as handle:
        text = handle.read()
    found = re.search(r"<!-- guard-corpus:%s -->\n(.*?)<!-- /guard-corpus:%s -->" % (name, name), text, re.DOTALL)
    if not found:
        raise AssertionError("README.md has no block <!-- guard-corpus:%s -->" % name)
    return [line for line in found.group(1).splitlines() if line.strip()]


def _readme_lines(verdict: str) -> list[str]:
    return ["- `%s`: %s" % (entry["command"], entry["why"]) for entry in _of(verdict)]


class CorpusShape(unittest.TestCase):
    def test_holds_at_least_sixty_commands_and_enough_of_each_verdict(self):
        self.assertGreaterEqual(len(_corpus()), MIN_COMMANDS)
        for verdict, floor in MIN_PER_VERDICT.items():
            self.assertGreaterEqual(len(_of(verdict)), floor, verdict)

    def test_each_entry_has_a_command_a_known_verdict_and_a_reason(self):
        for entry in _corpus():
            with self.subTest(command=entry.get("command")):
                self.assertTrue(entry["command"].strip())
                self.assertIn(entry["expected"], REFUSED_TODAY)
                self.assertIn(entry["blind"], (DELIVER, BENIGN, PASS_THROUGH))
                self.assertTrue(entry["why"].strip())
                self.assertNotIn("`", entry["command"] + entry["why"])   # both are quoted as they are in the README

    def test_no_command_appears_twice(self):
        commands = [entry["command"] for entry in _corpus()]
        self.assertEqual(len(commands), len(set(commands)))

    def test_a_verdict_changed_after_the_blind_draft_says_what_was_decided(self):
        for entry in _corpus():
            if entry["expected"] != entry["blind"] or entry["expected"] in (PASS_THROUGH, FALSE_REFUSAL):
                with self.subTest(command=entry["command"]):
                    self.assertTrue(entry.get("decision", "").strip())


class GuardOnTheCorpus(unittest.TestCase):
    def test_refuses_each_delivery(self):
        for entry in _of(DELIVER):
            with self.subTest(command=entry["command"]):
                self.assertTrue(guard.reasons(entry["command"]), "a delivery passes: " + entry["why"])

    def test_lets_each_ordinary_command_through(self):
        for entry in _of(BENIGN):
            with self.subTest(command=entry["command"]):
                self.assertEqual(guard.reasons(entry["command"]), [], "ordinary work is refused: " + entry["why"])

    def test_a_known_pass_through_still_passes(self):
        """When this fails the guardrail got better: move the entry to `deliver`, and it leaves the README."""
        for entry in _of(PASS_THROUGH):
            with self.subTest(command=entry["command"]):
                self.assertEqual(guard.reasons(entry["command"]), [])

    def test_a_pass_through_quoted_in_the_delivery_procedure_is_refused_where_the_corpus_says_so(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs", "agents"))
            with open(os.path.join(repo, "docs", "agents", "delivery.md"), "w", encoding="utf-8") as handle:
                handle.write("".join("- `%s`\n" % entry["command"] for entry in _of(PASS_THROUGH)))
            team = guard.team_lines(repo)
        for entry in _of(PASS_THROUGH):
            with self.subTest(command=entry["command"]):
                self.assertIs(bool(guard.reasons(entry["command"], team)), entry["refused_when_quoted"])

    def test_a_known_false_refusal_is_still_refused(self):
        """When this fails the guardrail got better: move the entry to `benign`, and it leaves the README."""
        for entry in _of(FALSE_REFUSAL):
            with self.subTest(command=entry["command"]):
                self.assertTrue(guard.reasons(entry["command"]))

    def test_the_command_line_gives_the_same_verdict_as_the_library(self):
        environ = {key: value for key, value in os.environ.items() if key not in guard.ALLOW_ENV_ALIASES}
        with tempfile.TemporaryDirectory() as repo:
            for verdict in REFUSED_TODAY:
                for entry in _of(verdict)[:2]:
                    with self.subTest(command=entry["command"]):
                        done = subprocess.run([sys.executable, CLI, "guard", "check", "--repo", repo, entry["command"]],
                                              capture_output=True, text=True, env=environ)
                        self.assertEqual(done.returncode, 1 if REFUSED_TODAY[verdict] else 0, done.stdout + done.stderr)


class ReadmeLimits(unittest.TestCase):
    def test_lists_exactly_the_pass_throughs_of_the_corpus(self):
        self.assertEqual(_readme_block("pass-through"), _readme_lines(PASS_THROUGH))

    def test_lists_exactly_the_false_refusals_of_the_corpus(self):
        self.assertEqual(_readme_block("false-refusal"), _readme_lines(FALSE_REFUSAL))

    def test_gives_the_counts_of_the_corpus(self):
        with open(README, encoding="utf-8") as handle:
            text = handle.read()
        deliveries = len(_of(DELIVER)) + len(_of(PASS_THROUGH))
        ordinary = len(_of(BENIGN)) + len(_of(FALSE_REFUSAL))
        self.assertIn("holds %d commands" % len(_corpus()), text)
        self.assertIn("refuses %d of the %d deliveries" % (len(_of(DELIVER)), deliveries), text)
        self.assertIn("refuses %d of the %d ordinary commands" % (len(_of(FALSE_REFUSAL)), ordinary), text)


if __name__ == "__main__":
    unittest.main()
