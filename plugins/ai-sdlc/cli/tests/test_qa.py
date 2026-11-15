"""Tests des portes de /qa : un test désactivé échoue, une suite instable échoue, la couverture se lit
d'un rapport, et chaque critère d'acceptation doit nommer un test qui existe."""
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
TEST = "import unittest\nfrom app import total\n\n\nclass T(unittest.TestCase):\n    def test_somme(self):\n        self.assertEqual(total(1, 2), 3)\n"
TICKET = "## Besoin\n" + "mot " * 20 + "\n\n## Critères d'acceptation\n1. La somme de 1 et 2 vaut 3.\n2. Une remise s'applique.\n"


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
        self.commit("app.py", SRC + "\n\ndef remise(a):\n    if a > 100:\n        return a * 0.9\n    return a\n")


class DisabledTests(Case):
    def test_an_ordinary_change_disables_nothing(self):
        self.change()
        self.assertEqual(self.gates()["desactives"]["status"], qa.OK)

    def test_each_way_of_skipping_a_test_fails(self):
        for marker in ("    @unittest.skip('instable')", "    @pytest.mark.skip", "it.skip('x', () => {})", "xit('x')", "@Disabled",
                       "t.Skip()", "#[ignore]", "        raise unittest.SkipTest('x')"):
            with self.subTest(marker=marker):
                git(self.repo, "checkout", "-q", "-B", "essai", "main")
                self.commit("tests/test_app.py", TEST + marker + "\n")
                self.assertEqual(self.gates()["desactives"]["status"], qa.FAIL)

    def test_a_deleted_test_file_fails_and_a_removed_assertion_is_said(self):
        git(self.repo, "rm", "-q", "tests/test_app.py")
        git(self.repo, "commit", "-q", "-m", "retire")
        self.assertEqual(self.gates()["desactives"]["status"], qa.FAIL)
        git(self.repo, "checkout", "-q", "-B", "essai", "main")
        self.commit("tests/test_app.py", TEST.replace("        self.assertEqual(total(1, 2), 3)\n", "        total(1, 2)\n"))
        gate = self.gates()["desactives"]
        self.assertEqual(gate["status"], qa.UNKNOWN)
        self.assertIn("tests/test_app.py", gate["evidence"])


class RepeatTests(Case):
    def test_a_suite_that_passes_every_time_is_ok(self):
        self.change()
        gate = self.gates(command=f"{sys.executable} -m unittest discover -s tests", runs=2)["repete"]
        self.assertEqual(gate["status"], qa.OK, gate["evidence"])

    def test_a_failing_or_a_flaky_suite_fails_and_no_command_is_not_measured(self):
        self.change()
        self.assertEqual(self.gates()["repete"]["status"], qa.UNKNOWN)
        self.assertEqual(self.gates(command=f"{sys.executable} -c 'raise SystemExit(1)'", runs=2)["repete"]["status"], qa.FAIL)
        flaky = ("import os,sys; p='compteur'; n=int(open(p).read()) if os.path.exists(p) else 0; "
                 "open(p,'w').write(str(n+1)); sys.exit(n % 2)")
        gate = self.gates(command=f'{sys.executable} -c "{flaky}"', runs=3)["repete"]
        self.assertEqual(gate["status"], qa.FAIL)
        self.assertIn("instable", gate["evidence"])
        os.remove(os.path.join(self.repo, "compteur"))
        self.assertEqual(self.gates(command="commande-qui-n-existe-pas", runs=1)["repete"]["status"], qa.FAIL)


class CoverageTests(Case):
    def report(self, name: str, text: str) -> str:
        path = self.repo + "-" + name
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_lcov_and_cobertura_give_the_share_of_added_lines_that_ran(self):
        self.change()       # lignes ajoutées : 5 à 8 (def, if, return, return)
        lcov = self.report("lcov.info", "SF:" + os.path.join(self.repo, "app.py") + "\nDA:1,1\nDA:2,1\nDA:5,1\nDA:6,1\nDA:7,0\nDA:8,1\nend_of_record\n")
        gate = self.gates(coverage=lcov)["couverture"]
        self.assertEqual(gate["status"], qa.FAIL)
        self.assertIn("3 lignes sur 4", gate["evidence"])
        self.assertIn("app.py:7", gate["evidence"])
        xml = ('<coverage><packages><package><classes><class filename="app.py"><lines>'
               + "".join(f'<line number="{n}" hits="1"/>' for n in range(1, 9)) + "</lines></class></classes></package></packages></coverage>")
        self.assertEqual(self.gates(coverage=self.report("cov.xml", xml))["couverture"]["status"], qa.OK)

    def test_no_report_or_a_report_about_other_files_is_not_measured(self):
        self.change()
        self.assertEqual(self.gates()["couverture"]["status"], qa.UNKNOWN)
        other = self.report("lcov.info", "SF:autre.py\nDA:1,1\nend_of_record\n")
        self.assertEqual(self.gates(coverage=other)["couverture"]["status"], qa.UNKNOWN)

    def test_a_broken_report_is_refused(self):
        self.change()
        for name, text in (("a.xml", "<coverage><class"), ("b.xml", '<!DOCTYPE x [<!ENTITY a "b">]><coverage/>')):
            with self.subTest(name=name), self.assertRaises(context.Refused):
                self.gates(coverage=self.report(name, text))
        with self.assertRaises(context.Refused):
            self.gates(coverage=self.repo + "-absent.info")


class CriteriaTests(Case):
    def trace(self, **kw) -> dict:
        return self.gates(ticket_text=TICKET, **kw)["criteres"]

    def test_each_criterion_needs_a_test_that_exists_or_a_written_reason(self):
        self.change()
        good = {"criteres": [{"critere": 1, "tests": ["tests/test_app.py::T::test_somme"]}],
                "non_couverts": [{"critere": 2, "pourquoi": "couvert par la recette manuelle"}]}
        gate = self.trace(mapping=good)
        self.assertEqual(gate["status"], qa.UNKNOWN)      # un critère sans test, même justifié, attend un humain
        full = {"criteres": [{"critere": 1, "tests": ["tests/test_app.py::test_somme"]}, {"critere": 2, "tests": ["tests/test_app.py"]}],
                "non_couverts": []}
        self.assertEqual(self.trace(mapping=full)["status"], qa.OK)

    def test_a_missing_criterion_a_test_that_does_not_exist_or_an_extra_one_fails(self):
        self.change()
        cases = {"sans test": {"criteres": [{"critere": 1, "tests": ["tests/test_app.py"]}], "non_couverts": []},
                 "introuvable": {"criteres": [{"critere": 1, "tests": ["tests/test_app.py::test_invente"]},
                                              {"critere": 2, "tests": ["tests/test_app.py"]}], "non_couverts": []},
                 "n'existe pas": {"criteres": [{"critere": 1, "tests": ["../ailleurs.py"]}, {"critere": 2, "tests": ["tests/absent.py"]}],
                                  "non_couverts": []},
                 "n'en a que 2": {"criteres": [{"critere": n, "tests": ["tests/test_app.py"]} for n in (1, 2, 3)], "non_couverts": []}}
        for needle, mapping in cases.items():
            with self.subTest(needle=needle):
                gate = self.trace(mapping=mapping)
                self.assertEqual(gate["status"], qa.FAIL)
                self.assertIn(needle, gate["evidence"])

    def test_a_malformed_trace_is_refused_and_no_ticket_is_not_measured(self):
        self.change()
        for mapping in ([], {"criteres": "x", "non_couverts": []}, {"criteres": [{"critere": "1", "tests": []}], "non_couverts": []},
                        {"criteres": [{"critere": 1, "tests": [3]}], "non_couverts": []}):
            with self.subTest(mapping=mapping), self.assertRaises(context.Refused):
                self.trace(mapping=mapping)
        self.assertEqual(self.gates()["criteres"]["status"], qa.UNKNOWN)


class CliTests(Case):
    def test_exit_codes_tell_failed_from_not_measured_from_passed(self):
        with self.assertRaises(context.Refused):
            qa.run_gates(self.table, self.repo, "main")          # aucun changement
        self.change()
        code, out, _ = run(["qa", "gate", self.repo, "--base", "main"])
        self.assertEqual(code, 3)
        self.assertIn("non mesuré", out)
        self.commit("tests/test_app.py", TEST + "    @unittest.skip('x')\n    def test_autre(self):\n        pass\n")
        code, out, _ = run(["qa", "gate", self.repo, "--base", "main"])
        self.assertEqual(code, 1)
        self.assertEqual(run(["qa", "gate", self.repo, "--base", "main", "--runs", "99"])[0], 2)

    def test_everything_given_and_good_exits_0(self):
        self.change()
        self.commit("tests/test_app.py", TEST + "\n    def test_remise(self):\n        from app import remise\n        self.assertEqual(remise(10), 10)\n")
        base = self.repo + "-"
        files = {"t.md": TICKET, "trace.json": json.dumps({"criteres": [{"critere": 1, "tests": ["tests/test_app.py::test_somme"]},
                                                                           {"critere": 2, "tests": ["tests/test_app.py::test_remise"]}],
                                                              "non_couverts": []}),
                 "lcov.info": "SF:app.py\n" + "".join(f"DA:{n},1\n" for n in range(1, 9)) + "end_of_record\n"}
        for name, text in files.items():
            self.addCleanup(lambda p=base + name: os.path.exists(p) and os.remove(p))
            with open(base + name, "w", encoding="utf-8") as fh:
                fh.write(text)
        code, out, err = run(["qa", "gate", self.repo, "--base", "main", "--runs", "2", "--run",
                              f"{sys.executable} -m unittest discover -s tests", "--coverage", base + "lcov.info",
                              "--ticket", base + "t.md", "--trace", base + "trace.json"])
        self.assertEqual(code, 0, out + err)
        self.assertIn("les quatre portes passent", out)

    def test_the_qa_phase_serves_the_framework_convention(self):
        code, out, _ = run(["context", "qa", self.repo, "--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("plusieurs fois de suite", out)


if __name__ == "__main__":
    unittest.main()
