"""Tests of the gates in CI: the settings are read on the base branch, a pull request cannot loosen its own
gates, and the exit code blocks when it must."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_sdlc  # noqa: E402
from aisdlclib import ci, context, points, qa  # noqa: E402

AWS = "AKIA" + "IOSFODNN7" + "EXAMPLE"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")


def git(repo: str, *args: str) -> str:
    out = subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args], capture_output=True, check=True)
    return out.stdout.decode().strip()


class Case(unittest.TestCase):
    CONFIG: dict | None = {"security": {"exclude": ["tests/secrets/**"]}, "qa": {"command": "python3 -m unittest discover -s tests", "runs": 2}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        self.write("app/calc.py", "def double(x):\n    return 2 * x\n")
        self.write("tests/__init__.py", "")
        self.write("tests/test_calc.py", "import unittest\nfrom app.calc import double\n\n\nclass T(unittest.TestCase):\n"
                                         "    def test_double(self):\n        self.assertEqual(double(2), 4)\n")
        self.write("app/__init__.py", "")
        if self.CONFIG is not None:
            self.write("docs/agents/gates.json", json.dumps(self.CONFIG))
        self.commit()
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.table = points.load()

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "c")

    def run_ci(self, **kwargs) -> dict:
        result = ci.run(self.table, self.repo, "main", **kwargs)
        return {g["id"]: g for g in result["gates"]} | {"_": result}


class GateTests(Case):
    def test_an_ordinary_change_passes_and_the_suite_is_replayed(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        gates = self.run_ci()
        self.assertTrue(gates["_"]["pass"])
        self.assertEqual(gates["repeat"]["status"], qa.OK)
        self.assertIn("2 runs out of 2", gates["repeat"]["evidence"])
        text = ci.render_md(gates["_"])
        self.assertIn("nothing failed", text)   # the scanner gate stays unmeasured without a report
        self.assertIn("neither the review", text)

    def test_a_secret_a_skipped_test_or_a_red_suite_blocks(self):
        cases = {"secrets": ("app/conf.py", f'KEY = "{AWS}"\n'),
                 "disabled": ("tests/test_calc.py", "import unittest\nfrom app.calc import double\n\n\nclass T(unittest.TestCase):\n"
                                                      "    @unittest." + "skip('later')\n    def test_double(self):\n        self.assertEqual(double(2), 4)\n"),
                 "repeat": ("app/calc.py", "def double(x):\n    return 3 * x\n")}
        for gate, (rel, text) in cases.items():
            with self.subTest(gate=gate):
                self.setUp()
                self.write(rel, text)
                self.commit()
                result = self.run_ci()["_"]
                self.assertIn(gate, result["failed"])
                self.assertFalse(result["pass"])
                self.assertIn("The merge is blocked", ci.render_md(result))
                self.assertNotIn(AWS, ci.render_md(result))

    def test_unmeasured_blocks_only_when_the_repo_asks_for_it(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        self.assertTrue(self.run_ci()["_"]["pass"])
        strict = self.run_ci(strict=True)["_"]
        self.assertFalse(strict["pass"])
        self.assertIn("requires them measured", ci.render_md(strict))

    def test_the_pipeline_tools_left_beside_the_code_do_not_stop_the_gates(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        self.write(".ai-sdlc/tool.py", "x = 1\n")   # the plugin fetched by the pipeline, untracked
        self.assertTrue(self.run_ci()["_"]["pass"])


class BaseBranchTests(Case):
    def test_a_folder_put_out_of_reading_on_the_base_branch_is_skipped_and_said(self):
        self.write("tests/secrets/fake.py", f'KEY = "{AWS}"\n')
        self.commit()
        result = self.run_ci()["_"]
        self.assertTrue(result["pass"])
        self.assertEqual(result["excluded"], ["tests/secrets/fake.py"])
        self.assertIn("Out of reading", ci.render_md(result))
        self.assertIn("1 file(s) out of reading.", ci.render_md(result).splitlines()[0])   # said from the title

    def test_a_test_about_skipping_can_be_put_out_of_the_disabled_gate_from_the_base_branch_only(self):
        skipped = ("import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest." + "skip('example')\n    def test_x(self):\n"
                   "        self.assertTrue(True)\n")
        self.write("tests/test_examples.py", skipped)
        self.commit()
        self.assertIn("disabled", self.run_ci()["_"]["failed"])
        git(self.repo, "checkout", "-q", "main")
        self.write("docs/agents/gates.json", json.dumps({**self.CONFIG, "qa": {**self.CONFIG["qa"], "exclude": ["tests/test_examples.py"]}}))
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")
        result = self.run_ci()["_"]
        self.assertNotIn("disabled", result["failed"])
        self.assertIn("tests/test_examples.py", result["excluded"])

    def test_a_deleted_test_is_spared_only_where_the_base_branch_puts_it_out_of_reading(self):
        body = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"
        git(self.repo, "checkout", "-q", "main")
        self.write("samples/tests/test_old.py", body)
        self.write("other/tests/test_kept.py", body)
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")
        os.remove(os.path.join(self.repo, "samples/tests/test_old.py"))
        self.commit()
        self.assertIn("disabled", self.run_ci()["_"]["failed"])
        git(self.repo, "checkout", "-q", "main")
        self.write("docs/agents/gates.json", json.dumps({**self.CONFIG, "qa": {**self.CONFIG["qa"], "exclude": ["samples/**"]}}))
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")
        self.assertNotIn("disabled", self.run_ci()["_"]["failed"])
        os.remove(os.path.join(self.repo, "other/tests/test_kept.py"))
        self.commit()
        self.assertIn("disabled", self.run_ci()["_"]["failed"])

    def test_a_pull_request_cannot_loosen_its_own_gates(self):
        self.write("docs/agents/gates.json", json.dumps({"security": {"exclude": ["app/**"]}, "qa": {}}))
        self.write("app/conf.py", f'KEY = "{AWS}"\n')
        self.write("app/calc.py", "def double(x):\n    return 3 * x\n")
        self.commit()
        result = self.run_ci()["_"]
        self.assertIn("secrets", result["failed"])   # the exclusion written by the PR is not read
        self.assertIn("repeat", result["failed"])    # the command removed by the PR is still run
        self.assertEqual(result["excluded"], [])

    def test_a_secret_added_then_removed_in_an_excluded_file_only_is_out_but_elsewhere_is_seen(self):
        self.write("app/conf.py", f'KEY = "{AWS}"\n')
        self.commit()
        self.write("app/conf.py", "KEY = None\n")
        self.commit()
        self.assertIn("secrets", self.run_ci()["_"]["failed"])   # the history of the branch is read in CI too


class ConfigTests(Case):
    CONFIG = None

    def set_config(self, value, name: str = "gates.json") -> None:
        git(self.repo, "checkout", "-q", "main")
        self.write(f"docs/agents/{name}", value if isinstance(value, str) else json.dumps(value))
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")

    def test_without_settings_the_suite_is_not_replayed_and_the_summary_says_so(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        gates = self.run_ci()
        self.assertNotIn("repeat", gates)
        self.assertIn("gives no command", ci.render_md(gates["_"]))

    def test_settings_that_put_everything_out_of_reading_or_are_malformed_are_refused(self):
        for bad in ({"security": {"exclude": ["**"]}}, {"security": {"exclude": ["*"]}}, {"security": {"exclude": ["**/*.py"]}},
                    {"security": {"exclude": ["/etc/**"]}}, {"security": {"exclude": "tests/**"}}, {"security": {"exclude": ["a/**"] * 21}},
                    {"security": {"ignore": []}}, {"other": 1}, [], {"qa": {"exclude": ["**/test_*.py"]}}, {"qa": {"exclude": "tests/**"}},
                    {"qa": {"runs": 0}}, {"qa": {"runs": True}}, {"qa": {"command": ""}}, {"qa": {"command": 3}}, "{",
                    {"secu": {"exclude": []}}, {"qa": {"commande": "make test"}}):   # the French keys belong to the former file only
            with self.subTest(bad=str(bad)[:40]):
                self.setUp()
                self.set_config(bad)
                self.write("app/calc.py", "def double(x):\n    return x + x\n")
                self.commit()
                with self.assertRaises(context.Refused):
                    self.run_ci()

    def test_the_former_french_settings_file_is_still_read_on_the_base_branch(self):
        self.set_config({"secu": {"exclure": ["tests/secrets/**"]}, "qa": {"commande": "python3 -m unittest discover -s tests", "passages": 2}},
                        "portes.json")
        self.write("tests/secrets/fake.py", f'KEY = "{AWS}"\n')
        self.write("app/calc.py", "def double(x):\n    return 3 * x\n")
        self.commit()
        result = self.run_ci()
        self.assertEqual(result["_"]["excluded"], ["tests/secrets/fake.py"])
        self.assertIn("repeat", result["_"]["failed"])   # the command of the former file is run
        self.assertIn("docs/agents/portes.json", ci.render_md(result["_"]))
        for bad in ({"security": {"exclude": []}}, {"secu": {"exclure": ["**"]}}, {"qa": {"passages": 0}}):
            with self.subTest(bad=str(bad)[:40]):
                self.setUp()
                self.set_config(bad, "portes.json")
                self.write("app/calc.py", "def double(x):\n    return x + x\n")
                self.commit()
                with self.assertRaises(context.Refused):
                    self.run_ci()

    def test_the_english_settings_file_wins_over_the_former_one(self):
        self.set_config({"secu": {"exclure": ["app/**"]}}, "portes.json")
        self.set_config({"security": {"exclude": ["tests/secrets/**"]}})
        self.write("app/conf.py", f'KEY = "{AWS}"\n')
        self.commit()
        self.assertIn("secrets", self.run_ci()["_"]["failed"])


class CliAndRepoTests(Case):
    def test_exit_codes_and_the_job_summary(self):
        summary = os.path.join(self.tmp.name, "summary.md")
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()

        def call(*extra: str) -> tuple[int, str]:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = ai_sdlc.main(["ci", "pr", self.repo, "--base", "main", *extra])
            return code, out.getvalue()

        os.environ["GITHUB_STEP_SUMMARY"] = summary
        self.addCleanup(os.environ.pop, "GITHUB_STEP_SUMMARY", None)
        self.assertEqual(call()[0], 0)
        self.assertEqual(call("--strict")[0], 1)
        with open(summary, encoding="utf-8") as fh:
            self.assertIn("### Gates", fh.read())
        self.write("app/conf.py", f'KEY = "{AWS}"\n')
        self.commit()
        code, out = call()
        self.assertEqual(code, 1)
        self.assertNotIn(AWS, out)
        git(self.repo, "checkout", "-q", "main")
        self.assertEqual(call()[0], 2)   # on the base branch itself: nothing to check

    def test_this_repository_settings_and_pipeline_files_hold_together(self):
        with open(os.path.join(ROOT, "docs", "agents", "gates.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertTrue(config["qa"]["command"])
        for glob in config["security"]["exclude"]:
            self.assertNotIn(glob, ci._TOO_WIDE)
        with open(os.path.join(ROOT, "scripts", "ci", "verify.sh"), encoding="utf-8") as fh:
            script = fh.read()
        for expected in ("discover -s cli/tests", "discover -s plugins/ai-sdlc/cli/tests", "progress check", "ci pr"):
            self.assertIn(expected, script)
        for workflow in (".github/workflows/ci.yml", ".forgejo/workflows/ci.yml"):
            with open(os.path.join(ROOT, workflow), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("sh scripts/ci/verify.sh", text)            # the YAML does not carry the logic
            self.assertIn("runs-on: [self-hosted, jre-server]", text)  # private repository: never a billed runner
            self.assertNotIn("ubuntu-latest", text)
            self.assertIn("fetch-depth: 0", text)
            self.assertIn("persist-credentials: false", text)
            self.assertIn("path: .base-branch", text)                  # the gates run with the code of the target branch
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            self.assertIn("head.repo.full_name == github.repository", fh.read())   # never a fork PR on this runner
        with open(os.path.join(ROOT, "plugins", "ai-sdlc", "ci", "gates.yml"), encoding="utf-8") as fh:
            template = fh.read()
        run_lines = [line for line in template.splitlines() if "ai_sdlc.py ci pr" in line]
        self.assertTrue(run_lines and all("${{" not in line for line in run_lines))   # a branch name does not enter a shell line


TICKET = "## Need\n" + "word " * 20 + "\n\n## Acceptance criteria\n1. Doubling 2 gives 4.\n2. Doubling 0 gives 0.\n"
TESTS = ("import unittest\nfrom app.calc import double\n\n\nclass T(unittest.TestCase):\n"
         "    def test_double(self):\n        self.assertEqual(double(2), 4)\n\n"
         "    def test_double_of_zero(self):\n        self.assertEqual(double(0), 0)\n")
TRACE = {"criteria": [{"criterion": 1, "tests": ["tests/test_calc.py::test_double"]},
                      {"criterion": 2, "tests": ["tests/test_calc.py::test_double_of_zero"]}], "not_covered": []}


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ai_sdlc.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CriteriaTests(Case):
    """"One test per criterion" in the pipeline, from the two files /qa leaves: the accepted ticket and the trace."""

    def setUp(self):
        super().setUp()
        self.write("tests/test_calc.py", TESTS)
        self.commit()
        self.ticket = self.outside("ticket.md", TICKET)
        os.environ.pop("GITHUB_STEP_SUMMARY", None)   # never the summary of the job that runs this test

    def outside(self, name: str, text: str) -> str:
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def pr(self, *extra: str) -> tuple[int, str, str]:
        return call("ci", "pr", self.repo, "--base", "main", *extra)

    def test_the_criteria_gate_passes_from_the_ticket_and_trace_files(self):
        code, out, _ = self.pr("--ticket", self.ticket, "--trace", self.outside("trace.json", json.dumps(TRACE)))
        self.assertEqual(code, 0)
        self.assertIn(f"**{qa.OK}** — Each acceptance criterion has its test (2 criteria out of 2)", out)
        self.assertNotIn("neither the review", out)        # the criteria gate ran: only the review is left unclaimed
        self.assertIn("do not run the review", out)

    def test_the_criteria_gate_fails_from_files_and_blocks_the_merge(self):
        cases = {"criterion 2 without a test": {"criteria": TRACE["criteria"][:1], "not_covered": []},
                 "test_invented not found": {"criteria": [TRACE["criteria"][0], {"criterion": 2, "tests": ["tests/test_calc.py::test_invented"]}],
                                             "not_covered": []}}
        for said, trace in cases.items():
            with self.subTest(said=said):
                code, out, _ = self.pr("--ticket", self.ticket, "--trace", self.outside("trace.json", json.dumps(trace)))
                self.assertEqual(code, 1)
                self.assertIn(said, out)
                self.assertIn("The merge is blocked", out)

    def test_a_criterion_left_to_a_human_is_unmeasured_and_blocks_only_under_strict(self):
        trace = {"criteria": TRACE["criteria"][:1], "not_covered": [{"criterion": 2, "reason": "checked by hand during acceptance testing"}]}
        files = ("--ticket", self.ticket, "--trace", self.outside("trace.json", json.dumps(trace)))
        result = ci.run(self.table, self.repo, "main", ticket_text=TICKET, mapping=trace)
        self.assertIn("criteria", result["unknown"])
        self.assertEqual(self.pr(*files)[0], 0)
        self.assertEqual(self.pr(*files, "--strict")[0], 1)

    def test_without_the_files_the_gate_is_not_run_and_the_summary_says_how_to_run_it(self):
        result = ci.run(self.table, self.repo, "main")
        self.assertNotIn("criteria", [g["id"] for g in result["gates"]])
        text = ci.render_md(result)
        self.assertIn("neither the review", text)
        self.assertIn("--ticket", text)
        self.assertIn("--trace", text)

    def test_one_file_without_the_other_or_an_unreadable_one_is_refused(self):
        trace = self.outside("trace.json", json.dumps(TRACE))
        for extra in (("--ticket", self.ticket), ("--trace", trace),
                      ("--ticket", self.ticket, "--trace", self.outside("broken.json", "{")),
                      ("--ticket", os.path.join(self.tmp.name, "absent.md"), "--trace", trace),
                      ("--ticket", self.ticket, "--trace", self.outside("list.json", "[]"))):
            with self.subTest(extra=[os.path.basename(e) for e in extra]):
                code, out, err = self.pr(*extra)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("ai-sdlc:", err)


class MainTests(unittest.TestCase):
    """`ci main`: the prerequisites of a delivery, said on each push to the delivery branch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo, remote = os.path.join(self.tmp.name, "repo"), os.path.join(self.tmp.name, "remote.git")
        os.makedirs(self.repo)
        git(self.tmp.name, "init", "-q", "--bare", "-b", "main", remote)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "remote", "add", "origin", remote)
        self.commit("app/a.py", "a = 1\n", "feat: first version")
        git(self.repo, "tag", "v1.2.3")
        self.commit("app/b.py", "b = 1\n", "fix: a rounding error")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "fetch", "-q", "origin")
        os.environ.pop("GITHUB_STEP_SUMMARY", None)   # never the summary of the job that runs this test

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, rel: str, text: str, message: str) -> None:
        self.write(rel, text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def checks(self, conclusion: str = "success") -> str:
        path = os.path.join(self.tmp.name, f"{conclusion}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([{"name": "tests", "status": "completed", "conclusion": conclusion, "headSha": git(self.repo, "rev-parse", "HEAD")}], fh)
        return path

    def main(self, *extra: str) -> tuple[int, str, str]:
        return call("ci", "main", self.repo, "--base", "origin/main", *extra)

    def test_exit_codes_follow_the_prerequisites_of_ship_check(self):
        code, out, _ = self.main("--checks", self.checks())
        self.assertEqual(code, 0)
        self.assertIn("### Delivery: the four prerequisites pass", out)
        self.assertIn("Proposed version: v1.2.4", out)
        self.assertIn("Nothing was tagged, pushed or deployed", out)
        code, out, _ = self.main()                      # no CI report: unmeasured, said, not blocking
        self.assertEqual(code, 0)
        self.assertIn("1 prerequisite(s) for a human to clear", out)
        code, out, _ = self.main("--strict")            # the repository requires every prerequisite cleared
        self.assertEqual(code, 1)
        self.assertIn("requires them cleared", out)
        self.assertEqual(self.main("--checks", self.checks(), "--strict")[0], 0)
        self.commit("app/c.py", "c = 1\n", "fix: not pushed")   # HEAD is no longer the head of the delivery branch
        code, out, _ = self.main()
        self.assertEqual(code, 1)
        self.assertIn("Do not deliver", out)

    def test_a_failed_check_of_the_commit_fails_the_job(self):
        self.assertEqual(self.main("--checks", self.checks("failure"))[0], 1)

    def test_the_pipeline_tools_left_beside_the_code_are_not_an_uncommitted_change(self):
        self.write(".ai-sdlc/tool.py", "x = 1\n")       # the plugin fetched by the pipeline, untracked
        self.assertEqual(self.main("--checks", self.checks())[0], 0)
        self.assertEqual(call("ship", "check", self.repo, "--base", "origin/main", "--checks", self.checks())[0], 1)   # in a session it still counts
        self.write("app/a.py", "a = 2\n")               # a tracked file changed by the job is not what was pushed
        code, out, _ = self.main("--checks", self.checks())
        self.assertEqual(code, 1)
        self.assertIn("uncommitted", out)

    def test_a_push_that_carries_nothing_since_the_last_version_passes_and_says_so(self):
        git(self.repo, "tag", "v1.2.4")
        code, out, _ = self.main()
        self.assertEqual(code, 0)
        self.assertIn("nothing to deliver", out)
        self.assertEqual(self.main("--strict")[0], 0)
        self.assertEqual(call("ship", "check", self.repo, "--base", "origin/main")[0], 2)   # `ship check` still refuses

    def test_a_refusal_exits_2_and_the_summary_receives_the_report(self):
        self.assertEqual(self.main("--since", "v9.9.9")[0], 2)
        self.assertEqual(self.main("--checks", os.path.join(self.tmp.name, "absent.json"))[0], 2)
        summary = os.path.join(self.tmp.name, "summary.md")
        os.environ["GITHUB_STEP_SUMMARY"] = summary
        self.addCleanup(os.environ.pop, "GITHUB_STEP_SUMMARY", None)
        self.main("--checks", self.checks())
        with open(summary, encoding="utf-8") as fh:
            self.assertIn("### Delivery", fh.read())


class TemplateTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "plugins", "ai-sdlc", "ci", "gates.yml"), encoding="utf-8") as fh:
            self.template = fh.read()

    def test_the_template_says_what_stays_unmeasured_and_how_to_require_it(self):
        strict = [line for line in self.template.splitlines() if "--strict" in line and "ai_sdlc.py ci pr" in line]
        self.assertTrue(strict and all(line.lstrip().startswith("#") for line in strict))   # offered, commented: off as shipped
        self.assertIn("no test is replayed", self.template)       # step 4 says what happens without a test command
        self.assertIn("unmeasured", self.template)
        self.assertIn("--ticket", self.template)
        self.assertIn("--trace", self.template)

    def test_the_template_runs_ci_main_on_a_push_and_no_branch_name_enters_a_shell_line(self):
        self.assertIn("push:", self.template)
        lines = [line for line in self.template.splitlines() if "ai_sdlc.py ci " in line]
        self.assertTrue(any("ci main" in line and not line.lstrip().startswith("#") for line in lines))
        self.assertTrue(all("${{" not in line for line in lines))


if __name__ == "__main__":
    unittest.main()
