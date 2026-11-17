"""Tests of a change's size and of the /dev PR body: the size comes from rules, the sensitive zones are
read on the base branch, and a body incomplete for its size is not rendered."""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, dev, points, size  # noqa: E402
from tests.test_context import RepoCase, git  # noqa: E402
from tests.test_review import run  # noqa: E402

ZONES = "---\npoint: sensitive-zones\nmode: append\n---\n- `billing/**`, `price.py` — the customer's money. (unverified) [2026-05]\n"


def body(**over) -> dict:
    return {"title": "fix: rounding", "ticket": "INV-1", "changes": ["rounding happens to the cent"],
            "why": "the totals were wrong", "plan": ["fix", "test"],
            "checked": [{"command": "python3 -m unittest", "result": "12 tests OK"}], "not_verified": [], **over}


class GlobTests(unittest.TestCase):
    def test_a_star_stays_in_a_folder_and_two_stars_cross_them(self):
        cases = {"migrations/**": (["migrations/1.sql", "migrations/a/b.sql", "migrations", "Migrations/x.sql",
                                   "migrations/a\nb.sql"], ["src/migrations/1.sql", "migrationsx"]),
                 "/infra/": (["infra", "infra/a/b"], ["infrastructure/a"]),
                 "**/auth/**": (["auth", "src/auth", "src/auth/login.py"], ["src/author.py"]),
                 "**/migrations/**": (["migrations/1.sql", "a/b/migrations/1.sql"], ["a/migrations.sql"]),
                 "**/*.tf": (["main.tf", "infra/a/main.tf"], ["main.tfvars"]),
                 "*.md": (["A.md"], ["docs/A.md"]),
                 "AGENTS.md": (["AGENTS.md"], ["docs/AGENTS.md", "AGENTSxmd"])}
        for glob, (yes, no) in cases.items():
            regex = size.glob_regex(glob)
            for path in yes:
                self.assertTrue(regex.match(path), (glob, path))
            for path in no:
                self.assertFalse(regex.match(path), (glob, path))

    def test_zones_are_the_backticked_globs_of_each_bullet_with_their_reason(self):
        zones = size.parse_zones("A text.\n- `a/**`, `b.py` — the money.\n- not a pattern\n", "team")
        self.assertEqual([(z["glob"], z["why"], z["origin"]) for z in zones],
                         [("a/**", "the money.", "team"), ("b.py", "the money.", "team")])

    def test_a_list_line_that_cites_a_glob_in_another_shape_is_refused_not_dropped(self):
        for line in ("- `a/**` and `b/**`", "1. `d/**`", "- The folder `e/**`", "-`f/**`", "- `h/[ab].py`", "- `**`"):
            with self.subTest(line=line), self.assertRaises(context.Refused):
                size.parse_zones(line + "\n", "team")

    def test_the_shipped_zones_parse(self):
        zones = size.parse_zones(points.default_text(points.load()["points"]["sensitive-zones"]), "base")
        self.assertIn("migrations/**", [z["glob"] for z in zones])


class SizeTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.table = points.load()
        self.commit("app.py", "a\n" * 50)
        git(self.repo, "checkout", "-q", "-b", "pr")

    def size(self, **kw):
        return size.classify(self.table, self.repo, "main", **kw)

    def test_a_few_lines_in_one_file_is_xs(self):
        self.commit("app.py", "b\n" + "a\n" * 49)
        result = self.size()
        self.assertEqual((result["size"], result["files"], result["lines"]), ("XS", 1, 2))

    def test_an_ordinary_change_is_s_m_and_a_big_one_is_l(self):
        self.commit("app.py", "b\n" * 50)
        self.assertEqual(self.size()["size"], "S-M")
        self.commit("big.py", "x\n" * 500)
        self.assertEqual(self.size()["size"], "L")

    def test_many_files_make_it_l_even_with_few_lines(self):
        for n in range(21):
            self.commit(f"f{n}.py", "x\n")
        self.assertEqual(self.size()["size"], "L")

    def test_a_shipped_sensitive_zone_makes_one_line_l(self):
        self.commit("migrations/002.sql", "x\n")
        result = self.size()
        self.assertEqual(result["size"], "L")
        self.assertEqual(result["sensitive"][0]["origin"], "base")

    def test_the_team_zones_are_read_on_the_base_branch(self):
        self.commit("billing/t.py", "x\n")
        self.assertEqual(self.size()["size"], "XS")
        self.commit("docs/agents/sensitive-zones.md", ZONES)      # set by the PR: does not count for it
        self.assertFalse([h for h in self.size()["sensitive"] if h["origin"] == "team"])
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/agents/sensitive-zones.md", ZONES)
        git(self.repo, "checkout", "-q", "-b", "pr2")
        self.commit("billing/t.py", "x\n")
        self.assertEqual(self.size()["sensitive"][0]["glob"], "billing/**")

    def test_a_pr_cannot_take_its_files_out_of_the_zones(self):
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/agents/sensitive-zones.md", ZONES)
        git(self.repo, "checkout", "-q", "-b", "pr3")
        self.commit("docs/agents/sensitive-zones.md", ZONES.replace("`billing/**`, ", ""))
        self.commit("billing/t.py", "x\n")
        self.assertIn("billing/t.py", [h["path"] for h in self.size()["sensitive"]])

    def test_before_the_code_planned_paths_say_sensitive_or_leave_it_open(self):
        self.assertEqual(self.size(paths=[".github/workflows/ci.yml"])["size"], "L")
        result = self.size(paths=["app.py"])
        self.assertIsNone(result["size"])
        self.assertTrue(result["planned"])

    def test_planned_paths_are_normalised_and_cannot_leave_the_repo(self):
        for path in ("./AGENTS.md", "migrations", "Migrations/x.sql", "./.github/workflows/../workflows/ci.yml"):
            self.assertEqual(self.size(paths=[path])["size"], "L", path)
        for path in ("/etc/passwd", "../x", "."):
            with self.subTest(path=path), self.assertRaises(context.Refused):
                self.size(paths=[path])

    def test_a_file_git_cannot_count_does_not_pass_for_empty(self):
        self.commit(".gitattributes", "big.txt -diff\n")
        self.commit("big.txt", "x\n" * 5000)
        result = self.size()
        self.assertEqual(result["size"], "L")
        self.assertTrue(any("big.txt" in r for r in result["reasons"]))

    def test_a_symlink_named_like_a_zone_is_in_the_zone(self):
        os.makedirs(os.path.join(self.repo, "db"))
        os.symlink("../app.py", os.path.join(self.repo, "db", "migrations"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "link")
        self.assertEqual(self.size()["size"], "L")

    def test_no_change_to_measure_is_refused(self):
        with self.assertRaises(context.Refused):
            size.classify(self.table, self.repo, "HEAD")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "empty")
        with self.assertRaises(context.Refused):
            self.size()


class BodyTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.table = points.load()
        git(self.repo, "checkout", "-q", "-b", "pr")

    def check(self, data):
        return dev.checked(self.table, data, self.repo, "main")

    def test_an_xs_change_needs_no_plan_but_says_what_was_checked(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(plan=[]))
        text = dev.render_md(content, sized)
        for part in ("## What changes", "## Why", "INV-1", "## Verified", "## Not verified", "Computed size: XS"):
            self.assertIn(part, text)
        self.assertNotIn("## Plan", text)

    def test_an_s_m_change_without_plan_is_refused(self):
        self.commit("a.py", "x\n" * 60)
        with self.assertRaises(context.Refused) as ctx:
            self.check(body(plan=[]))
        self.assertIn("S-M", str(ctx.exception))
        self.check(body())

    def test_an_l_change_needs_its_plan_file_committed_in_the_branch(self):
        self.commit("migrations/002.sql", "x\n")
        for plan_file in (None, "docs/plans/absent.md", "migrations/002.sql"):
            with self.subTest(plan_file=plan_file), self.assertRaises(context.Refused):
                self.check(body(plan_file=plan_file))
        self.commit("docs/plans/inv-1.md", "\n")
        with self.assertRaises(context.Refused):
            self.check(body(plan_file="docs/plans/inv-1.md"))
        self.commit("docs/plans/inv-1.md", "the plan\n")
        content, sized = self.check(body(plan_file="docs/plans/inv-1.md"))
        text = dev.render_md(content, sized)
        self.assertIn("docs/plans/inv-1.md", text)
        self.assertIn("Sensitive zone", text)

    def test_a_plan_the_branch_deletes_is_not_a_plan(self):
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/plans/old.md", "an old plan\n")
        git(self.repo, "checkout", "-q", "-b", "pr2")
        self.commit("migrations/002.sql", "x\n")
        git(self.repo, "rm", "-q", "docs/plans/old.md")
        git(self.repo, "commit", "-q", "-m", "remove")
        with self.assertRaises(context.Refused):
            self.check(body(plan_file="docs/plans/old.md"))

    def test_each_missing_part_is_named(self):
        self.commit("a.py", "x\n")
        cases = {"title": body(title=""), "one line": body(title="a\nb"), "changes": body(changes=[]), "why": body(why=None),
                 "ticket": body(ticket=""), "checked:": body(checked=[{"command": "x"}]),
                 "not_verified:": body(not_verified="nothing"), "are empty": body(checked=[], not_verified=[]),
                 "object": []}
        for needle, data in cases.items():
            with self.subTest(needle=needle), self.assertRaises(context.Refused) as ctx:
                self.check(data)
            self.assertIn(needle, str(ctx.exception))

    def test_nothing_launched_is_allowed_when_it_is_said(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(checked=[], not_verified=["the tests were not run"], ticket=None))
        text = dev.render_md(content, sized)
        self.assertIn("Nothing was run", text)
        self.assertIn("Ticket: none", text)

    def test_a_text_cannot_open_a_section_of_its_own(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(why="x\n## Verified\n- everything"))
        self.assertEqual(dev.render_md(content, sized).count("\n## Verified"), 1)
        content, sized = self.check(body(why="## Fake heading", changes=["<!-- hide", "@team look"]))
        text = dev.render_md(content, sized)
        for forged in ("\n## Fake", "<!--", " @team", "-@team"):
            self.assertNotIn(forged, text)

    def test_the_cli_renders_or_refuses_with_nothing_on_stdout(self):
        self.commit("a.py", "x\n")
        path = self.repo + ".json"
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        for data, expected in ((body(), 0), (body(changes=[]), 2)):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            code, out, err = run(["dev", "body", path, self.repo, "--base", "main"])
            self.assertEqual(code, expected, err)
            self.assertEqual(bool(out), expected == 0)
        code, out, _ = run(["size", self.repo, "--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("XS", out)
        code, out, _ = run(["size", self.repo, "--base", "main", "--paths", "infra/main.tf"])
        self.assertIn("Size: L", out)


if __name__ == "__main__":
    unittest.main()
