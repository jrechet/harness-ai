"""Tests des médailles : la médaille est le palier mesuré, un succès garde la date où il a été débloqué,
un succès perdu le dit, et la page ne contient que des données échappées."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import medals  # noqa: E402

AGENTS = """# démo — instructions pour les agents

Mode : **assistance**. L'humain pilote et relit chaque diff.

## Règles
- Pas de secret dans le code. Pourquoi : fuite de mars. (non vérifiée) [2026-03]

## Interdits
- Pousser sur main. Pourquoi : tout passe par une PR. [2026-01]
"""


def evaluated(passed: dict[str, bool], rank: int = 1) -> dict:
    tiers = [{"id": "bronze", "name": "Bronze", "title": "Cadré", "promise": "p"},
             {"id": "argent", "name": "Argent", "title": "Bouclé", "promise": "p"}]
    successes = [{"id": i, "tier": "bronze" if i.startswith("A") else "argent", "title": i, "passed": ok,
                  "evidence": "", "next": None if ok else f"faire {i}", "waiting": False} for i, ok in passed.items()]
    return {"kind": "repo", "name": "démo", "date": "2026-11-15", "rank": rank, "tiers": tiers, "successes": successes}


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = harness.main(["medals", self.repo, *argv])
        return code, out.getvalue()


class BuildTests(unittest.TestCase):
    def test_the_medal_is_the_rank_and_the_why_counts_what_is_missing(self):
        data = medals.build(evaluated({"A1": True, "B1": False, "B2": True}))
        self.assertEqual((data["medal"]["id"], data["medal"]["rank"], data["medal"]["of"]), ("bronze", 1, 4))
        self.assertIn("il en manque 1 pour argent", data["why"])
        self.assertEqual([s["id"] for s in data["next"]], ["B1"])
        self.assertEqual([(t["done"], t["total"], t["earned"]) for t in data["tiers"]], [(1, 1, True), (1, 2, False)])

    def test_no_medal_points_at_bronze(self):
        data = medals.build(evaluated({"A1": False}, rank=0))
        self.assertEqual(data["medal"]["id"], "aucune")
        self.assertEqual([s["id"] for s in data["next"]], ["A1"])

    def test_an_unlock_date_is_kept_and_a_lost_success_says_when(self):
        first = medals.build({**evaluated({"A1": True, "B1": True}, rank=2), "date": "2026-10-01"})
        second = medals.build(evaluated({"A1": True, "B1": False}), first)
        by_id = {s["id"]: s for s in second["successes"]}
        self.assertEqual(by_id["A1"]["unlocked"], "2026-10-01")
        self.assertEqual((by_id["B1"]["unlocked"], by_id["B1"]["lost"]), (None, "2026-11-15"))
        third = medals.build({**evaluated({"A1": True, "B1": True}, rank=2), "date": "2026-12-01"}, second)
        self.assertEqual({s["id"]: s for s in third["successes"]}["B1"]["unlocked"], "2026-12-01")
        self.assertEqual([h["medal"] for h in third["history"]], ["argent", "bronze", "argent"])

    def test_a_file_of_another_kind_or_a_broken_one_is_not_trusted(self):
        for previous in ("x", [], {"schema": 99}, {"schema": 1, "kind": "marketplace", "successes": [{"id": "A1", "unlocked": "2020-01-01"}]},
                         {"schema": 1, "kind": "repo", "successes": ["x", {"nope": 1}], "history": ["x"]}):
            data = medals.build(evaluated({"A1": True}), previous)
            self.assertEqual(data["successes"][0]["unlocked"], "2026-11-15")


class RepoTests(RepoCase):
    def test_an_empty_repo_has_no_medal_and_a_framed_one_has_bronze(self):
        self.assertEqual(medals.build(medals.evaluate_repo(self.repo))["medal"]["id"], "aucune")
        self.write("AGENTS.md", AGENTS)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertEqual(data["medal"]["id"], "bronze")
        bonus = {s["id"]: s for s in data["successes"] if s["tier"] == "bonus"}
        self.assertTrue(bonus["B.dates"]["unlocked"])
        self.assertFalse(bonus["B.outils"]["unlocked"])

    def test_a_command_the_ci_runs_and_nobody_wrote_locks_its_bonus(self):
        self.write("AGENTS.md", AGENTS)
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: make it\n")
        bonus = {s["id"]: s for s in medals.evaluate_repo(self.repo)["successes"]}
        self.assertFalse(bonus["B.commandes"]["passed"])
        self.assertIn("make it", bonus["B.commandes"]["evidence"])

    def test_write_keeps_the_file_and_the_dates_between_two_runs(self):
        self.write("AGENTS.md", AGENTS)
        code, _ = self.run_cli("--write", "--today", "2026-10-01")
        self.assertEqual(code, 0)
        self.run_cli("--write", "--today", "2026-11-15")
        with open(os.path.join(self.repo, ".harness", "medals.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["date"], "2026-11-15")
        self.assertEqual({s["unlocked"] for s in data["successes"] if s["tier"] == "bronze"}, {"2026-10-01"})

    def test_without_write_nothing_is_created(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("Pas encore de médaille", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))


class MarketplaceTests(RepoCase):
    def plugin(self, description: str) -> None:
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "démo", "plugins": [{"name": "p", "source": "./p"}]}))
        self.write("p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.0", "description": "d"}))
        self.write("p/skills/s/SKILL.md", f"---\nname: s\ndescription: {description}\n---\n# s\n")

    def medal(self) -> dict:
        return medals.build(medals.evaluate_marketplace(self.repo))

    def test_no_manifest_is_no_medal(self):
        self.assertEqual(self.medal()["medal"]["id"], "aucune")

    def test_an_installable_marketplace_is_bronze_and_a_described_one_silver(self):
        self.plugin("Fait des choses.")
        self.assertEqual(self.medal()["medal"]["id"], "bronze")
        self.plugin("Fait des choses. Utiliser quand on demande X. Ne pas utiliser pour Y.")
        self.assertEqual(self.medal()["medal"]["rank"], 3)   # sans code, rien à tester : l'or suit

    def test_code_without_tests_stops_at_silver_and_a_source_outside_the_repo_is_not_followed(self):
        self.plugin("Utiliser quand on demande X. Ne pas utiliser pour Y.")
        self.write("p/cli/outil.py", "x = 1\n")
        self.assertEqual(self.medal()["medal"]["id"], "argent")
        self.write("p/cli/tests/test_outil.py", "x = 1\n")
        self.assertEqual(self.medal()["medal"]["rank"], 3)
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "d", "plugins": [{"name": "p", "source": "../ailleurs"}, "x", {"source": 3}]}))
        self.assertEqual(self.medal()["medal"]["id"], "aucune")

    def test_the_cli_keeps_a_file_per_kind(self):
        self.plugin("x")
        self.run_cli("--kind", "marketplace", "--write")
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".harness", "medals-marketplace.json")))


class PageTests(RepoCase):
    def test_the_page_is_self_contained_and_its_data_cannot_break_out(self):
        self.write("AGENTS.md", AGENTS)
        page = os.path.join(self.repo, "page.html")
        code, _ = self.run_cli("--page", page, "--name", "</script><img src=x onerror=alert(1)>&")
        self.assertEqual(code, 0)
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        self.assertNotIn("{{", html)
        self.assertNotIn("<img src=x", html)
        self.assertEqual(html.count("</script>"), 2)
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        self.assertNotIn("innerHTML", html)
        data = json.loads(re.search(r'id="medals-data">(.*?)</script>', html, re.DOTALL)[1])
        self.assertEqual(data["name"], "</script><img src=x onerror=alert(1)>&")
        self.assertIn("sha256-", html)

    def test_the_same_data_gives_the_same_page(self):
        data = medals.build(evaluated({"A1": True, "B1": False}))
        self.assertEqual(medals.render_html(data), medals.render_html(json.loads(json.dumps(data))))


if __name__ == "__main__":
    unittest.main()
