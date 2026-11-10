"""Tests du vérificateur de fixtures : chaque fixture est conforme à son
expected.json, le notateur d'audit distingue un bon audit d'un mauvais, et le
notateur d'init distingue un fichier écrit avec soin d'un fichier généré."""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import fixtures  # noqa: E402

JAVA_BACK = os.path.join(fixtures.FIXTURES_ROOT, "java-back")


def load_expected(name):
    with open(os.path.join(fixtures.FIXTURES_ROOT, name, "expected.json"), encoding="utf-8") as fh:
        return json.load(fh)


def good_audit():
    """Un audit qui trouve tous les pièges de java-back avec des verdicts acceptés."""
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
            {"rule": "VERSION n'est jamais mis à jour après la release", "told_in": "scripts/release.mjs:7", "belongs_in": "L3"},
        ],
        "guarded_rules": [{"rule": "no business logic in controllers", "guarded_by": "ArchitectureTest.java"}],
    }


class AllFixturesTests(unittest.TestCase):
    """Chaque fixture de fixtures/repos est conforme à son expected.json et son traps.md liste ses pièges."""

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
                                f"{name} : un bloc init demande un owner.md")

    def test_author_init_runs_are_conformant(self):
        """La base de régression : l'init écrit par l'auteur de la fixture satisfait le bloc init."""
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
        """Un bloc audit doit être satisfiable : l'audit écrit par l'auteur de la fixture est conforme."""
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
        audit["elements"][0]["verdict"] = "KEEP"   # CLAUDE.md jugé sain
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
                 "process_leaks": [], "guarded_rules": [{"rule": "toute chaîne passe par t()", "guarded_by": "scripts/check-i18n.mjs"}]}
        r = fixtures.check_audit(audit, exp)
        self.assertTrue(any("check-i18n" in x for x in r["sane_flagged"]), r)
        # le même script attribué à la règle qu'il vérifie vraiment n'est pas pénalisé
        audit["guarded_rules"] = [{"rule": "parité des clés fr/en", "guarded_by": "scripts/check-i18n.mjs:13"}]
        self.assertEqual(fixtures.check_audit(audit, exp)["sane_flagged"], [])

    def test_global_expectations(self):
        audit = good_audit()
        audit["audit"]["cut_the_agent_test"]["passed"] = True
        audit["audit"]["health_score"] = 85
        audit["process_leaks"] = []
        r = fixtures.check_audit(audit, self.expected)
        self.assertTrue(any("coupe l'agent" in g for g in r["global"]))
        self.assertTrue(any("score 85" in g for g in r["global"]))
        # sans fuite « injection » ni élément PUSH_DOWN sur CLAUDE.md, T2 est en mauvais verdict
        self.assertTrue(any("T2" in w for w in r["wrong"]), r)


if __name__ == "__main__":
    unittest.main()


class InitGraderTests(unittest.TestCase):
    """Le notateur d'init : faits remontés, bruit recopié, garde-fous cités ou crus à tort."""

    GOOD = """# x

Mode : **délégation**.

## Règles
- Le domaine ne dépend de rien. Pourquoi : ADR 0001. Vérifiée par : `tools/archcheck`, job `arch`.
- Toute écriture exige une clé d'idempotence. Pourquoi : incident du double débit. (non vérifiée)
- Un montant est un entier en centimes, jamais un flottant. Pourquoi : ADR 0002. (non vérifiée)
- Une migration appliquée ne se modifie plus. (non vérifiée)

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
        self.assertEqual(result["score"], "5/5")

    def test_missing_fact_is_reported(self):
        result = self.grade(self.GOOD.replace("- `make reset-db` hors base locale.", "- Rien à signaler."))
        self.assertTrue(any(p.startswith("I2 non remonté") for p in result["problems"]), result["problems"])

    def test_copied_noise_is_reported_with_its_file(self):
        result = self.grade(self.GOOD + "- Écrire du Go idiomatique ; `gofmt` avant de commiter.\n- `make e2e` avant de pousser.\n")
        text = " ".join(result["problems"])
        self.assertIn("N1 écrit à tort", text)
        self.assertIn("N2 écrit à tort", text)
        self.assertIn("AGENTS.md", text)

    def test_lying_guard_is_not_believed(self):
        lie = self.GOOD.replace("jamais un flottant. Pourquoi : ADR 0002. (non vérifiée)",
                                "jamais un flottant. Pourquoi : ADR 0002. Vérifiée par : golangci-lint, job `lint`.")
        result = self.grade(lie)
        self.assertTrue(any("garde-fou mensonger" in p for p in result["problems"]), result["problems"])

    def test_real_guard_must_be_cited(self):
        result = self.grade(self.GOOD.replace("Vérifiée par : `tools/archcheck`, job `arch`.", "Voir `tools/archcheck`. (non vérifiée)"))
        self.assertTrue(any("archcheck cité par aucune règle" in p for p in result["problems"]), result["problems"])

    def test_citing_a_contract_that_does_not_exist_is_reported(self):
        result = self.grade(self.GOOD + "\n## Tâches déléguées\n- `add-endpoint` : ajouter un endpoint.\n")
        self.assertTrue(any("référence sans cible : `add-endpoint`" in p for p in result["problems"]), result["problems"])

    def test_first_step_must_not_lay_material_of_later_levels(self):
        init = {**self.init, "only_level_material": True}
        with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(self.GOOD + "\n## Maintenance de ce fichier\n- `rule:` en review.\n\n<!-- harvest: last=2026-11-10 ref=init -->\n")
        result = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10))
        self.assertTrue(any("paliers suivants" in p for p in result["problems"]), result["problems"])

    def test_rewriting_a_healthy_file_is_zeal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as base:
            with open(os.path.join(base, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.GOOD)
            init = {**self.init, "min_similarity": [{"path": "AGENTS.md", "ratio": 0.8}]}
            with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.GOOD.replace("(non vérifiée)\n\n## Interdits", "(non vérifiée) [2026-11]\n\n## Interdits"))
            touched = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10), base=base)
            self.assertEqual(touched["problems"], [])
            rewritten = "\n".join(reversed(self.GOOD.replace("Pourquoi", "Raison").splitlines())) + "\n"
            with open(os.path.join(self.tmp.name, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write("# x\n\nMode : **délégation**.\n\n## Interdits\n- `make reset-db`.\n\n## Règles\n" + rewritten)
            zealous = fixtures.check_init(self.tmp.name, init, date(2026, 11, 10), base=base)
            self.assertTrue(any("réécrit" in p for p in zealous["problems"]), zealous["problems"])

    def test_level_below_target_is_reported(self):
        result = self.grade(self.GOOD.replace("Mode : **délégation**.", ""))
        self.assertTrue(any("L1.mode" in p for p in result["problems"]), result["problems"])

    def test_generated_file_never_reviewed_fails_on_every_noise_family(self):
        repo = os.path.join(fixtures.FIXTURES_ROOT, "ts-monorepo", "repo")
        result = fixtures.check_init(repo, load_expected("ts-monorepo")["init"], date(2026, 11, 10))
        text = " ".join(result["problems"])
        for noise in ("N1", "N2", "N3", "N4", "N5", "N6", "N7"):
            self.assertIn(f"{noise} écrit à tort", text)
        self.assertEqual(result["score"], "4/4")      # les faits y sont, noyés : le défaut est le bruit


class RemovalGraderTests(unittest.TestCase):
    """Le verdict de retrait : motif accepté, question au propriétaire pour le périmé, lignes à garder."""

    def setUp(self):
        self.expected = {k: v for k, v in load_expected("ts-monorepo")["audit"].items() if k in ("removals", "must_keep")}

    def removals(self, **override):
        base = {
            "N2": {"path": "CLAUDE.md", "line": 62, "text": "Use meaningful variable names.", "reason": "useless"},
            "N3": {"path": "CLAUDE.md", "line": 71, "text": "IMPORTANT: Think step by step before making any change.", "reason": "useless"},
            "N3b": {"path": "CLAUDE.md", "line": 74, "text": "Never apply partial edits to a file larger than 500 lines", "reason": "harmful"},
            "N4": {"path": "apps/web/CLAUDE.md", "line": 6, "text": "Pas d'optional chaining : IE11", "reason": "outdated", "ask_owner": True},
            "N5": {"path": "apps/web/CLAUDE.md", "line": 5, "text": "importe-le depuis ../../api/src/tickets/service.ts", "reason": "harmful"},
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
        self.assertTrue(any("question au propriétaire" in w for w in result["wrong"]), result)

    def test_removing_a_line_worth_keeping_is_penalised(self):
        gold = {"path": "CLAUDE.md", "line": 103, "text": "when you change anything in `packages/shared`, run npm run test:web", "reason": "useless"}
        result = fixtures.check_audit(self.removals(GOLD=gold), self.expected)
        self.assertTrue(any(f.startswith("I1") for f in result["sane_flagged"]), result)
        self.assertFalse(result["ok"])
