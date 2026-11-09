"""Tests de l'adaptateur GitHub, sans réseau : un collecteur factice sert des
réponses d'API préparées. Lancer : python3 -m unittest discover -s cli/tests
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
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
    """Sert data[path] ; une liste est paginée ; un chemin absent renvoie [] ou {}."""

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
    """Un repo avec, dans la fenêtre : 2 PRs humaines, 5 PRs d'agent, des reviews, des commits."""
    base = f"repos/{REPO}"
    data = {base: {"default_branch": "main"}}
    prs = [
        # S1 : rule: explicite sur une PR humaine
        pr(1, "Add payment webhook", "alice", merged="2026-10-05T12:00:00Z"),
        # S2 : PR d'agent fermée sans merge
        pr(2, "chore(deps): bump lodash from 4.17.20 to 4.17.21", "claude", branch="claude/deps-1",
           closed="2026-10-07T10:00:00Z"),
        # S2 fix après merge + S4 check failing ; S6 par titre (deps x3) ; S7 question
        pr(3, "chore(deps): bump axios from 1.6.0 to 1.7.0", "claude", branch="claude/deps-2",
           merged="2026-10-10T10:00:00Z", merge_sha="m3",
           body="I assumed the retry policy lives in src/http/client.ts. Not sure about timeouts?"),
        pr(4, "chore(deps): bump react from 18.2 to 18.3", "bob", branch="claude/deps-3",
           merged="2026-10-12T10:00:00Z", merge_sha="m4",
           body="I assumed the retry policy is configured in src/http/client.ts."),
        # S2 revert d'une PR d'agent ; S3 commentaire récurrent de carol sur 2 PRs
        pr(5, "Add export endpoint", "claude", merged="2026-10-15T10:00:00Z", merge_sha="m5"),
        pr(6, "Add import endpoint", "dave", labels=["agent"], merged="2026-10-16T10:00:00Z", merge_sha="m6"),
        # Renovate : ni agent ni tâche récurrente ; son squash-merge touche package.json après la PR 3
        pr(8, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-10T11:00:00Z", merged="2026-10-10T12:00:00Z", merge_sha="m8"),
        pr(9, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-20T11:00:00Z", merged="2026-10-20T12:00:00Z", merge_sha="m9"),
        pr(10, "chore(deps): update all non-major dependencies", "alice", branch="renovate/all-minor-patch",
           labels=["dependencies"], created="2026-10-25T11:00:00Z", merged="2026-10-25T12:00:00Z", merge_sha="m10"),
        # hors fenêtre : doit arrêter la pagination
        pr(7, "Old stuff", "alice", created="2026-09-01T10:00:00Z"),
    ]
    data[f"{base}/pulls"] = prs
    files = {1: ["src/payments/webhook.ts"], 2: ["package.json"], 3: ["package.json", "src/http/client.ts"],
             4: ["package.json"], 5: ["src/api/export.ts"], 6: ["src/api/import.ts"],
             8: ["package.json"], 9: ["package.json"], 10: ["package.json"]}
    for n, fs in files.items():
        data[f"{base}/pulls/{n}/files"] = [{"filename": f} for f in fs]
    # commits par PR (le trailer rend la PR 6 agent même sans login/branche)
    data[f"{base}/pulls/6/commits"] = [commit("c6a", "feat: import\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
                                              "dave", "2026-10-16T09:00:00Z")]
    # rafale sur PR 5 : review à 08:00 puis 3 commits en 30 min
    data[f"{base}/pulls/5/reviews"] = [review(50, "carol", "2026-10-15T08:00:00Z")]
    data[f"{base}/pulls/5/commits"] = [commit(f"c5{i}", "fix review", "claude", f"2026-10-15T08:{10*i:02d}:00Z")
                                       for i in range(1, 4)]
    # commentaires
    data[f"{base}/pulls/1/comments"] = [comment(10, "rule: les appels HTTP sortants passent par le client de src/http, jamais fetch direct",
                                                "alice", path="src/payments/webhook.ts")]
    data[f"{base}/pulls/5/comments"] = [comment(51, "Please validate the request body with the shared zod schema before handling",
                                                "carol", path="src/api/export.ts")]
    data[f"{base}/pulls/6/comments"] = [comment(61, "Validate the request body with the shared zod schema before handling it",
                                                "carol", path="src/api/import.ts")]
    # notes de l'auteur sur ses propres PRs : jamais une correction de review (S3)
    data[f"{base}/issues/5/comments"] = [comment(52, "Merge en cours par la session x (demande du propriétaire)", "claude")]
    data[f"{base}/issues/6/comments"] = [comment(62, "Merge en cours par la session x (demande du propriétaire)", "dave")]
    # checks : même check en échec sur PR 3 et 4
    for n in (3, 4):
        data[f"{base}/commits/head{n}/check-runs"] = {"check_runs": [
            {"name": "lint", "conclusion": "failure", "completed_at": f"2026-10-{8+n:02d}T09:00:00Z",
             "html_url": f"https://gh/check/{n}"}]}
    # branche par défaut : fix de bob 5 h après merge de PR 3 ; revert de PR 5 ; merge commits
    data[f"{base}/commits"] = [
        commit("m3", "Merge pull request #3", "claude", "2026-10-10T10:00:00Z"),
        commit("f1", "fix: restore axios timeout", "bob", "2026-10-10T15:00:00Z"),
        commit("m5", "Merge pull request #5", "claude", "2026-10-15T10:00:00Z"),
        commit("r1", "Revert \"Add export endpoint\" (#5)", "carol", "2026-10-15T18:00:00Z"),
        commit("f2", "docs: unrelated", "erin", "2026-10-10T16:00:00Z"),
        # squash-merge Renovate 2 h après la PR 3, sur package.json : pas une correction
        commit("m8", "chore(deps): update all non-major dependencies (#8)", "alice", "2026-10-10T12:00:00Z"),
    ]
    data[f"{base}/commits/m8"] = commit("m8", "chore(deps): update all non-major dependencies (#8)", "alice",
                                        "2026-10-10T12:00:00Z", files=["package.json"])
    data[f"{base}/commits/f1"] = commit("f1", "fix: restore axios timeout", "bob", "2026-10-10T15:00:00Z",
                                        files=["src/http/client.ts"])
    data[f"{base}/commits/f2"] = commit("f2", "docs: unrelated", "erin", "2026-10-10T16:00:00Z", files=["README.md"])
    return data


AGENTS_MD = """# app

Mode : **délégation**.

## Règles
- Les appels HTTP sortants passent par le client de `src/http/`. Pourquoi : retries centralisés. (non vérifiée)
- Les migrations ne suppriment jamais une colonne dans la même release. Pourquoi : incident #42. Vérifiée par : `scripts/check-migrations.sh`

## Maintenance de ce fichier
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
        self.assertEqual(self.result["prs_scanned"], 9)       # la PR 7 est hors fenêtre
        self.assertEqual(self.result["agent_prs"], 5)         # login, branche, label, trailer ; pas Renovate
        self.assertEqual(self.result["errors"], [])

    def test_s1_explicit_rule(self):
        s1 = by_signal(self.result, "S1")
        self.assertEqual(len(s1), 1)
        self.assertTrue(s1[0]["text"].startswith("les appels HTTP sortants"))
        self.assertEqual(s1[0]["files"], ["src/payments/webhook.ts"])
        self.assertFalse(s1[0]["agent_authored"])

    def test_s2_after_the_fact(self):
        texts = [e["text"] for e in by_signal(self.result, "S2")]
        self.assertTrue(any("fermée sans merge" in t for t in texts), texts)
        self.assertTrue(any("3 commits en 60 min" in t for t in texts), texts)
        self.assertTrue(any("Revert d'une PR d'agent" in t for t in texts), texts)
        fix = [e for e in by_signal(self.result, "S2") if "Correction" in e["text"]]
        self.assertEqual(len(fix), 1)
        self.assertEqual(fix[0]["files"], ["src/http/client.ts"])
        self.assertIn("5 h après", fix[0]["text"])
        # le commit docs d'erin ne touche pas les fichiers de la PR : pas d'évidence
        self.assertFalse(any("unrelated" in t for t in texts))
        # le squash-merge Renovate sur package.json n'est pas une correction
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
        # la règle HTTP est liée au rule: d'alice et au fix de bob sur src/http/client.ts
        linked = [e for e in self.result["evidence"] if e["related_rule"] and "HTTP" in e["related_rule"]]
        self.assertGreaterEqual(len(linked), 2)

    def test_s6_recurring_task(self):
        s6 = by_signal(self.result, "S6")
        self.assertEqual(len(s6), 3)                          # les 3 Renovate sont exclues
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
        self.assertTrue(by_signal(result, "S1"))              # le reste est collecté

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
        self.assertEqual(len(g.parse_rules(AGENTS_MD)), 2)    # la puce de Maintenance est exclue
        self.assertEqual(g.parse_rules("# x\n## Pièges\n- a\n  suite de a\n- b\n## Tâches déléguées\n- c\n\ntexte"),
                         ["a suite de a", "b"])
        self.assertEqual(g.parse_rules("## Règles\n- r\n## Interdits\n- i\n## Processus de travail\n- p\n"), ["r", "i"])

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
            self.assertIsNone(g.read_marker(fh.name))   # un marqueur d'init n'est pas un harvest
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
        self.assertIn("PRs : 9", err.getvalue())

    def test_main_exit_2_on_error(self):
        fake = FakeGitHub(build_fixture(), failing={f"repos/{REPO}/pulls/1/comments"})
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = g.main(["--repo", REPO, "--since", "2026-10-01"], fetch=fake)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
