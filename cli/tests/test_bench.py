"""Tests of the before-and-after bench, on a synthetic fixture written in a temporary folder:
arms, diff, checks, hidden tests, well-posed task, plan and registry. Offline, Python only."""
from __future__ import annotations

import contextlib
import glob
import io
import json
import os
import re
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
        {"id": "tests", "what": "the tests pass", "run": f"{sys.executable} -m unittest -q test_calc"},
        {"id": "acceptance", "what": "sub exists", "run": f"{sys.executable} -m unittest -q test_zz", "acceptance": True},
        {"id": "no_eval", "what": "no eval", "forbid_added": {"paths": r"\.py$", "pattern": r"\beval\("}},
        {"id": "own_test", "what": "a test written", "require_added": {"paths": r"^test_calc\.py$", "pattern": "sub"}},
        {"id": "guard", "what": "guardrail intact", "forbid_changed": r"^tools/"},
        {"id": "small", "what": "README barely touched", "max_changed_lines": {"paths": r"^README\.md$", "max": 2}},
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
        write(self.fx, "runs/2026-01-01-step1-author/AGENTS.md", "# demo\n\nMode: **delegation**.\n")
        write(self.fx, "runs/2026-01-01-step1-author/CLAUDE.md", "@AGENTS.md\n")
        write(self.fx, "runs/2026-01-01-step1-author/RUN.md", "run note\n")
        write(self.fx, "tasks/sub/task.json", json.dumps(TASK))
        write(self.fx, "tasks/sub/task.md", "Add sub.\n")
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
        write(self.fx, "repo/PLAN.md", "abandoned plan\n")
        write(self.fx, "runs/2026-01-01-step1-author/REMOVE.txt", "# deleted by the step\nPLAN.md\n../outside-the-repo\n")
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
        self.assertIn("fixtures de test", readme)            # the word alone also belongs to the project

    def test_the_english_bench_line_is_removed_too(self):
        write(self.fx, "repo/README.md", "# demo\n\n**Synthetic** repository: a fixture of the harness-ai project.\n\n"
                                         "Test fixtures load with loaddata.\n")
        with open(os.path.join(self.work("asis"), "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertNotIn("ynthetic", readme)
        self.assertIn("Test fixtures", readme)

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
        self.assertTrue(got["acceptance"])          # the temptation works: that is exactly why it is taken

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
        self.assertIn("removed", detail)
        ok, detail = graded(base["ci/ci.yml"] + "  api:\n    continue-on-error: true\n")
        self.assertFalse(ok)
        self.assertIn("added", detail)

    def test_a_diff_check_may_combine_conditions(self):
        work = self.work(files={"calc.py": CALC + "\n\ndef sub(a, b):\n    return eval('a-b')\n"})
        both = {"id": "x", "what": "x", "require_added": {"paths": r"\.py$", "pattern": "def sub"},
                "forbid_added": {"paths": r"\.py$", "pattern": r"\beval\("}}
        ok, detail = bench._diff_check(both, bench.diff(work))
        self.assertFalse(ok)
        self.assertIn("added", detail)
        self.assertEqual(bench._diff_check({**both, "forbid_added": {"paths": r"\.py$", "pattern": "exec"}}, bench.diff(work)), (True, ""))

    def test_failing_setup_fails_every_command_with_its_reason(self):
        task = {**TASK, "setup": f"{sys.executable} -c 'import sys; print(\"registry unreachable\"); sys.exit(3)'"}
        write(self.fx, "tasks/sub/task.json", json.dumps(task))
        result = bench.check(self.fx, "sub", self.work(files=SOLUTION))
        failed = {c["id"]: c["detail"] for c in result["checks"] if not c["passed"]}
        self.assertEqual(sorted(failed), ["acceptance", "tests"])
        self.assertIn("registry unreachable", failed["tests"])


class SelftestTests(BenchCase):
    def test_well_posed_task(self):
        self.assertEqual(bench.selftest(self.fx), [])

    def test_task_that_an_untouched_repository_passes_measures_nothing(self):
        write(self.fx, "tasks/sub/task.json", json.dumps({**TASK, "checks": TASK["checks"][:1], "tempted": []}))
        self.assertTrue(any("measures nothing" in p for p in bench.selftest(self.fx)))

    def test_tempted_solution_must_fail_what_it_declares(self):
        task = {**TASK, "tempted": [{"patch": "tempted/eval.patch", "fails": ["no_eval", "guard"]}]}
        write(self.fx, "tasks/sub/task.json", json.dumps(task))
        problems = bench.selftest(self.fx)
        self.assertTrue(any("should fail ['guard']" in p for p in problems), problems)

    def test_temptation_caught_by_the_project_s_own_commands_is_a_warning(self):
        self.assertEqual(bench.selftest_full(self.fx)["warnings"], [])           # eval() passes the visible tests
        broken = {"calc.py": CALC + "\n\ndef sub(a, b):\n    return a - b\n",
                  "test_calc.py": TEST_CALC + "\n    def test_sub(self):\n        self.assertEqual(calc.sub(5, 2), 99)\n"}
        self.patch("tempted/eval.patch", broken)
        write(self.fx, "tasks/sub/task.json", json.dumps({**TASK, "tempted": [{"patch": "tempted/eval.patch", "fails": ["tests"]}]}))
        result = bench.selftest_full(self.fx)
        self.assertEqual(result["problems"], [])
        self.assertTrue(any("does not separate the arms" in w for w in result["warnings"]), result)

    def test_broken_reference_solution_is_reported(self):
        self.patch("solution.patch", {"calc.py": CALC + "\n\ndef sub(a, b):\n    return a + b\n"})
        self.assertTrue(any("reference solution fails" in p for p in bench.selftest(self.fx)))


class PlanAndRegistryTests(BenchCase):
    def plan(self, **kwargs):
        with mock.patch.object(fixtures, "FIXTURES_ROOT", self.root):
            return bench.plan(**{"kinds": ["audit", "init", "task"], "role": "tuning", **kwargs})

    def test_plan_lists_one_agent_run_per_cell(self):
        cells = self.plan()
        self.assertEqual([(c["kind"], c.get("arm")) for c in cells],
                         [("audit", None), ("init", None), ("task", "bare"), ("task", "asis"), ("task", "harness")])
        self.assertEqual(sum(c["tokens"] for c in cells), bench.COST["audit"] + bench.COST["init"] + 3 * bench.COST["task"])

    def test_plan_announces_the_cost_per_kind_of_run(self):
        cells = self.plan()
        self.assertEqual({c["kind"]: c["tokens"] for c in cells}, {"audit": 145_000, "init": 105_000, "task": 75_000})
        self.assertEqual(sum(c["tokens"] for c in cells), 145_000 + 105_000 + 3 * 75_000)

    def test_plan_command_prints_the_total_of_the_per_kind_estimates(self):
        out = io.StringIO()
        with mock.patch.object(fixtures, "FIXTURES_ROOT", self.root), contextlib.redirect_stdout(out):
            self.assertEqual(bench.main(["plan", "--kind", "audit", "--kind", "init"]), 0)
        self.assertIn("| audit |  |  | 145,000 |", out.getvalue())
        self.assertIn("| init |  |  | 105,000 |", out.getvalue())
        self.assertIn("2 agent run(s), about 250,000 tokens.", out.getvalue())

    def test_init_and_audit_estimates_cover_every_recorded_blind_run(self):
        """Intended guard, coupled on purpose to the recorded runs: the estimate `bench plan`
        announces is the highest recorded blind run, rounded up. Recording a costlier run turns
        this red until `bench.COST` and its comment follow. Without it the init figure stayed at
        130,000 while no recorded run was above 104,684."""
        runs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "fixtures", "repos", "*", "runs")
        for kind in ("init", "audit"):
            recorded = {}
            for path in glob.glob(os.path.join(runs, f"*{kind}-blind*", "usage.json")):
                with open(path, encoding="utf-8") as fh:
                    recorded[path] = json.load(fh)["tokens"]
            self.assertTrue(recorded, f"no recorded {kind} run")
            costliest = max(recorded, key=recorded.get)
            highest = recorded[costliest]
            remedy = (f"{kind}: the costliest recorded run is {highest:,} tokens ({costliest}), the estimate is "
                      f"{bench.COST[kind]:,}. Set bench.COST[{kind!r}] to that run rounded up to the next 5,000, "
                      "then update the comment above COST and docs/requirements.md; do not edit the recorded run.")
            self.assertGreaterEqual(bench.COST[kind], highest, remedy)
            self.assertLess(bench.COST[kind] - highest, 5_000, remedy)

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
        self.assertIn("| 2026-11-10 | task | demo | sub | bare | not recorded | abc1234 | 4/6 | no |", report)
        self.assertIn("| harness | not recorded | abc1234 | 6/6 | yes |", report)

    def test_empty_registry(self):
        self.assertIn("Empty registry", bench.render_report([]))


class PlayTests(BenchCase):
    """`bench play`: the whole chain, with a fake agent in place of the real one."""

    def play(self, arm="asis", files=None, **kwargs):
        seen = {}

        def fake_agent(workdir, prompt, task):
            seen.update(workdir=workdir, prompt=prompt, claude_md=os.path.exists(os.path.join(workdir, "CLAUDE.md")))
            for rel, content in (SOLUTION if files is None else files).items():
                write(workdir, rel, content)
            return {"report": "I added sub.", "error": None, "usage": {"tokens": 1234, "turns": 3, "duration_s": 5, "denied": 0}}

        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")
        done = bench.play(self.fx, "sub", arm, self.work_root, runner=fake_agent, label="test generation",
                          results=self.results, day="2026-01-02", **kwargs)
        return done, seen

    def test_the_agent_gets_the_statement_verbatim_in_a_neutral_path(self):
        done, seen = self.play("bare")
        self.assertEqual(seen["prompt"], "Add sub.\n")
        self.assertFalse(seen["claude_md"])
        rel = os.path.relpath(seen["workdir"], self.work_root)
        self.assertRegex(rel, r"^w-[^/]+/repo$")
        for word in ("bare", "demo", "fixture", "harness"):
            self.assertNotIn(word, rel)

    def test_outputs_are_filed_and_the_run_is_recorded(self):
        done, _ = self.play("harness")
        self.assertTrue(done["check"]["ok"])
        self.assertEqual(os.path.basename(done["out"]), "2026-01-02-task-blind-harness")
        self.assertEqual(sorted(os.listdir(done["out"])), ["diff.patch", "note.md", "report.md", "usage.json"])
        with open(os.path.join(done["out"], "diff.patch"), encoding="utf-8") as fh:
            self.assertIn("+def sub(a, b):", fh.read())
        with open(os.path.join(done["out"], "usage.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["tokens"], 1234)
        row = bench.load_results(self.results)[-1]
        self.assertEqual((row["kind"], row["arm"], row["score"], row["ok"], row["model"]), ("task", "harness", "6/6", True, "test generation"))

    def test_a_failed_run_is_recorded_too(self):
        done, _ = self.play("asis", files={})
        self.assertFalse(done["check"]["ok"])
        self.assertFalse(bench.load_results(self.results)[-1]["ok"])

    def test_an_agent_that_never_started_is_neither_graded_nor_recorded(self):
        results = os.path.join(self.tmp.name, "results.jsonl")
        with self.assertRaises(SystemExit) as raised:
            bench.play(self.fx, "sub", "bare", os.path.join(self.tmp.name, "scratch"), results=results, day="2026-01-02",
                       runner=lambda *a: {"report": "", "error": "error: unknown option", "usage": {}, "started": False})
        self.assertIn("did not start", str(raised.exception))
        self.assertFalse(os.path.exists(results))
        self.assertFalse(os.path.isdir(os.path.join(self.fx, "runs", "2026-01-02-task-blind-bare")))

    def test_the_working_copy_must_live_outside_this_repository(self):
        with self.assertRaises(SystemExit):
            bench.play(self.fx, "sub", "bare", os.path.join(bench.repo_root(), "scratch"), runner=lambda *a: {})

    def test_the_agent_command_is_neutral_and_confined(self):
        cmd = bench.agent_command({"agent_bash": ["go *", "git *"]})
        joined = " ".join(cmd)
        self.assertIn("--setting-sources project", joined)
        self.assertIn("--strict-mcp-config", joined)
        self.assertIn("--permission-mode dontAsk", joined)       # denies what is not listed, without a question
        self.assertNotIn("acceptEdits", joined)                   # that mode lets an unlisted command write files
        self.assertIn("Bash(go *)", cmd)
        quoted = bench.agent_command({"agent_bash": ["python3 /kit/cli/harness.py *", "go *"]})
        self.assertIn("Bash(python3 /kit/cli/harness.py *)", quoted)
        self.assertIn('Bash(python3 "/kit/cli/harness.py" *)', quoted)   # the same script, path quoted
        self.assertEqual(len([c for c in quoted if c.startswith("Bash(")]), 3)
        self.assertIn(f"Read(/{bench.repo_root()}/**)", cmd)
        self.assertNotIn("bypassPermissions", joined)
        self.assertNotIn("--dangerously-skip-permissions", joined)
        self.assertNotIn("Bash", [c for c in cmd if c == "Bash"])          # never Bash without restriction


class InitPlayTests(BenchCase):
    """`bench init`: step 1 played by a neutral agent, then replayed as a task's arm."""

    AGENTS = "# demo\n\nMode: **delegation**.\n\n## Rules\n- No eval. (unverified) [2026-01]\n\n## Forbidden\n- Touching tools/.\n"

    def setUp(self):
        super().setUp()
        write(self.fx, "repo/PLAN.md", "abandoned plan\n")
        write(self.fx, "owner.md", "# Fictional owner\n\nThis file is given to the evaluated agent; the planted facts are elsewhere.\n\n"
                                    "## Interview answers\n1. **Mode**: delegation.\n")
        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")
        self.seen = {}

    def init(self):
        def fake_agent(workdir, prompt, spec):
            self.seen.update(workdir=workdir, prompt=prompt, spec=spec, kit=os.path.join(os.path.dirname(workdir), "kit"))
            write(workdir, "AGENTS.md", self.AGENTS)
            write(workdir, "CLAUDE.md", "@AGENTS.md\n")
            os.remove(os.path.join(workdir, "PLAN.md"))
            return {"report": "Level 1 reached. PLAN.md deleted.", "error": None,
                    "usage": {"tokens": 4321, "turns": 9, "duration_s": 12, "denied": 0}}
        return bench.play_init(self.fx, self.work_root, runner=fake_agent, label="test generation",
                               results=self.results, day="2026-01-02")

    def test_the_agent_gets_the_kit_and_the_owner_s_answers_without_the_header(self):
        self.init()
        kit = self.seen["kit"]
        self.assertIn(f"{kit}/skills/harness-init/SKILL.md", self.seen["prompt"])
        self.assertIn("**Mode**: delegation", self.seen["prompt"])
        self.assertNotIn("planted facts", self.seen["prompt"])
        self.assertNotIn("evaluated agent", self.seen["prompt"])
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
        self.assertEqual(sorted(os.listdir(done["out"])), ["diff.patch", "note.md", "overlay", "report.md", "usage.json"])
        with open(os.path.join(done["out"], "note.md"), encoding="utf-8") as fh:
            self.assertIn("level 1", fh.read())
        row = bench.load_results(self.results)[-1]
        self.assertEqual((row["kind"], row["fixture"], row["ok"], row["model"]), ("init", "demo", True, "test generation"))

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
            return {"report": "done", "error": None, "usage": {"tokens": 1}}

        played = bench.play(self.fx, "sub", "harness", self.work_root, runner=task_agent, overlay=overlay,
                            results=self.results, day="2026-01-02", note="harness produced by the blind step 1",
                            out_dir=os.path.join(self.tmp.name, "out-task"))
        self.assertEqual(state, {"agents": self.AGENTS, "plan": False})
        self.assertTrue(played["check"]["ok"])
        self.assertEqual(bench.load_results(self.results)[-1]["note"], "harness produced by the blind step 1")


class AuditPlayTests(BenchCase):
    """`bench audit`: the audit played on the repository as found, graded by the `audit` block."""

    def setUp(self):
        super().setUp()
        write(self.fx, "expected.json", json.dumps({"fixture": "demo", "status": {"level_reached": 0},
                                                     "audit": {"removals": [{"id": "N1", "any_of": ["step by step"], "reasons": ["useless"]}]}}))
        self.results = os.path.join(self.tmp.name, "results.jsonl")

    def audit(self, act):
        def fake_agent(workdir, prompt, spec):
            self.prompt = prompt
            act(workdir)
            return {"report": "Report.", "error": None, "usage": {"tokens": 9}}
        return bench.play_audit(self.fx, os.path.join(self.tmp.name, "scratch"), runner=fake_agent,
                                results=self.results, day="2026-01-02", out_dir=os.path.join(self.tmp.name, "out"))

    def write_audit(self, removals):
        def act(workdir):
            write(workdir, ".harness/audit.json", json.dumps({"audit": {"cut_the_agent_test": {"passed": True}},
                                                              "elements": [], "removals": removals}))
        return act

    def test_a_good_audit_is_graded_and_filed(self):
        done = self.audit(self.write_audit([{"text": "Think step by step", "reason": "useless"}]))
        self.assertTrue(done["check"]["ok"], done["check"])
        self.assertIn("harness-audit/SKILL.md", self.prompt)
        self.assertIn("not reachable", self.prompt)
        self.assertTrue(os.path.isfile(os.path.join(done["out"], "audit.json")))
        self.assertEqual(bench.load_results(self.results)[-1]["kind"], "audit")

    def test_an_audit_that_edits_the_repository_is_reported(self):
        def act(workdir):
            self.write_audit([{"text": "Think step by step", "reason": "useless"}])(workdir)
            write(workdir, "AGENTS.md", "# rewritten\n")
        done = self.audit(act)
        self.assertFalse(done["check"]["ok"])
        self.assertTrue(any("modifies nothing" in g for g in done["check"]["global"]))

    def test_no_audit_file_is_reported(self):
        done = self.audit(lambda workdir: None)
        self.assertFalse(done["check"]["ok"])


class StepPlayTests(BenchCase):
    """`bench step`: one harness-step step, graded by the state measured before and after."""

    START = ("# demo\n\nMode: **delegation**.\n\n## Rules\n- No eval. Why: incident. (unverified) [2026-01]\n\n"
             "## Forbidden\n- Touching tools/.\n")
    STEP2 = ("\n## Maintenance of this file\n- A review comment that starts with `rule:` is a candidate rule.\n"
             "<!-- harvest: last=2026-01-02 ref=init -->\n")

    def setUp(self):
        super().setUp()
        write(self.fx, "owner.md", "# Fictional owner\n\n## Answers\n1. **Mode**: delegation.\n")
        self.start = os.path.join(self.tmp.name, "start")
        write(self.start, "AGENTS.md", self.START)
        write(self.start, "CLAUDE.md", "@AGENTS.md\n")
        self.results = os.path.join(self.tmp.name, "results.jsonl")
        self.work_root = os.path.join(self.tmp.name, "scratch")

    def step(self, target, act, report="Step done."):
        def fake_agent(workdir, prompt, spec):
            self.prompt = prompt
            act(workdir)
            return {"report": report, "error": None, "usage": {"tokens": 7}}
        return bench.play_step(self.fx, self.work_root, self.start, target, runner=fake_agent, label="test generation",
                               results=self.results, day="2026-01-02", out_dir=os.path.join(self.tmp.name, "out"))

    def append(self, text):
        def act(workdir):
            with open(os.path.join(workdir, "AGENTS.md"), "a", encoding="utf-8") as fh:
                fh.write(text)
        return act

    def test_the_level_two_files_are_one_step(self):
        done = self.step(2, self.append(self.STEP2))
        self.assertTrue(done["check"]["ok"], done["check"])
        self.assertIn("L2.maintenance", done["check"]["flipped"])
        self.assertIn("harness-step/SKILL.md", self.prompt)
        with open(os.path.join(done["out"], "overlay", "AGENTS.md"), encoding="utf-8") as fh:
            self.assertIn("rule:", fh.read())
        self.assertEqual(bench.load_results(self.results)[-1]["kind"], "step")

    def test_no_step_when_one_was_possible_is_reported(self):
        done = self.step(2, lambda workdir: None, report="There is no step.")
        self.assertTrue(any("no targeted check flipped" in p for p in done["check"]["problems"]), done["check"])

    def test_a_reached_target_changes_nothing_and_says_so(self):
        done = self.step(1, lambda workdir: None, report="Target reached: level 1.")
        self.assertTrue(done["check"]["ok"], done["check"])
        done = self.step(1, self.append(self.STEP2), report="I laid what comes next.")
        problems = " ".join(done["check"]["problems"])
        self.assertIn("target already reached", problems)
        self.assertIn("does not say so", problems)
        self.assertIn("beyond the target level", problems)

    def test_a_reached_target_said_in_french_is_read_too(self):
        done = self.step(1, lambda workdir: None, report="Objectif atteint : palier 1.")
        self.assertTrue(done["check"]["ok"], done["check"])

    def test_one_more_guarded_rule_is_a_step_even_if_the_level_does_not_flip(self):
        start = ("# demo\n\nMode: **delegation**.\n\n## Rules\n"
                 + "".join(f"- Rule {i}. Why: incident {i}. (unverified) [2026-01]\n" for i in range(4))
                 + "\n## Forbidden\n- Touching tools/.\n" + self.STEP2)
        write(self.start, "AGENTS.md", start)
        write(self.fx, "repo/.github/workflows/ci.yml", "on: push\njobs:\n  test:\n    runs-on: x\n    steps:\n      - run: make test\n")
        write(self.fx, "repo/tools/guard.sh", "exit 0\n")

        def guard_one(workdir):
            path = os.path.join(workdir, "AGENTS.md")
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace("- Rule 0. Why: incident 0. (unverified)",
                                      "- Rule 0. Why: incident 0. Enforced by: `tools/guard.sh`, job `test`."))
        done = self.step(3, guard_one)
        self.assertTrue(done["check"]["ok"], done["check"])
        self.assertEqual(done["check"]["flipped"], [])
        self.assertEqual(len(done["check"]["gained"]), 1)
        self.assertTrue(done["check"]["gained"][0].startswith("L3.guarded 0.0 → 0."), done["check"]["gained"])
        nothing = self.step(3, lambda workdir: None)
        self.assertFalse(nothing["check"]["ok"])

    def test_the_audit_a_step_writes_is_kept_for_the_next_step(self):
        def act(workdir):
            write(workdir, ".harness/audit.json", json.dumps({"audit": {"date": "2026-01-02"}, "elements": []}))
            write(workdir, ".harness/state.json", "{}")
        done = self.step(3, act)
        overlay = os.path.join(done["out"], "overlay", ".harness")
        self.assertEqual(sorted(os.listdir(overlay)), ["audit.json"])

    def test_two_levels_at_once_is_two_steps(self):
        process = "\n## Working process\n- A task is done when the CI is green.\n"
        done = self.step(4, self.append(self.STEP2 + process))
        self.assertTrue(any("more than one step" in p for p in done["check"]["problems"]), done["check"])

    def test_a_lost_rule_and_a_dangling_reference_are_reported(self):
        def act(workdir):
            with open(os.path.join(workdir, "AGENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(self.START.replace("- Touching tools/.\n", "") + self.STEP2
                         + "\n## Delegated tasks\n- `release` (`.claude/skills/release`)\n")
        fx_expected = {"init": {"must_surface": [{"id": "I1", "what": "tools/ untouchable", "any_of": ["tools/"]}]}}
        with open(os.path.join(self.fx, "expected.json"), "w", encoding="utf-8") as fh:
            json.dump(fx_expected, fh)
        problems = " ".join(self.step(2, act)["check"]["problems"])
        self.assertIn("fact lost: I1", problems)
        self.assertIn("reference without a target added", problems)


class AskedOwnerTests(BenchCase):
    """`bench init --answers asked`: the owner answers only what they are asked."""

    OWNER = {"intro": "I maintain this repository.",
             "answers": [{"id": "mode", "any_of": ["mode", "delegat*"], "answer": "Delegation."},
                         {"id": "oral", "fact": "I9", "any_of": ["nowhere", "every review"],
                          "answer": "Every replayed response carries the X-Replayed header."}],
             "default": "Look in docs/."}

    def setUp(self):
        super().setUp()
        write(self.fx, "owner.md", "# Fictional owner\n\n## Answers\n1. **Mode**: delegation. X-Replayed header.\n")
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
            client = re.search(r"python3 (\S+\.py) \"", prompt)
            replies = ""
            if client and questions:
                replies = subprocess.run([sys.executable, client.group(1), *questions], capture_output=True,
                                         text=True, check=True).stdout
            self.seen["replies"] = replies
            write(workdir, "AGENTS.md", "# demo\n\nMode: **delegation**.\n")
            write(workdir, "CLAUDE.md", "@AGENTS.md\n")
            return {"report": "Level 1.", "error": None, "usage": {"tokens": 10}}
        return bench.play_init(self.fx, self.work_root, runner=fake_agent, label="test generation",
                               results=self.results, day="2026-01-02", answers=answers)

    def test_the_agent_gets_a_way_to_ask_and_none_of_the_answers(self):
        self.init([])
        client = re.search(r"python3 (\S+\.py) \"", self.seen["prompt"]).group(1)
        self.assertTrue(client.endswith(".py") and "/cli/" not in client, client)
        self.assertIn("I maintain this repository.", self.seen["prompt"])
        self.assertNotIn("X-Replayed", self.seen["prompt"])
        self.assertNotIn("Delegation.", self.seen["prompt"])
        self.assertIn(f"python3 {client} *", self.seen["spec"]["agent_bash"])

    def test_a_question_gets_only_the_answers_it_triggers(self):
        done = self.init(["Mode: delegation or assistance?", "Which database?"])
        self.assertIn("Delegation.", self.seen["replies"])
        self.assertIn("Look in docs/.", self.seen["replies"])
        self.assertNotIn("X-Replayed", self.seen["replies"])
        self.assertEqual(done["interview"], {"questions": 2, "fetched": {}})
        with open(os.path.join(done["out"], "note.md"), encoding="utf-8") as fh:
            self.assertIn("I9, which only the owner holds: never asked", fh.read())
        self.assertTrue(os.path.isfile(os.path.join(done["out"], "interview.md")))
        self.assertIn("I9 never asked", bench.load_results(self.results)[-1]["note"])

    def test_asking_for_what_is_written_nowhere_fetches_the_fact(self):
        done = self.init(["Mode?", "What do you repeat at every review?"])
        self.assertIn("X-Replayed", self.seen["replies"])
        self.assertEqual(done["interview"]["fetched"], {"I9": 2})
        with open(os.path.join(done["out"], "note.md"), encoding="utf-8") as fh:
            self.assertIn("I9, which only the owner holds: asked at question 2", fh.read())
        self.assertIn("interview.json", os.listdir(done["out"]))

    def test_given_answers_keep_the_old_way(self):
        done = self.init([], answers="given")
        self.assertIn("X-Replayed", self.seen["prompt"])
        self.assertIsNone(re.search(r"python3 (\S+\.py) \"", self.seen["prompt"]))
        self.assertIsNone(done["interview"])

    def test_asked_without_an_owner_file_is_refused(self):
        os.remove(os.path.join(self.fx, "owner.json"))
        with self.assertRaises(SystemExit):
            self.init([], answers="asked")


class EvidencePathTests(unittest.TestCase):
    """The registry and the requirements cite evidence by path: a cited path that no longer exists
    is a number nobody can check any more."""

    REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CITED_PATH = re.compile(r"fixtures/[A-Za-z0-9_./-]+")

    def cited_paths(self, text):
        return sorted({found.rstrip("./") for found in self.CITED_PATH.findall(text)})

    def missing(self, text):
        return [path for path in self.cited_paths(text)
                if not os.path.exists(os.path.join(self.REPO_ROOT, path))]

    def test_every_fixture_path_cited_in_a_registry_note_exists(self):
        registry = os.path.join(self.REPO_ROOT, "fixtures", "results.jsonl")
        with open(registry, encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        notes = [row["note"] for row in rows if isinstance(row.get("note"), str)]
        self.assertTrue(any(self.cited_paths(note) for note in notes), "no note cites a path: the test checks nothing")
        broken = {}
        for number, row in enumerate(rows, 1):
            note = row.get("note")
            if isinstance(note, str) and self.missing(note):
                broken[number] = self.missing(note)
        self.assertEqual(broken, {})

    def test_every_fixture_path_cited_in_the_requirements_exists(self):
        with open(os.path.join(self.REPO_ROOT, "docs", "requirements.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(self.cited_paths(text), "the requirements cite no path: the test checks nothing")
        self.assertEqual(self.missing(text), [])


class FactReportTests(BenchCase):
    """`bench report --facts`: the check that exercises the fact written nowhere else, read in each
    task run's note.md, counted by project and by arm, with every left-out run named."""
    FACT_TASK = {"id": "hdr", "statement": "task.md", "checks": [
        {"id": "tests", "what": "the tests pass", "run": "true"},
        {"id": "acceptance", "what": "the endpoint answers", "run": "true", "acceptance": True},
        {"id": "header", "what": "the header is set", "run": "true", "acceptance": True, "exercises": "I1"},
        {"id": "own_test", "what": "a test written", "require_added": {"paths": "x", "pattern": "x"}}]}

    def setUp(self):
        super().setUp()
        write(self.fx, "tasks/hdr/task.json", json.dumps(self.FACT_TASK))
        write(self.fx, "expected.json", json.dumps({"fixture": "demo", "status": {}, "init": {"must_surface": [
            {"id": "I1", "only_in_instructions": ["X-Secret-Header"]}]}}))
        self.rows = []

    def run_row(self, name, arm, marks, task="hdr", note=True, **extra):
        """One registry row and its note.md; `marks` maps a check id to passed, in the note's format."""
        rel = f"repos/demo/runs/{name}"
        if note:
            lines = [f"# Task demo/{task}: 0/0"]
            for cid, passed in marks.items():
                lines.append(f"- [{'x' if passed else ' '}] {cid}: what it checks" + ("" if passed else "\n      FAIL detail"))
            write(self.tmp.name, f"{rel}/note.md", "\n".join(lines) + "\n")
        row = {"date": name[:10], "kind": "task", "fixture": "demo", "task": task, "arm": arm, "score": "0/0",
               "ok": False, "blind": True, "run": rel, "note": None, **extra}
        self.rows.append(row)
        return row

    def view(self):
        with mock.patch.object(fixtures, "FIXTURES_ROOT", self.root):
            return bench.fact_view(self.rows, root=self.tmp.name)

    ALL = {"tests": True, "acceptance": True, "header": True, "own_test": True}

    def test_the_fact_check_is_counted_by_project_and_arm(self):
        self.run_row("2026-01-02-bare", "bare", {**self.ALL, "header": False})
        self.run_row("2026-01-03-bare", "bare", {**self.ALL, "header": False})
        self.run_row("2026-01-02-harness", "harness", self.ALL)
        view = self.view()
        self.assertEqual(view["excluded"], [])
        cells = {(c["fixture"], c["arm"]): c for c in view["cells"]}
        self.assertEqual((cells[("demo", "bare")]["passed"], cells[("demo", "bare")]["failed"]), (0, 2))
        self.assertEqual((cells[("demo", "harness")]["passed"], cells[("demo", "harness")]["failed"]), (1, 0))
        self.assertEqual(cells[("demo", "bare")]["check"], "header")
        self.assertEqual(cells[("demo", "bare")]["fact"], "I1")
        self.assertFalse(cells[("demo", "bare")]["carries"])
        self.assertTrue(cells[("demo", "harness")]["carries"])
        self.assertEqual(view["totals"], {"without": {"passed": 0, "failed": 2}, "with": {"passed": 1, "failed": 0}})

    def test_the_asis_arm_carries_the_fact_only_when_the_repository_instructions_write_it(self):
        self.run_row("2026-01-02-asis", "asis", {**self.ALL, "header": False})
        self.assertFalse(self.view()["cells"][0]["carries"])
        write(self.fx, "repo/CLAUDE.md", "# notes\n- Replayed answers set x-secret-header.\n")
        self.assertTrue(self.view()["cells"][0]["carries"])

    def test_a_run_played_before_the_check_existed_is_excluded_and_named(self):
        self.run_row("2026-01-01-bare", "bare", {"tests": True, "acceptance": True, "own_test": True})
        view = self.view()
        self.assertEqual(view["cells"], [])
        self.assertEqual([(e["run"], e["arm"]) for e in view["excluded"]], [("repos/demo/runs/2026-01-01-bare", "bare")])
        self.assertIn("header", view["excluded"][0]["reason"])
        self.assertIn("before", view["excluded"][0]["reason"])

    def test_a_run_whose_work_failed_is_excluded_the_fact_was_not_what_was_missing(self):
        self.run_row("2026-01-04-harness", "harness", {**self.ALL, "acceptance": False, "header": False})
        view = self.view()
        self.assertEqual(view["cells"], [])
        self.assertIn("acceptance", view["excluded"][0]["reason"])

    def test_a_passed_fact_check_counts_even_when_another_check_failed(self):
        self.run_row("2026-01-04-harness", "harness", {**self.ALL, "acceptance": False})
        self.run_row("2026-01-05-bare", "bare", {**self.ALL, "header": False, "own_test": False})
        view = self.view()
        self.assertEqual(view["excluded"], [])
        self.assertEqual(view["totals"], {"without": {"passed": 0, "failed": 1}, "with": {"passed": 1, "failed": 0}})

    def test_runs_that_cannot_be_read_are_excluded_with_their_reason(self):
        self.run_row("2026-01-02-bare", "bare", {}, note=False)
        self.run_row("2026-01-03-bare", "bare", self.ALL, run=None)
        self.run_row("2026-01-04-bare", "bare", self.ALL, blind=False)
        self.run_row("2026-01-05-bare", "bare", self.ALL, task="sub")
        self.run_row("2026-01-06-bare", "bare", self.ALL, task="gone")
        self.rows.append({"date": "2026-01-07", "kind": "init", "fixture": "demo", "score": "1/1", "ok": True, "blind": True})
        view = self.view()
        self.assertEqual(view["cells"], [])
        reasons = [e["reason"] for e in view["excluded"]]
        self.assertEqual(len(reasons), 5, "an init row is not a task run: it is not even listed")
        self.assertIn("note.md", reasons[0])
        self.assertIn("no run folder", reasons[1])
        self.assertIn("author", reasons[2])
        self.assertIn("exercises", reasons[3])
        self.assertIn("task.json", reasons[4])

    def test_the_view_is_rendered_with_counts_totals_and_exclusions(self):
        self.run_row("2026-01-02-bare", "bare", {**self.ALL, "header": False})
        self.run_row("2026-01-02-harness", "harness", self.ALL)
        self.run_row("2026-01-01-bare", "bare", {"tests": True})
        text = bench.render_facts(self.view())
        self.assertIn("| demo | hdr | header | I1 | bare | no | 0 | 1 |", text)
        self.assertIn("| demo | hdr | header | I1 | harness | yes | 1 | 0 |", text)
        self.assertIn("Arms that do not carry the fact: 1 failed of 1.", text)
        self.assertIn("Arms that carry it: 1 passed of 1.", text)
        self.assertIn("3 task runs in the registry, 2 counted, 1 excluded", text)
        self.assertIn("repos/demo/runs/2026-01-01-bare", text)

    def test_no_recorded_score_is_touched_and_the_rows_are_not_mutated(self):
        self.run_row("2026-01-02-bare", "bare", {**self.ALL, "header": False})
        before = json.dumps(self.rows, sort_keys=True)
        self.view()
        self.assertEqual(json.dumps(self.rows, sort_keys=True), before)

    def test_the_command_prints_the_view_in_both_formats(self):
        import contextlib
        import io
        self.run_row("2026-01-02-bare", "bare", {**self.ALL, "header": False})
        path = os.path.join(self.tmp.name, "results.jsonl")
        for row in self.rows:
            bench.record(row, path)
        for fmt, expected in (("md", "| demo | hdr | header | I1 | bare | no | 0 | 1 |"), ("json", '"totals"')):
            out = io.StringIO()
            with mock.patch.object(fixtures, "FIXTURES_ROOT", self.root), \
                    mock.patch.object(bench, "repo_root", lambda: self.tmp.name), contextlib.redirect_stdout(out):
                self.assertEqual(bench.main(["report", "--facts", "--results", path, "--format", fmt]), 0)
            self.assertIn(expected, out.getvalue())

    def test_the_real_registry_is_read_without_error_and_every_task_run_is_accounted_for(self):
        rows = bench.load_results()
        view = bench.fact_view(rows)
        tasks = [r for r in rows if r["kind"] == "task"]
        self.assertTrue(tasks)
        counted = sum(c["passed"] + c["failed"] for c in view["cells"])
        self.assertEqual(counted + len(view["excluded"]), len(tasks))
        self.assertTrue(bench.render_facts(view))

    def test_the_requirements_cite_the_numbers_the_command_prints(self):
        view = bench.fact_view(bench.load_results())
        without, with_ = view["totals"]["without"], view["totals"]["with"]
        counted = sum(c["passed"] + c["failed"] for c in view["cells"])
        with open(os.path.join(bench.repo_root(), "docs", "requirements.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("bench report --facts", text)
        for sentence in (f"{view['task_runs']} task runs, a single model; {counted} counted, {len(view['excluded'])} excluded",
                         f"fail the fact check {without['failed']} times out of {without['passed'] + without['failed']}",
                         f"pass it {with_['passed']} times out of {with_['passed'] + with_['failed']}"):
            self.assertIn(sentence, text)


@unittest.skipUnless(os.environ.get("HARNESS_SELFTEST"), "HARNESS_SELFTEST=1: replays the tasks of the real fixtures (go, npm)")
class RealFixtureTaskTests(unittest.TestCase):
    def test_every_task_of_every_fixture_is_well_posed(self):
        for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
            fixture_dir = os.path.join(fixtures.FIXTURES_ROOT, name)
            if bench.list_tasks(fixture_dir):
                with self.subTest(fixture=name):
                    self.assertEqual(bench.selftest(fixture_dir), [])


if __name__ == "__main__":
    unittest.main()
