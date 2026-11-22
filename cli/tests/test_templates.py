"""The skill texts agree with what `harness status` counts: a Forbidden line counts in the
"enforced by a tool" ratio, so the template gives it the slot and the level-3 step says how to fill it."""
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
from harnesslib import facts, maturity  # noqa: E402
from harnesslib.github import parse_rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = "skills/harness-init/references/agents-template.md"
STEPS = "skills/harness-step/references/steps.md"
FORBIDDEN_ENFORCERS = ("permission deny", "PreToolUse hook", "branch protection")


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def step_1_block() -> str:
    """The AGENTS.md block of "Step 1", as the template gives it."""
    section = read(TEMPLATE).split("## Step 1 ", 1)[1]
    return re.search(r"```markdown\n(.*?)```", section, flags=re.S).group(1)


def forbidden_line() -> str:
    lines = step_1_block().split("## Forbidden\n", 1)[1].splitlines()
    return next(line for line in lines if line.startswith("- "))


def level_3_section() -> str:
    return read(STEPS).split("## Level 3 ", 1)[1].split("\n## ", 1)[0]


class ForbiddenLineTemplateTest(unittest.TestCase):
    def test_every_line_the_ratio_counts_has_the_enforced_by_slot(self):
        rules = parse_rules(step_1_block())

        self.assertEqual(len(rules), 2, "one Rules line and one Forbidden line are counted")
        for rule in rules:
            with self.subTest(rule=rule[:40]):
                self.assertRegex(rule, facts.GUARDED_RE)
                self.assertRegex(rule, facts.UNGUARDED_RE)

    def test_the_forbidden_line_names_what_can_enforce_a_forbidden_item(self):
        line = forbidden_line()

        slot = line.split("Enforced by:", 1)[1]
        for enforcer in FORBIDDEN_ENFORCERS:
            with self.subTest(enforcer=enforcer):
                self.assertIn(enforcer, slot)
        self.assertIn("| (unverified)", slot)
        self.assertRegex(line, r"Why: .*Enforced by: .*\[<YYYY-MM>\]$")

    def test_forbidden_lines_written_as_the_template_reach_the_enforced_ratio(self):
        with tempfile.TemporaryDirectory() as repo:
            rules = [f"- Rule {i}. Why: incident {i}. (unverified) [2026-11]" for i in range(3)]
            forbidden = [f"- Never do {i}. Why: incident {i}. Enforced by: {enforcer} [2026-11]"
                         for i, enforcer in enumerate(FORBIDDEN_ENFORCERS)]
            text = "\n".join(["# demo", "", "## Rules", *rules, "", "## Forbidden", *forbidden, ""])
            with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(text)

            source = facts.instruction_facts(repo)["source"]
            dangling = facts.dangling_facts(repo, text)

        self.assertEqual(source["rules_total"], 6)
        self.assertEqual(source["rules_guarded"], 3)
        self.assertGreaterEqual(source["rules_guarded"] / source["rules_total"], maturity.MIN_GUARDED_RATIO)
        self.assertEqual(dangling, [], "a permission, a hook or a branch protection is not a path to find")


class ForbiddenStepTest(unittest.TestCase):
    def test_the_level_3_step_has_a_forbidden_item_variant(self):
        section = level_3_section()

        variant = next((p for p in section.split("\n\n") if "nature=limit" in p), "")
        self.assertIn("`L3.guarded`", variant)
        self.assertRegex(variant, r"(?i)forbidden")
        self.assertIn("harness.py\" place one nature=limit", variant)
        for enforcer in FORBIDDEN_ENFORCERS:
            with self.subTest(enforcer=enforcer):
                self.assertIn(enforcer, variant)

    def test_the_command_the_step_points_to_asks_who_must_not_override_the_limit(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                harness.main(["place", "one", "nature=limit"])
            except SystemExit:
                pass

        self.assertIn("bypass_limit", out.getvalue())


class ForbiddenInitTextTest(unittest.TestCase):
    def test_harness_init_says_what_enforces_a_forbidden_item(self):
        text = read("skills/harness-init/SKILL.md")

        sentence = next(line for line in text.splitlines() if "each forbidden item" in line)
        for enforcer in FORBIDDEN_ENFORCERS:
            with self.subTest(enforcer=enforcer):
                self.assertIn(enforcer, sentence)


if __name__ == "__main__":
    unittest.main()
