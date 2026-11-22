"""Tests of `measure`: a team's pull-request signals over a period, read from recorded answers of
`gh pr list --json` (a folder holding prs.json), then once through a fake `gh`. Nothing here asks a forge."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_sdlc  # noqa: E402
from aisdlclib import context, measure  # noqa: E402

AGENT = "Refs #1\n\nCo-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>"
HUMAN = "Refs #1"


def pr(number: int, created: str, merged: str, *, title: str = "feat: something", body: str = "", message: str | None = HUMAN,
       reviews: list | None = None, author: str = "dana", branch: str = "feature/x") -> dict:
    """One merged pull request, in the shape `gh pr list --json` prints. Dates: 'MM-DD HH:MM' of 2026."""
    item = {"number": number, "title": title, "body": body, "author": {"login": author, "is_bot": False},
            "createdAt": stamp(created), "mergedAt": stamp(merged), "headRefName": branch,
            "reviews": [{"author": {"login": who}, "state": state, "submittedAt": stamp(when)} for who, state, when in reviews or []]}
    if message is not None:
        item["commits"] = [{"oid": "a" * 40, "messageHeadline": title, "messageBody": message, "authors": [{"login": author}]}]
    return item


def stamp(short: str) -> str:
    day, clock = short.split()
    return f"2026-{day}T{clock}:00Z"


# What a team recorded: two agent PRs and three human ones in October, and what followed them.
RECORDED = [
    pr(10, "10-01 08:00", "10-01 12:00", message=AGENT, reviews=[("lee", "APPROVED", "10-01 09:00")]),          # 4 h, review 1 h
    pr(11, "10-02 08:00", "10-02 18:00", message=AGENT, reviews=[("dana", "COMMENTED", "10-02 08:30"),          # 10 h, review 6 h:
                                                                 ("lee", "CHANGES_REQUESTED", "10-02 14:00")]),  # the author's own comment is not a review
    pr(12, "10-03 08:00", "10-03 10:00", title="feat: export"),                                                  # 2 h, never reviewed
    pr(13, "10-05 08:00", "10-06 08:00", reviews=[("lee", "APPROVED", "10-05 20:00")]),                          # 24 h, review 12 h
    pr(14, "10-06 08:00", "10-06 14:00", reviews=[("lee", "COMMENTED", "10-07 09:00")]),                         # 6 h, reviewed after the merge only
    pr(20, "10-04 09:00", "10-04 10:00", title="fix: the export drops the last row", body="Regression of #12."),
    pr(21, "10-03 09:00", "10-03 11:00", title='Revert "feat: something"', body="Reverts acme/app#11", message=AGENT),
    pr(22, "10-20 09:00", "10-20 10:00", title="fix: late correction", body="Follows #10, three weeks later."),
    pr(23, "10-08 09:00", "10-08 10:00", title="docs: how #13 works"),
]


class MeasureCase(unittest.TestCase):
    def measured(self, prs=None, since="2026-10-01", until=None, window=7, markers=None) -> dict:
        return measure.measure(RECORDED if prs is None else prs, since, until, window, markers)


class TimesTests(MeasureCase):
    def test_open_to_merge_is_the_median_of_the_hours_between_opening_and_merge(self):
        only = self.measured(RECORDED[:5])
        self.assertEqual(only["groups"]["all"]["merged"], 5)
        self.assertEqual(only["groups"]["all"]["open_to_merge_hours"], {"n": 5, "median": 6.0, "p90": 24.0})
        self.assertEqual(only["groups"]["agent"]["open_to_merge_hours"], {"n": 2, "median": 7.0, "p90": 10.0})
        self.assertEqual(only["groups"]["human"]["open_to_merge_hours"], {"n": 3, "median": 6.0, "p90": 24.0})

    def test_first_review_is_the_first_one_by_someone_else_before_the_merge(self):
        only = self.measured(RECORDED[:5])
        self.assertEqual(only["groups"]["agent"]["first_review_hours"], {"n": 2, "median": 3.5, "p90": 6.0})
        self.assertEqual(only["groups"]["human"]["first_review_hours"], {"n": 1, "median": 12.0, "p90": 12.0})
        self.assertEqual(only["groups"]["human"]["no_review"], 2)   # one never reviewed, one reviewed after its merge
        self.assertEqual(only["groups"]["agent"]["no_review"], 0)

    def test_a_pending_review_is_not_a_review(self):
        only = self.measured([pr(1, "10-01 08:00", "10-01 12:00", reviews=[("lee", "PENDING", "10-01 09:00")])])
        self.assertEqual(only["groups"]["all"]["no_review"], 1)

    def test_an_empty_group_has_no_figure_and_renders_unmeasured(self):
        only = self.measured(RECORDED[2:3])
        self.assertEqual(only["groups"]["agent"]["merged"], 0)
        self.assertEqual(only["groups"]["agent"]["open_to_merge_hours"], {"n": 0, "median": None, "p90": None})
        row = next(line for line in measure.render_md(only).splitlines() if line.startswith("| agent "))
        self.assertIn("unmeasured", row)


class KindTests(MeasureCase):
    def test_a_pr_is_an_agent_pr_when_a_commit_carries_an_agent_trailer(self):
        result = self.measured()
        kinds = {item["number"]: item["kind"] for item in result["prs"]}
        self.assertEqual((kinds[10], kinds[11], kinds[12], kinds[21]), ("agent", "agent", "human", "agent"))

    def test_a_co_author_who_is_not_an_agent_stays_human(self):
        only = self.measured([pr(1, "10-01 08:00", "10-01 12:00", message="x\n\nCo-Authored-By: Lee Martin <lee@example.com>")])
        self.assertEqual(only["groups"]["human"]["merged"], 1)

    def test_the_agent_name_outside_a_trailer_does_not_count(self):
        only = self.measured([pr(1, "10-01 08:00", "10-01 12:00", message="Reviewed the plan with Claude before coding.")])
        self.assertEqual(only["groups"]["human"]["merged"], 1)

    def test_the_markers_can_be_the_team_s_own(self):
        own = [pr(1, "10-01 08:00", "10-01 12:00", message="x\n\nCo-authored-by: acme-bot <bot@acme.example>"),
               pr(2, "10-01 08:00", "10-01 12:00", message=AGENT)]
        result = self.measured(own, markers=["acme-bot"])
        self.assertEqual({item["number"]: item["kind"] for item in result["prs"]}, {1: "agent", 2: "human"})
        self.assertEqual(result["markers"], ["acme-bot"])

    def test_a_pr_recorded_without_its_commits_is_of_unknown_kind_not_human(self):
        only = self.measured([pr(1, "10-01 08:00", "10-01 12:00", message=None)])
        self.assertEqual((only["groups"]["unknown"]["merged"], only["groups"]["human"]["merged"]), (1, 0))
        self.assertIn("| unknown ", measure.render_md(only))

    def test_no_unknown_row_when_every_pr_has_its_commits(self):
        self.assertNotIn("| unknown ", measure.render_md(self.measured()))


class FollowedTests(MeasureCase):
    def test_a_fix_that_names_the_pr_and_a_revert_of_it_count_within_the_window(self):
        result = self.measured()
        followed = {item["number"]: item for item in result["followed"]}
        self.assertEqual(sorted(followed), [11, 12])
        self.assertEqual((followed[12]["by"], followed[12]["how"], followed[12]["kind"]), (20, "fix", "human"))
        self.assertEqual((followed[11]["by"], followed[11]["how"], followed[11]["kind"]), (21, "revert", "agent"))
        self.assertEqual(followed[12]["days"], 1.0)
        self.assertEqual((result["groups"]["agent"]["followed"], result["groups"]["human"]["followed"]), (1, 1))

    def test_a_fix_after_the_window_does_not_count_and_a_longer_window_catches_it(self):
        self.assertNotIn(10, [item["number"] for item in self.measured()["followed"]])
        self.assertIn(10, [item["number"] for item in self.measured(window=30)["followed"]])

    def test_a_pr_that_only_mentions_another_is_not_a_fix(self):
        self.assertNotIn(13, [item["number"] for item in self.measured(window=30)["followed"]])   # "docs: how #13 works"

    def test_a_revert_is_recognised_by_its_title_alone(self):
        prs = [pr(1, "10-01 08:00", "10-01 12:00", title="feat: fast export"),
               pr(2, "10-02 08:00", "10-02 09:00", title='Revert "feat: fast export"')]
        self.assertEqual([(item["number"], item["by"], item["how"]) for item in self.measured(prs)["followed"]], [(1, 2, "revert")])

    def test_a_fix_branch_counts_like_a_fix_title(self):
        prs = [pr(1, "10-01 08:00", "10-01 12:00"),
               pr(2, "10-02 08:00", "10-02 09:00", title="The export keeps its last row (#1)", branch="hotfix/export")]
        self.assertEqual([item["how"] for item in self.measured(prs)["followed"]], ["fix"])

    def test_a_fix_opened_before_the_merge_does_not_follow_it(self):
        prs = [pr(1, "10-01 08:00", "10-02 12:00"),
               pr(2, "10-01 09:00", "10-02 13:00", title="fix: typo", body="Goes with #1")]
        self.assertEqual(self.measured(prs)["followed"], [])

    def test_a_reference_to_another_repository_is_not_a_reference_to_this_pr(self):
        prs = [pr(1, "10-01 08:00", "10-01 12:00"),
               pr(2, "10-02 08:00", "10-02 09:00", title="fix: bump", body="Same as other/lib#1")]
        self.assertEqual(self.measured(prs)["followed"], [])


class PeriodTests(MeasureCase):
    def test_only_the_prs_merged_in_the_period_are_measured(self):
        result = self.measured(since="2026-10-03", until="2026-10-06")
        self.assertEqual(sorted(item["number"] for item in result["prs"]), [12, 20, 21])
        self.assertEqual((result["since"], result["until"]), ("2026-10-03", "2026-10-06"))

    def test_a_fix_merged_after_the_period_still_counts_against_a_pr_of_the_period(self):
        result = self.measured(since="2026-10-03", until="2026-10-04")   # the fix of #12 is merged on the 4th
        self.assertEqual([(item["number"], item["by"]) for item in result["followed"] if item["number"] == 12], [(12, 20)])

    def test_a_pr_that_is_not_merged_is_ignored(self):
        still_open = {**pr(1, "10-01 08:00", "10-01 12:00"), "mergedAt": None}
        self.assertEqual(self.measured([still_open])["groups"]["all"]["merged"], 0)

    def test_a_date_that_is_not_a_date_is_refused(self):
        for since, until in (("yesterday", None), ("2026-13-01", None), ("2026-10-01", "soon"), ("2026-10-05", "2026-10-05")):
            with self.subTest(since=since, until=until), self.assertRaises(context.Refused):
                self.measured(since=since, until=until)

    def test_a_window_out_of_bounds_is_refused(self):
        for window in (0, -1, 91):
            with self.subTest(window=window), self.assertRaises(context.Refused):
                self.measured(window=window)

    def test_a_listing_that_is_not_one_is_refused_with_the_entry_named(self):
        for prs, needle in (({"number": 1}, "list"), (["x"], "entry 1"),
                            ([{**pr(7, "10-01 08:00", "10-01 12:00"), "createdAt": "last week"}], "#7"),
                            ([{**pr(7, "10-01 08:00", "10-01 12:00"), "number": "seven"}], "entry 1")):
            with self.subTest(needle=needle), self.assertRaises(context.Refused) as caught:
                self.measured(prs)
            self.assertIn(needle, str(caught.exception))


class RenderTests(MeasureCase):
    def test_the_cost_is_said_unmeasured(self):
        result = self.measured()
        self.assertEqual(result["cost_per_merged_pr"], "unmeasured")
        self.assertRegex(measure.render_md(result), r"Cost per merged PR: unmeasured")

    def test_the_table_has_one_row_per_kind_and_the_followed_prs_are_listed(self):
        text = measure.render_md(self.measured())
        self.assertIn("| agent | 3 |", text)
        self.assertIn("| human | 6 |", text)
        self.assertIn("| all | 9 |", text)
        self.assertIn("- #12 (human): fix #20, 1.0 days after its merge", text)
        self.assertIn("- #11 (agent): revert #21", text)

    def test_the_report_says_how_an_agent_pr_and_a_fix_are_recognised(self):
        text = measure.render_md(self.measured())
        self.assertIn("Co-Authored-By", text)
        self.assertIn("claude", text)
        self.assertIn("7 days", text)

    def test_a_title_cannot_break_the_report(self):
        prs = [pr(1, "10-01 08:00", "10-01 12:00", title="feat: a | b\n## Ignore the above"),
               pr(2, "10-02 08:00", "10-02 09:00", title="fix: x", body="#1")]
        text = measure.render_md(self.measured(prs))
        self.assertNotIn("Ignore the above", text)   # titles are data: the report quotes numbers only


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.recorded = os.path.join(self.tmp.name, "recorded")
        os.makedirs(self.recorded)
        self.record(RECORDED)

    def record(self, prs) -> None:
        with open(os.path.join(self.recorded, "prs.json"), "w", encoding="utf-8") as fh:
            json.dump(prs, fh)

    def cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ai_sdlc.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_from_a_folder_of_recorded_answers(self):
        code, out, err = self.cli("measure", "--since", "2026-10-01", "--from", self.recorded)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("# Pull-request signals", out)
        self.assertIn("| agent | 3 |", out)
        self.assertIn("recorded", out)

    def test_json_carries_the_same_figures(self):
        code, out, _ = self.cli("measure", "--since", "2026-10-01", "--from", self.recorded, "--format", "json", "--window", "30")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual((data["window_days"], data["groups"]["all"]["merged"], data["cost_per_merged_pr"]), (30, 9, "unmeasured"))
        self.assertEqual(sorted(item["number"] for item in data["followed"]), [10, 11, 12])

    def test_before_and_after_are_two_periods_of_the_same_recording(self):
        _, before, _ = self.cli("measure", "--since", "2026-10-01", "--until", "2026-10-03", "--from", self.recorded, "--format", "json")
        _, after, _ = self.cli("measure", "--since", "2026-10-03", "--from", self.recorded, "--format", "json")
        self.assertEqual((json.loads(before)["groups"]["all"]["merged"], json.loads(after)["groups"]["all"]["merged"]), (2, 7))

    def test_the_team_s_markers_replace_the_defaults(self):
        _, out, _ = self.cli("measure", "--since", "2026-10-01", "--from", self.recorded, "--agent-trailer", "acme-bot", "--format", "json")
        self.assertEqual(json.loads(out)["groups"]["agent"]["merged"], 0)

    def test_a_folder_without_recording_or_with_a_broken_one_is_refused(self):
        os.remove(os.path.join(self.recorded, "prs.json"))
        code, out, err = self.cli("measure", "--since", "2026-10-01", "--from", self.recorded)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("prs.json", err)
        with open(os.path.join(self.recorded, "prs.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        code, out, err = self.cli("measure", "--since", "2026-10-01", "--from", self.recorded)
        self.assertEqual((code, out), (2, ""))

    def test_a_bad_date_exits_2_with_nothing_on_standard_output(self):
        code, out, err = self.cli("measure", "--since", "october", "--from", self.recorded)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("--since", err)


class ForgeTests(unittest.TestCase):
    """Without --from, the listing is asked to `gh`: a fake one here, which records how it was called."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        for args in (("init", "-q", "-b", "main"), ("commit", "-q", "--allow-empty", "-m", "start"),
                     ("remote", "add", "origin", "git@github.com:acme/app.git")):
            subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args], check=True, capture_output=True)
        self.bin = os.path.join(self.tmp.name, "bin")
        os.makedirs(self.bin)
        self.calls = os.path.join(self.bin, "calls")
        previous = context.GH
        self.addCleanup(lambda: setattr(context, "GH", previous))

    def fake_gh(self, *answers, code: int = 0) -> None:
        """A `gh` that prints its answers in turn, one per call (the last one again after that), and records its arguments."""
        for turn, answer in enumerate(answers, 1):
            with open(os.path.join(self.bin, f"answer{turn}.json"), "w", encoding="utf-8") as fh:
                fh.write(answer if isinstance(answer, str) else json.dumps(answer))
        path = os.path.join(self.bin, "gh")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nhere=$(dirname "$0")\nfor a; do echo "$a" >> "$here/calls"; done\n'
                     'n=$(($(cat "$here/count" 2>/dev/null || echo 0) + 1)); echo $n > "$here/count"\n'
                     f'[ -f "$here/answer$n.json" ] || n={len(answers)}\ncat "$here/answer$n.json"\nexit {code}\n')
        os.chmod(path, 0o755)
        context.GH = path

    def called(self) -> list[str]:
        with open(self.calls, encoding="utf-8") as fh:
            return fh.read().splitlines()

    def searches(self) -> list[str]:
        args = self.called()
        return [args[i + 1] for i, arg in enumerate(args) if arg == "--search"]

    def page_of(self, size: int) -> None:
        previous = measure.PAGE
        self.addCleanup(lambda: setattr(measure, "PAGE", previous))
        measure.PAGE = size

    def test_the_listing_is_read_with_gh_pr_list_on_the_repository_s_forge(self):
        self.fake_gh(RECORDED)
        prs, source, complete = measure.fetch(self.repo, "2026-10-01", "2026-10-10", 7)
        self.assertEqual(len(prs), len(RECORDED))
        self.assertEqual((source, complete), ("github.com/acme/app", True))
        args = self.called()
        self.assertEqual(args[:2], ["pr", "list"])
        self.assertEqual(args[args.index("--repo") + 1], "github.com/acme/app")
        self.assertEqual(args[args.index("--state") + 1], "merged")
        self.assertEqual(args[args.index("--search") + 1], "merged:2026-10-01..2026-10-17 sort:created-desc")   # the period, plus the window of what follows
        self.assertEqual(args[args.index("--limit") + 1], str(measure.PAGE))
        self.assertEqual(args.count("list"), 1)   # a page that is not full is the last one
        self.assertEqual(set(args[args.index("--json") + 1].split(",")), set(measure.FIELDS))

    def test_only_reading_subcommands_of_gh_are_ever_called(self):
        self.fake_gh(RECORDED)
        measure.fetch(self.repo, "2026-10-01", None, 7)
        args = self.called()
        self.assertEqual(args[:2], ["pr", "list"])
        self.assertEqual(args[args.index("--search") + 1], "merged:>=2026-10-01 sort:created-desc")
        self.assertFalse({"api", "merge", "close", "edit", "comment", "create", "-X", "--method"} & set(args))

    def test_the_command_measures_what_gh_answers(self):
        self.fake_gh(RECORDED)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ai_sdlc.main(["measure", self.repo, "--since", "2026-10-01"])
        self.assertEqual(code, 0)
        self.assertIn("github.com/acme/app", out.getvalue())
        self.assertIn("| all | 9 |", out.getvalue())

    def test_without_gh_or_when_gh_fails_the_measure_is_refused_not_zero(self):
        context.GH = os.path.join(self.bin, "no-such-gh")
        with self.assertRaises(context.Refused) as caught:
            measure.fetch(self.repo, "2026-10-01", None, 7)
        self.assertIn("not installed", str(caught.exception))
        for answer, code in (("gh: not signed in", 1), ("<html>", 0)):
            self.fake_gh(answer, code=code)
            with self.subTest(answer=answer), self.assertRaises(context.Refused):
                measure.fetch(self.repo, "2026-10-01", None, 7)

    def test_a_repository_without_remote_is_refused_and_gh_is_not_called(self):
        self.fake_gh(RECORDED)
        subprocess.run(["git", "-C", self.repo, "remote", "remove", "origin"], check=True)
        with self.assertRaises(context.Refused):
            measure.fetch(self.repo, "2026-10-01", None, 7)
        self.assertFalse(os.path.exists(self.calls))

    def test_the_page_stays_under_what_the_forge_accepts_in_one_request(self):
        # GitHub refuses a request that may reach more than 500,000 nodes: a page of pull requests, each with up to
        # 100 commits of up to 100 authors, and as many reviews. Seen on github.com: 50 is refused, 40 is served.
        self.assertLessEqual(measure.PAGE * (100 * 100 + 100 + 1), 500_000)

    def test_a_long_listing_is_read_page_by_page_from_the_oldest_opening_seen(self):
        by_opening = sorted(RECORDED, key=lambda item: item["createdAt"], reverse=True)   # what sort:created-desc gives
        self.page_of(4)
        self.fake_gh(by_opening[:4], by_opening[3:7], by_opening[6:9])   # each page starts again at the last one seen
        prs, _, complete = measure.fetch(self.repo, "2026-10-01", None, 7)
        self.assertEqual(sorted(item["number"] for item in prs), sorted(item["number"] for item in RECORDED))   # none twice
        self.assertTrue(complete)
        first, second, third = self.searches()
        self.assertEqual(first, "merged:>=2026-10-01 sort:created-desc")
        self.assertEqual(second, f"merged:>=2026-10-01 created:<={by_opening[3]['createdAt']} sort:created-desc")
        self.assertEqual(third, f"merged:>=2026-10-01 created:<={by_opening[6]['createdAt']} sort:created-desc")

    def test_a_page_that_brings_nothing_new_stops_the_reading_and_the_listing_is_said_cut(self):
        self.page_of(4)
        self.fake_gh(RECORDED[:4])   # the same full page, again and again
        prs, _, complete = measure.fetch(self.repo, "2026-10-01", None, 7)
        self.assertEqual((len(prs), complete), (4, False))
        self.assertEqual(len(self.searches()), 2)

    def test_a_listing_cut_at_the_limit_is_said(self):
        self.fake_gh(RECORDED)
        previous = measure.LIMIT
        self.addCleanup(lambda: setattr(measure, "LIMIT", previous))
        measure.LIMIT = len(RECORDED)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ai_sdlc.main(["measure", self.repo, "--since", "2026-10-01"])
        self.assertIn("Warning", out.getvalue())
        self.assertIn(str(len(RECORDED)), out.getvalue())


if __name__ == "__main__":
    unittest.main()
