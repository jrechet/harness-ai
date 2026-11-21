"""Tests of the GitHub adapter, without network: a fake fetcher serves prepared
API responses. Run: python3 -m unittest discover -s cli/tests
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import github as g  # noqa: E402

REPO = "acme/app"
SINCE = datetime(2026, 10, 1, tzinfo=timezone.utc)


def user(login):
    return {"login": login}


def pr(number, title, login, *, branch="feat/x", labels=(), created="2026-10-05T10:00:00Z",
       merged=None, closed=None, body="", head_sha=None, merge_sha=None):
    return {
        "number": number, "title": title, "user": user(login), "html_url": f"https://gh/{REPO}/pull/{number}",
        "head": {"ref": branch, "sha": head_sha or f"head{number}"}, "labels": [{"name": l} for l in labels],
        "created_at": created, "updated_at": created, "merged_at": merged, "closed_at": closed or merged,
        "merge_commit_sha": merge_sha, "body": body,
    }


def comment(cid, body, login, created="2026-10-06T10:00:00Z", path=None):
    c = {"id": cid, "body": body, "user": user(login), "created_at": created, "html_url": f"https://gh/c/{cid}"}
    if path:
        c["path"] = path
    return c


def review(rid, login, submitted, body=""):
    return {"id": rid, "user": user(login), "submitted_at": submitted, "body": body, "html_url": f"https://gh/r/{rid}"}


def commit(sha, message, login, date, files=()):
    return {"sha": sha, "html_url": f"https://gh/commit/{sha}", "author": user(login) if login else None,
            "commit": {"message": message, "author": {"name": login or "x", "date": date},
                       "committer": {"date": date}},
            "files": [{"filename": f} for f in files]}


class FakeGitHub:
    """Serves data[path]; a list is paginated; a missing path returns [] or {}."""

    def __init__(self, data: dict, failing: set[str] | None = None):
        self.data = data
        self.failing = failing or set()
        self.calls: list[str] = []

    def __call__(self, path, params=None):
        self.calls.append(path)
        if path in self.failing:
            raise g.GhError(f"boom {path}")
        value = self.data.get(path)
        if isinstance(value, list):
            page = (params or {}).get("page", 1)
            per = (params or {}).get("per_page", 100)
            return value[(page - 1) * per: page * per]
        if value is None:
            return {} if path.endswith("check-runs") or path.count("/") <= 1 else []
        return value


def build_fixture():
    """A repo with, in the window: 2 human PRs, 5 agent PRs, reviews, commits."""
    base = f"repos/{REPO}"
    data = {base: {"default_branch": "main"}}
    prs = [
        # S1: explicit rule: on a human PR (written in French: the team's language is read as is)
        pr(1, "Add payment webhook", "alice", merged="2026-10-05T12:00:00Z"),
        # S2: agent PR closed without merge
        pr(2, "chore(deps): bump lodash from 4.17.20 to 4.17.21", "claude", branch="claude/deps-1",
           closed="2026-10-07T10:00:00Z"),
        # S2 fix after merge + S4 failing check; S6 by title (deps x3); S7 question
        pr(3, "chore(deps): bump axios from 1.6.0 to 1.7.0", "claude", branch="claude/deps-2",
           merged="2026-10-10T10:00:00Z", merge_sha="m3",
           body="I assumed the retry policy lives in src/http/client.ts. Not sure about timeouts?"),
        pr(4, "chore(deps): bump react from 18.2 to 18.3", "bob", branch="claude/deps-3",
           merged="2026-10-12T10:00:00Z", merge_sha="m4",
           body="I assumed the retry policy is configured in src/http/client.ts."),
        # S2 revert of an agent PR; S3 recurring comment by carol on 2 PRs
        pr(5, "Add export endpoint", "claude", merged="2026-10-15T10:00:00Z", merge_sha="m5"),
        pr(6, "Add import endpoint", "dave", labels=["agent"], merged="2026-10-16T10:00:00Z", merge_sha="m6"),
        # Renovate: neither agent nor recurring task; its squash-merge touches package.json after PR 3
        pr(8, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-10T11:00:00Z", merged="2026-10-10T12:00:00Z", merge_sha="m8"),
        pr(9, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-20T11:00:00Z", merged="2026-10-20T12:00:00Z", merge_sha="m9"),
        pr(10, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-25T11:00:00Z", merged="2026-10-25T12:00:00Z", merge_sha="m10"),
        # outside the window: must stop the pagination
        pr(7, "Old stuff", "alice", created="2026-09-01T10:00:00Z"),
    ]
    data[f"{base}/pulls"] = prs
    files = {1: ["src/payments/webhook.ts"], 2: ["package.json"], 3: ["package.json", "src/http/client.ts"],
             4: ["package.json"], 5: ["src/api/export.ts"], 6: ["src/api/import.ts"],
             8: ["package.json"], 9: ["package.json"], 10: ["package.json"]}
    for n, fs in files.items():
        data[f"{base}/pulls/{n}/files"] = [{"filename": f} for f in fs]
    # commits per PR (the trailer makes PR 6 an agent PR even without login/branch)
    data[f"{base}/pulls/6/commits"] = [commit("c6a", "feat: import\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
                                              "dave", "2026-10-16T09:00:00Z")]
    # burst on PR 5: review at 08:00 then 3 commits in 30 min
    data[f"{base}/pulls/5/reviews"] = [review(50, "carol", "2026-10-15T08:00:00Z")]
    data[f"{base}/pulls/5/commits"] = [commit(f"c5{i}", "fix review", "claude", f"2026-10-15T08:{10*i:02d}:00Z")
                                       for i in range(1, 4)]
    # comments
    data[f"{base}/pulls/1/comments"] = [comment(10, "rule: les appels HTTP sortants passent par le client de src/http, jamais fetch direct",
                                                "alice", path="src/payments/webhook.ts")]
    data[f"{base}/pulls/5/comments"] = [comment(51, "Please validate the request body with the shared zod schema before handling",
                                                "carol", path="src/api/export.ts")]
    data[f"{base}/pulls/6/comments"] = [comment(61, "Validate the request body with the shared zod schema before handling it",
                                                "carol", path="src/api/import.ts")]
    # the author's notes on their own PRs: never a review correction (S3)
    data[f"{base}/issues/5/comments"] = [comment(52, "Merge in progress by session x (owner's request)", "claude")]
    data[f"{base}/issues/6/comments"] = [comment(62, "Merge in progress by session x (owner's request)", "dave")]
    # checks: same check failing on PR 3 and 4
    for n in (3, 4):
        data[f"{base}/commits/head{n}/check-runs"] = {"check_runs": [
            {"name": "lint", "conclusion": "failure", "completed_at": f"2026-10-{8+n:02d}T09:00:00Z",
             "html_url": f"https://gh/check/{n}"}]}
    # default branch: bob's fix 5 h after PR 3's merge; revert of PR 5; merge commits
    data[f"{base}/commits"] = [
        commit("m3", "Merge pull request #3", "claude", "2026-10-10T10:00:00Z"),
        commit("f1", "fix: restore axios timeout", "bob", "2026-10-10T15:00:00Z"),
        commit("m5", "Merge pull request #5", "claude", "2026-10-15T10:00:00Z"),
        commit("r1", "Revert \"Add export endpoint\" (#5)", "carol", "2026-10-15T18:00:00Z"),
        commit("f2", "docs: unrelated", "erin", "2026-10-10T16:00:00Z"),
        # Renovate squash-merge 2 h after PR 3, on package.json: not a correction
        commit("m8", "chore(deps): update all non-major dependencies (#8)", "alice", "2026-10-10T12:00:00Z"),
    ]
    data[f"{base}/commits/m8"] = commit("m8", "chore(deps): update all non-major dependencies (#8)", "alice",
                                        "2026-10-10T12:00:00Z", files=["package.json"])
    data[f"{base}/commits/f1"] = commit("f1", "fix: restore axios timeout", "bob", "2026-10-10T15:00:00Z",
                                        files=["src/http/client.ts"])
    data[f"{base}/commits/f2"] = commit("f2", "docs: unrelated", "erin", "2026-10-10T16:00:00Z", files=["README.md"])
    return data


# Written in French: the team's AGENTS.md is read in either language (see AGENTS_MD_EN).
AGENTS_MD = """# app

Mode : **délégation**.

## Règles
- Les appels HTTP sortants passent par le client de `src/http/`. Pourquoi : retries centralisés. (non vérifiée)
- Les migrations ne suppriment jamais une colonne dans la même release. Pourquoi : incident #42. Vérifiée par : `scripts/check-migrations.sh`

## Maintenance de ce fichier
- bla
<!-- harvest: last=2026-10-01 ref=https://gh/pr/1 -->
"""

AGENTS_MD_EN = """# app

Mode: **delegation**.

## Rules
- Outgoing HTTP calls go through the client in `src/http/`. Why: centralised retries. (unverified)
- Migrations never drop a column in the same release. Why: incident #42. Enforced by: `scripts/check-migrations.sh`

## Delegated tasks
- dependency bumps

## Maintenance of this file
- bla
<!-- harvest: last=2026-10-01 ref=https://gh/pr/1 -->
"""


def run_harvester(data, failing=None, **kw):
    fake = FakeGitHub(data, failing)
    markers = g.AgentMarkers(logins=["claude"], branch_prefixes=["claude/"], labels=["agent"],
                             trailers=["co-authored-by: claude"])
    h = g.Harvester(REPO, SINCE, markers, fake, **kw)
    return h.run(), fake


def by_signal(result, signal):
    return [e for e in result["evidence"] if e["signal"] == signal]


class HarvesterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        self.tmp.write(AGENTS_MD)
        self.tmp.close()
        self.result, self.fake = run_harvester(build_fixture(), agents_md=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_window_stops_pagination_and_classifies_agents(self):
        self.assertEqual(self.result["prs_scanned"], 9)       # PR 7 is outside the window
        self.assertEqual(self.result["agent_prs"], 5)         # login, branch, label, trailer; not Renovate
        self.assertEqual(self.result["errors"], [])

    def test_s1_explicit_rule(self):
        s1 = by_signal(self.result, "S1")
        self.assertEqual(len(s1), 1)
        self.assertTrue(s1[0]["text"].startswith("les appels HTTP sortants"))
        self.assertEqual(s1[0]["files"], ["src/payments/webhook.ts"])
        self.assertFalse(s1[0]["agent_authored"])

    def test_s2_after_the_fact(self):
        texts = [e["text"] for e in by_signal(self.result, "S2")]
        self.assertTrue(any("closed without merge" in t for t in texts), texts)
        self.assertTrue(any("3 commits in 60 min" in t for t in texts), texts)
        self.assertTrue(any("Revert of an agent PR" in t for t in texts), texts)
        fix = [e for e in by_signal(self.result, "S2") if e["text"].startswith("Fix ")]
        self.assertEqual(len(fix), 1)
        self.assertEqual(fix[0]["files"], ["src/http/client.ts"])
        self.assertIn("5 h after", fix[0]["text"])
        # erin's docs commit does not touch the PR's files: no evidence
        self.assertFalse(any("unrelated" in t for t in texts))
        # the Renovate squash-merge on package.json is not a correction
        self.assertFalse(any("non-major" in t for t in texts), texts)

    def test_s3_recurring_review_comment(self):
        s3 = by_signal(self.result, "S3")
        self.assertEqual(len(s3), 2)
        self.assertEqual({e["author"] for e in s3}, {"carol"})
        self.assertEqual(len({e["group_key"] for e in s3}), 1)

    def test_s4_ignored_check(self):
        s4 = by_signal(self.result, "S4")
        self.assertEqual(len(s4), 2)
        self.assertEqual({e["group_key"] for e in s4}, {"check:lint"})

    def test_s5_orphan_rule_and_linking(self):
        s5 = by_signal(self.result, "S5")
        self.assertEqual(len(s5), 1)
        self.assertIn("migrations", s5[0]["text"])
        # the HTTP rule is linked to alice's rule: and to bob's fix on src/http/client.ts
        linked = [e for e in self.result["evidence"] if e["related_rule"] and "HTTP" in e["related_rule"]]
        self.assertGreaterEqual(len(linked), 2)

    def test_s5_reads_an_english_agents_md_the_same_way(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(AGENTS_MD_EN)
        try:
            result, _ = run_harvester(build_fixture(), agents_md=fh.name)
        finally:
            os.unlink(fh.name)
        s5 = by_signal(result, "S5")
        self.assertEqual(len(s5), 1)
        self.assertIn("Migrations", s5[0]["text"])
        linked = [e for e in result["evidence"] if e["related_rule"] and "HTTP" in e["related_rule"]]
        self.assertGreaterEqual(len(linked), 2)

    def test_s6_recurring_task(self):
        s6 = by_signal(self.result, "S6")
        self.assertEqual(len(s6), 3)                          # the 3 Renovate PRs are excluded
        keys = {e["group_key"] for e in s6}
        self.assertEqual(len(keys), 1)
        self.assertIn("bump", keys.pop())
        self.assertFalse(any(e["group_key"].startswith("task:label") for e in s6))

    def test_s7_repeated_question(self):
        s7 = by_signal(self.result, "S7")
        self.assertEqual(len({e["url"] for e in s7}), 2)
        self.assertTrue(all(e["agent_authored"] for e in s7))

    def test_schema(self):
        keys = {"id", "signal", "source", "url", "date", "author", "agent_authored", "files", "text",
                "related_rule", "group_key"}
        for e in self.result["evidence"]:
            self.assertEqual(set(e), keys)
            self.assertEqual(e["source"], "github")
        ids = [e["id"] for e in self.result["evidence"]]
        self.assertEqual(len(ids), len(set(ids)))


class RobustnessTests(unittest.TestCase):
    def test_failed_source_is_reported_not_fatal(self):
        result, _ = run_harvester(build_fixture(), failing={f"repos/{REPO}/commits"})
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("commits", result["errors"][0])
        self.assertTrue(by_signal(result, "S1"))              # the rest is collected

    def test_thresholds_are_options(self):
        result, _ = run_harvester(build_fixture(), min_recurrence=3, min_task_count=4)
        self.assertEqual(by_signal(result, "S3"), [])
        self.assertEqual(by_signal(result, "S4"), [])
        self.assertEqual(by_signal(result, "S6"), [])

    def test_no_agent_prs_no_default_branch_scan(self):
        data = build_fixture()
        data[f"repos/{REPO}/pulls"] = [pr(1, "x", "alice", merged="2026-10-05T12:00:00Z")]
        _, fake = run_harvester(data)
        self.assertNotIn(f"repos/{REPO}/commits", fake.calls)


class HelpersTests(unittest.TestCase):
    def test_parse_rules(self):
        self.assertEqual(len(g.parse_rules(AGENTS_MD)), 2)    # the Maintenance bullet is excluded
        self.assertEqual(g.parse_rules("# x\n## Pièges\n- a\n  suite de a\n- b\n## Tâches déléguées\n- c\n\ntexte"),
                         ["a suite de a", "b"])
        self.assertEqual(g.parse_rules("## Règles\n- r\n## Interdits\n- i\n## Processus de travail\n- p\n"), ["r", "i"])

    def test_parse_rules_reads_english_headings_too(self):
        self.assertEqual(len(g.parse_rules(AGENTS_MD_EN)), 2)
        self.assertEqual(g.parse_rules("## Rules\n- r\n## Forbidden\n- i\n## Working process\n- p\n"
                                       "## Delegated tasks\n- d\n## Maintaining this file\n- m\n"
                                       "## What this repository does\n- w\n## Commands\n- c\n"), ["r", "i"])

    def test_rule_comments_in_either_language(self):
        for body in ("rule: les appels HTTP sortants passent par src/http",
                     "Rule: outgoing HTTP calls go through src/http",
                     "  RULE : outgoing HTTP calls go through src/http"):
            with self.subTest(body=body):
                self.assertTrue(g.RULE_PREFIX.match(body))
        self.assertFalse(g.RULE_PREFIX.match("As a rule: be careful"))

    def test_an_agent_saying_it_guessed_is_heard_in_either_language(self):
        guessed = ["J'ai supposé que le client HTTP vit dans src/http.",
                   "Je ne sais pas où se règlent les timeouts.",
                   "Hypothèse : les retries sont centralisés.",
                   "I assumed the retry policy lives in src/http.",
                   "I don't know where the timeouts are set.",
                   "I don’t know where the timeouts are set.",
                   "My assumption is that retries are centralised.",
                   "Working hypothesis: retries are centralised."]
        for sentence in guessed:
            with self.subTest(sentence=sentence):
                self.assertTrue(g.QUESTION_PATTERNS.search(sentence))
        for sentence in ("Adds the export endpoint.", "Ajoute l'endpoint d'export."):
            with self.subTest(sentence=sentence):
                self.assertFalse(g.QUESTION_PATTERNS.search(sentence))

    def test_title_similarity(self):
        same = g.jaccard(g.title_words("chore(deps): bump lodash from 4.17.20 to 4.17.21"),
                         g.title_words("chore(deps): bump axios from 1.6.0 to 1.7.0"))
        other = g.jaccard(g.title_words("Add export endpoint"), g.title_words("Fix login redirect"))
        self.assertGreaterEqual(same, g.TITLE_THRESHOLD)
        self.assertLess(other, g.TITLE_THRESHOLD)

    def test_cluster_is_greedy_and_deterministic(self):
        groups = g.cluster([{"a", "b", "c"}, {"a", "b", "d"}, {"x", "y"}, set()], 0.5)
        self.assertEqual([grp["idx"] for grp in groups], [[0, 1], [2]])
        self.assertEqual(groups[0]["common"], {"a", "b"})

    def test_zone(self):
        self.assertEqual(g.Harvester.zone(["src/api/a.ts", "src/api/b.ts"]), "src/api")
        self.assertEqual(g.Harvester.zone(["src/api/a.ts", "src/http/b.ts"]), "src")
        self.assertEqual(g.Harvester.zone(["README.md"]), ".")

    def test_marker(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(AGENTS_MD)
        try:
            self.assertEqual(g.read_marker(fh.name), "2026-10-01")
        finally:
            os.unlink(fh.name)
        self.assertIsNone(g.read_marker("/nonexistent/AGENTS.md"))
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write("# x\n<!-- harvest: last=2026-11-09 ref=init -->\n")
        try:
            self.assertIsNone(g.read_marker(fh.name))   # an init marker is not a harvest
        finally:
            os.unlink(fh.name)


class CliTests(unittest.TestCase):
    def test_main_outputs_json_and_exit_code(self):
        fake = FakeGitHub(build_fixture())
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = g.main(["--repo", REPO, "--since", "2026-10-01", "--agent-login", "claude",
                           "--agent-branch-prefix", "claude/", "--agent-label", "agent", "--summary"], fetch=fake)
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["repo"], REPO)
        self.assertIn("S1", payload["counts"])
        self.assertIn("PRs: 9", err.getvalue())

    def test_main_exit_2_on_error(self):
        fake = FakeGitHub(build_fixture(), failing={f"repos/{REPO}/pulls/1/comments"})
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = g.main(["--repo", REPO, "--since", "2026-10-01"], fetch=fake)
        self.assertEqual(code, 2)


def build_tiny():
    """The smallest repo that says three things: one `rule:` comment on a human PR, one fix after
    the merge of an agent PR, and one merge commit on the same files that is not a fix."""
    base = f"repos/{REPO}"
    data = {base: {"default_branch": "main"}}
    data[f"{base}/pulls"] = [
        pr(1, "Add payment webhook", "alice", merged="2026-10-05T12:00:00Z"),
        pr(2, "Add export endpoint", "claude", branch="claude/export", merged="2026-10-10T10:00:00Z", merge_sha="m2"),
    ]
    data[f"{base}/pulls/1/files"] = [{"filename": "src/payments/webhook.ts"}]
    data[f"{base}/pulls/2/files"] = [{"filename": "src/api/export.ts"}]
    data[f"{base}/pulls/1/comments"] = [comment(10, "rule: outgoing HTTP calls go through the client in src/http",
                                                "alice", path="src/payments/webhook.ts")]
    fix = commit("f1", "fix: export escapes commas", "bob", "2026-10-10T15:00:00Z")
    merge = commit("g1", "Merge branch 'feat/import' into feat/all", "bob", "2026-10-10T16:00:00Z")
    merge["parents"] = [{"sha": "p1"}, {"sha": "p2"}]
    data[f"{base}/commits"] = [commit("m2", "Merge pull request #2", "claude", "2026-10-10T10:00:00Z"), fix, merge]
    data[f"{base}/commits/f1"] = {**fix, "files": [{"filename": "src/api/export.ts"}]}
    data[f"{base}/commits/g1"] = {**merge, "files": [{"filename": "src/api/export.ts"}]}
    return data


class MergeCommitTests(unittest.TestCase):
    def fixes(self, data):
        result, fake = run_harvester(data)
        return [e for e in by_signal(result, "S2") if e["text"].startswith("Fix ")], fake

    def test_a_merge_commit_is_not_an_after_the_fact_fix(self):
        fixes, fake = self.fixes(build_tiny())
        self.assertEqual([e["url"] for e in fixes], ["https://gh/commit/f1"])
        self.assertNotIn(f"repos/{REPO}/commits/g1", fake.calls)   # not even read

    def test_a_commit_with_two_parents_is_a_merge_whatever_its_message(self):
        data = build_tiny()
        data[f"repos/{REPO}/commits"][2]["commit"]["message"] = "Bring the import work in"
        fixes, _ = self.fixes(data)
        self.assertEqual([e["url"] for e in fixes], ["https://gh/commit/f1"])

    def test_a_merge_message_is_a_merge_even_without_the_parents(self):
        for message in ("Merge branch 'feat/import' into feat/all", "Merge remote-tracking branch 'origin/main'",
                        "Merge commit 'abc1234'", "Merge tag 'v1.2'"):
            with self.subTest(message=message):
                data = build_tiny()
                del data[f"repos/{REPO}/commits"][2]["parents"]
                data[f"repos/{REPO}/commits"][2]["commit"]["message"] = message
                fixes, _ = self.fixes(data)
                self.assertEqual([e["url"] for e in fixes], ["https://gh/commit/f1"])

    def test_a_fix_that_talks_about_a_merge_still_counts(self):
        data = build_tiny()
        data[f"repos/{REPO}/commits"][1]["commit"]["message"] = "fix: merge the two export paths"
        fixes, _ = self.fixes(data)
        self.assertEqual([e["url"] for e in fixes], ["https://gh/commit/f1"])


class RecordReplayTests(unittest.TestCase):
    ARGS = ["--repo", REPO, "--since", "2026-10-01", "--agent-login", "claude"]

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.folder = os.path.join(self.dir.name, "recorded")

    def run_main(self, argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = g.main(argv, **kw)
        return code, out.getvalue(), err.getvalue()

    def record(self):
        return self.run_main(self.ARGS + ["--record", self.folder], fetch=FakeGitHub(build_tiny()))

    def test_record_writes_one_json_file_per_call(self):
        fake = FakeGitHub(build_tiny())
        code, _, _ = self.run_main(self.ARGS + ["--record", self.folder], fetch=fake)
        self.assertEqual(code, 0)
        self.assertIn(g.WINDOW_FILE, os.listdir(self.folder))   # the window is not a call: counted apart
        names = sorted(n for n in os.listdir(self.folder) if n != g.WINDOW_FILE)
        self.assertEqual(len(names), len(fake.calls))
        self.assertTrue(all(n.endswith(".json") for n in names), names)
        with open(os.path.join(self.folder, "repos_acme_app.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"call": "repos/acme/app", "answer": {"default_branch": "main"}})

    def test_replay_gives_the_harvest_that_was_recorded_without_calling_gh(self):
        code, recorded, _ = self.record()
        self.assertEqual(code, 0)

        def no_gh(path, params=None):
            raise AssertionError(f"gh called for {path}")

        code, replayed, err = self.run_main(self.ARGS + ["--from", self.folder], fetch=no_gh)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(replayed), json.loads(recorded))

    def test_the_tiny_recorded_folder_says_one_rule_one_fix_and_no_merge(self):
        self.record()
        code, out, err = self.run_main(self.ARGS + ["--from", self.folder])
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["counts"], {"S1": 1, "S2": 1})
        self.assertEqual(by_signal(result, "S2")[0]["url"], "https://gh/commit/f1")
        self.assertFalse(any("Merge branch" in e["text"] for e in result["evidence"]))

    def test_replay_works_without_gh_on_path(self):
        self.record()
        old = os.environ.get("PATH", "")
        os.environ["PATH"] = self.dir.name
        try:
            code, out, err = self.run_main(self.ARGS + ["--from", self.folder])
        finally:
            os.environ["PATH"] = old
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["counts"], {"S1": 1, "S2": 1})

    def test_a_call_that_was_not_recorded_is_an_error_not_an_empty_answer(self):
        self.record()
        os.unlink(os.path.join(self.folder, g.record_name(f"repos/{REPO}/pulls/1/comments?per_page=100&page=1")))
        code, out, err = self.run_main(self.ARGS + ["--from", self.folder])
        self.assertEqual(code, 2)
        self.assertIn("no recorded answer", err)
        self.assertIn("pulls/1/comments", err)
        self.assertEqual(json.loads(out)["counts"], {"S2": 1})

    def test_a_file_that_answers_another_call_is_refused(self):
        self.record()
        with open(os.path.join(self.folder, "repos_acme_app.json"), "w", encoding="utf-8") as fh:
            json.dump({"call": "repos/other/app", "answer": {"default_branch": "trunk"}}, fh)
        code, out, err = self.run_main(self.ARGS + ["--from", self.folder])
        self.assertEqual(code, 2)
        self.assertIn("repos/other/app", err)
        self.assertEqual(json.loads(out)["default_branch"], "main")

    def test_an_unreadable_recorded_file_is_an_error(self):
        self.record()
        with open(os.path.join(self.folder, "repos_acme_app.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        code, _, err = self.run_main(self.ARGS + ["--from", self.folder])
        self.assertEqual(code, 2)
        self.assertIn("repos_acme_app.json", err)

    def test_from_a_folder_that_does_not_exist_prints_no_harvest(self):
        code, out, err = self.run_main(self.ARGS + ["--from", os.path.join(self.dir.name, "nope")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("is not a directory", err)

    def test_from_and_record_together_are_refused(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            g.main(self.ARGS + ["--from", self.folder, "--record", self.folder])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("not allowed with", err.getvalue())

    def test_a_failed_call_is_not_recorded(self):
        failing = f"repos/{REPO}/pulls/1/comments"
        fake = FakeGitHub(build_tiny(), failing={failing})
        code, _, _ = self.run_main(self.ARGS + ["--record", self.folder], fetch=fake)
        self.assertEqual(code, 2)
        self.assertNotIn(g.record_name(f"{failing}?per_page=100&page=1"), os.listdir(self.folder))

    NO_SINCE = ["--repo", REPO, "--agent-login", "claude"]

    def test_replay_without_since_takes_the_window_of_the_recording(self):
        code, recorded, _ = self.record()
        self.assertEqual(code, 0)
        code, replayed, err = self.run_main(self.NO_SINCE + ["--from", self.folder])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(replayed), json.loads(recorded))
        self.assertEqual(json.loads(replayed)["since"], "2026-10-01")
        self.assertNotIn("30-day window", err)

    def test_record_writes_its_window_next_to_the_answers(self):
        self.record()
        with open(os.path.join(self.folder, g.WINDOW_FILE), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"since": "2026-10-01T00:00:00Z"})
        stem = g.WINDOW_FILE[:-len(".json")]
        self.assertNotEqual(g.record_name(stem), g.WINDOW_FILE)   # no call can be named like it

    def test_a_default_window_is_replayed_to_the_second(self):
        fake = FakeGitHub(build_tiny())
        code, _, _ = self.run_main(self.NO_SINCE + ["--record", self.folder], fetch=fake)
        self.assertEqual(code, 0)
        with open(os.path.join(self.folder, g.WINDOW_FILE), encoding="utf-8") as fh:
            self.assertRegex(json.load(fh)["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        with open(os.path.join(self.folder, g.WINDOW_FILE), "w", encoding="utf-8") as fh:
            json.dump({"since": "2026-09-20T08:09:10Z"}, fh)   # as if recorded another day
        seen = []

        def spy(path, params=None):
            seen.append((params or {}).get("since"))
            return fake(path, params)

        with mock.patch.object(g, "replaying", lambda folder: spy):
            code, _, err = self.run_main(self.NO_SINCE + ["--from", self.folder])
        self.assertEqual(code, 0, err)
        self.assertIn("2026-09-20T08:09:10Z", seen)

    def test_the_window_of_the_recording_wins_over_the_marker_of_agents_md(self):
        self.record()
        agents_md = os.path.join(self.dir.name, "AGENTS.md")
        with open(agents_md, "w", encoding="utf-8") as fh:
            fh.write("# Rules\n<!-- harvest: last=2026-10-09 ref=abc -->\n")
        code, out, err = self.run_main(self.NO_SINCE + ["--agents-md", agents_md, "--from", self.folder])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["since"], "2026-10-01")

    def test_replay_with_another_since_than_the_recording_is_refused(self):
        self.record()
        code, out, err = self.run_main(self.NO_SINCE + ["--since", "2026-10-02", "--from", self.folder])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("2026-10-01", err)
        self.assertIn("2026-10-02", err)

    def test_a_recording_without_its_window_still_replays_with_since(self):
        self.record()
        os.unlink(os.path.join(self.folder, g.WINDOW_FILE))
        code, out, err = self.run_main(self.ARGS + ["--from", self.folder])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["counts"], {"S1": 1, "S2": 1})

    def test_a_recording_without_its_window_and_without_since_says_what_to_do(self):
        self.record()
        os.unlink(os.path.join(self.folder, g.WINDOW_FILE))
        code, out, err = self.run_main(self.NO_SINCE + ["--from", self.folder])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--since", err)

    def test_an_unreadable_window_file_is_an_error(self):
        self.record()
        for content in ("{not json", '{"since": "yesterday"}', "[]"):
            with self.subTest(content=content):
                with open(os.path.join(self.folder, g.WINDOW_FILE), "w", encoding="utf-8") as fh:
                    fh.write(content)
                code, out, err = self.run_main(self.NO_SINCE + ["--from", self.folder])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn(g.WINDOW_FILE, err)

    def test_record_names_are_distinct_and_plain(self):
        a = g.record_name("repos/acme/app/pulls?state=all&per_page=100&page=1")
        b = g.record_name("repos/acme/app/pulls?state=all&per_page=100&page=2")
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^[A-Za-z0-9._-]+\.json$")
        long = g.record_name("repos/acme/app/commits/" + "x" * 400)
        self.assertLessEqual(len(long), 200)
        self.assertNotEqual(long, g.record_name("repos/acme/app/commits/" + "x" * 399 + "y"))


class GhMissingTests(unittest.TestCase):
    def test_without_gh_the_command_says_so_and_prints_no_harvest(self):
        with tempfile.TemporaryDirectory() as empty:
            old = os.environ.get("PATH", "")
            os.environ["PATH"] = empty
            out, err = io.StringIO(), io.StringIO()
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    code = g.main(["--repo", REPO, "--since", "2026-10-01"])
            finally:
                os.environ["PATH"] = old
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue().count("gh is not installed or not on PATH"), 1)

    def test_the_harness_command_offers_from_and_record(self):
        cli = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "harness.py")
        proc = subprocess.run([sys.executable, cli, "harvest", "github", "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--from", proc.stdout)
        self.assertIn("--record", proc.stdout)


if __name__ == "__main__":
    unittest.main()
