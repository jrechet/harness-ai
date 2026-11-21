"""Tests of `harness status`: facts and levels on temporary repositories."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, maturity, rules, status  # noqa: E402

TODAY = date(2026, 11, 9)

AGENTS_LEVEL1 = """# demo — instructions for agents

Mode: **delegation**. An agent can receive a whole task.

## What this repo does
A billing API.

## Rules
- HTTP calls go through `src/http`. Why: centralised retries. Enforced by: `eslint/no-raw-fetch`
- No raw SQL in a business transaction. Why: incident #42. (unverified)

## Forbidden
- Never force push.
"""

AGENTS_LEVEL2 = AGENTS_LEVEL1 + """
## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule.

<!-- harvest: last=2026-11-01 ref=https://gh/pr/9 -->
"""

AGENTS_LEVEL4 = AGENTS_LEVEL2.replace("## Forbidden", """## Working process
- Stop and ask when the task touches a forbidden item.

## Delegated tasks
- `bump-dependency` — bump a dependency and prove nothing breaks.

## Forbidden""")

# The same files written by a French-speaking team: they must reach the same levels.
AGENTS_LEVEL1_FR = """# demo — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière.

## Ce que fait ce repo
Une API de facturation.

## Règles
- Les appels HTTP passent par `src/http`. Pourquoi : retries centralisés. Vérifiée par : `eslint/no-raw-fetch`
- Pas de SQL brut dans une transaction métier. Pourquoi : incident #42. (non vérifiée)

## Interdits
- Jamais de force push.
"""

AGENTS_LEVEL2_FR = AGENTS_LEVEL1_FR + """
## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate.

<!-- harvest: last=2026-11-01 ref=https://gh/pr/9 -->
"""

AGENTS_LEVEL4_FR = AGENTS_LEVEL2_FR.replace("## Interdits", """## Processus de travail
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


class TargetLevelTests(TempRepo):
    """A level is a place where one can stay: beyond the target level, status does not push."""

    def test_without_target_the_next_level_is_proposed(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        s = self.state()
        self.assertEqual(s["target"], {"level": None, "name": None, "reached": False})
        self.assertTrue(s["next_actions"])
        self.assertIn("no target level", maturity.render_markdown(s))

    def test_target_reached_proposes_nothing_and_says_so(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 1}))
        s = self.state()
        self.assertEqual(s["level"]["reached"], 1)
        self.assertTrue(s["target"]["reached"])
        self.assertEqual(s["next_actions"], [])
        md = maturity.render_markdown(s)
        self.assertIn("target reached", md)
        self.assertIn("Level 2 — Looped (beyond target)", md)
        self.assertNotIn("A maintenance section", md)

    def test_target_above_current_level_keeps_pushing_up_to_it_only(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 2}))
        s = self.state()
        self.assertFalse(s["target"]["reached"])
        self.assertTrue(s["next_actions"])
        self.assertEqual([l["in_scope"] for l in s["levels"]], [True, True, True, False, False])

    def test_a_level_that_only_waits_for_time_does_not_hold_back_the_next_one(self):
        # 2026-11-14: target 3, level 2 set up without a review signal; the step stopped, no guardrail set up
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1 + "\n## Maintaining this file\n"
              "- A review comment that starts with `rule:` is a candidate rule.\n"
              f"<!-- harvest: last={TODAY.isoformat()} ref=init -->\n")
        write(self.repo, ".github/workflows/ci.yml", "on: push\njobs:\n  test:\n    runs-on: x\n    steps:\n      - run: make test\n")
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 3}))
        s = self.state()
        self.assertEqual(s["level"]["reached"], 1)            # the level stays honest
        self.assertEqual(s["waiting"], ["L2.signal"])
        self.assertTrue(s["next_actions"])
        self.assertTrue(all("harvest" not in a.lower() and "rule:" not in a for a in s["next_actions"]), s["next_actions"])
        self.assertTrue(self.check(s, "L2.signal")["waits"])
        md = maturity.render_markdown(s)
        self.assertIn("## Waiting", md)
        self.assertIn("**waiting**", md)

    def test_waiting_stops_at_the_target(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1 + "\n## Maintaining this file\n"
              "- A review comment that starts with `rule:` is a candidate rule.\n"
              f"<!-- harvest: last={TODAY.isoformat()} ref=init -->\n")
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 2}))
        s = self.state()
        self.assertEqual(s["waiting"], ["L2.signal"])
        self.assertEqual(s["next_actions"], [])

    def test_invalid_target_is_ignored(self):
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 9}))
        self.assertIsNone(self.state()["target"]["level"])

    def test_target_command_writes_config_and_keeps_other_keys(self):
        write(self.repo, ".harness/config.json", json.dumps({"schema": "harness-config/1", "note": "x"}))
        from harness import main as harness_main
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(harness_main(["target", "3", self.repo]), 0)
        with open(os.path.join(self.repo, ".harness/config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertEqual(config, {"schema": "harness-config/1", "note": "x", "target_level": 3})
        self.assertIn("Verified", out.getvalue())


class AuditRemovalFactsTests(TempRepo):
    def test_removals_of_the_last_audit_are_counted_by_reason(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        audit = json.loads(audit_json())
        audit["removals"] = [{"reason": "useless"}, {"reason": "useless"}, {"reason": "harmful"}, {"reason": "outdated", "ask_owner": True}]
        write(self.repo, ".harness/audit.json", json.dumps(audit))
        self.assertEqual(self.state()["facts"]["audit"]["removals"], {"useless": 2, "harmful": 1, "outdated": 1})


class DanglingReferenceTests(TempRepo):
    """What is set up stays consistent: a cited contract or guardrail must exist."""

    def test_contract_cited_without_skill_is_dangling(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4)
        self.assertEqual([(d["kind"], d["ref"]) for d in self.state()["dangling"]], [("contract", "bump-dependency")])
        write(self.repo, ".claude/skills/bump-dependency/SKILL.md", "# x\n")
        self.assertEqual(self.state()["dangling"], [])

    def test_guard_path_that_does_not_exist_is_dangling(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1.replace("`eslint/no-raw-fetch`", "`tools/check.mjs`, job `lint`"))
        self.assertEqual([(d["kind"], d["ref"]) for d in self.state()["dangling"]], [("guard", "tools/check.mjs")])
        write(self.repo, "tools/check.mjs", "")
        self.assertEqual(self.state()["dangling"], [])

    def test_linter_rule_name_and_job_name_are_not_paths(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)          # `eslint/no-raw-fetch`: no eslint/ folder
        self.assertEqual(self.state()["dangling"], [])

    def test_ci_job_cited_but_gone_from_the_workflows_is_dangling(self):
        rule = "- An applied migration is never modified. Enforced by: the CI job `frozen-migrations`."
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1 + rule + "\n")
        self.assertEqual(self.state()["dangling"], [])          # no workflow: nothing to confront
        write(self.repo, ".github/workflows/ci.yml", "name: CI\non: push\njobs:\n  test:\n    runs-on: x\n    steps: []\n")
        self.assertEqual([(d["kind"], d["ref"]) for d in self.state()["dangling"]], [("job", "frozen-migrations")])
        self.assertIn("absent from the workflows", maturity.render_markdown(self.state()))
        write(self.repo, ".github/workflows/ci.yml", "jobs:\n    test:\n        steps: []\n    frozen-migrations:\n        steps: []\n")
        self.assertEqual(self.state()["dangling"], [])

    def test_file_cited_by_basename_is_found_anywhere(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1.replace("`eslint/no-raw-fetch`", "`ci.yml`"))
        self.assertEqual(len(self.state()["dangling"]), 1)
        write(self.repo, ".github/workflows/ci.yml", "on: push\n")
        self.assertEqual(self.state()["dangling"], [])


class RuleDateTests(TempRepo):
    DATED = AGENTS_LEVEL1.replace("(unverified)", "(unverified) [2026-03]")

    def test_dated_rules_are_counted(self):
        write(self.repo, "AGENTS.md", self.DATED)
        src = self.state()["facts"]["instructions"]["source"]
        self.assertEqual((src["rules_total"], src["rules_dated"], src["oldest_rule_date"]), (3, 1, "2026-03"))

    def test_rules_command_reads_the_date_from_the_rule(self):
        write(self.repo, "AGENTS.md", self.DATED)
        rows = rules.collect(self.repo, TODAY)
        dated = [r for r in rows if r["since_source"] == "rule"]
        self.assertEqual(len(dated), 1)
        self.assertEqual((dated[0]["since"], dated[0]["age_days"], dated[0]["marked_unguarded"], dated[0]["justified"]),
                         ("2026-03", 253, True, True))
        self.assertTrue(any(r["guarded"] for r in rows))

    def test_rules_command_falls_back_on_git_blame(self):
        import subprocess
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        env = {**os.environ, "GIT_AUTHOR_NAME": "o", "GIT_AUTHOR_EMAIL": "o@example.test", "GIT_COMMITTER_NAME": "o",
               "GIT_COMMITTER_EMAIL": "o@example.test", "GIT_AUTHOR_DATE": "2025-01-15T10:00:00Z",
               "GIT_COMMITTER_DATE": "2025-01-15T10:00:00Z"}
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", self.repo, *cmd], check=True, env=env, capture_output=True)
        rows = rules.collect(self.repo, TODAY)
        self.assertTrue(rows)
        self.assertTrue(all(r["since"] == "2025-01-15" and r["since_source"] == "git" for r in rows))
        self.assertIn("(git)", rules.render_markdown(rows))

    def test_instruction_files_inside_test_data_are_not_the_repository_s_rules(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, "fixtures/repos/demo/repo/CLAUDE.md", "# x\n- Think step by step.\n")
        self.assertEqual({r["file"] for r in rules.collect(self.repo, TODAY, blame=False)}, {"AGENTS.md"})

    def test_rules_of_subdirectory_files_are_listed_with_their_path(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, "apps/web/CLAUDE.md", "# Web\n- Everything goes through `escapeHtml`. Why: pentest. [2026-03]\n")
        files = {r["file"] for r in rules.collect(self.repo, TODAY, blame=False)}
        self.assertEqual(files, {"AGENTS.md", "apps/web/CLAUDE.md"})


class HeadingAndToolDetectionTests(TempRepo):
    def test_git_workflow_heading_is_not_a_working_process(self):
        write(self.repo, "CLAUDE.md", "# Guide\n\n## Git Workflow\n- Use conventional commits.\n")
        self.assertFalse(self.state()["facts"]["instructions"]["source"]["has_process_section"])

    def test_working_process_headings_are_recognised(self):
        for heading in ("Processus de travail", "Working process", "Workflow"):
            write(self.repo, "AGENTS.md", f"# x\n\n## {heading}\n- Stop when the CI is red.\n")
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
        self.assertEqual(src["rules_total"], 3)          # 2 rules + 1 forbidden item (bullet)
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
        self.assertFalse(self.check(s, "L3.guarded")["passed"])     # 1 rule out of 4 bullets
        self.assertFalse(self.check(s, "L3.audit")["passed"])
        self.assertTrue(self.check(s, "L3.ci")["passed"])

    def test_level_4_reached_when_everything_measured(self):
        guarded = AGENTS_LEVEL4.replace("(unverified)", "Enforced by: `archunit/NoRawSql`") \
            .replace("- Never force push.", "- Never force push. Why: incident #7. Enforced by: branch protection") \
            .replace("- `bump-dependency` — bump", "- `bump-dependency` — Enforced by: CI. Why: #3. bump")
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
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4.replace("`bump-dependency`", "`something-else`"))
        s = self.state()
        self.assertEqual(s["facts"]["contracts"]["count"], 1)
        self.assertFalse(self.check(s, "L4.contracts")["passed"])


class BilingualTests(TempRepo):
    """An AGENTS.md is written by a team, in French or in English: the same file in either language
    reaches the same level, with the same facts."""

    GUARDED_EN = AGENTS_LEVEL4.replace("(unverified)", "Enforced by: `archunit/NoRawSql`") \
        .replace("- Never force push.", "- Never force push. Why: incident #7. Enforced by: branch protection")
    GUARDED_FR = AGENTS_LEVEL4_FR.replace("(non vérifiée)", "Vérifiée par : `archunit/NoRawSql`") \
        .replace("- Jamais de force push.", "- Jamais de force push. Pourquoi : incident #7. Vérifiée par : branch protection")
    PAIRS = {"level 1": (AGENTS_LEVEL1, AGENTS_LEVEL1_FR), "level 2": (AGENTS_LEVEL2, AGENTS_LEVEL2_FR),
             "level 4": (AGENTS_LEVEL4, AGENTS_LEVEL4_FR), "level 4 guarded": (GUARDED_EN, GUARDED_FR)}
    SOURCE_FACTS = ("mode", "rules_total", "rules_guarded", "rules_unguarded_marked", "rules_justified",
                    "has_maintenance_section", "has_process_section", "has_forbidden_section",
                    "mentions_rule_convention", "harvest_marker")

    def measure(self, text: str) -> tuple:
        write(self.repo, "AGENTS.md", text)
        s = self.state()
        src = s["facts"]["instructions"]["source"]
        checks = {c["id"]: c["passed"] for l in s["levels"] for c in l["checks"]}
        rules_rows = [(r["guarded"], r["marked_unguarded"], r["justified"]) for r in rules.collect(self.repo, TODAY, blame=False)]
        return (s["level"]["reached"], checks, {k: src[k] for k in self.SOURCE_FACTS},
                [(d["kind"], d["ref"]) for d in s["dangling"]], rules_rows)

    def test_the_same_file_in_english_and_in_french_reaches_the_same_level(self):
        write(self.repo, ".harness/harvest.json", harvest_json(real=1))
        write(self.repo, ".harness/audit.json", audit_json(p1=0, passed=True))
        write(self.repo, ".github/workflows/ci.yml", "name: ci\n")
        write(self.repo, ".claude/skills/bump-dependency/SKILL.md", "---\nname: bump-dependency\n---\n")
        expected = {"level 1": 1, "level 2": 2, "level 4": 2, "level 4 guarded": 4}
        for name, (english, french) in self.PAIRS.items():
            with self.subTest(name):
                en, fr = self.measure(english), self.measure(french)
                self.assertEqual(en, fr)
                self.assertEqual(en[0], expected[name])

    def test_english_markers_are_read(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4)
        src = self.state()["facts"]["instructions"]["source"]
        self.assertEqual(src["mode"], "delegation")
        self.assertTrue(src["has_maintenance_section"])
        self.assertTrue(src["has_process_section"])
        self.assertTrue(src["has_forbidden_section"])
        self.assertEqual((src["rules_total"], src["rules_guarded"], src["rules_unguarded_marked"], src["rules_justified"]),
                         (3, 1, 1, 2))
        self.assertEqual([(d["kind"], d["ref"]) for d in self.state()["dangling"]], [("contract", "bump-dependency")])

    def test_assistance_mode_is_read_in_both_languages(self):
        for line in ("Mode: assistance.", "Mode : **assistance**.", "- Mode: **Assistance**"):
            with self.subTest(line):
                write(self.repo, "AGENTS.md", f"# x\n\n{line}\n")
                self.assertEqual(self.state()["facts"]["instructions"]["source"]["mode"], "assistance")

    def test_maintaining_and_delegated_sections_are_not_rules(self):
        write(self.repo, "AGENTS.md", "# x\n\n## Maintaining this file\n- A comment `rule:` is a candidate.\n\n"
                                      "## Delegated tasks\n- `bump` — bump a dependency.\n")
        self.assertEqual(self.state()["facts"]["instructions"]["source"]["rules_total"], 0)


class NoSourceTests(TempRepo):
    """No instruction file at all: one thing is missing, the file. What the file would carry is not
    reported as failed for a reason that is not true."""
    WITH_FILE = {"L1.mode", "L1.short", "L1.single_source", "L1.forbidden"}

    def test_only_the_file_is_missing_and_the_four_others_come_with_it(self):
        s = self.state()
        level1 = s["levels"][1]
        self.assertEqual((s["level"]["reached"], level1["achieved"], level1["passed_checks"], level1["total_checks"]),
                         (0, False, 0, 5))                              # the level computed does not move
        self.assertIsNone(self.check(s, "L1.source").get("follows"))
        self.assertIn("harness-init", self.check(s, "L1.source")["next_action"])
        for cid in self.WITH_FILE:
            with self.subTest(check=cid):
                c = self.check(s, cid)
                self.assertEqual((c["passed"], c["follows"], c["next_action"]), (False, "L1.source", None))

    def test_there_is_one_next_action_and_it_is_the_file(self):
        s = self.state()
        self.assertEqual(len(s["next_actions"]), 1)
        self.assertIn("harness-init", s["next_actions"][0])

    def test_status_says_comes_with_the_file_and_no_false_reason(self):
        md = maturity.render_markdown(self.state())
        self.assertIn("- [ ] An instruction file exists (AGENTS.md) → Run harness-init", md)
        self.assertIn("- [ ] CLAUDE.md is an @AGENTS.md stub (or absent) → comes with the instruction file", md)
        self.assertEqual(md.count("→ comes with the instruction file"), 4)
        for false_reason in ("Reduce CLAUDE.md", "Move the reference material", "Add the mode line", "Add the Forbidden section"):
            self.assertNotIn(false_reason, md)
        actions = md.split("## Next actions\n")[1].strip().splitlines()
        self.assertEqual(len(actions), 1, actions)

    def test_the_map_lists_one_missing_thing(self):
        m = maturity.render_map(self.state())
        needs = m.split("What level 1 still needs:\n")[1].split("Next step:")[0].strip().splitlines()
        self.assertEqual(needs, ["- there is no instruction file (AGENTS.md) for the agent"])
        self.assertNotIn("longer than", m)
        self.assertNotIn("CLAUDE.md carries", m)
        self.assertIn("Next step: write a short AGENTS.md", m)

    def test_a_real_project_without_instruction_file_reads_the_same(self):
        fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fixtures", "repos", "go-hexa", "repo")
        shutil.copytree(fixture, self.repo, dirs_exist_ok=True)
        s = self.state()
        self.assertIsNone(s["facts"]["instructions"]["source"].get("path"))
        self.assertEqual(len(s["next_actions"]), 1)
        self.assertEqual(maturity.render_map(s).count("\n- "), 1)

    def test_with_a_file_each_failed_check_keeps_its_own_reason(self):
        write(self.repo, "AGENTS.md", "# x\n\n" + "\n".join(f"- line {i}" for i in range(80)))
        s = self.state()
        for cid in ("L1.mode", "L1.short", "L1.forbidden"):
            with self.subTest(check=cid):
                c = self.check(s, cid)
                self.assertFalse(c["passed"])
                self.assertIsNone(c.get("follows"))
                self.assertTrue(c["next_action"])
        self.assertIn("longer than", maturity.render_map(s))
        self.assertEqual(len(s["next_actions"]), 3)


class MapTests(TempRepo):
    """`status --map`: the few plain lines the skills show before doing or asking anything."""

    def test_every_check_and_level_has_plain_words(self):
        s = self.state()
        ids = {c["id"] for l in s["levels"] for c in l["checks"]}
        self.assertEqual(ids, set(maturity.CHECK_PLAIN))
        self.assertEqual(set(maturity.LEVEL_PLAIN), {num for num, _, _ in maturity.LEVELS})

    def test_empty_repo_is_here_at_level_0_and_the_step_is_the_instruction_file(self):
        m = maturity.render_map(self.state())
        self.assertRegex(m, r"0 None .*← you are here")
        self.assertIn("Target: none chosen yet", m)
        self.assertIn("What level 1 still needs:", m)
        self.assertIn("Next step: write a short AGENTS.md", m)

    def test_no_check_id_or_signal_code_reaches_the_user(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        m = maturity.render_map(self.state())
        self.assertNotRegex(m, r"\bL\d\.|\bS\d\b|harvest|guardrail")
        self.assertRegex(m, r"✓ 1 Framed .*← you are here")
        self.assertIn("review remarks become rules", m)

    def test_target_reached_offers_the_next_level_as_a_choice(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 1}))
        m = maturity.render_map(self.state())
        self.assertIn("Target: level 1, Framed — reached.", m)
        self.assertIn("level 2 (Looped) would bring this", m)
        self.assertIn("(beyond your target)", m)
        self.assertNotIn("still needs", m)

    def test_a_level_held_above_the_target_offers_the_level_above_it(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 1}))
        state = self.state()
        levels = [{**l, "achieved": l["level"] <= 3} for l in state["levels"]]
        m = maturity.render_map({**state, "levels": levels, "level": {**state["level"], "reached": 3}})
        self.assertIn("level 4 (Delegated) would bring this", m)
        self.assertNotIn("level 2 (Looped) would bring this", m)
        self.assertNotIn("✓ 2 Looped", m.split("(beyond your target)")[0].splitlines()[-1])

    def test_every_level_reached_without_a_target_says_so(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        state = self.state()
        levels = [{**l, "achieved": True} for l in state["levels"]]
        m = maturity.render_map({**state, "levels": levels, "level": {**state["level"], "reached": 4}, "dangling": []})
        self.assertIn("every level is reached", m)

    def test_a_waiting_level_says_time_and_the_step_goes_to_the_level_above(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL2)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 3}))
        m = maturity.render_map(self.state())
        self.assertIn("(comes with time, not with work)", m)
        self.assertIn("(towards level 3)", m)

    def test_broken_references_come_first(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL4)
        m = maturity.render_map(self.state())
        self.assertIn("Broken references", m)
        self.assertIn("Next step: fix or remove", m)

    def test_map_flag_prints_only_the_map_and_still_writes_the_state(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(status.main([self.repo, "--map", "--today", "2026-11-09"]), 0)
        self.assertTrue(out.getvalue().startswith("Where this repository stands"))
        self.assertNotIn("Level reached", out.getvalue())
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".harness", "state.json")))


class CliTests(TempRepo):
    def test_writes_state_json_and_renders_markdown(self):
        write(self.repo, "AGENTS.md", AGENTS_LEVEL1)
        out = io.StringIO()
        with redirect_stdout(out):
            code = status.main([self.repo, "--today", "2026-11-09"])
        self.assertEqual(code, 0)
        self.assertIn("Level reached", out.getvalue())
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
