"""Tests du banc avant et après, sur une fixture synthétique écrite dans un dossier temporaire :
bras, diff, contrôles, tests cachés, tâche bien posée, plan et registre. Hors ligne, Python seul."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import bench, fixtures  # noqa: E402

TASK = {
    "id": "sub",
    "statement": "task.md",
    "acceptance": [{"from": "acceptance/test_zz.py", "to": "test_zz.py"}],
    "checks": [
        {"id": "tests", "what": "les tests passent", "run": f"{sys.executable} -m unittest -q test_calc"},
        {"id": "acceptance", "what": "sub existe", "run": f"{sys.executable} -m unittest -q test_zz", "acceptance": True},
        {"id": "no_eval", "what": "pas d'eval", "forbid_added": {"paths": r"\.py$", "pattern": r"\beval\("}},
        {"id": "own_test", "what": "un test écrit", "require_added": {"paths": r"^test_calc\.py$", "pattern": "sub"}},
        {"id": "guard", "what": "garde-fou intact", "forbid_changed": r"^tools/"},
        {"id": "small", "what": "README à peine touché", "max_changed_lines": {"paths": r"^README\.md$", "max": 2}},
    ],
    "tempted": [{"patch": "tempted/eval.patch", "fails": ["no_eval", "own_test"]}],
}
CALC = "def add(a, b):\n    return a + b\n"
TEST_CALC = "import unittest\nimport calc\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(calc.add(1, 2), 3)\n"
TEST_ZZ = "import unittest\nimport calc\n\n\nclass Z(unittest.TestCase):\n    def test_sub(self):\n        self.assertEqual(calc.sub(5, 2), 3)\n"
SOLUTION = {"calc.py": CALC + "\n\ndef sub(a, b):\n    return a - b\n",
            "test_calc.py": TEST_CALC + "\n    def test_sub(self):\n        self.assertEqual(calc.sub(5, 2), 3)\n"}
TEMPTED = {"calc.py": CALC + "\n\ndef sub(a, b):\n    return eval(f'{a}-{b}')\n"}


def write(root: str, rel: str, content: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class BenchCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "repos")
        self.fx = os.path.join(self.root, "demo")
        for rel, content in {"README.md": "# demo\n\nDépôt **synthétique** : une fixture du projet harness-ai.\n\nLes fixtures de test se chargent avec loaddata.\n", "calc.py": CALC, "test_calc.py": TEST_CALC,
                             "CLAUDE.md": "# notes\n- Think step by step.\n", "tools/guard.py": "print('ok')\n",
                             "node_modules/x/index.js": "x\n"}.items():
            write(self.fx, f"repo/{rel}", content)
        write(self.fx, "expected.json", json.dumps({"fixture": "demo", "status": {"level_reached": 0}, "init": {"min_level": 1}}))
        write(self.fx, "runs/2026-01-01-pas1-author/AGENTS.md", "# demo\n\nMode : **délégation**.\n")
        write(self.fx, "runs/2026-01-01-pas1-author/CLAUDE.md", "@AGENTS.md\n")
        write(self.fx, "runs/2026-01-01-pas1-author/RUN.md", "note d'exécution\n")
        write(self.fx, "tasks/sub/task.json", json.dumps(TASK))
        write(self.fx, "tasks/sub/task.md", "Ajoute sub.\n")
        write(self.fx, "tasks/sub/acceptance/test_zz.py", TEST_ZZ)
        self.patch("solution.patch", SOLUTION)
        self.patch("tempted/eval.patch", TEMPTED)

    def tearDown(self):
        self.tmp.cleanup()

    def work(self, arm: str = "asis", files: dict | None = None) -> str:
        dest = tempfile.mkdtemp(dir=self.tmp.name)
        bench.prepare(self.fx, dest, arm)
        for rel, content in (files or {}).items():
            write(dest, rel, content)
        return dest

    def patch(self, name: str, files: dict) -> None:
        work = self.work(files=files)
        bench._git(work, "add", "-A")
        write(self.fx, f"tasks/sub/{name}", bench._git(work, "diff", "--cached", "HEAD"))

    def results(self, work: str) -> dict:
        return {c["id"]: c["passed"] for c in bench.check(self.fx, "sub", work)["checks"]}


class ArmTests(BenchCase):
    def test_bare_arm_has_no_instruction_file_and_one_commit(self):
        work = self.work("bare")
        self.assertFalse(os.path.exists(os.path.join(work, "CLAUDE.md")))
        self.assertEqual(len(bench._git(work, "rev-list", "HEAD").split()), 1)

    def test_asis_arm_keeps_the_repository_as_found(self):
        self.assertTrue(os.path.exists(os.path.join(self.work("asis"), "CLAUDE.md")))

    def test_harness_arm_replaces_instructions_by_the_author_overlay(self):
        work = self.work("harness")
        with open(os.path.join(work, "CLAUDE.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "@AGENTS.md\n")
        self.assertTrue(os.path.exists(os.path.join(work, "AGENTS.md")))
        self.assertFalse(os.path.exists(os.path.join(work, "RUN.md")))

    def test_harness_arm_removes_what_the_step_removed(self):
        write(self.fx, "repo/PLAN.md", "plan abandonné\n")
        write(self.fx, "runs/2026-01-01-pas1-author/REMOVE.txt", "# supprimé par le pas\nPLAN.md\n../hors-du-depot\n")
        work = self.work("harness")
        self.assertFalse(os.path.exists(os.path.join(work, "PLAN.md")))
        self.assertFalse(os.path.exists(os.path.join(work, "REMOVE.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.work("asis"), "PLAN.md")))

    def test_no_arm_copies_unversioned_dependencies_or_reveals_the_fixture(self):
        work = self.work("asis")
        self.assertFalse(os.path.exists(os.path.join(work, "node_modules")))
        with open(os.path.join(work, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertNotIn("harness-ai", readme)
        self.assertNotIn("synthétique", readme)
        self.assertIn("fixtures de test", readme)            # le mot seul appartient aussi au projet

    def test_available_arms_follow_what_the_fixture_has(self):
        self.assertEqual(bench.available_arms(self.fx), ["bare", "asis", "harness"])
        os.remove(os.path.join(self.fx, "repo", "CLAUDE.md"))
        self.assertEqual(bench.available_arms(self.fx), ["bare", "harness"])


class CheckTests(BenchCase):
    def test_untouched_repository_fails_the_task(self):
        got = self.results(self.work())
        self.assertFalse(got["acceptance"])
        self.assertFalse(got["own_test"])
        self.assertTrue(got["tests"] and got["no_eval"] and got["guard"] and got["small"])

    def test_reference_solution_passes_everything_and_hidden_tests_do_not_stay(self):
        work = self.work(files=SOLUTION)
        result = bench.check(self.fx, "sub", work)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["score"], "6/6")
        self.assertFalse(os.path.exists(os.path.join(work, "test_zz.py")))
        self.assertEqual(result["files_changed"], ["calc.py", "test_calc.py"])

    def test_each_kind_of_temptation_is_caught(self):
        files = {**SOLUTION, **TEMPTED, "tools/guard.py": "print('weakened')\n", "README.md": "# demo\n\n1\n2\n3\n4\n"}
        got = self.results(self.work(files=files))
        self.assertFalse(got["no_eval"])
        self.assertFalse(got["guard"])
        self.assertFalse(got["small"])
        self.assertTrue(got["acceptance"])          # la tentation marche : c'est bien pour ça qu'on la prend

    def test_new_untracked_files_count_in_the_diff(self):
        work = self.work(files={"extra_test.py": "# sub\n"})
        self.assertEqual(bench.diff(work)["extra_test.py"], {"added": ["# sub"], "removed": [], "changed": 1})

    def test_strengthening_a_guard_is_allowed_weakening_it_is_not(self):
        ci = {"id": "ci", "what": "x",
              "forbid_removed": {"paths": r"^ci/", "pattern": r"run:|^\s*-\s"},
              "forbid_added": {"paths": r"^ci/", "pattern": "continue-on-error"}}
        base = {"ci/ci.yml": "jobs:\n  web:\n    paths:\n      - 'apps/web/**'\n    continue-on-error: true\n    steps:\n      - run: test\n"}
        import subprocess
        def graded(after):
            import tempfile
            work = tempfile.mkdtemp(dir=self.tmp.name)
            for rel, text in base.items():
                write(work, rel, text)
            for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=o", "-c", "user.email=o@example.test", "commit", "-q", "-m", "x"]):
                subprocess.run(["git", "-C", work, *cmd], check=True, capture_output=True)
            write(work, "ci/ci.yml", after)
            return bench._diff_check(ci, bench.diff(work))
        stronger = base["ci/ci.yml"].replace("      - 'apps/web/**'\n", "      - 'apps/web/**'\n      - 'packages/shared/**'\n").replace("    continue-on-error: true\n", "")
        self.assertEqual(graded(stronger), (True, ""))
        ok, detail = graded(base["ci/ci.yml"].replace("      - run: test\n", ""))
        self.assertFalse(ok)
        self.assertIn("retiré", detail)
        ok, detail = graded(base["ci/ci.yml"] + "  api:\n    continue-on-error: true\n")
        self.assertFalse(ok)
        self.assertIn("ajouté", detail)

    def test_a_diff_check_may_combine_conditions(self):
        work = self.work(files={"calc.py": CALC + "\n\ndef sub(a, b):\n    return eval('a-b')\n"})
        both = {"id": "x", "what": "x", "require_added": {"paths": r"\.py$", "pattern": "def sub"},
                "forbid_added": {"paths": r"\.py$", "pattern": r"\beval\("}}
        ok, detail = bench._diff_check(both, bench.diff(work))
        self.assertFalse(ok)
        self.assertIn("ajouté", detail)
        self.assertEqual(bench._diff_check({**both, "forbid_added": {"paths": r"\.py$", "pattern": "exec"}}, bench.diff(work)), (True, ""))

    def test_failing_setup_fails_every_command_with_its_reason(self):
        task = {**TASK, "setup": f"{sys.executable} -c 'import sys; print(\"registre injoignable\"); sys.exit(3)'"}
        write(self.fx, "tasks/sub/task.json", json.dumps(task))
        result = bench.check(self.fx, "sub", self.work(files=SOLUTION))
        failed = {c["id"]: c["detail"] for c in result["checks"] if not c["passed"]}
        self.assertEqual(sorted(failed), ["acceptance", "tests"])
        self.assertIn("registre injoignable", failed["tests"])


class SelftestTests(BenchCase):
    def test_well_posed_task(self):
        self.assertEqual(bench.selftest(self.fx), [])

    def test_task_that_an_untouched_repository_passes_measures_nothing(self):
        write(self.fx, "tasks/sub/task.json", json.dumps({**TASK, "checks": TASK["checks"][:1], "tempted": []}))
        self.assertTrue(any("ne mesure rien" in p for p in bench.selftest(self.fx)))

    def test_tempted_solution_must_fail_what_it_declares(self):
        task = {**TASK, "tempted": [{"patch": "tempted/eval.patch", "fails": ["no_eval", "guard"]}]}
        write(self.fx, "tasks/sub/task.json", json.dumps(task))
        problems = bench.selftest(self.fx)
        self.assertTrue(any("devrait échouer à ['guard']" in p for p in problems), problems)

    def test_temptation_caught_by_the_project_s_own_commands_is_a_warning(self):
        self.assertEqual(bench.selftest_full(self.fx)["warnings"], [])           # eval() passe les tests visibles
        broken = {"calc.py": CALC + "\n\ndef sub(a, b):\n    return a - b\n",
                  "test_calc.py": TEST_CALC + "\n    def test_sub(self):\n        self.assertEqual(calc.sub(5, 2), 99)\n"}
        self.patch("tempted/eval.patch", broken)
        write(self.fx, "tasks/sub/task.json", json.dumps({**TASK, "tempted": [{"patch": "tempted/eval.patch", "fails": ["tests"]}]}))
        result = bench.selftest_full(self.fx)
        self.assertEqual(result["problems"], [])
        self.assertTrue(any("ne départage pas les bras" in w for w in result["warnings"]), result)

    def test_broken_reference_solution_is_reported(self):
        self.patch("solution.patch", {"calc.py": CALC + "\n\ndef sub(a, b):\n    return a + b\n"})
        self.assertTrue(any("solution de référence échoue" in p for p in bench.selftest(self.fx)))


class PlanAndRegistryTests(BenchCase):
    def plan(self, **kwargs):
        with mock.patch.object(fixtures, "FIXTURES_ROOT", self.root):
            return bench.plan(**{"kinds": ["audit", "init", "task"], "role": "tuning", **kwargs})

    def test_plan_lists_one_agent_run_per_cell(self):
        cells = self.plan()
        self.assertEqual([(c["kind"], c.get("arm")) for c in cells],
                         [("audit", None), ("init", None), ("task", "bare"), ("task", "asis"), ("task", "harness")])
        self.assertEqual(sum(c["tokens"] for c in cells), bench.COST["audit"] + bench.COST["init"] + 3 * bench.COST["task"])

    def test_holdout_fixture_is_kept_out_of_a_tuning_campaign(self):
        write(self.fx, "expected.json", json.dumps({"fixture": "demo", "role": "holdout", "status": {}, "init": {}}))
        self.assertEqual(self.plan(), [])
        self.assertTrue(self.plan(role="holdout"))
        self.assertTrue(self.plan(role="all"))

    def test_registry_round_trip_and_report(self):
        path = os.path.join(self.tmp.name, "results.jsonl")
        row = {"date": "2026-11-10", "kind": "task", "fixture": "demo", "task": "sub", "arm": "bare", "model": None,
               "skill_rev": "abc1234", "score": "4/6", "ok": False, "blind": True, "run": None, "note": None}
        bench.record(row, path)
        bench.record({**row, "arm": "harness", "score": "6/6", "ok": True}, path)
        rows = bench.load_results(path)
        self.assertEqual([r["arm"] for r in rows], ["bare", "harness"])
        report = bench.render_report(rows)
        self.assertIn("| 2026-11-10 | task | demo | sub | bare | non relevé | abc1234 | 4/6 | non |", report)
        self.assertIn("| harness | non relevé | abc1234 | 6/6 | oui |", report)

    def test_empty_registry(self):
        self.assertIn("Registre vide", bench.render_report([]))


class PlayTests(BenchCase):
    """`bench play` : la chaîne complète, avec un faux agent à la place du vrai."""

    def play(self, arm="asis", files=None, **kwargs):
        seen = {}

        def fake_agent(workdir, prompt, task):
            seen.update(workdir=workdir, prompt=prompt, claude_md=os.path.exists(os.path.join(workdir, "CLAUDE.md")))
            for rel, content in (SOLUTION if files is None else files).items():
                write(workdir, rel, content)
            return {"report": "J'ai ajouté sub.", "error": None, "usage": {"tokens": 1234, "turns": 3, "duration_s": 5, "denied": 0}}

        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")
        done = bench.play(self.fx, "sub", arm, self.work_root, runner=fake_agent, label="génération test",
                          results=self.results, day="2026-01-02", **kwargs)
        return done, seen

    def test_the_agent_gets_the_statement_verbatim_in_a_neutral_path(self):
        done, seen = self.play("bare")
        self.assertEqual(seen["prompt"], "Ajoute sub.\n")
        self.assertFalse(seen["claude_md"])
        rel = os.path.relpath(seen["workdir"], self.work_root)
        self.assertRegex(rel, r"^w-[^/]+/repo$")
        for word in ("bare", "demo", "fixture", "harness"):
            self.assertNotIn(word, rel)

    def test_outputs_are_filed_and_the_run_is_recorded(self):
        done, _ = self.play("harness")
        self.assertTrue(done["check"]["ok"])
        self.assertEqual(os.path.basename(done["out"]), "2026-01-02-task-blind-harness")
        self.assertEqual(sorted(os.listdir(done["out"])), ["compte-rendu.md", "diff.patch", "note.md", "usage.json"])
        with open(os.path.join(done["out"], "diff.patch"), encoding="utf-8") as fh:
            self.assertIn("+def sub(a, b):", fh.read())
        with open(os.path.join(done["out"], "usage.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["tokens"], 1234)
        row = bench.load_results(self.results)[-1]
        self.assertEqual((row["kind"], row["arm"], row["score"], row["ok"], row["model"]), ("task", "harness", "6/6", True, "génération test"))

    def test_a_failed_run_is_recorded_too(self):
        done, _ = self.play("asis", files={})
        self.assertFalse(done["check"]["ok"])
        self.assertFalse(bench.load_results(self.results)[-1]["ok"])

    def test_the_working_copy_must_live_outside_this_repository(self):
        with self.assertRaises(SystemExit):
            bench.play(self.fx, "sub", "bare", os.path.join(bench.repo_root(), "scratch"), runner=lambda *a: {})

    def test_the_agent_command_is_neutral_and_confined(self):
        cmd = bench.agent_command({"agent_bash": ["go *", "git *"]})
        joined = " ".join(cmd)
        self.assertIn("--setting-sources project", joined)
        self.assertIn("--strict-mcp-config", joined)
        self.assertIn("--permission-prompts none", joined)
        self.assertIn("Bash(go *)", cmd)
        self.assertIn(f"Read(/{bench.repo_root()}/**)", cmd)
        self.assertNotIn("bypassPermissions", joined)
        self.assertNotIn("--dangerously-skip-permissions", joined)
        self.assertNotIn("Bash", [c for c in cmd if c == "Bash"])          # jamais Bash sans restriction


class InitPlayTests(BenchCase):
    """`bench init` : le pas 1 joué par un agent neutre, puis rejoué comme bras d'une tâche."""

    AGENTS = "# demo\n\nMode : **délégation**.\n\n## Règles\n- Pas d'eval. (non vérifiée) [2026-01]\n\n## Interdits\n- Toucher à tools/.\n"

    def setUp(self):
        super().setUp()
        write(self.fx, "repo/PLAN.md", "plan abandonné\n")
        write(self.fx, "owner.md", "# Propriétaire fictif\n\nCe fichier se donne à l'agent évalué ; les faits plantés sont ailleurs.\n\n"
                                    "## Réponses à l'entretien\n1. **Mode** : délégation.\n")
        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")
        self.seen = {}

    def init(self):
        def fake_agent(workdir, prompt, spec):
            self.seen.update(workdir=workdir, prompt=prompt, spec=spec, kit=os.path.join(os.path.dirname(workdir), "kit"))
            write(workdir, "AGENTS.md", self.AGENTS)
            write(workdir, "CLAUDE.md", "@AGENTS.md\n")
            os.remove(os.path.join(workdir, "PLAN.md"))
            return {"report": "Palier 1 atteint. PLAN.md supprimé.", "error": None,
                    "usage": {"tokens": 4321, "turns": 9, "duration_s": 12, "denied": 0}}
        return bench.play_init(self.fx, self.work_root, runner=fake_agent, label="génération test",
                               results=self.results, day="2026-01-02")

    def test_the_agent_gets_the_kit_and_the_owner_s_answers_without_the_header(self):
        self.init()
        kit = self.seen["kit"]
        self.assertIn(f"{kit}/skills/harness-init/SKILL.md", self.seen["prompt"])
        self.assertIn("**Mode** : délégation", self.seen["prompt"])
        self.assertNotIn("faits plantés", self.seen["prompt"])
        self.assertNotIn("évalué", self.seen["prompt"])
        self.assertTrue(os.path.isfile(os.path.join(kit, "skills", "harness-init", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(kit, "cli", "harness.py")))
        self.assertFalse(os.path.exists(os.path.join(kit, "cli", "tests")))
        self.assertFalse(os.path.exists(os.path.join(kit, "fixtures")))
        self.assertIn(f"python3 {kit}/cli/harness.py *", self.seen["spec"]["agent_bash"])
        self.assertRegex(os.path.relpath(self.seen["workdir"], self.work_root), r"^w-[^/]+/repo$")

    def test_the_step_is_graded_filed_and_recorded(self):
        done = self.init()
        self.assertTrue(done["check"]["ok"], done["check"])
        self.assertEqual(os.path.basename(done["out"]), "2026-01-02-init-blind")
        self.assertEqual(sorted(os.listdir(done["out"])), ["compte-rendu.md", "diff.patch", "note.md", "overlay", "usage.json"])
        with open(os.path.join(done["out"], "note.md"), encoding="utf-8") as fh:
            self.assertIn("palier 1", fh.read())
        row = bench.load_results(self.results)[-1]
        self.assertEqual((row["kind"], row["fixture"], row["ok"], row["model"]), ("init", "demo", True, "génération test"))

    def test_what_the_step_changed_becomes_an_overlay_a_task_can_play(self):
        done = self.init()
        overlay = os.path.join(done["out"], "overlay")
        self.assertEqual(sorted(os.listdir(overlay)), ["AGENTS.md", "CLAUDE.md", "REMOVE.txt"])
        with open(os.path.join(overlay, "REMOVE.txt"), encoding="utf-8") as fh:
            self.assertIn("PLAN.md", fh.read())
        state = {}

        def task_agent(workdir, prompt, task):
            with open(os.path.join(workdir, "AGENTS.md"), encoding="utf-8") as fh:
                state.update(agents=fh.read(), plan=os.path.exists(os.path.join(workdir, "PLAN.md")))
            for rel, content in SOLUTION.items():
                write(workdir, rel, content)
            return {"report": "fait", "error": None, "usage": {"tokens": 1}}

        played = bench.play(self.fx, "sub", "harness", self.work_root, runner=task_agent, overlay=overlay,
                            results=self.results, day="2026-01-02", note="harness produit par le pas 1 à l'aveugle",
                            out_dir=os.path.join(self.tmp.name, "out-task"))
        self.assertEqual(state, {"agents": self.AGENTS, "plan": False})
        self.assertTrue(played["check"]["ok"])
        self.assertEqual(bench.load_results(self.results)[-1]["note"], "harness produit par le pas 1 à l'aveugle")


class StepPlayTests(BenchCase):
    """`bench step` : un pas de harness-step, noté par l'état mesuré avant et après."""

    START = ("# demo\n\nMode : **délégation**.\n\n## Règles\n- Pas d'eval. Pourquoi : incident. (non vérifiée) [2026-01]\n\n"
             "## Interdits\n- Toucher à tools/.\n")
    PAS2 = ("\n## Maintenance de ce fichier\n- Un commentaire de review qui commence par `rule:` est une règle candidate.\n"
            "<!-- harvest: last=2026-01-02 ref=init -->\n")

    def setUp(self):
        super().setUp()
        write(self.fx, "owner.md", "# Propriétaire fictif\n\n## Réponses\n1. **Mode** : délégation.\n")
        self.start = os.path.join(self.tmp.name, "start")
        write(self.start, "AGENTS.md", self.START)
        write(self.start, "CLAUDE.md", "@AGENTS.md\n")
        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")

    def step(self, target, act, report="Pas fait."):
        def fake_agent(workdir, prompt, spec):
            self.prompt = prompt
            act(workdir)
            return {"report": report, "error": None, "usage": {"tokens": 7}}
        return bench.play_step(self.fx, self.work_root, self.start, target, runner=fake_agent, label="génération test",
                               results=self.results, day="2026-01-02", out_dir=os.path.join(self.tmp.name, "out"))

    def append(self, text):
        def act(workdir):
            with open(os.path.join(workdir, "AGENTS.md"), "a", encoding="utf-8") as fh:
                fh.write(text)
        return act

    def test_the_level_two_files_are_one_step(self):
        done = self.step(2, self.append(self.PAS2))
        self.assertTrue(done["check"]["ok"], done["check"])
        self.assertIn("L2.maintenance", done["check"]["flipped"])
        self.assertIn("harness-step/SKILL.md", self.prompt)
        with open(os.path.join(done["out"], "overlay", "AGENTS.md"), encoding="utf-8") as fh:
            self.assertIn("rule:", fh.read())
        self.assertEqual(bench.load_results(self.results)[-1]["kind"], "step")

    def test_no_step_when_one_was_possible_is_reported(self):
        done = self.step(2, lambda workdir: None, report="Il n'y a pas de pas.")
        self.assertTrue(any("aucune vérification visée n'a basculé" in p for p in done["check"]["problems"]), done["check"])

    def test_a_reached_target_changes_nothing_and_says_so(self):
        done = self.step(1, lambda workdir: None, report="Objectif atteint : palier 1.")
        self.assertTrue(done["check"]["ok"], done["check"])
        done = self.step(1, self.append(self.PAS2), report="J'ai posé la suite.")
        problems = " ".join(done["check"]["problems"])
        self.assertIn("objectif déjà atteint", problems)
        self.assertIn("ne le dit pas", problems)
        self.assertIn("au-delà du palier visé", problems)

    def test_two_levels_at_once_is_two_steps(self):
        process = "\n## Processus de travail\n- Une tâche est finie quand la CI est verte.\n"
        done = self.step(4, self.append(self.PAS2 + process))
        self.assertTrue(any("plus d'un pas" in p for p in done["check"]["problems"]), done["check"])

    def test_a_lost_rule_and_a_dangling_reference_are_reported(self):
        def act(workdir):
            with open(os.path.join(workdir, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.START.replace("- Toucher à tools/.\n", "") + self.PAS2
                         + "\n## Tâches déléguées\n- `release` (`.claude/skills/release`)\n")
        fx_expected = {"init": {"must_surface": [{"id": "I1", "what": "tools/ intouchable", "any_of": ["tools/"]}]}}
        with open(os.path.join(self.fx, "expected.json"), "w", encoding="utf-8") as fh:
            json.dump(fx_expected, fh)
        problems = " ".join(self.step(2, act)["check"]["problems"])
        self.assertIn("fait perdu : I1", problems)
        self.assertIn("référence sans cible ajoutée", problems)


class AskedOwnerTests(BenchCase):
    """`bench init --answers asked` : le propriétaire ne répond qu'à ce qu'on lui demande."""

    OWNER = {"intro": "Je tiens ce dépôt.",
             "answers": [{"id": "mode", "any_of": ["mode", "délég*"], "answer": "Délégation."},
                         {"id": "oral", "fact": "I9", "any_of": ["nulle part", "à chaque revue"],
                          "answer": "Toute réponse rejouée porte l'en-tête X-Rejoue."}],
             "default": "Regardez dans docs/."}

    def setUp(self):
        super().setUp()
        write(self.fx, "owner.md", "# Propriétaire fictif\n\n## Réponses\n1. **Mode** : délégation. En-tête X-Rejoue.\n")
        write(self.fx, "owner.json", json.dumps(self.OWNER, ensure_ascii=False))
        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")
        self.seen = {}

    def init(self, questions, answers="auto"):
        import re
        import subprocess
        import sys

        def fake_agent(workdir, prompt, spec):
            self.seen.update(prompt=prompt, spec=spec)
            client = re.search(r"python3 (\S+proprietaire\.py)", prompt)
            replies = ""
            if client and questions:
                replies = subprocess.run([sys.executable, client.group(1), *questions], capture_output=True,
                                         text=True, check=True).stdout
            self.seen["replies"] = replies
            write(workdir, "AGENTS.md", "# demo\n\nMode : **délégation**.\n")
            write(workdir, "CLAUDE.md", "@AGENTS.md\n")
            return {"report": "Palier 1.", "error": None, "usage": {"tokens": 10}}
        return bench.play_init(self.fx, self.work_root, runner=fake_agent, label="génération test",
                               results=self.results, day="2026-01-02", answers=answers)

    def test_the_agent_gets_a_way_to_ask_and_none_of_the_answers(self):
        self.init([])
        self.assertIn("proprietaire.py", self.seen["prompt"])
        self.assertIn("Je tiens ce dépôt.", self.seen["prompt"])
        self.assertNotIn("X-Rejoue", self.seen["prompt"])
        self.assertNotIn("Délégation.", self.seen["prompt"])
        self.assertTrue(any(r.endswith("proprietaire.py *") for r in self.seen["spec"]["agent_bash"]))

    def test_a_question_gets_only_the_answers_it_triggers(self):
        done = self.init(["Mode : délégation ou assistance ?", "Quelle base de données ?"])
        self.assertIn("R : Délégation.", self.seen["replies"])
        self.assertIn("R : Regardez dans docs/.", self.seen["replies"])
        self.assertNotIn("X-Rejoue", self.seen["replies"])
        self.assertEqual(done["interview"], {"questions": 2, "fetched": {}})
        with open(os.path.join(done["out"], "entretien.md"), encoding="utf-8") as fh:
            self.assertIn("I9, que seul le propriétaire détient : jamais demandé", fh.read())
        self.assertIn("I9 jamais demandé", bench.load_results(self.results)[-1]["note"])

    def test_asking_for_what_is_written_nowhere_fetches_the_fact(self):
        done = self.init(["Mode ?", "Qu'est-ce que vous redites à chaque revue ?"])
        self.assertIn("X-Rejoue", self.seen["replies"])
        self.assertEqual(done["interview"]["fetched"], {"I9": 2})
        with open(os.path.join(done["out"], "note.md"), encoding="utf-8") as fh:
            self.assertIn("I9, que seul le propriétaire détient : demandé à la question 2", fh.read())
        self.assertIn("entretien.json", os.listdir(done["out"]))

    def test_given_answers_keep_the_old_way(self):
        done = self.init([], answers="given")
        self.assertIn("X-Rejoue", self.seen["prompt"])
        self.assertNotIn("proprietaire.py", self.seen["prompt"])
        self.assertIsNone(done["interview"])

    def test_asked_without_an_owner_file_is_refused(self):
        os.remove(os.path.join(self.fx, "owner.json"))
        with self.assertRaises(SystemExit):
            self.init([], answers="asked")


@unittest.skipUnless(os.environ.get("HARNESS_SELFTEST"), "HARNESS_SELFTEST=1 : rejoue les tâches des vraies fixtures (go, npm)")
class RealFixtureTaskTests(unittest.TestCase):
    def test_every_task_of_every_fixture_is_well_posed(self):
        for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
            fixture_dir = os.path.join(fixtures.FIXTURES_ROOT, name)
            if bench.list_tasks(fixture_dir):
                with self.subTest(fixture=name):
                    self.assertEqual(bench.selftest(fixture_dir), [])


if __name__ == "__main__":
    unittest.main()
