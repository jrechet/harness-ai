"""Tests de `harness status` : faits et paliers sur des dépôts temporaires."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, maturity, status  # noqa: E402

TODAY = date(2026, 11, 9)

AGENTS_LEVEL1 = """# demo — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière.

## Ce que fait ce repo
Une API de facturation.

## Règles
- Les appels HTTP passent par `src/http`. Pourquoi : retries centralisés. Vérifiée par : `eslint/no-raw-fetch`
- Pas de SQL brut dans une transaction métier. Pourquoi : incident #42. (non vérifiée)

## Interdits
- Jamais de force push.
"""

AGENTS_LEVEL2 = AGENTS_LEVEL1 + """
## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate.

<!-- harvest: last=2026-11-01 ref=https://gh/pr/9 -->
"""

AGENTS_LEVEL4 = AGENTS_LEVEL2.replace("## Interdits", """## Processus de travail
- Arrête-toi et pose la question quand la tâche touche un interdit.

## Tâches déléguées
- `bump-dependency` — monter une dépendance et prouver que rien ne casse.

## Interdits""")


def write(repo: str, rel: str, content: str) -> None:
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def harvest_json(real: int, agent_prs: int = 2, s2: int = 0) -> str:
    ev = [{"signal": "S1"} for _ in range(real)] + [{"signal": "S2"} for _ in range(s2)] + [{"signal": "S5"}]
    return json.dumps({"since": "2026-10-01", "prs_scanned": 5, "agent_prs": agent_prs, "errors": [], "evidence": ev})


def audit_json(p1: int = 0, passed: bool = True) -> str:
    elements = [{"actual_layer": "L2", "verdict": "KEEP", "priority": None},
                {"actual_layer": "L3", "verdict": "PUSH_DOWN", "priority": "P2"}]
    elements += [{"actual_layer": "L2", "verdict": "BLOCK", "priority": "P1"} for _ in range(p1)]
    return json.dumps({"audit": {"date": "2026-11-05", "health_score": 70,
                                 "cut_the_agent_test": {"passed": passed, "leaked_steps": 0 if passed else 2}},
                       "elements": elements, "process_leaks": [], "guarded_rules": [{"rule": "x"}]})


class TempRepo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def state(self):
        return maturity.evaluate(facts.collect(self.repo, today=TODAY))

    def check(self, state, cid):
        for lvl in state["levels"]:
            for c in lvl["checks"]:
                if c["id"] == cid:
                    return c
        raise KeyError(cid)


class Level0Tests(TempRepo):
    def test_empty_repo_is_level_0_with_init_as_next_action(self):
        s = self.state()
        self.assertEqual(s["level"]["reached"], 0)
        self.assertEqual(s["level"]["next"], 1)
        self.assertIn("harness-init", s["next_actions"][0])
        self.assertEqual(s["layers"]["source"], "estimate")

    def test_claude_md_monolith_counts_as_source_but_fails_short(self):
        write(self.repo, "CLAUDE.md", "# Guide\n\n" + "\n".join(f"- ligne {i}" for i in range(80)))
        s = self.state()
        self.assertEqual(s["facts"]["instructions"]["source"]["path"], "CLAUDE.md")
        self.assertTrue(self.check(s, "L1.source")["passed"])
        self.assertFalse(self.check(s, "L1.short")["passed"])


class HeadingAndToolDetectionTests(TempRepo):
    def test_git_workflow_heading_is_not_a_working_process(self):
        write(self.repo, "CLAUDE.md", "# Guide\n\n## Git Workflow\n- Use conventional commits.\n")
        self.assertFalse(self.state()["facts"]["instructions"]["source"]["has_process_section"])

    def test_working_process_headings_are_recognised(self):
        for heading in ("Processus de travail", "Working process", "Workflow"):
            write(self.repo, "AGENTS.md", f"# x\n\n## {heading}\n- Arrête-toi quand la CI est rouge.\n")
            self.assertTrue(self.state()["facts"]["instructions"]["source"]["has_process_section"], heading)

    def test_golangci_config_is_a_guardrail_marker(self):
        write(self.repo, ".golangci.yml", "linters: {}\n")
        self.assertIn("golangci-lint", self.state()["facts"]["guardrails"]["tools"])


class Level1Tests(TempRepo):
    def setUp(self):
        super().setUp()
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, "CLAUDE.md", "@AGENTS.md\n")

    def test_level_1_reached(self):
        s = self.state()
        self.assertEqual(s["level"]["reached"], 1)
        self.assertTrue(all(c["passed"] for c in s["levels"][1]["checks"]))
        self.assertEqual(s["facts"]["instructions"]["files"]["CLAUDE.md"]["is_stub"], True)
        self.assertEqual(s["facts"]["instructions"]["source"]["mode"], "delegation")

    def test_rule_metrics(self):
        src = facts.collect(self.repo, today=TODAY)["instructions"]["source"]
        self.assertEqual(src["rules_total"], 3)          # 2 règles + 1 interdit (puce)
        self.assertEqual(src["rules_guarded"], 1)
        self.assertEqual(src["rules_unguarded_marked"], 1)
        self.assertEqual(src["rules_justified"], 2)

    def test_non_stub_claude_md_blocks_single_source(self):
        write(self.repo, "CLAUDE.md", "# Build\n- ./gradlew test\n- ./gradlew run\n- ./gradlew assemble\n")
        s = self.state()
        self.assertFalse(self.check(s, "L1.single_source")["passed"])
        self.assertEqual(s["level"]["reached"], 0)

    def test_includes_are_resolved_in_loaded_lines(self):
        write(self.repo, "CLAUDE.md", "@AGENTS.md\n")
        f = facts.collect(self.repo, today=TODAY)
        self.assertGreater(f["instructions"]["files"]["CLAUDE.md"]["loaded_lines"], 5)


class Level2Tests(TempRepo):
    def setUp(self):
        super().setUp()
        write(self.repo, "AGENTS.md", AGENTS_LEVEL2)

    def test_marker_and_signal_required(self):
        s = self.state()
        self.assertEqual(s["level"]["reached"], 1)
        self.assertTrue(self.check(s, "L2.marker_fresh")["passed"])
        self.assertEqual(self.check(s, "L2.marker_fresh")["value"], 8)
        self.assertFalse(self.check(s, "L2.signal")["passed"])
        write(self.repo, ".harness/harvest.json", harvest_json(real=1))
        self.assertEqual(self.state()["level"]["reached"], 2)

    def test_orphan_rules_alone_do_not_count_as_signal(self):
        write(self.repo, ".harness/harvest.json", harvest_json(real=0))
        self.assertFalse(self.check(self.state(), "L2.signal")["passed"])

    def test_stale_marker_fails(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL2.replace("last=2026-11-01", "last=2026-08-01"))
        self.assertFalse(self.check(self.state(), "L2.marker_fresh")["passed"])


class Level3And4Tests(TempRepo):
    def setUp(self):
        super().setUp()
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4)
        write(self.repo, ".harness/harvest.json", harvest_json(real=1))
        write(self.repo, ".github/workflows/ci.yml", "name: ci\n")
        write(self.repo, ".claude/skills/bump-dependency/SKILL.md", "---\nname: bump-dependency\n---\n")

    def test_level_3_needs_guarded_ratio_and_clean_audit(self):
        s = self.state()
        self.assertEqual(s["level"]["reached"], 2)
        self.assertFalse(self.check(s, "L3.guarded")["passed"])     # 1 règle sur 4 puces
        self.assertFalse(self.check(s, "L3.audit")["passed"])
        self.assertTrue(self.check(s, "L3.ci")["passed"])

    def test_level_4_reached_when_everything_measured(self):
        guarded = AGENTS_LEVEL4.replace("(non vérifiée)", "Vérifiée par : `archunit/NoRawSql`") \
            .replace("- Jamais de force push.", "- Jamais de force push. Pourquoi : incident #7. Vérifiée par : branch protection") \
            .replace("- `bump-dependency` — monter", "- `bump-dependency` — Vérifiée par : CI. Pourquoi : #3. monter")
        write(self.repo, "AGENTS.md", guarded)
        write(self.repo, ".harness/audit.json", audit_json(p1=0, passed=True))
        s = self.state()
        self.assertEqual(s["level"]["reached"], 4, [c for l in s["levels"] for c in l["checks"] if not c["passed"]])
        self.assertEqual(s["layers"]["source"], "audit")
        self.assertEqual(s["layers"]["layers"]["L3"]["misplaced"], 1)
        self.assertEqual(s["next_actions"], [])

    def test_p1_in_audit_blocks_level_3(self):
        write(self.repo, ".harness/audit.json", audit_json(p1=1))
        self.assertFalse(self.check(self.state(), "L3.audit")["passed"])

    def test_s2_corrections_block_level_4(self):
        write(self.repo, ".harness/harvest.json", harvest_json(real=1, s2=1))
        self.assertFalse(self.check(self.state(), "L4.clean_prs")["passed"])

    def test_contract_must_be_referenced(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4.replace("`bump-dependency`", "`autre-chose`"))
        s = self.state()
        self.assertEqual(s["facts"]["contracts"]["count"], 1)
        self.assertFalse(self.check(s, "L4.contracts")["passed"])


class CliTests(TempRepo):
    def test_writes_state_json_and_renders_markdown(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        out = io.StringIO()
        with redirect_stdout(out):
            code = status.main([self.repo, "--today", "2026-11-09"])
        self.assertEqual(code, 0)
        self.assertIn("Palier atteint", out.getvalue())
        with open(os.path.join(self.repo, ".harness", "state.json"), encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["schema"], "harness-state/1")
        self.assertEqual(state["level"]["reached"], 1)

    def test_json_format_and_no_write(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status.main([self.repo, "--format", "json", "--no-write", "--today", "2026-11-09"])
        self.assertEqual(json.loads(out.getvalue())["level"]["reached"], 0)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))


if __name__ == "__main__":
    unittest.main()
