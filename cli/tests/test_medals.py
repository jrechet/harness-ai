"""Tests of the medals: the medal is the measured level, an achievement keeps the date it was unlocked,
a lost achievement says so, and the page contains only escaped data."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import facts, maturity, medals  # noqa: E402

AGENTS = """# demo — instructions for agents

Mode: **assistance**. The human drives and reviews every diff.

## Rules
- No secret in the code. Why: the March leak. (unverified) [2026-03]

## Forbidden
- Pushing to main. Why: everything goes through a PR. [2026-01]
"""

# The same file written by a French-speaking team.
AGENTS_FR = """# démo — instructions pour les agents

Mode : **assistance**. L'humain pilote et relit chaque diff.

## Règles
- Pas de secret dans le code. Pourquoi : fuite de mars. (non vérifiée) [2026-03]

## Interdits
- Pousser sur main. Pourquoi : tout passe par une PR. [2026-01]
"""


def evaluated(passed: dict[str, bool], rank: int = 1) -> dict:
    tiers = [{"id": "bronze", "name": "Bronze", "title": "Framed", "promise": "p"},
             {"id": "silver", "name": "Silver", "title": "Looped", "promise": "p"}]
    successes = [{"id": i, "tier": "bronze" if i.startswith("A") else "silver", "title": i, "passed": ok,
                  "evidence": "", "next": None if ok else f"do {i}", "waiting": False} for i, ok in passed.items()]
    return {"kind": "repo", "name": "demo", "date": "2026-11-15", "rank": rank, "tiers": tiers, "successes": successes}


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
        self.assertIn("1 missing for silver", data["why"])
        self.assertEqual([s["id"] for s in data["next"]], ["B1"])
        self.assertEqual([(t["done"], t["total"], t["earned"]) for t in data["tiers"]], [(1, 1, True), (1, 2, False)])

    def test_no_medal_points_at_bronze(self):
        data = medals.build(evaluated({"A1": False}, rank=0))
        self.assertEqual(data["medal"]["id"], "none")
        self.assertEqual([s["id"] for s in data["next"]], ["A1"])

    def test_an_unlock_date_is_kept_and_a_lost_success_says_when(self):
        first = medals.build({**evaluated({"A1": True, "B1": True}, rank=2), "date": "2026-10-01"})
        second = medals.build(evaluated({"A1": True, "B1": False}), first)
        by_id = {s["id"]: s for s in second["successes"]}
        self.assertEqual(by_id["A1"]["unlocked"], "2026-10-01")
        self.assertEqual((by_id["B1"]["unlocked"], by_id["B1"]["lost"]), (None, "2026-11-15"))
        third = medals.build({**evaluated({"A1": True, "B1": True}, rank=2), "date": "2026-12-01"}, second)
        self.assertEqual({s["id"]: s for s in third["successes"]}["B1"]["unlocked"], "2026-12-01")
        self.assertEqual([h["medal"] for h in third["history"]], ["silver", "bronze", "silver"])

    def test_a_previous_file_with_french_ids_keeps_its_dates_under_the_english_ids(self):
        previous = {"schema": 1, "kind": "repo",
                    "successes": [{"id": "B.outils", "unlocked": "2026-10-01"}, {"id": "M4.aveugle", "unlocked": "2026-09-01"},
                                  {"id": "B.frais", "unlocked": None, "lost": "2026-10-05"}],
                    "history": [{"date": "2026-09-01", "medal": "aucune"}, {"date": "2026-10-01", "medal": "argent"}]}
        current = evaluated({"B.tools": True, "M4.blind": True, "B.fresh": False}, rank=2)
        data = medals.build(current, previous)
        by_id = {s["id"]: s for s in data["successes"]}
        self.assertEqual((by_id["B.tools"]["unlocked"], by_id["M4.blind"]["unlocked"]), ("2026-10-01", "2026-09-01"))
        self.assertEqual(by_id["B.fresh"]["lost"], "2026-10-05")
        self.assertEqual([h["medal"] for h in data["history"]], ["none", "silver"])

    def test_a_file_of_another_kind_or_a_broken_one_is_not_trusted(self):
        for previous in ("x", [], {"schema": 99}, {"schema": 1, "kind": "repo", "successes": None},
                         {"schema": 1, "kind": "repo", "successes": [{"id": ["A1"], "unlocked": "2020-01-01"}]},
                         {"schema": 1, "kind": "repo", "successes": [{"id": "A1", "unlocked": 5}]},
                         {"schema": 1, "kind": "repo", "successes": [{"id": "A1", "unlocked": "2099-01-01"}], "history": {}}, {"schema": 1, "kind": "marketplace", "successes": [{"id": "A1", "unlocked": "2020-01-01"}]},
                         {"schema": 1, "kind": "repo", "successes": ["x", {"nope": 1}], "history": ["x"]}):
            data = medals.build(evaluated({"A1": True}), previous)
            self.assertEqual(data["successes"][0]["unlocked"], "2026-11-15")


class RepoTests(RepoCase):
    def test_an_empty_repo_has_no_medal_and_a_framed_one_has_bronze(self):
        self.assertEqual(medals.build(medals.evaluate_repo(self.repo))["medal"]["id"], "none")
        for text in (AGENTS, AGENTS_FR):
            with self.subTest(language="en" if text is AGENTS else "fr"):
                self.write("AGENTS.md", text)
                data = medals.build(medals.evaluate_repo(self.repo))
                self.assertEqual(data["medal"]["id"], "bronze")
                bonus = {s["id"]: s for s in data["successes"] if s["tier"] == "bonus"}
                self.assertTrue(bonus["B.dates"]["unlocked"])
                self.assertTrue(bonus["B.why"]["unlocked"])
                self.assertFalse(bonus["B.tools"]["unlocked"])

    def test_a_command_the_ci_runs_and_nobody_wrote_locks_its_bonus(self):
        self.write("AGENTS.md", AGENTS)
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: make it\n")
        bonus = {s["id"]: s for s in medals.evaluate_repo(self.repo)["successes"]}
        self.assertFalse(bonus["B.commands"]["passed"])
        self.assertIn("make it", bonus["B.commands"]["evidence"])

    def test_write_keeps_the_file_and_the_dates_between_two_runs(self):
        self.write("AGENTS.md", AGENTS)
        code, _ = self.run_cli("--write", "--today", "2026-10-01")
        self.assertEqual(code, 0)
        self.run_cli("--write", "--today", "2026-11-15")
        with open(os.path.join(self.repo, ".harness", "medals.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual({s["unlocked"] for s in data["successes"] if s["tier"] == "bronze"}, {"2026-10-01"})
        self.write("AGENTS.md", AGENTS.replace("## Forbidden", "## Other"))     # a bronze achievement is lost
        self.run_cli("--write", "--today", "2026-12-01")
        with open(os.path.join(self.repo, ".harness", "medals.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual((data["date"], data["medal"]["id"]), ("2026-12-01", "none"))
        lost = [s for s in data["successes"] if s["lost"]]
        self.assertEqual([(s["id"], s["lost"]) for s in lost], [("L1.forbidden", "2026-12-01")])

    def test_the_same_measure_another_day_does_not_touch_the_file_and_keeps_its_name(self):
        self.write("AGENTS.md", AGENTS)
        self.run_cli("--write", "--today", "2026-10-01", "--name", "my-repo")
        path = os.path.join(self.repo, ".harness", "medals.json")
        with open(path, encoding="utf-8") as fh:
            first = fh.read()
        code, out = self.run_cli("--write", "--today", "2026-11-15")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), first)
        self.assertIn("my-repo", out)
        self.assertFalse(os.path.exists(path + ".tmp"))

    def test_a_broken_file_or_a_bad_argument_is_a_message_not_a_crash(self):
        self.write("AGENTS.md", AGENTS)
        self.write(".harness/medals.json", "{")
        self.assertEqual(self.run_cli("--write")[0], 0)
        self.assertEqual(self.run_cli("--today", "2026-13-45")[0], 2)
        self.assertEqual(self.run_cli("--page", os.path.join(self.repo, "absent", "p.html"))[0], 2)

    def test_without_write_nothing_is_created(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("No medal yet", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))


class NoSourceTests(RepoCase):
    """No instruction file: what cannot be measured is said so, not shown as measured and failed."""
    NEED_THE_FILE = ("B.fresh", "B.dates", "B.why", "B.tools", "B.targets", "B.commands")

    def test_off_rank_achievements_say_not_measured(self):
        found = medals.evaluate_repo(self.repo)
        self.assertEqual(found["rank"], 0)
        by_id = {s["id"]: s for s in found["successes"]}
        for ident in self.NEED_THE_FILE:
            with self.subTest(achievement=ident):
                self.assertFalse(by_id[ident]["passed"])
                self.assertEqual(by_id[ident]["evidence"], "not measured: no instruction file")
                self.assertIn("harness-init", by_id[ident]["next"])
        self.assertIn("target", by_id["B.target"]["evidence"])          # this one does not read the file

    def test_the_text_shows_no_false_count_and_one_next_step(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("[ ] No reference without a target (not measured: no instruction file)", out)
        self.assertNotIn("0 reference(s) without a target", out)
        self.assertNotIn("0 of 0", out)
        steps = out.split("## Next steps\n")[1].strip().splitlines()
        self.assertEqual(len(steps), 1, steps)
        self.assertIn("harness-init", steps[0])

    def test_the_rank_achievements_that_come_with_the_file_say_so_and_still_count_as_missing(self):
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertEqual(data["medal"]["id"], "none")
        self.assertEqual(data["why"], "No medal yet: 5 achievement(s) missing for bronze.")
        bronze = {s["id"]: s for s in data["successes"] if s["tier"] == "bronze"}
        self.assertTrue(bronze["L1.source"]["next"])
        for ident in ("L1.mode", "L1.short", "L1.single_source", "L1.forbidden"):
            with self.subTest(achievement=ident):
                self.assertIsNone(bronze[ident]["unlocked"])
                self.assertIsNone(bronze[ident]["next"])
                self.assertEqual(bronze[ident]["evidence"], "comes with the instruction file")
        self.assertEqual([s["id"] for s in data["next"]], ["L1.source"])

    def test_with_a_file_the_measure_is_shown(self):
        self.write("AGENTS.md", AGENTS)
        by_id = {s["id"]: s for s in medals.evaluate_repo(self.repo)["successes"]}
        self.assertEqual(by_id["B.targets"]["evidence"], "0 reference(s) without a target")
        self.assertTrue(by_id["B.targets"]["passed"])


class TargetTests(RepoCase):
    """A level is a place where one can stay: at the target, medals proposes nothing more and makes
    the same one-line offer as the map (`status --map`)."""

    def target(self, level: int) -> None:
        self.write("AGENTS.md", AGENTS)
        self.write(".harness/config.json", json.dumps({"target_level": level}))

    def test_target_reached_gives_no_next_step_beyond_it(self):
        self.target(1)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertEqual(data["medal"]["id"], "bronze")
        self.assertEqual(data["next"], [])
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertNotIn("## Next steps", out)
        self.assertNotIn("harness-harvest", out)

    def test_target_reached_makes_the_offer_of_the_map(self):
        self.target(1)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertIn("level 2 (Looped) would bring this", data["offer"])
        self.assertIn("It is your choice.", data["offer"])
        shown = maturity.render_map(maturity.evaluate(facts.collect(self.repo)))
        self.assertIn(data["offer"][1:], shown)                 # the same sentence, capital apart
        _, out = self.run_cli()
        self.assertIn("## Target reached\n" + data["offer"], out)

    def test_a_target_above_the_rank_keeps_the_steps_towards_it(self):
        self.target(2)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertIsNone(data["offer"])
        self.assertTrue(data["next"])
        self.assertTrue(all(s["id"].startswith("L2.") for s in data["next"]), data["next"])

    def test_without_a_target_the_next_rank_is_still_proposed(self):
        self.write("AGENTS.md", AGENTS)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertIsNone(data["offer"])
        self.assertTrue(data["next"])
        self.assertIn("## Next steps", medals.render_md(data))

    def test_a_marketplace_has_no_target_and_keeps_its_steps(self):
        data = medals.build(medals.evaluate_marketplace(self.repo))
        self.assertIsNone(data["offer"])
        self.assertTrue(data["next"])


class PlainWordsTests(RepoCase):
    """The text speaks like the map: no check id, signal code or priority code; ids stay in the JSON."""

    def test_the_next_steps_are_the_plain_phrases_of_the_map(self):
        self.write("AGENTS.md", AGENTS)
        data = medals.build(medals.evaluate_repo(self.repo))
        self.assertTrue(data["next"])
        for step in data["next"]:
            with self.subTest(step=step["id"]):
                plain = maturity.CHECK_PLAIN[step["id"]][1]
                self.assertEqual(step["action"], plain[0].upper() + plain[1:] + ".")
        self.assertTrue(any(s["waiting"] for s in data["next"]))

    def test_every_missing_achievement_of_a_rank_says_its_step_in_plain_words(self):
        self.write("AGENTS.md", AGENTS)
        found = medals.evaluate_repo(self.repo)
        missing = [s for s in found["successes"] if s["tier"] != "bonus" and not s["passed"]]
        self.assertTrue(missing)
        for s in missing:
            with self.subTest(achievement=s["id"]):
                self.assertNotRegex(s["next"], r"\bL\d\b|\bS\d\b|\bP\d")
                self.assertIn(maturity.CHECK_PLAIN[s["id"]][1][1:], s["next"])

    def test_no_id_or_code_reaches_the_text(self):
        for name, files in (("no file", {}), ("level 1", {"AGENTS.md": AGENTS})):
            with self.subTest(repo=name):
                for rel, text in files.items():
                    self.write(rel, text)
                code, out = self.run_cli()
                self.assertEqual(code, 0)
                self.assertNotRegex(out, r"\bL\d\.|\bL\d\b|\bS\d\b|\bP\d\b")

    def test_the_ids_stay_in_the_json(self):
        self.write("AGENTS.md", AGENTS)
        _, out = self.run_cli("--format", "json")
        data = json.loads(out)
        self.assertIn("L2.signal", [s["id"] for s in data["successes"]])
        self.assertIn("L2.signal", [s["id"] for s in data["next"]])


class MarketplaceTests(RepoCase):
    def plugin(self, description: str) -> None:
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "demo", "plugins": [{"name": "p", "source": "./p"}]}))
        self.write("p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.0", "description": "d"}))
        self.write("p/skills/s/SKILL.md", f"---\nname: s\ndescription: {description}\n---\n# s\n")

    def medal(self) -> dict:
        return medals.build(medals.evaluate_marketplace(self.repo))

    def test_no_manifest_is_no_medal(self):
        self.assertEqual(self.medal()["medal"]["id"], "none")

    def test_an_installable_marketplace_is_bronze_and_a_described_one_silver(self):
        self.plugin("Does things.")
        self.assertEqual(self.medal()["medal"]["id"], "bronze")
        self.plugin("Does things. Use when someone asks for X. Do not use for Y.")
        self.assertEqual(self.medal()["medal"]["rank"], 3)   # without code, nothing to test: gold follows

    def test_code_without_tests_stops_at_silver_and_a_source_outside_the_repo_is_not_followed(self):
        self.plugin("Use when someone asks for X. Do not use for Y.")
        self.write("p/cli/tool.py", "x = 1\n")
        self.assertEqual(self.medal()["medal"]["id"], "silver")
        self.write("p/cli/tests/test_tool.py", "def test_tool():\n    assert True\n")
        self.assertEqual(self.medal()["medal"]["rank"], 3)
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "d", "plugins": [{"name": "p", "source": "../elsewhere"}, "x", {"source": 3}]}))
        self.assertEqual(self.medal()["medal"]["id"], "none")

    def test_descriptions_are_read_as_people_write_them(self):
        for description, when, when_not in (
                ("Utiliser dès que l'utilisateur veut X. Ne pas utiliser pour Y.", True, True),
                (">\n  Fait X. Utiliser quand on demande X.\n  Ne pas utiliser pour Y.", True, True),
                ("Use this when the user asks for X. Do not use for Y.", True, True),
                ("Do not trigger this. Ne pas utiliser pour Y.", False, True),
                ("Fait des choses.", False, False)):
            with self.subTest(description=description):
                self.plugin(description)
                got = {s["id"]: s["passed"] for s in medals.evaluate_marketplace(self.repo)["successes"]}
                self.assertEqual((got["M2.when"], got["M2.when-not"]), (when, when_not))

    def test_a_folder_named_like_a_url_is_a_source_and_a_link_out_of_the_repo_is_not(self):
        self.plugin("x")
        os.rename(os.path.join(self.repo, "p"), os.path.join(self.repo, "http-tools"))
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "d", "plugins": [{"name": "p", "source": "./http-tools"}]}))
        self.assertEqual(self.medal()["medal"]["id"], "bronze")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        os.symlink(outside.name, os.path.join(self.repo, "link"))
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "d", "plugins": [{"name": "p", "source": "./link"}]}))
        self.assertEqual(self.medal()["medal"]["id"], "none")

    def test_an_empty_blind_folder_or_a_test_that_asserts_nothing_unlocks_nothing(self):
        self.plugin("Use when X. Do not use for Y.")
        os.makedirs(os.path.join(self.repo, "fixtures", "a", "runs", "2026-blind"))
        self.write("p/scripts/tool.sh", "echo x\n")
        self.write("p/cli/tests/test_tool.py", "x = 1\n")
        got = {s["id"]: s["passed"] for s in medals.evaluate_marketplace(self.repo)["successes"]}
        self.assertFalse(got["M4.blind"])
        self.assertFalse(got["M3.tests"])

    def test_the_cli_keeps_a_file_per_kind(self):
        self.plugin("x")
        self.run_cli("--kind", "marketplace", "--write")
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".harness", "medals-marketplace.json")))


class PageTests(RepoCase):
    def test_the_page_is_self_contained_and_its_data_cannot_break_out(self):
        self.write("AGENTS.md", AGENTS)
        page = os.path.join(self.repo, "page.html")
        code, _ = self.run_cli("--page", page, "--name", "</script><img src=x onerror=alert(1)>&{{data}}")
        self.assertEqual(code, 0)
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        self.assertNotIn("{{csp}}", html)
        self.assertNotIn("{{title}}", html)
        self.assertEqual(html.count("{{data}}"), 2)   # in the title and in the data: the name, never read again
        self.assertNotIn("<img src=x", html)
        self.assertEqual(html.count("</script>"), 2)
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        self.assertNotIn("innerHTML", html)
        data = json.loads(re.search(r'id="medals-data">(.*?)</script>', html, re.DOTALL)[1])
        self.assertEqual(data["name"], "</script><img src=x onerror=alert(1)>&{{data}}")
        self.assertLess(len(re.search(r"<title>(.*?)</title>", html, re.DOTALL)[1]), 120)
        self.assertIn("sha256-", html)

    def test_the_same_data_gives_the_same_page(self):
        data = medals.build(evaluated({"A1": True, "B1": False}))
        self.assertEqual(medals.render_html(data), medals.render_html(json.loads(json.dumps(data))))


# A stand-in for the browser, just enough for the page's script: it lays the page out, then prints its text.
PAGE_DOM = r"""
const make = (tag) => ({ tag, kids: [], dataset: {}, textContent: "", style: { setProperty() {} },
  setAttribute() {}, addEventListener() {}, querySelectorAll() { return []; },
  append(...kids) { this.kids.push(...kids); }, replaceChildren(...kids) { this.kids = kids; } });
const byId = { "medals-data": { textContent: process.argv[2] }, app: make("main"), detail: make("dialog") };
globalThis.document = { documentElement: make("html"), createElement: make, getElementById: (id) => byId[id] };
const text = (node) => (typeof node === "string" ? node : [node.textContent, ...node.kids.map(text)].join("\n"));
eval(process.argv[1]);
console.log(text(byId.app));
"""
NEEDS_NODE = unittest.skipUnless(shutil.which("node"), "node is not installed: the page's script cannot be run")


class PageTargetTests(RepoCase):
    """The page says what the text says: at the target, the offer of the map, and no step towards a rank."""

    def shown(self, data: dict) -> str:
        script = re.findall(r"<script>(.*?)</script>", medals.render_html(data), re.DOTALL)[-1]
        done = subprocess.run(["node", "-e", PAGE_DOM, "--", script, json.dumps(data)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def reached(self) -> dict:
        self.write("AGENTS.md", AGENTS)
        self.write(".harness/config.json", json.dumps({"target_level": 1}))
        return medals.build(medals.evaluate_repo(self.repo))

    def test_the_template_reads_the_offer(self):
        with open(medals.TEMPLATE_FILE, encoding="utf-8") as fh:
            template = fh.read()
        self.assertTrue("data.offer" in template, "the page's script never reads the offer")
        self.assertTrue("Target reached" in template, "the page's script never says the target is reached")

    @NEEDS_NODE
    def test_target_reached_shows_the_offer_and_no_next_rank(self):
        data = self.reached()
        shown = self.shown(data)
        self.assertIn("Target reached", shown)
        self.assertIn(data["offer"], shown)
        self.assertNotIn("Towards silver", shown)
        self.assertNotIn("Nothing to do for the next rank.", shown)
        self.assertNotIn("before the next rank", shown)

    @NEEDS_NODE
    def test_without_a_target_the_page_keeps_the_steps_towards_the_next_rank(self):
        self.write("AGENTS.md", AGENTS)
        data = medals.build(medals.evaluate_repo(self.repo))
        shown = self.shown(data)
        self.assertIn("Towards silver", shown)
        self.assertIn("before the next rank", shown)
        self.assertIn(data["next"][0]["action"], shown)
        self.assertNotIn("Target reached", shown)

    @NEEDS_NODE
    def test_a_medals_file_written_before_the_offer_still_shows(self):
        self.write("AGENTS.md", AGENTS)
        data = medals.build(medals.evaluate_repo(self.repo))
        del data["offer"]
        self.assertIn("Towards silver", self.shown(data))


if __name__ == "__main__":
    unittest.main()
