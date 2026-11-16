"""Tests of the /qa gates: a disabled test fails, a flaky suite fails, coverage is read from a
report, and each acceptance criterion must name a test that exists."""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, points, qa  # noqa: E402
from tests.test_context import RepoCase, git, write  # noqa: E402
from tests.test_review import run  # noqa: E402

SRC = "def total(a, b):\n    return a + b\n"
TEST = "import unittest\nfrom app import total\n\n\nclass T(unittest.TestCase):\n    def test_sum(self):\n        self.assertEqual(total(1, 2), 3)\n"
TICKET = "## Need\n" + "word " * 20 + "\n\n## Acceptance criteria\n1. The sum of 1 and 2 is 3.\n2. A discount applies.\n"
TICKET_FR = "## Besoin\n" + "mot " * 20 + "\n\n## Critères d'acceptation\n1. La somme de 1 et 2 vaut 3.\n2. Une remise s'applique.\n"


class Case(RepoCase):
    def setUp(self):
        super().setUp()
        self.table = points.load()
        self.commit("app.py", SRC)
        self.commit("tests/test_app.py", TEST)
        git(self.repo, "checkout", "-q", "-b", "pr")

    def gates(self, **kw) -> dict[str, dict]:
        return {g["id"]: g for g in qa.run_gates(self.table, self.repo, "main", **kw)["gates"]}

    def change(self) -> None:
        self.commit("app.py", SRC + "\n\ndef discount(a):\n    if a > 100:\n        return a * 0.9\n    return a\n")


class DisabledTests(Case):
    def test_an_ordinary_change_disables_nothing(self):
        self.change()
        self.assertEqual(self.gates()["disabled"]["status"], qa.OK)

    def test_each_way_of_skipping_a_test_fails(self):
        for marker in ("    @unittest.skip('flaky')", "    @pytest.mark.skip", "it.skip('x', () => {})", "xit('x')", "@Disabled",
                       "t.Skip()", "#[ignore]", "        raise unittest.SkipTest('x')"):
            with self.subTest(marker=marker):
                git(self.repo, "checkout", "-q", "-B", "attempt", "main")
                self.commit("tests/test_app.py", TEST + marker + "\n")
                self.assertEqual(self.gates()["disabled"]["status"], qa.FAIL)

    def test_a_test_renamed_out_of_collection_or_made_exclusive_fails(self):
        for old, new in (("    def test_sum(self):", "    def _test_sum(self):"), ("    def test_sum(self):", "    def xtest_sum(self):")):
            with self.subTest(new=new):
                git(self.repo, "checkout", "-q", "-B", "attempt", "main")
                self.commit("tests/test_app.py", TEST.replace(old, new))
                gate = self.gates()["disabled"]
                self.assertEqual(gate["status"], qa.FAIL)
                self.assertIn("test_sum", gate["evidence"])
        for marker in ("it.only('x', () => {})", "fdescribe('x')", "pytest.importorskip('numpy')", '#[ignore = "slow"]', '[Fact(Skip = "x")]'):
            with self.subTest(marker=marker):
                git(self.repo, "checkout", "-q", "-B", "attempt", "main")
                self.commit("tests/test_app.py", TEST + marker + "\n")
                self.assertEqual(self.gates()["disabled"]["status"], qa.FAIL)

    def test_a_changed_test_configuration_is_not_measured_and_a_word_in_the_docs_is_not_a_skip(self):
        self.commit("pytest.ini", "[pytest]\ntestpaths = nowhere\n")
        gate = self.gates()["disabled"]
        self.assertEqual(gate["status"], qa.UNKNOWN)
        self.assertIn("pytest.ini", gate["evidence"])
        git(self.repo, "checkout", "-q", "-B", "attempt", "main")
        self.commit("README.md", "Use pytest.skip( to skip a test.\n")
        self.assertEqual(self.gates()["disabled"]["status"], qa.OK)

    def test_a_moved_test_file_is_not_a_deleted_one_and_other_test_names_are_known(self):
        git(self.repo, "mv", "tests/test_app.py", "tests/test_total.py")
        git(self.repo, "commit", "-q", "-m", "rename")
        self.assertEqual(self.gates()["disabled"]["status"], qa.OK)
        for path in ("tests.py", "src/FooTest.php", "src/foo_test.rs", "src/FooIT.java", "e2e/login.ts", "features/a.feature", "conftest.py"):
            self.assertTrue(qa.is_test(path), path)
        for path in ("src/contest/x.py", "latest/a.py", "attest.py", "src/app.py"):
            self.assertFalse(qa.is_test(path), path)

    def test_a_deleted_test_file_fails_and_a_removed_assertion_is_said(self):
        git(self.repo, "rm", "-q", "tests/test_app.py")
        git(self.repo, "commit", "-q", "-m", "remove")
        self.assertEqual(self.gates()["disabled"]["status"], qa.FAIL)
        git(self.repo, "checkout", "-q", "-B", "attempt", "main")
        self.commit("tests/test_app.py", TEST.replace("        self.assertEqual(total(1, 2), 3)\n", "        total(1, 2)\n"))
        gate = self.gates()["disabled"]
        self.assertEqual(gate["status"], qa.UNKNOWN)
        self.assertIn("tests/test_app.py", gate["evidence"])


class RepeatTests(Case):
    def test_a_suite_that_passes_every_time_is_ok(self):
        self.change()
        gate = self.gates(command=f"{sys.executable} -m unittest discover -s tests", runs=2)["repeat"]
        self.assertEqual(gate["status"], qa.OK, gate["evidence"])

    def test_a_failing_or_a_flaky_suite_fails_and_no_command_is_not_measured(self):
        self.change()
        self.assertEqual(self.gates()["repeat"]["status"], qa.UNKNOWN)
        self.assertEqual(self.gates(command=f"{sys.executable} -c 'raise SystemExit(1)'", runs=2)["repeat"]["status"], qa.FAIL)
        flaky = ("import os,sys; p='counter'; n=int(open(p).read()) if os.path.exists(p) else 0; "
                 "open(p,'w').write(str(n+1)); sys.exit(n % 2)")
        gate = self.gates(command=f'{sys.executable} -c "{flaky}"', runs=3)["repeat"]
        self.assertEqual(gate["status"], qa.FAIL)
        self.assertIn("flaky", gate["evidence"])
        os.remove(os.path.join(self.repo, "counter"))
        self.assertEqual(self.gates(command="command-that-does-not-exist", runs=1)["repeat"]["status"], qa.FAIL)

    def test_a_command_that_needs_a_shell_is_refused_not_half_run(self):
        self.change()
        for command in ("echo tests && false", "true || false", "pytest | tee out", "CI=1 pytest", "cd tests", "pytest > out"):
            with self.subTest(command=command), self.assertRaises(context.Refused) as ctx:
                self.gates(command=command, runs=1)
            self.assertIn("without a shell", str(ctx.exception))

    def test_uncommitted_work_is_refused(self):
        self.change()
        write(self.repo, "tests/test_new.py", "def test_x():\n    pass\n")
        with self.assertRaises(context.Refused) as ctx:
            self.gates()
        self.assertIn("not committed", str(ctx.exception))


class CoverageTests(Case):
    def report(self, name: str, text: str) -> str:
        path = self.repo + "-" + name
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_lcov_and_cobertura_give_the_share_of_added_lines_that_ran(self):
        self.change()       # added lines: 5 to 8 (def, if, return, return)
        lcov = self.report("lcov.info", "SF:" + os.path.join(self.repo, "app.py") + "\nDA:1,1\nDA:2,1\nDA:5,1\nDA:6,1\nDA:7,0\nDA:8,1\nend_of_record\n")
        gate = self.gates(coverage=lcov)["coverage"]
        self.assertEqual(gate["status"], qa.FAIL)
        self.assertIn("3 lines out of 4", gate["evidence"])
        self.assertIn("app.py:7", gate["evidence"])
        xml = ('<coverage><packages><package><classes><class filename="app.py"><lines>'
               + "".join(f'<line number="{n}" hits="1"/>' for n in range(1, 9)) + "</lines></class></classes></package></packages></coverage>")
        self.assertEqual(self.gates(coverage=self.report("cov.xml", xml))["coverage"]["status"], qa.OK)

    def test_a_changed_file_the_report_does_not_know_is_not_measured_and_test_files_do_not_count(self):
        self.change()
        self.commit("other.py", "def f():\n    return 1\n")
        self.commit("tests.py", "x = 1\n" * 30)
        lcov = self.report("lcov.info", "SF:app.py\n" + "".join(f"DA:{n},1\n" for n in range(1, 9))
                           + "end_of_record\nSF:tests.py\n" + "".join(f"DA:{n},1\n" for n in range(1, 31)) + "end_of_record\n")
        gate = self.gates(coverage=lcov)["coverage"]
        self.assertEqual(gate["status"], qa.UNKNOWN)
        self.assertIn("other.py", gate["evidence"])
        self.assertIn("6 lines out of 6", gate["evidence"])       # those of app.py: tests.py inflates nothing
        self.assertIn("1 file(s) out of 2", gate["evidence"])

    def test_a_pure_deletion_adds_no_line_and_an_ambiguous_or_stale_report_is_not_measured(self):
        self.commit("app.py", "def total(a, b):\n")              # one line removed, none added
        self.commit("pkg/util.py", "def g():\n    return 2\n")
        self.commit("lib/util.py", "def h():\n    return 3\n")
        lcov = self.report("lcov.info", "SF:app.py\nDA:1,0\nDA:2,0\nend_of_record\nSF:util.py\nDA:1,1\nDA:2,1\nend_of_record\n")
        gate = self.gates(coverage=lcov)["coverage"]
        self.assertEqual(gate["status"], qa.UNKNOWN)
        self.assertIn("ambiguous", gate["evidence"])
        self.assertNotIn("app.py:", gate["evidence"])
        old = self.report("old.info", "SF:pkg/util.py\nDA:1,1\nend_of_record\n")
        os.utime(old, (0, 0))
        self.assertIn("older", self.gates(coverage=old)["coverage"]["evidence"])

    def test_no_report_or_a_report_about_other_files_is_not_measured(self):
        self.change()
        self.assertEqual(self.gates()["coverage"]["status"], qa.UNKNOWN)
        other = self.report("lcov.info", "SF:other.py\nDA:1,1\nend_of_record\n")
        self.assertEqual(self.gates(coverage=other)["coverage"]["status"], qa.UNKNOWN)

    def test_a_broken_report_is_refused(self):
        self.change()
        for name, text in (("a.xml", "<coverage><class"), ("b.xml", '<!DOCTYPE x [<!ENTITY a "b">]><coverage/>'),
                           ("c.xml", "<coverage><!--" + "x" * 3000 + '--></coverage><!DOCTYPE x [<!ENTITY a "b">]>')):
            with self.subTest(name=name), self.assertRaises(context.Refused):
                self.gates(coverage=self.report(name, text))
        with self.assertRaises(context.Refused):
            self.gates(coverage=self.repo + "-absent.info")


class CriteriaTests(Case):
    def trace(self, ticket: str = TICKET, **kw) -> dict:
        return self.gates(ticket_text=ticket, **kw)["criteria"]

    def test_each_criterion_needs_a_test_that_exists_or_a_written_reason(self):
        self.change()
        good = {"criteria": [{"criterion": 1, "tests": ["tests/test_app.py::T::test_sum"]}],
                "not_covered": [{"criterion": 2, "reason": "covered by manual acceptance testing"}]}
        gate = self.trace(mapping=good)
        self.assertEqual(gate["status"], qa.UNKNOWN)      # a criterion without a test, even with a reason, waits for a human
        self.commit("tests/test_app.py", TEST + "\n    def test_discount(self):\n        self.assertEqual(total(0, 0), 0)\n")
        full = {"criteria": [{"criterion": 1, "tests": ["tests/test_app.py::test_sum"]},
                             {"criterion": 2, "tests": ["tests/test_app.py::T::test_discount"]}], "not_covered": []}
        self.assertEqual(self.trace(mapping=full)["status"], qa.OK)
        self.assertEqual(self.trace(ticket=TICKET_FR, mapping=full)["status"], qa.OK)   # a ticket written in French is read too
        same = {"criteria": [{"criterion": n, "tests": ["tests/test_app.py::test_sum"]} for n in (1, 2)], "not_covered": []}
        self.assertEqual(self.trace(mapping=same)["status"], qa.UNKNOWN)     # one test for all criteria: to look at

    def test_a_reference_must_name_a_real_test_in_a_test_file(self):
        self.change()
        self.commit("README.md", "test_sum is described here\n")
        self.commit("tests/test_app.py", TEST + "    # test_ghost only exists in this comment\n")
        for ref, needle in (("tests/test_app.py", "does not name"), ("README.md::test_sum", "is not a test file"),
                            ("tests/test_app.py::test_ghost", "not found"), ("tests/test_app.py::t", "not found"),
                            ("tests/test_app.py::", "does not name")):
            with self.subTest(ref=ref):
                gate = self.trace(mapping={"criteria": [{"criterion": 1, "tests": [ref]}, {"criterion": 2, "tests": [ref]}], "not_covered": []})
                self.assertEqual(gate["status"], qa.FAIL)
                self.assertIn(needle, gate["evidence"])
        excused = {"criteria": [], "not_covered": [{"criterion": n, "reason": "checked by hand during acceptance testing"} for n in (1, 2)]}
        self.assertIn("no criterion has a test", self.trace(mapping=excused)["evidence"])
        short = {"criteria": [{"criterion": 1, "tests": ["tests/test_app.py::test_sum"]}], "not_covered": [{"criterion": 2, "reason": "."}]}
        self.assertEqual(self.trace(mapping=short)["status"], qa.FAIL)

    def test_a_missing_criterion_a_test_that_does_not_exist_or_an_extra_one_fails(self):
        self.change()
        cases = {"without a test": {"criteria": [{"criterion": 1, "tests": ["tests/test_app.py"]}], "not_covered": []},
                 "not found": {"criteria": [{"criterion": 1, "tests": ["tests/test_app.py::test_invented"]},
                                            {"criterion": 2, "tests": ["tests/test_app.py"]}], "not_covered": []},
                 "does not exist": {"criteria": [{"criterion": 1, "tests": ["../elsewhere.py::t"]}, {"criterion": 2, "tests": ["tests/absent.py::t"]}],
                                    "not_covered": []},
                 "has only 2": {"criteria": [{"criterion": n, "tests": ["tests/test_app.py"]} for n in (1, 2, 3)], "not_covered": []}}
        for needle, mapping in cases.items():
            with self.subTest(needle=needle):
                gate = self.trace(mapping=mapping)
                self.assertEqual(gate["status"], qa.FAIL)
                self.assertIn(needle, gate["evidence"])

    def test_a_malformed_trace_is_refused_and_no_ticket_is_not_measured(self):
        self.change()
        for mapping in ([], {"criteria": "x", "not_covered": []}, {"criteria": [{"criterion": "1", "tests": []}], "not_covered": []},
                        {"criteria": [{"criterion": 1, "tests": [3]}], "not_covered": []}):
            with self.subTest(mapping=mapping), self.assertRaises(context.Refused):
                self.trace(mapping=mapping)
        self.assertEqual(self.gates()["criteria"]["status"], qa.UNKNOWN)


class CliTests(Case):
    def test_exit_codes_tell_failed_from_not_measured_from_passed(self):
        with self.assertRaises(context.Refused):
            qa.run_gates(self.table, self.repo, "main")          # no change
        self.change()
        code, out, _ = run(["qa", "gate", self.repo, "--base", "main"])
        self.assertEqual(code, 3)
        self.assertIn("unmeasured", out)
        self.commit("tests/test_app.py", TEST + "    @unittest.skip('x')\n    def test_other(self):\n        pass\n")
        code, out, _ = run(["qa", "gate", self.repo, "--base", "main"])
        self.assertEqual(code, 1)
        self.assertEqual(run(["qa", "gate", self.repo, "--base", "main", "--runs", "99"])[0], 2)

    def test_everything_given_and_good_exits_0(self):
        self.change()
        self.commit("tests/test_app.py", TEST + "\n    def test_discount(self):\n        from app import discount\n        self.assertEqual(discount(10), 10)\n")
        base = self.repo + "-"
        files = {"t.md": TICKET, "trace.json": json.dumps({"criteria": [{"criterion": 1, "tests": ["tests/test_app.py::test_sum"]},
                                                                           {"criterion": 2, "tests": ["tests/test_app.py::test_discount"]}],
                                                              "not_covered": []}),
                 "lcov.info": "SF:app.py\n" + "".join(f"DA:{n},1\n" for n in range(1, 9)) + "end_of_record\n"}
        for name, text in files.items():
            self.addCleanup(lambda p=base + name: os.path.exists(p) and os.remove(p))
            with open(base + name, "w", encoding="utf-8") as fh:
                fh.write(text)
        code, out, err = run(["qa", "gate", self.repo, "--base", "main", "--runs", "2", "--run",
                              f"{sys.executable} -m unittest discover -s tests", "--coverage", base + "lcov.info",
                              "--ticket", base + "t.md", "--trace", base + "trace.json"])
        self.assertEqual(code, 0, out + err)
        self.assertIn("all four gates pass", out)

    def test_the_qa_phase_serves_the_framework_convention(self):
        code, out, _ = run(["context", "qa", self.repo, "--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("several times in a row", out)


if __name__ == "__main__":
    unittest.main()
