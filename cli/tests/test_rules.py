"""Tests of `harness rules`: what counts as a rule in an instruction file, and what is only a line."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, github, maturity, rules  # noqa: E402

TODAY = date(2026, 11, 21)

# The shape of this repository's own AGENTS.md: rules, forbidden things, a working process whose last
# bullet is enforced, a description of the pipelines, and housekeeping sections.
OWN_SHAPE = """# demo — instructions for agents

Mode: **delegation**.

## What this repo does
- Skills and a CLI.

## Rules
- Everything that must be guaranteed goes into `cli/`. Why: the grid applied to ourselves. (unverified) [2026-11]
- An answer key is strict on evidence. Why: two audits diverge. (unverified) [2026-11]

## Forbidden
- Reading an answer key during a blind run. [2026-11]
- Starting a blind run without the owner's request. Why: about 130,000 tokens per run. [2026-11]

## Working process
- Open questions are asked at the end of the message.
- A task is done when the tests pass.
- All work has its row in the progress plan. Enforced by: Stop hook, `python3 cli/harness.py progress check` [2026-11]

## Available CI/CD
- GitHub Actions: `.github/workflows/ci.yml` runs `scripts/ci/verify.sh`. [2026-11]
- Forge: `.forgejo/workflows/ci.yml` runs the same script. [2026-11]

## Delegated tasks
- `harness-stress` — a campaign, on request.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule.
"""

# A file of notes: a session log, a to-do list, open questions. No Rules or Forbidden heading.
NOTES = """# vibe-app

## Stack
- React and Vite.
- Supabase for the data.

## Session log
- 2026-10-02: moved the cart to a context.
- 2026-10-03: the build broke on the image import, fixed.

## TODO
- [ ] add the tests of the cart
- [x] remove the unused route

## Open questions
- Do we keep the legacy checkout?

## Deploy
- The deploy goes through the pipeline only. Enforced by: `scripts/check-deploy.sh`
"""

# The same notes around a real Rules section.
NOTES_WITH_RULES = NOTES + """
## Rules
- Prices are computed on the server. Why: incident #7.

### Database
- No migration drops a column. Why: incident #12.

## Scratch
- try the new router one day
"""


def write(root: str, rel: str, content: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class IterRulesTests(unittest.TestCase):
    def test_a_bullet_that_says_enforced_by_is_a_rule_in_any_section(self):
        found = github.parse_rules(OWN_SHAPE)
        enforced = [r for r in found if "Enforced by:" in r]
        self.assertEqual(len(enforced), 1)
        self.assertTrue(enforced[0].startswith("All work has its row"))

    def test_the_other_bullets_of_the_working_process_are_still_not_rules(self):
        found = github.parse_rules(OWN_SHAPE)
        self.assertFalse([r for r in found if r.startswith(("Open questions", "A task is done"))])

    def test_pipeline_descriptions_are_not_rules(self):
        found = github.parse_rules(OWN_SHAPE)
        self.assertFalse([r for r in found if r.startswith(("GitHub Actions", "Forge"))])
        self.assertEqual(github.parse_rules("## Pitfalls\n- a\n## CI/CD disponibles\n- GitHub Actions: x\n"), ["a"])

    def test_own_shape_gives_the_rules_the_forbidden_and_the_enforced_bullet(self):
        self.assertEqual([line for line, _ in github.iter_rules(OWN_SHAPE)], [9, 10, 13, 14, 19])

    def test_the_enforced_marker_is_read_in_french_too(self):
        text = "## Règles\n- r\n## Processus de travail\n- p\n- q. Vérifiée par : hook Stop\n"
        self.assertEqual(github.parse_rules(text), ["r", "q. Vérifiée par : hook Stop"])

    def test_with_a_rules_heading_only_its_bullets_and_the_enforced_ones_count(self):
        found = github.parse_rules(NOTES_WITH_RULES)
        self.assertEqual(found, ["The deploy goes through the pipeline only. Enforced by: `scripts/check-deploy.sh`",
                                 "Prices are computed on the server. Why: incident #7.",
                                 "No migration drops a column. Why: incident #12."])

    def test_a_subsection_of_rules_ends_at_the_next_heading_of_the_same_level(self):
        text = "## Rules\n- a\n### Database\n- b\n## Notes\n- c\n### Rules of the game\n- d\n## Other\n- e\n"
        self.assertEqual(github.parse_rules(text), ["a", "b", "d"])

    def test_without_a_rules_heading_every_bullet_is_kept(self):
        self.assertFalse(github.has_rule_headings(NOTES))
        self.assertEqual(len(github.parse_rules(NOTES)), 8)

    def test_rule_headings_are_recognised_in_both_languages(self):
        for heading in ("## Rules", "## Forbidden", "## Règles", "## Interdits", "### Coding rules", "# RULES"):
            with self.subTest(heading=heading):
                self.assertTrue(github.has_rule_headings(heading + "\n- x\n"))
        for heading in ("## Pitfalls", "## Database", "## Unruly things", "## Maintenance rules of this file"):
            with self.subTest(heading=heading):
                self.assertFalse(github.has_rule_headings(heading + "\n- x\n"))


class RulesCommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_own_shape_lists_the_enforced_bullet_as_guarded_and_no_pipeline(self):
        write(self.repo, "AGENTS.md", OWN_SHAPE)
        rows = rules.collect(self.repo, TODAY, blame=False)
        self.assertEqual([r["line"] for r in rows], [9, 10, 13, 14, 19])
        self.assertEqual([r["line"] for r in rows if r["guarded"]], [19])
        self.assertTrue(all(r["kind"] == "rule" for r in rows))
        out = rules.render_markdown(rows)
        self.assertIn("5 rule(s)", out)
        self.assertIn("1 with a guardrail", out)
        self.assertNotIn("not rules", out)

    def test_a_notes_file_is_listed_as_lines_not_rules(self):
        write(self.repo, "CLAUDE.md", NOTES)
        rows = rules.collect(self.repo, TODAY, blame=False)
        self.assertEqual([r["kind"] for r in rows].count("rule"), 1)      # the bullet that says Enforced by
        self.assertEqual([r["kind"] for r in rows].count("line"), 7)
        out = rules.render_markdown(rows)
        self.assertIn("lines, not rules", out)
        self.assertIn("CLAUDE.md", out.split("lines, not rules")[1])
        self.assertIn("1 rule(s)", out)
        self.assertIn("7 line(s)", out)
        self.assertNotIn("8 rule(s)", out)

    def test_a_notes_file_with_a_rules_section_lists_only_its_rules(self):
        write(self.repo, "CLAUDE.md", NOTES_WITH_RULES)
        rows = rules.collect(self.repo, TODAY, blame=False)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["kind"] == "rule" for r in rows))
        self.assertNotIn("not rules", rules.render_markdown(rows))

    def test_each_file_is_judged_on_its_own_headings(self):
        write(self.repo, "AGENTS.md", OWN_SHAPE)
        write(self.repo, "apps/web/CLAUDE.md", "# Web\n- Everything goes through `escapeHtml`. Why: pentest.\n")
        kinds = {r["file"]: r["kind"] for r in rules.collect(self.repo, TODAY, blame=False)}
        self.assertEqual(kinds, {"AGENTS.md": "rule", "apps/web/CLAUDE.md": "line"})


class ProjectRulesHeadingTests(unittest.TestCase):
    """The reading taken for a file that has a rules heading next to other sections of constraints,
    on the django-mvc sample project: "## Project rules" makes the file strict, so the bullets of
    "Compatibility" and "Style" are no longer counted. The totals move, the level boxes do not."""
    REPO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "fixtures", "repos", "django-mvc", "repo")

    def setUp(self):
        with open(os.path.join(self.REPO, "AGENTS.md"), encoding="utf-8") as fh:
            self.text = fh.read()

    def test_only_the_bullets_under_project_rules_are_counted(self):
        self.assertTrue(github.has_rule_headings(self.text))
        found = github.iter_rules(self.text)
        self.assertEqual(len(found), 7)
        lines = self.text.splitlines()
        start = lines.index("## Project rules") + 1
        end = lines.index("## Git") + 1
        for number, _ in found:
            self.assertTrue(start < number < end, f"line {number} is outside Project rules")

    def test_the_compatibility_and_style_bullets_are_left_out(self):
        found = github.parse_rules(self.text)
        self.assertFalse([r for r in found if "Python 3.8" in r or "Django 4.2" in r or "PEP 8" in r])

    def test_the_level_boxes_fed_by_the_ratios_stay_unticked(self):
        collected = facts.collect(self.REPO, today=TODAY)
        source = collected["instructions"]["source"]
        self.assertEqual((source["rules_total"], source["rules_guarded"]), (7, 1))
        boxes = {c["id"]: c["passed"] for c in maturity.level3(collected)}
        self.assertFalse(boxes["L3.guarded"])
        self.assertFalse(boxes["L3.justified"])


if __name__ == "__main__":
    unittest.main()
