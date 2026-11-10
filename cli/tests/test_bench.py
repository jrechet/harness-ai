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
        for rel, content in {"README.md": "# demo\n\nUne fixture.\n", "calc.py": CALC, "test_calc.py": TEST_CALC,
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

    def test_no_arm_copies_unversioned_dependencies_or_reveals_the_fixture(self):
        work = self.work("asis")
        self.assertFalse(os.path.exists(os.path.join(work, "node_modules")))
        with open(os.path.join(work, "README.md"), encoding="utf-8") as fh:
            self.assertNotIn("fixture", fh.read())

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
        self.assertEqual(bench.diff(work)["extra_test.py"], {"added": ["# sub"], "changed": 1})

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
        self.assertEqual(sum(c["tokens"] for c in cells), 2 * 130_000 + 3 * 90_000)

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
