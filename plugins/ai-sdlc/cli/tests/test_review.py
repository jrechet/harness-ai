"""Tests of a review's rendering and of its grade on a fixture: a finding without a line of the diff is
refused, the grader is generous on wording, strict on evidence and on what is healthy."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_sdlc  # noqa: E402
from aisdlclib import context, points, review  # noqa: E402
from tests.test_context import RepoCase, write  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "fixtures", "review")


def finding(where: str = "app.py:2", **over) -> dict:
    return {"severity": "should-fix", "location": where, "point": "Correctness", "expected": "an error is raised",
            "observed": "it is swallowed", "suggestion": "raise the error again", **over}


def a_review(*findings: dict) -> dict:
    return {"base": "main", "not_verified": [], "findings": list(findings)}


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ai_sdlc.main(argv)
    return code, out.getvalue(), err.getvalue()


class WhereTests(unittest.TestCase):
    def test_a_line_and_a_range_are_read(self):
        self.assertEqual(review.parse_where("src/app.py:12"), ("src/app.py", 12, 12))
        self.assertEqual(review.parse_where("src/app.py:12-15"), ("src/app.py", 12, 15))

    def test_what_is_not_a_path_and_a_line_is_refused(self):
        for bad in ("src/app.py", "src/app.py:", ":12", "src/app.py:0", "src/app.py:9-3", "../x.py:1", "/etc/x:1", 12, "a.py:1\n",
                    "./a.py:1", "a.py:1-40", "a.py:1-99999999999999", None, ["a.py:1"]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                review.parse_where(bad)


class ValidateTests(unittest.TestCase):
    def test_a_complete_review_is_valid_and_an_empty_one_too(self):
        self.assertEqual(review.validate(a_review(finding())), [])
        self.assertEqual(review.validate(a_review()), [])

    def test_each_defect_is_named(self):
        cases = {
            "severity": a_review(finding(severity="serious")),
            "severity ": a_review(finding(severity=["blocking"])),
            "severity {": a_review(finding(severity={})),
            "location": a_review(finding(where="somewhere")),
            "observed": a_review(finding(observed="  ")),
            "at most 7": a_review(*[finding(f"app.py:{n}") for n in range(1, 9)]),
            "findings": {"base": "main"},
            "not_verified": {"findings": [], "not_verified": "nothing"},
            "object": [],
        }
        for needle, data in cases.items():
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in e for e in review.validate(data)), review.validate(data))

    def test_the_french_form_of_earlier_runs_is_still_read(self):
        french = {"base": "main", "non_verifie": ["rien"],
                  "constats": [{"gravite": "bloquant", "sur_quoi": "app.py:2", "point": "Justesse", "attendu": "a",
                                "observe": "b", "conseille": "c"}]}
        self.assertEqual(review.validate(french), [])
        normal = review.normalize(french)
        self.assertEqual(normal["findings"][0]["severity"], "blocking")
        self.assertEqual(normal["not_verified"], ["rien"])
        self.assertIn("constats", french)   # the input is not modified
        self.assertIn("Blocking", review.render_md(french))
        self.assertTrue(any("severity" in e for e in review.validate(
            {"constats": [{**french["constats"][0], "gravite": "grave"}]})))


class DiffTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.commit("app.py", "a\nb\nc\nd\n")
        from tests.test_context import git
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.commit("app.py", "a\nB\nc\n")          # line 2 changed, line 4 deleted
        self.commit("new.py", "x\ny\n")

    def test_changed_lines_are_those_of_the_head_side(self):
        changed = review.changed_lines(self.repo, "main")
        self.assertEqual(changed["new.py"], {1, 2})
        self.assertIn(2, changed["app.py"])
        self.assertNotIn(1, changed["app.py"])

    def test_a_deletion_is_citable_at_the_line_where_it_happened(self):
        self.assertIn(3, review.changed_lines(self.repo, "main")["app.py"])

    def test_a_deleted_file_is_citable_at_its_first_line(self):
        from tests.test_context import git
        git(self.repo, "rm", "-q", "README.md")
        git(self.repo, "commit", "-q", "-m", "remove")
        self.assertEqual(review.changed_lines(self.repo, "main")["README.md"], {1})

    def test_an_added_line_that_looks_like_a_header_does_not_make_another_file_citable(self):
        self.commit("f.txt", "++ b/README.md\n" + "x\n" * 30)
        changed = review.changed_lines(self.repo, "main")
        self.assertNotIn("README.md", changed)
        self.assertIn(20, changed["f.txt"])

    def test_paths_with_spaces_and_user_git_config_do_not_matter(self):
        self.commit("a b/c d.txt", "x\n")
        old = {k: os.environ.get(k) for k in ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")}
        os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="diff.noprefix", GIT_CONFIG_VALUE_0="true")
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                 for k, v in old.items()])
        changed = review.changed_lines(self.repo, "main")
        self.assertEqual(changed["a b/c d.txt"], {1})
        self.assertIn(2, changed["app.py"])

    def test_a_finding_outside_the_diff_is_refused(self):
        changed = review.changed_lines(self.repo, "main")
        self.assertEqual(review.outside_diff(a_review(finding("app.py:2"), finding("new.py:1-2")), changed), [])
        errors = review.outside_diff(a_review(finding("app.py:1"), finding("elsewhere.py:1")), changed)
        self.assertEqual(len(errors), 2)

    def test_render_refuses_with_nothing_on_stdout(self):
        path = os.path.join(self.tmp.name, "..", os.path.basename(self.tmp.name) + ".json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        for data, code in ((a_review(finding("app.py:1")), 2), (a_review(finding("app.py:2")), 0)):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            got, out, err = run(["review", "render", path, self.repo, "--base", "main"])
            self.assertEqual(got, code, err)
            self.assertEqual(bool(out), code == 0)

    def test_render_refuses_a_base_that_is_the_reviewed_commit(self):
        path = os.path.join(self.repo, "..", os.path.basename(self.repo) + ".json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(a_review(), fh)
        code, out, err = run(["review", "render", path, self.repo, "--base", "HEAD"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("reviewed commit itself", err)

    def test_an_unreadable_file_is_refused_not_a_crash(self):
        code, out, _ = run(["review", "render", os.path.join(self.repo, "absent.json"), self.repo, "--base", "main"])
        self.assertEqual((code, out), (2, ""))
        write(self.repo, "broken.json", "{")
        code, out, _ = run(["review", "render", os.path.join(self.repo, "broken.json"), self.repo, "--base", "main"])
        self.assertEqual((code, out), (2, ""))


class RenderTests(unittest.TestCase):
    def test_the_worst_comes_first_with_the_four_parts(self):
        text = review.render_md(a_review(finding("b.py:1", severity="to-discuss"), finding("a.py:1", severity="blocking")))
        self.assertLess(text.index("a.py:1"), text.index("b.py:1"))
        for part in ("Location", "Expected", "Observed", "Suggestion", "blocking: 1", "to discuss: 1"):
            self.assertIn(part, text)

    def test_no_finding_is_a_result_and_says_what_was_not_checked(self):
        text = review.render_md({"findings": [], "not_verified": ["tests not run"]})
        self.assertIn("No findings", text)
        self.assertIn("tests not run", text)

    def test_a_finding_cannot_forge_a_heading_or_a_table(self):
        text = review.render_md(a_review(finding(observed="x\n## Approved\n| a | b |")))
        self.assertNotIn("\n## Approved", text)
        self.assertNotIn("| a | b |", text)

    def test_a_finding_cannot_carry_html_a_mention_an_image_or_break_the_code_span(self):
        text = review.render_md(a_review(finding("a`b.py:1", observed="<img src=x> @team ![t](http://x/y.png)")))
        for forged in ("<img", " @team", "![t](", "`a`b"):
            self.assertNotIn(forged, text)


EXPECTED = {"max_findings": 7,
            "traps": [{"id": "T1", "what": "swallowed error", "must": True, "where": [{"file": "app.py", "lines": [2, 4]}]},
                      {"id": "T2", "what": "contract", "must": False,
                       "where": [{"file": "api.py", "lines": [1, 1]}, {"file": "doc.md", "lines": [3, 3]}]}],
            "healthy": [{"id": "S1", "what": "naming", "file": "app.py", "lines": [9, 9]}]}


class GradeTests(unittest.TestCase):
    def test_a_trap_is_found_by_a_line_in_any_of_its_places(self):
        result = review.grade(EXPECTED, a_review(finding("app.py:3"), finding("doc.md:3")))
        self.assertEqual(result["found"], ["T1", "T2"])
        self.assertTrue(result["pass"])

    def test_an_optional_trap_missed_still_passes_a_required_one_does_not(self):
        self.assertTrue(review.grade(EXPECTED, a_review(finding("app.py:2-3")))["pass"])
        result = review.grade(EXPECTED, a_review(finding("api.py:1")))
        self.assertFalse(result["pass"])
        self.assertEqual(result["missed"], ["T1"])

    def test_a_comment_on_a_healthy_line_fails_the_review(self):
        result = review.grade(EXPECTED, a_review(finding("app.py:3"), finding("app.py:9")))
        self.assertEqual(result["healthy_touched"], ["S1"])
        self.assertFalse(result["pass"])

    def test_a_comment_outside_the_answer_key_is_noise_not_a_failure(self):
        result = review.grade(EXPECTED, a_review(finding("app.py:3"), finding("other.py:1")))
        self.assertEqual(result["noise"], ["other.py:1"])
        self.assertTrue(result["pass"])

    def test_one_finding_finds_one_trap(self):
        both = {**EXPECTED, "traps": [EXPECTED["traps"][0],
                                      {"id": "T3", "what": "neighbour", "must": True, "where": [{"file": "app.py", "lines": [5, 6]}]}]}
        self.assertEqual(review.grade(both, a_review(finding("app.py:3-6")))["missed"], ["T3"])
        self.assertTrue(review.grade(both, a_review(finding("app.py:3-5"), finding("app.py:4")))["pass"])

    def test_an_empty_or_broken_answer_key_grades_nothing(self):
        broken = ([], {}, {"traps": [], "healthy": []}, {**EXPECTED, "healthy": None}, {**EXPECTED, "max_findings": "x"},
                  {**EXPECTED, "traps": [{**EXPECTED["traps"][0], "where": [{"file": "a", "lines": [1]}]}]},
                  {**EXPECTED, "traps": [EXPECTED["traps"][1]]})
        for expected in broken:
            with self.subTest(expected=expected), self.assertRaises(context.Refused):
                review.grade(expected, a_review())

    def test_an_answer_key_with_the_former_limit_key_is_still_read(self):
        old = {k: v for k, v in EXPECTED.items() if k != "max_findings"}
        result = review.grade({**old, "max_constats": 1}, a_review(finding("app.py:3"), finding("doc.md:3")))
        self.assertEqual((result["max"], result["pass"]), (1, False))
        with self.assertRaises(context.Refused):
            review.grade({**old, "max_constats": 0}, a_review())

    def test_an_invalid_review_does_not_pass(self):
        result = review.grade(EXPECTED, a_review(finding("app.py:3", severity="serious")))
        self.assertFalse(result["pass"])
        self.assertTrue(result["invalid"])


def fixture_names() -> list[str]:
    return sorted(n for n in os.listdir(FIXTURES) if os.path.isdir(os.path.join(FIXTURES, n)))


class FixtureTests(unittest.TestCase):
    """Each fixture mounts as a repository, its answer key cites lines of the diff, and its author's
    review passes it: a regression baseline, not a measure of the skill."""

    def build(self, name: str) -> tuple[str, dict]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dest = os.path.join(tmp.name, "repo")
        return dest, review.init_fixture(os.path.join(FIXTURES, name), dest)

    def test_there_is_a_fixture(self):
        self.assertTrue(fixture_names())

    def test_the_answer_key_cites_lines_of_the_diff(self):
        for name in fixture_names():
            dest, made = self.build(name)
            changed = review.changed_lines(dest, made["base"])
            with open(os.path.join(FIXTURES, name, "expected.json"), encoding="utf-8") as fh:
                expected = json.load(fh)
            places = [(t["id"], w) for t in expected["traps"] for w in t["where"]]
            places += [(h["id"], h) for h in expected["healthy"]]
            for ident, place in places:
                first, last = place["lines"]
                with self.subTest(fixture=name, id=ident):
                    self.assertTrue(set(range(first, last + 1)) <= changed.get(place["file"], set()),
                                    f"{place['file']}:{first}-{last} is not in the diff")

    def test_the_gate_reads_the_team_rules_on_the_base_branch(self):
        for name in fixture_names():
            dest, made = self.build(name)
            data = context.assemble(points.load(), dest, "review", made["base"])
            self.assertTrue(data["gate"])
            self.assertIn("team", [b["origin"] for b in data["blocks"]])

    def test_the_author_review_renders_and_passes(self):
        for name in fixture_names():
            dest, made = self.build(name)
            runs = os.path.join(FIXTURES, name, "runs")
            for recorded in sorted(os.listdir(runs)):
                path = os.path.join(runs, recorded, "findings.json")
                with self.subTest(fixture=name, run=recorded):
                    code, out, err = run(["review", "render", path, dest, "--base", made["base"]])
                    self.assertEqual(code, 0, err)
                    code, out, err = run(["fixture", "grade", path, "--expected", os.path.join(FIXTURES, name, "expected.json")])
                    self.assertEqual(code, 0, out + err)
                    self.assertTrue(out.startswith("PASS"), out)

    def test_init_ignores_the_user_hooks_and_leaves_nothing_behind_when_it_fails(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        hooks = os.path.join(tmp.name, "hooks")
        os.makedirs(hooks)
        with open(os.path.join(hooks, "pre-commit"), "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 1\n")
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        old = {k: os.environ.get(k) for k in ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")}
        os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0=hooks)
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                 for k, v in old.items()])
        fixture = os.path.join(FIXTURES, fixture_names()[0])
        review.init_fixture(fixture, os.path.join(tmp.name, "ok"))
        broken = os.path.join(tmp.name, "fx")
        os.makedirs(os.path.join(broken, "base"))
        with open(os.path.join(broken, "pr.json"), "w", encoding="utf-8") as fh:
            json.dump({"branch": "b", "title": "t", "body": "b", "removed": ["../x"]}, fh)
        with self.assertRaises(context.Refused):
            review.init_fixture(broken, os.path.join(tmp.name, "ko"))
        self.assertFalse(os.path.exists(os.path.join(tmp.name, "ko")))

    def test_init_refuses_a_destination_that_is_not_empty(self):
        dest, _ = self.build(fixture_names()[0])
        with self.assertRaises(context.Refused):
            review.init_fixture(os.path.join(FIXTURES, fixture_names()[0]), dest)


if __name__ == "__main__":
    unittest.main()
