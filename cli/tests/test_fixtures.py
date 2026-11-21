"""Tests of the fixture checker: each fixture matches its expected.json, the
audit grader tells a good audit from a bad one, and the init grader tells a
carefully written file from a generated one."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import fixtures  # noqa: E402

JAVA_BACK = os.path.join(fixtures.FIXTURES_ROOT, "java-back")


def load_expected(name):
    with open(os.path.join(fixtures.FIXTURES_ROOT, name, "expected.json"), encoding="utf-8") as fh:
        return json.load(fh)


def good_audit():
    """An audit that finds all the traps of java-back with accepted verdicts."""
    el = lambda path, verdict, prio, layer="L2": {"id": path, "path": path, "actual_layer": layer,  # noqa: E731
                                                   "verdict": verdict, "priority": prio, "evidence": [f"{path}:1"]}
    return {
        "audit": {"health_score": 20, "cut_the_agent_test": {"passed": False, "leaked_steps": 2}},
        "elements": [
            el("CLAUDE.md", "SPLIT", "P2"),
            el(".claude/skills/release/SKILL.md", "PUSH_DOWN", "P1"),
            el("scripts/release.mjs", "PROMOTE", "P3", "L3"),
            el("scripts/hotfix.mjs", "MERGE", "P2", "L3"),
            el(".github/workflows/release.yml", "BLOCK", "P1", "L4"),
            el("scripts/old-deploy.sh", "BLOCK", "P3", "L3"),
            el("src/test/java/com/acme/billing/ArchitectureTest.java", "KEEP", None, "L3"),
        ],
        "process_leaks": [
            {"rule": "constructor injection, never field injection", "told_in": "CLAUDE.md:52", "belongs_in": "L3", "guard_tool": "ArchUnit"},
            {"rule": "develop est vert avant la release", "told_in": ".claude/skills/release/SKILL.md:9", "belongs_in": "L3"},
            {"rule": "VERSION is never updated after the release", "told_in": "scripts/release.mjs:7", "belongs_in": "L3"},
        ],
        "guarded_rules": [{"rule": "no business logic in controllers", "guarded_by": "ArchitectureTest.java"}],
    }


class AllFixturesTests(unittest.TestCase):
    """Each fixture of fixtures/repos matches its expected.json and its traps.md lists its traps."""

    def fixture_names(self):
        return sorted(d for d in os.listdir(fixtures.FIXTURES_ROOT)
                      if os.path.isfile(os.path.join(fixtures.FIXTURES_ROOT, d, "expected.json")))

    def test_at_least_two_fixtures(self):
        self.assertGreaterEqual(len(self.fixture_names()), 2)

    def test_status_matches_expected(self):
        for name in self.fixture_names():
            with self.subTest(fixture=name):
                problems = fixtures.check_status(os.path.join(fixtures.FIXTURES_ROOT, name),
                                                 load_expected(name)["status"], date(2026, 11, 9))
                self.assertEqual(problems, [])

    def test_traps_md_and_expected_agree_on_trap_ids(self):
        for name in self.fixture_names():
            with self.subTest(fixture=name):
                with open(os.path.join(fixtures.FIXTURES_ROOT, name, "traps.md"), encoding="utf-8") as fh:
                    traps_md = fh.read()
                exp = load_expected(name)["audit"]
                for trap in exp["traps"] + exp["sane"] + exp.get("removals", []) + exp.get("must_keep", []):
                    self.assertIn(f"| {trap['id']} |", traps_md, f"{name}:{trap['id']}")

    def test_traps_md_lists_every_init_expectation(self):
        for name in self.fixture_names():
            init = load_expected(name).get("init")
            if not init:
                continue
            with self.subTest(fixture=name):
                with open(os.path.join(fixtures.FIXTURES_ROOT, name, "traps.md"), encoding="utf-8") as fh:
                    traps_md = fh.read()
                for item in init["must_surface"] + init["must_not_write"]:
                    self.assertIn(f"| {item['id']} |", traps_md, f"{name}:{item['id']}")
                self.assertTrue(os.path.isfile(os.path.join(fixtures.FIXTURES_ROOT, name, "owner.md")),
                                f"{name}: an init block needs an owner.md")

    def test_author_init_runs_are_conformant(self):
        """The regression baseline: the init written by the fixture author satisfies the init block."""
        seen = 0
        for name in self.fixture_names():
            runs = os.path.join(fixtures.FIXTURES_ROOT, name, "runs")
            init = load_expected(name).get("init")
            for run in sorted(os.listdir(runs)) if init and os.path.isdir(runs) else []:
                if run.endswith("-author"):
                    with self.subTest(fixture=name, run=run):
                        result = fixtures.check_init(os.path.join(runs, run), init, date(2026, 11, 10),
                                                     base=os.path.join(fixtures.FIXTURES_ROOT, name, "repo"))
                        self.assertEqual(result["problems"], [])
                        seen += 1
        self.assertGreaterEqual(seen, 2)

    def test_author_audits_satisfy_the_audit_block(self):
        """An audit block must be satisfiable: the audit written by the fixture author passes it."""
        seen = 0
        for name in self.fixture_names():
            runs = os.path.join(fixtures.FIXTURES_ROOT, name, "runs")
            for run in sorted(os.listdir(runs)) if os.path.isdir(runs) else []:
                if run.endswith("-audit-author.json"):
                    with self.subTest(fixture=name, run=run):
                        with open(os.path.join(runs, run), encoding="utf-8") as fh:
                            result = fixtures.check_audit(json.load(fh), load_expected(name)["audit"])
                        self.assertTrue(result["ok"], {k: result[k] for k in ("missed", "wrong", "sane_flagged", "global")})
                        seen += 1
        self.assertGreaterEqual(seen, 2)

    def test_every_example_project_carries_a_fact_written_nowhere_else(self):
        """A sample project: at least one fact that is read only in its instructions or held only
        by its owner, exercised by a task check that a tempted solution misses."""
        seen = 0
        for name in self.fixture_names():
            fixture_dir = os.path.join(fixtures.FIXTURES_ROOT, name)
            if os.path.isdir(os.path.join(fixture_dir, "tasks")):
                with self.subTest(fixture=name):
                    self.assertEqual(fixtures.check_oral_facts(fixture_dir, load_expected(name)), [])
                    seen += 1
        self.assertGreaterEqual(seen, 5)

    def test_fixture_readme_does_not_point_to_the_answer_key(self):
        for name in self.fixture_names():
            readme = os.path.join(fixtures.FIXTURES_ROOT, name, "repo", "README.md")
            if os.path.exists(readme):
                with open(readme, encoding="utf-8") as fh:
                    self.assertNotIn("traps.md", fh.read(), name)


class BareCopyTests(unittest.TestCase):
    def test_bare_copy_strips_instrumentation_and_measures_level_0(self):
        import tempfile
        from datetime import date as _date
        from harnesslib import facts, maturity
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "bare")
            removed = fixtures.bare_copy(os.path.join(fixtures.FIXTURES_ROOT, "node-front"), dest)
            self.assertIn("AGENTS.md", removed)
            self.assertIn(".claude/", removed)
            self.assertFalse(os.path.exists(os.path.join(dest, "CLAUDE.md")))
            self.assertTrue(os.path.exists(os.path.join(dest, "package.json")))
            self.assertTrue(os.path.isdir(os.path.join(dest, ".git")))
            with open(os.path.join(dest, "README.md"), encoding="utf-8") as fh:
                self.assertNotIn("fixture", fh.read().lower())
            state = maturity.evaluate(facts.collect(dest, today=_date(2026, 11, 9)))
            self.assertEqual(state["level"]["reached"], 0)


class AuditGraderTests(unittest.TestCase):
    def setUp(self):
        self.expected = load_expected("java-back")["audit"]

    def test_good_audit_is_conformant(self):
        r = fixtures.check_audit(good_audit(), self.expected)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["score"], "8/8")

    def test_missed_trap_and_wrong_verdict_are_reported(self):
        audit = good_audit()
        audit["elements"] = [e for e in audit["elements"] if e["path"] != "scripts/old-deploy.sh"]
        audit["elements"][0]["verdict"] = "KEEP"   # CLAUDE.md judged healthy
        r = fixtures.check_audit(audit, self.expected)
        self.assertFalse(r["ok"])
        self.assertTrue(any("T6" in m for m in r["missed"]))
        self.assertTrue(any("T1" in w for w in r["wrong"]))

    def test_flagging_a_sane_element_is_penalised(self):
        audit = good_audit()
        for e in audit["elements"]:
            if e["path"].endswith("ArchitectureTest.java"):
                e["verdict"], e["priority"] = "PUSH_DOWN", "P2"
        r = fixtures.check_audit(audit, self.expected)
        self.assertEqual(len(r["sane_flagged"]), 1)

    def test_style_convention_in_leaks_is_a_bias(self):
        audit = good_audit()
        audit["process_leaks"].append({"rule": "Classes PascalCase", "told_in": "CLAUDE.md:66", "belongs_in": "L3"})
        r = fixtures.check_audit(audit, self.expected)
        self.assertTrue(any("pascalcase" in x for x in r["sane_flagged"]), r)

    def test_guarded_rule_matched_by_path_not_language(self):
        audit = good_audit()
        audit["guarded_rules"] = [{"rule": "pas de logique métier dans les contrôleurs", "guarded_by": "ArchitectureTest.java:14"}]
        self.assertTrue(fixtures.check_audit(audit, self.expected)["ok"])
        audit["guarded_rules"] = []
        self.assertTrue(any("ArchitectureTest" in g for g in fixtures.check_audit(audit, self.expected)["global"]))

    def test_require_leak_ignores_element_verdict(self):
        audit = good_audit()
        audit["process_leaks"] = [l for l in audit["process_leaks"] if "VERSION" not in l["rule"]]
        r = fixtures.check_audit(audit, self.expected)
        self.assertTrue(any("T13" in m for m in r["missed"]), r)

    def test_lying_guard_is_penalised(self):
        exp = load_expected("node-front")["audit"]
        audit = {"audit": {"cut_the_agent_test": {"passed": False}, "health_score": 10}, "elements": [],
                 "process_leaks": [], "guarded_rules": [{"rule": "every string goes through t()", "guarded_by": "scripts/check-i18n.mjs"}]}
        r = fixtures.check_audit(audit, exp)
        self.assertTrue(any("check-i18n" in x for x in r["sane_flagged"]), r)
        # the same script attributed to the rule it really verifies is not penalised
        audit["guarded_rules"] = [{"rule": "fr/en key parity", "guarded_by": "scripts/check-i18n.mjs:13"}]
        self.assertEqual(fixtures.check_audit(audit, exp)["sane_flagged"], [])

    def test_a_leak_is_matched_one_entry_at_a_time(self):
        trap = {"id": "T", "path": "nowhere", "verdicts": ["PUSH_DOWN"], "leak_keywords": ["mail", "import"], "require_leak": True}
        spread = {"process_leaks": [{"rule": "no e-mail per line"}, {"rule": "an import does not exceed the capacity"}]}
        self.assertTrue(fixtures.check_audit(spread, {"traps": [trap]})["missed"])
        together = {"process_leaks": [{"rule": "an import does not send one mail per line"}]}
        self.assertEqual(fixtures.check_audit(together, {"traps": [trap]})["found"], ["T"])

    def test_leak_any_of_accepts_either_wording(self):
        trap = {"id": "T", "path": "nowhere", "verdicts": ["PUSH_DOWN"], "leak_any_of": ["select_for_update", "enroll("], "require_leak": True}
        self.assertEqual(fixtures.check_audit({"process_leaks": [{"rule": "everything goes through enroll()"}]}, {"traps": [trap]})["found"], ["T"])
        result = fixtures.check_audit({"process_leaks": [{"rule": "no bulk e-mail"}]}, {"traps": [trap]})
        self.assertIn("one of", result["missed"][0])

    def test_a_rule_nothing_verifies_cannot_be_declared_guarded_whatever_the_guard(self):
        never = {"never_guarded": [{"what": "only the review", "rule_keywords": ["idempot"]}]}
        lie = {"guarded_rules": [{"rule": "idempotency key on writes", "guarded_by": "code review"}]}
        self.assertTrue(any("nothing verifies it" in f for f in fixtures.check_audit(lie, never)["sane_flagged"]))
        honest = {"guarded_rules": [{"rule": "dependencies between layers", "guarded_by": "tools/archcheck"}]}
        self.assertTrue(fixtures.check_audit(honest, never)["ok"])
        self.assertFalse(fixtures.check_audit(honest, {"no_guard_exists": True})["ok"])

    def test_rule_all_of_needs_every_word(self):
        never = {"never_guarded": [{"what": "x", "rule_all_of": ["packages/shared", "web"]}]}
        other = {"guarded_rules": [{"rule": "a status is declared in packages/shared", "guarded_by": "ticket.test.ts"}]}
        self.assertTrue(fixtures.check_audit(other, never)["ok"])
        lie = {"guarded_rules": [{"rule": "packages/shared is validated with the web tests", "guarded_by": "ci.yml"}]}
        self.assertFalse(fixtures.check_audit(lie, never)["ok"])

    def test_a_sane_file_cited_as_contrast_does_not_borrow_a_verdict(self):
        sane = {"sane": [{"id": "S1", "path": "test/orders.test.js", "verdicts": ["KEEP"]}]}
        audit = {"elements": [{"path": "test/webhook-retry.test.js", "verdict": "BLOCK", "priority": "P2",
                               "evidence": ["test/webhook-retry.test.js:4", "test/orders.test.js:10"]}]}
        self.assertEqual(fixtures.check_audit(audit, sane)["sane_flagged"], [])
        audit["elements"].append({"path": "test/orders.test.js", "verdict": "PUSH_DOWN", "priority": "P3", "evidence": []})
        self.assertTrue(fixtures.check_audit(audit, sane)["sane_flagged"])

    def test_global_expectations(self):
        audit = good_audit()
        audit["audit"]["cut_the_agent_test"]["passed"] = True
        audit["audit"]["health_score"] = 85
        audit["process_leaks"] = []
        r = fixtures.check_audit(audit, self.expected)
        self.assertTrue(any("cut the agent" in g for g in r["global"]))
        self.assertTrue(any("score 85" in g for g in r["global"]))
        # without an "injection" leak nor a PUSH_DOWN element on CLAUDE.md, T2 has a wrong verdict
        self.assertTrue(any("T2" in w for w in r["wrong"]), r)


if __name__ == "__main__":
    unittest.main()


class InitGraderTests(unittest.TestCase):
    """The init grader: facts surfaced, noise copied, guardrails cited or wrongly believed."""

    GOOD = """# x

Mode: **delegation**.

## Rules
- The domain depends on nothing. Why: ADR 0001. Enforced by: `tools/archcheck`, job `arch`.
- Every write requires an idempotency key. Why: the double debit incident. (unverified)
- An amount is an integer in cents, never a float. Why: ADR 0002. (unverified)
- An applied migration is never modified again. (unverified)
- A replayed response carries the `Idempotency-Replayed: true` header. Why: the mobile app, told by the team. (unverified)

## Forbidden
- `make reset-db` outside the local database.
"""

    # The same file in French: the graders read the instructions in either language.
    GOOD_FR = """# x

Mode : **délégation**.

## Règles
- Le domaine ne dépend de rien. Pourquoi : ADR 0001. Vérifiée par : `tools/archcheck`, job `arch`.
- Toute écriture exige une clé d'idempotence. Pourquoi : incident du double débit. (non vérifiée)
- Un montant est un entier en centimes, jamais un flottant. Pourquoi : ADR 0002. (non vérifiée)
- Une migration appliquée ne se modifie plus. (non vérifiée)
- Une réponse rejouée porte l'en-tête `Idempotency-Replayed: true`. Pourquoi : l'application mobile, dit par l'équipe. (non vérifiée)

## Interdits
- `make reset-db` hors base locale.
"""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.init = load_expected("go-hexa")["init"]

    def tearDown(self):
        self.tmp.cleanup()

    def grade(self, agents_md):
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(agents_md)
        return fixtures.check_init(self.tmp.name, self.init, date(2026, 11, 10))

    def test_good_init_is_conformant(self):
        result = self.grade(self.GOOD)
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["score"], "6/6")

    def test_good_init_in_french_is_conformant_too(self):
        result = self.grade(self.GOOD_FR)
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["score"], "6/6")

    def test_missing_fact_is_reported(self):
        result = self.grade(self.GOOD.replace("- `make reset-db` outside the local database.", "- Nothing to report."))
        self.assertTrue(any(p.startswith("I2 not surfaced") for p in result["problems"]), result["problems"])

    def test_copied_noise_is_reported_with_its_file(self):
        result = self.grade(self.GOOD + "- Write idiomatic Go; `gofmt` before committing.\n- `make e2e` before pushing.\n")
        text = " ".join(result["problems"])
        self.assertIn("N1 wrongly written", text)
        self.assertIn("N2 wrongly written", text)
        self.assertIn("AGENTS.md", text)

    # The project's original repository: without it, nothing says whether a line is copied, and every word counts.
    ORIGIN = os.path.join(fixtures.FIXTURES_ROOT, "go-hexa", "repo")

    def grade_against_origin(self, agents_md):
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(agents_md)
        return fixtures.check_init(self.tmp.name, self.init, date(2026, 11, 10), base=self.ORIGIN)

    def test_a_command_named_to_say_it_is_gone_is_a_citation_not_noise(self):
        result = self.grade_against_origin(self.GOOD + "- The README cites `make e2e`, which no longer exists: `make test` is the reference.\n")
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(result["mentions"]), 1, result["mentions"])
        self.assertIn("N1 cited, not counted", result["mentions"][0])
        self.assertIn("make e2e", result["mentions"][0])

    def test_a_command_named_to_say_it_is_gone_in_french_is_a_citation_too(self):
        result = self.grade_against_origin(self.GOOD_FR + "- Le README cite `make e2e`, qui n'existe plus : `make test` fait foi.\n")
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(result["mentions"]), 1, result["mentions"])

    def test_english_gone_markers(self):
        for said in ("was deleted", "is outdated", "is stale", "doesn’t exist"):
            with self.subTest(said=said):
                result = self.grade_against_origin(self.GOOD + f"- The README cites `make e2e`, which {said}.\n")
                self.assertEqual(result["problems"], [], said)

    def test_a_gone_command_given_as_a_thing_to_run_still_counts(self):
        result = self.grade_against_origin(self.GOOD + "- `make e2e` before pushing.\n")
        self.assertTrue(any(p.startswith("N1 wrongly written") for p in result["problems"]), result["problems"])
        self.assertEqual(result["mentions"], [])

    def test_a_line_taken_from_the_original_counts_even_when_it_says_gone(self):
        with open(os.path.join(self.ORIGIN, "README.md"), encoding="utf-8") as fh:
            source = next(line for line in fh if "make e2e" in line)
        copied = source.strip().lstrip("-# ").rstrip() + " (removed since)"
        result = self.grade_against_origin(self.GOOD + f"- {copied}\n")
        self.assertTrue(any(p.startswith("N1 wrongly written") for p in result["problems"]), (copied, result))

    def test_a_citation_is_not_excused_without_the_original_repository(self):
        result = self.grade(self.GOOD + "- The README cites `make e2e`, which no longer exists.\n")
        self.assertTrue(any(p.startswith("N1 wrongly written") for p in result["problems"]), result["problems"])

    def test_noise_that_no_rule_needs_to_name_counts_wherever_it_stands(self):
        result = self.grade_against_origin(self.GOOD + "- The \"idiomatic Go\" style of CONTRIBUTING no longer exists.\n")
        self.assertTrue(any(p.startswith("N2 wrongly written") for p in result["problems"]), result["problems"])

    def test_lying_guard_is_not_believed(self):
        lie = self.GOOD.replace("never a float. Why: ADR 0002. (unverified)",
                                "never a float. Why: ADR 0002. Enforced by: golangci-lint, job `lint`.")
        result = self.grade(lie)
        self.assertTrue(any("lying guardrail" in p for p in result["problems"]), result["problems"])

    def test_real_guard_must_be_cited(self):
        result = self.grade(self.GOOD.replace("Enforced by: `tools/archcheck`, job `arch`.", "See `tools/archcheck`. (unverified)"))
        self.assertTrue(any("archcheck cited by no" in p for p in result["problems"]), result["problems"])

    def test_citing_a_contract_that_does_not_exist_is_reported(self):
        result = self.grade(self.GOOD + "\n## Delegated tasks\n- `add-endpoint`: add an endpoint.\n")
        self.assertTrue(any("reference without a target: `add-endpoint`" in p for p in result["problems"]), result["problems"])

    def test_first_step_must_not_lay_material_of_later_levels(self):
        init = {**self.init, "only_level_material": True}
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(self.GOOD + "\n## Maintenance of this file\n- `rule:` in review.\n\n<!-- harvest: last=2026-11-10 ref=init -->\n")
        result = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))
        self.assertTrue(any("later levels" in p for p in result["problems"]), result["problems"])

    def test_rewriting_a_healthy_file_is_zeal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as base:
            with open(os.path.join(base, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.GOOD)
            init = {**self.init, "min_similarity": [{"path": "AGENTS.md", "ratio": 0.8}]}
            with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.GOOD.replace("(unverified)\n\n## Forbidden", "(unverified) [2026-11]\n\n## Forbidden"))
            touched = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10), base=base)
            self.assertEqual(touched["problems"], [])
            rewritten = "\n".join(reversed(self.GOOD.replace("Why", "Reason").splitlines())) + "\n"
            with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write("# x\n\nMode: **delegation**.\n\n## Forbidden\n- `make reset-db`.\n\n## Rules\n" + rewritten)
            zealous = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10), base=base)
            self.assertTrue(any("rewritten" in p for p in zealous["problems"]), zealous["problems"])

    def test_verified_by_review_is_refused_for_a_rule_nothing_verifies(self):
        init = {**self.init, "never_guarded": [{"what": "only the review", "rule_keywords": ["idempot"]}]}
        lie = self.GOOD.replace("Why: the double debit incident. (unverified)", "Why: the double debit incident. Enforced by: code review.")
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(lie)
        result = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))
        self.assertTrue(any("nothing verifies it" in p for p in result["problems"]), result["problems"])
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(self.GOOD)
        self.assertEqual(fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))["problems"], [])
        self.assertTrue(fixtures.check_init(self.tmp.name, {**init, "no_guard_exists": True}, date(2026, 11, 10))["problems"])

    def test_side_notes_left_as_they_were_are_reported(self):
        init = {**self.init, "must_not_remain": [{"path": "PLAN.md", "what": "abandoned plan", "max_lines": 3},
                                                 {"path": "NOTES.md", "what": "log", "any_of": ["session 3"]}]}
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(self.GOOD)
        self.assertEqual(fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))["problems"], [])   # absent: nothing to say
        for name, text in (("PLAN.md", "a\nb\nc\nd\n"), ("NOTES.md", "Session 3: fixed the total\n")):
            with open(os.path.join(self.tmp.name, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        problems = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))["problems"]
        self.assertEqual(len(problems), 2, problems)

    def test_the_report_is_graded_when_given(self):
        init = {**self.init, "report_must_mention": [{"what": "where the key is", "any_of": ["default.json"]}],
                "report_must_not_mention": [{"what": "the value of a secret", "any_of": ["sk_test_"]}]}
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(self.GOOD)
        grade = lambda report: fixtures.check_init(self.tmp.name, init, date(2026, 11, 10), report=report)["problems"]  # noqa: E731
        self.assertEqual(grade(None), [])
        self.assertEqual(grade("A key is in clear in config/default.json, to regenerate."), [])
        self.assertTrue(any("says nothing" in p for p in grade("All is well.")))
        self.assertTrue(any("contains the value" in p for p in grade("default.json contains sk_test_abc")))

    def test_level_below_target_is_reported(self):
        result = self.grade(self.GOOD.replace("Mode: **delegation**.", ""))
        self.assertTrue(any("L1.mode" in p for p in result["problems"]), result["problems"])

    def test_generated_file_never_reviewed_fails_on_every_noise_family(self):
        repo = os.path.join(fixtures.FIXTURES_ROOT, "ts-monorepo", "repo")
        result = fixtures.check_init(repo, load_expected("ts-monorepo")["init"], date(2026, 11, 10))
        text = " ".join(result["problems"])
        for noise in ("N1", "N2", "N3", "N4", "N5", "N6", "N7"):
            self.assertIn(f"{noise} wrongly written", text)
        self.assertEqual(result["score"], "4/5")      # the repository's facts are there, drowned; the one only the team holds is not


class RemovalGraderTests(unittest.TestCase):
    """The removal verdict: accepted reason, question to the owner for what is outdated, lines to keep."""

    def setUp(self):
        self.expected = {k: v for k, v in load_expected("ts-monorepo")["audit"].items() if k in ("removals", "must_keep")}

    def removals(self, **override):
        base = {
            "N2": {"path": "CLAUDE.md", "line": 62, "text": "Use meaningful variable names.", "reason": "useless"},
            "N3": {"path": "CLAUDE.md", "line": 71, "text": "IMPORTANT: Think step by step before making any change.", "reason": "useless"},
            "N3b": {"path": "CLAUDE.md", "line": 74, "text": "Never apply partial edits to a file larger than 500 lines", "reason": "harmful"},
            "N4": {"path": "apps/web/CLAUDE.md", "line": 6, "text": "No optional chaining: IE11", "reason": "outdated", "ask_owner": True},
            "N5": {"path": "apps/web/CLAUDE.md", "line": 5, "text": "import it from ../../api/src/tickets/service.ts", "reason": "harmful"},
        }
        base.update(override)
        return {"removals": [r for r in base.values() if r]}

    def test_every_expected_removal_found(self):
        result = fixtures.check_audit(self.removals(), self.expected)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["score"], "5/5")

    def test_missing_removal_is_reported(self):
        result = fixtures.check_audit(self.removals(N3b=None), self.expected)
        self.assertTrue(any(m.startswith("N3b") for m in result["missed"]), result)

    def test_wrong_reason_is_reported(self):
        result = fixtures.check_audit(self.removals(N2={"path": "CLAUDE.md", "text": "Use meaningful variable names.", "reason": "harmful"}), self.expected)
        self.assertTrue(any(w.startswith("N2") for w in result["wrong"]), result)

    def test_outdated_line_removed_without_asking_the_owner_is_wrong(self):
        result = fixtures.check_audit(self.removals(N4={"path": "apps/web/CLAUDE.md", "text": "IE11", "reason": "outdated"}), self.expected)
        self.assertTrue(any("question to the owner" in w for w in result["wrong"]), result)

    def test_a_removal_cited_by_part_of_its_line_is_recognised_from_its_location(self):
        # 2026-11-14: the removed 64 KB limit, quoted by its "Why" alone, missed by the grader
        import tempfile
        with tempfile.TemporaryDirectory() as repo:
            with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write("# x\n- An event weighs less than 64 KB. Why: the shared plan cuts the connection.\n")
            removal = {"path": "AGENTS.md", "line": 2, "text": "Why: the shared plan cuts the connection", "reason": "outdated", "ask_owner": True}
            expected = {"removals": [{"id": "N2", "any_of": ["64 kb"], "reasons": ["outdated"], "ask_owner": True}]}
            self.assertEqual(fixtures.check_audit({"removals": [removal]}, expected)["found"], [])
            self.assertEqual(fixtures.check_audit({"removals": [removal]}, expected, repo=repo)["found"], ["N2"])
            outside = dict(removal, path="../AGENTS.md")
            self.assertEqual(fixtures.check_audit({"removals": [outside]}, expected, repo=repo)["found"], [])

    def test_removing_a_line_worth_keeping_is_penalised(self):
        gold = {"path": "CLAUDE.md", "line": 103, "text": "when you change anything in `packages/shared`, run npm run test:web", "reason": "useless"}
        result = fixtures.check_audit(self.removals(GOLD=gold), self.expected)
        self.assertTrue(any(f.startswith("I1") for f in result["sane_flagged"]), result)
        self.assertFalse(result["ok"])


class OralFactTests(unittest.TestCase):
    """A fact "written nowhere else": absent from the rest of the repository, learnable, exercised, separating."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = self.tmp.name
        self.put("repo/README.md", "# demo\n")
        self.put("repo/src/app.py", "def deposit():\n    return 201\n")
        self.put("owner.md", "A replayed response carries the Idempotency-Replayed header.\n")
        self.task = {"checks": [{"id": "replay_header", "what": "x", "run": "true", "acceptance": True, "exercises": "I6"}],
                     "tempted": [{"patch": "tempted/without.patch", "fails": ["replay_header"]}]}
        self.expected = {"init": {"must_surface": [
            {"id": "I1", "what": "in the docs", "any_of": ["idempot"]},
            {"id": "I6", "what": "header", "any_of": ["idempotency-replayed"], "only_in_instructions": ["idempotency-replayed"]}]}}
        self.save_task()

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text):
        path = os.path.join(self.fx, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def save_task(self):
        self.put("tasks/deposit/task.json", json.dumps(self.task))

    def problems(self):
        return fixtures.check_oral_facts(self.fx, self.expected)

    def test_a_fact_only_the_owner_holds_exercised_by_a_separating_check(self):
        self.assertEqual(self.problems(), [])

    def test_a_fixture_without_tasks_is_not_concerned(self):
        import shutil
        shutil.rmtree(os.path.join(self.fx, "tasks"))
        self.assertEqual(fixtures.check_oral_facts(self.fx, {"init": {"must_surface": []}}), [])

    def test_a_project_whose_every_fact_is_documented_is_reported(self):
        self.expected["init"]["must_surface"].pop()
        self.assertTrue(any("only_in_instructions" in p for p in self.problems()))

    def test_a_fact_also_written_in_a_document_is_discoverable(self):
        self.put("repo/docs/adr/0004.md", "We set the Idempotency-Replayed header on replays.\n")
        self.assertTrue(any("discoverable" in p and "docs/adr/0004.md" in p for p in self.problems()), self.problems())

    def test_a_piece_of_the_fact_that_leads_to_it_is_a_hint(self):
        # 2026-11-13: a validator that lists `deprecated` among its annotations, and the bare agent set it on its own
        self.put("owner.md", 'A replaced field gets "deprecated": true.\n')
        self.expected["init"]["must_surface"][1]["only_in_instructions"] = ['"deprecated": true']
        self.put("repo/tools/schema.py", 'ANNOTATIONS = {"title", "description", "deprecated"}\n')
        self.assertTrue(any("a piece of the fact" in p and "tools/schema.py" in p for p in self.problems()), self.problems())

    def test_a_piece_inside_a_longer_word_is_no_hint(self):
        self.put("owner.md", 'A replaced field gets "deprecated": true.\n')
        self.expected["init"]["must_surface"][1]["only_in_instructions"] = ['"deprecated": true']
        self.put("repo/src/app.py", "def undeprecated_helper():\n    return deprecated_v2\n")
        self.assertEqual(self.problems(), [])

    def test_the_pieces_of_a_fact(self):
        self.assertEqual(fixtures.hint_tokens('"deprecated": true'), ["deprecated"])
        self.assertEqual(fixtures.hint_tokens("idempotency-replayed"), [])
        self.assertEqual(fixtures.hint_tokens("shared/package.json"), [])

    def test_a_fact_in_the_repository_s_own_instructions_is_fine(self):
        self.put("owner.md", "nothing\n")
        self.put("repo/services/billing/AGENTS.md", "- A replayed response carries Idempotency-Replayed.\n")
        self.assertEqual(self.problems(), [])

    def test_a_fact_nobody_can_learn_is_reported(self):
        self.put("owner.md", "nothing\n")
        self.assertTrue(any("nowhere to learn it" in p for p in self.problems()))

    def test_a_fact_no_task_check_exercises_is_reported(self):
        del self.task["checks"][0]["exercises"]
        self.save_task()
        self.assertTrue(any("no task check" in p for p in self.problems()))

    def test_an_exercising_check_no_tempted_solution_fails_is_reported(self):
        self.task["tempted"] = [{"patch": "tempted/other.patch", "fails": ["acceptance"]}]
        self.save_task()
        self.assertTrue(any("nothing proves that the check separates" in p for p in self.problems()))


class CleanErrorTests(unittest.TestCase):
    """A typo on the command line ends in one sentence and exit code 2, never in a traceback."""

    HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "harness.py")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, self.HARNESS, *args], capture_output=True, text=True, timeout=60)

    def assert_one_sentence(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)

    def test_an_unknown_fixture_lists_the_known_names(self):
        result = self.run_cli("fixture", "check", "nope-unknown")
        self.assert_one_sentence(result)
        self.assertIn("nope-unknown", result.stderr)
        self.assertIn("java-back", result.stderr)

    def test_an_unknown_fixture_for_a_bare_copy_lists_the_known_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("fixture", "bare", "nope-unknown", os.path.join(tmp, "dest"))
            self.assert_one_sentence(result)
            self.assertIn("java-back", result.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "dest")))

    def test_a_folder_without_expected_json_is_not_a_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("fixture", "check", tmp)
            self.assert_one_sentence(result)
            self.assertIn("expected.json", result.stderr)

    def test_a_missing_audit_file_says_where_it_comes_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "audit.json")
            result = self.run_cli("fixture", "check", "java-back", "--audit", missing)
            self.assert_one_sentence(result)
            self.assertIn(missing, result.stderr)
            self.assertIn("harness-audit", result.stderr)

