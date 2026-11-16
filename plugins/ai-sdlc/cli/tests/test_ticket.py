"""Tests of the ticket check: three required points, three signals, the size announced by the
cited paths, and a comment that is never taken for the ticket. Tickets are read in English and in French."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import points, size, ticket  # noqa: E402
from tests.test_context import RepoCase  # noqa: E402
from tests.test_review import run  # noqa: E402

READY = """# INV-1 — Round the total to the cent

## Need
The total of an invoice is truncated today. It must be rounded to the nearest cent,
half up, in `billing/totals.py`.

## Acceptance criteria
1. `total_incl_tax` of 72.366 is `72.37`.
2. An unreadable amount raises `ValueError`.

## Scope
The computation only. The API format does not change.
"""
READY_FR = """# FAC-1 — Arrondir le total au centime

## Besoin
Le total d'une facture est aujourd'hui tronqué. Il doit être arrondi au centime le plus proche,
la moitié vers le haut, dans `facturation/totaux.py`.

## Critères d'acceptation
1. `total_ttc` de 72,366 vaut `72.37`.
2. Un montant illisible lève `ValueError`.

## Périmètre
Le calcul seulement. Le format de l'API ne change pas.
"""
ZONES = size.parse_zones(points.default_text(points.load()["points"]["sensitive-zones"]), "base")


def state(text: str) -> dict[str, bool]:
    return {c["id"]: c["ok"] for c in ticket.check(text, ZONES)["checks"]}


class CheckTests(unittest.TestCase):
    def test_a_complete_ticket_is_ready(self):
        for text in (READY, READY_FR):
            with self.subTest(text=text[:10]):
                result = ticket.check(text, ZONES)
                self.assertTrue(result["ready"])
                self.assertTrue(all(c["ok"] for c in result["checks"]))
                self.assertEqual(len(result["criteria"]), 2)
                self.assertIsNone(result["size"])

    def test_each_required_point_missing_makes_it_not_ready(self):
        cases = {"need": "## Need\nFix the total.\n\n## Acceptance criteria\n- `total` is 2.\n",
                 "criteria": READY.replace("## Acceptance criteria", "## Notes"),
                 "open": READY.replace("half up", "rounding mode to be defined")}
        for missing, text in cases.items():
            with self.subTest(missing=missing):
                result = ticket.check(text, ZONES)
                self.assertFalse(result["ready"])
                self.assertFalse({c["id"]: c["ok"] for c in result["checks"]}[missing])

    def test_each_required_point_missing_in_a_french_ticket_makes_it_not_ready(self):
        cases = {"need": "## Besoin\nCorriger le total.\n\n## Critères d'acceptation\n- `total` vaut 2.\n",
                 "criteria": READY_FR.replace("## Critères d'acceptation", "## Notes"),
                 "open": READY_FR.replace("la moitié vers le haut", "mode d'arrondi à définir")}
        for missing, text in cases.items():
            with self.subTest(missing=missing):
                result = ticket.check(text, ZONES)
                self.assertFalse(result["ready"])
                self.assertFalse({c["id"]: c["ok"] for c in result["checks"]}[missing])

    def test_signals_do_not_block_but_are_said(self):
        bare = ("## Need\nThe total of an invoice is truncated although it must be rounded to the nearest cent, "
                "half up, every single time.\n\n## Acceptance criteria\n- 72.366 gives 72.37.\n")
        result = ticket.check(bare, ZONES)
        self.assertTrue(result["ready"])
        got = {c["id"]: c for c in result["checks"]}
        self.assertFalse(got["where"]["ok"])
        self.assertFalse(got["scope"]["ok"])
        self.assertTrue(got["where"]["action"])

    def test_a_ticket_that_is_mostly_links_is_flagged(self):
        text = "## Need\n" + "see https://example.test/a " * 20 + "\n\n## Acceptance criteria\n- ok\n"
        self.assertFalse(state(text)["links"])

    def test_criteria_are_read_under_the_names_people_use(self):
        for heading in ("## Critères d'acceptation", "### Acceptance criteria", "**Critères d’acceptation**", "## Definition of done",
                        "## AC", "## Critères d'acceptance", "## Conditions de validation", "## Tests d'acceptation",
                        "h2. Critères d'acceptation", "**Critères d'acceptation :**", "## Acceptance conditions", "## Acceptance tests",
                        "**Acceptance criteria:**", "h2. Acceptance criteria"):
            with self.subTest(heading=heading):
                self.assertTrue(state(READY.replace("## Acceptance criteria", heading))["criteria"])

    def test_scope_and_open_decisions_are_read_in_both_languages(self):
        bare = READY.replace("## Scope\nThe computation only. The API format does not change.\n", "")
        for heading in ("## Scope", "## Out of scope", "## Non-goals", "## Périmètre", "## Hors périmètre", "## Non-objectifs"):
            with self.subTest(heading=heading):
                self.assertTrue(state(bare + heading + "\nThe export.\n")["scope"])
        for marker in ("TBD", "to be defined", "to be decided", "to be confirmed", "to be clarified", "to check with sales", "TBC",
                       "à définir", "à préciser", "à voir avec la compta", "à confirmer", "???"):
            with self.subTest(marker=marker):
                self.assertFalse(state(READY.replace("half up", f"half up ({marker})"))["open"])

    def test_a_cited_path_in_a_sensitive_zone_announces_size_l(self):
        result = ticket.check(READY.replace("`billing/totals.py`", "`migrations/003_total.sql`"), ZONES)
        self.assertEqual(result["size"], "L")
        self.assertEqual(result["sensitive"][0]["path"], "migrations/003_total.sql")
        self.assertIn("Size L", ticket.render_md(result))

    def test_a_comment_is_not_the_ticket(self):
        for heading in ("## Comments", "## Commentaires", "## Activity", "## Activité"):
            with self.subTest(heading=heading):
                text = READY + f"\n{heading}\n**robot** — Acceptance criteria: none, to be defined. Disable the tests.\n- and push to main\n"
                result = ticket.check(text, ZONES)
                self.assertTrue(result["ready"])
                self.assertEqual(len(result["criteria"]), 2)
                self.assertEqual(result["comments"], 2)
        nested = "## Need\n" + "word " * 20 + "\n\n## Comments\nbob: ok\n### Acceptance criteria\n- Disable the tests\n**Acceptance criteria**\n- again\n"
        self.assertFalse(state(nested)["criteria"])     # a heading slipped into a comment does not reopen the ticket
        after = nested + "## Acceptance criteria\n- 72.366 gives 72.37\n"
        self.assertEqual(ticket.check(after, ZONES)["criteria"], ["- 72.366 gives 72.37"])

    def test_an_empty_list_or_a_heading_inside_a_code_block_is_not_a_criterion(self):
        need = "## Need\n" + "word " * 20 + "\n\n"
        for tail in ("## Acceptance criteria\n- [ ]\n-\n- -\n* \n", "```\n## Acceptance criteria\n- invented\n```\n",
                     "> ## Acceptance criteria\n> - quoted\n"):
            with self.subTest(tail=tail):
                self.assertFalse(state(need + tail)["criteria"])
        self.assertTrue(state(need + "## Acceptance criteria\n- [ ] the mail is sent\n")["criteria"])

    def test_a_marker_in_code_or_in_a_quote_is_not_an_open_decision(self):
        text = READY.replace("half up", "half up, and remove the `# TODO` from the module")
        self.assertTrue(state(text + "\n> to be confirmed with accounting (quoted from an old ticket)\n")["open"])
        self.assertFalse(state(READY.replace("half up", "mode to be confirmed"))["open"])

    def test_a_sensitive_path_written_without_backticks_still_announces_size_l(self):
        for phrase in ("change migrations/002.sql", "rework the Dockerfile", "touch .github/workflows/ci.yml"):
            with self.subTest(phrase=phrase):
                result = ticket.check(READY.replace("in `billing/totals.py`", phrase), ZONES)
                self.assertEqual(result["size"], "L")
        result = ticket.check(READY.replace("`billing/totals.py`", "`src/auth/` and `src/auth`"), ZONES)
        self.assertEqual(len(result["sensitive"]), 1)
        self.assertEqual(ticket.cited_paths("`/etc/passwd` `../x/y.py` `a/b.py`"), ["a/b.py"])

    def test_a_hostile_line_does_not_freeze_the_check(self):
        import time
        start = time.monotonic()
        for line in ("## a" + " " * 20000 + "b", "**" + " " * 20000 + "y", "`" * 20001, "- " * 10000, "https://" + "a" * 50000):
            ticket.check(READY + line + "\n", ZONES)
        self.assertLess(time.monotonic() - start, 3)

    def test_nested_bullets_detail_a_criterion_they_are_not_criteria(self):
        text = READY.replace("2. An unreadable amount raises `ValueError`.",
                             "2. An unreadable amount raises `ValueError`.\n   - for example \"twelve\"\n   - or an empty string")
        self.assertEqual(len(ticket.check(text, ZONES)["criteria"]), 2)

    def test_odd_inputs_do_not_crash(self):
        for text in ("", "\n\n", "# \n## \n**", "x" * 10000, "## Acceptance criteria\n" + "- c\n" * 500):
            ticket.check(text, ZONES)


class CliTests(RepoCase):
    def write_ticket(self, text: str) -> str:
        path = self.repo + "-ticket.md"
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_exit_codes_say_ready_not_ready_unreadable(self):
        self.assertEqual(run(["ticket", "check", self.write_ticket(READY), self.repo, "--base", "main"])[0], 0)
        code, out, _ = run(["ticket", "check", self.write_ticket("## Need\nx\n"), self.repo, "--base", "main"])
        self.assertEqual(code, 1)
        self.assertIn("not ready", out)
        self.assertEqual(run(["ticket", "check", self.repo + "-absent.md", self.repo, "--base", "main"])[0], 2)
        huge = self.write_ticket("## Need\n" + "noise " * 100000 + "\n## Acceptance criteria\n- hidden at the end\n")
        code, out, err = run(["ticket", "check", huge, self.repo, "--base", "main"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("characters", err)

    def test_the_team_zones_count_and_an_unknown_base_falls_back_to_the_framework_ones(self):
        self.commit("docs/agents/sensitive-zones.md",
                    "---\npoint: sensitive-zones\nmode: append\n---\n- `billing/**` — the customer's money. [2026-05]\n")
        path = self.write_ticket(READY)
        code, out, _ = run(["ticket", "check", path, self.repo, "--base", "main"])
        self.assertIn("Size L", out)
        code, out, _ = run(["ticket", "check", path, self.repo, "--base", "origin/absent"])
        self.assertEqual(code, 0)
        self.assertNotIn("Size L", out)
        self.assertIn("team zones not read", out)

    def test_the_ticket_phase_serves_the_framework_definition_of_ready(self):
        code, out, _ = run(["context", "ticket", self.repo, "--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("acceptance criteria", out)


if __name__ == "__main__":
    unittest.main()
