"""Tests du vérificateur de fixtures : la fixture java-back est conforme à son
expected.json, et le notateur d'audit distingue un bon audit d'un mauvais."""
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
        ],
        "guarded_rules": [{"rule": "no business logic in controllers", "guarded_by": "ArchitectureTest.java"}],
    }


class JavaBackFixtureTests(unittest.TestCase):
    def test_status_matches_expected(self):
        problems = fixtures.check_status(JAVA_BACK, load_expected("java-back")["status"], date(2026, 11, 9))
        self.assertEqual(problems, [])

    def test_traps_md_and_expected_agree_on_trap_ids(self):
        with open(os.path.join(JAVA_BACK, "traps.md"), encoding="utf-8") as fh:
            traps_md = fh.read()
        exp = load_expected("java-back")["audit"]
        for trap in exp["traps"] + exp["sane"]:
            self.assertIn(f"| {trap['id']} |", traps_md, trap["id"])


class AuditGraderTests(unittest.TestCase):
    def setUp(self):
        self.expected = load_expected("java-back")["audit"]

    def test_good_audit_is_conformant(self):
        r = fixtures.check_audit(good_audit(), self.expected)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["score"], "7/7")

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
