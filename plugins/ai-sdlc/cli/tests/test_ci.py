"""Tests des portes en CI : les réglages se lisent sur la branche de base, une pull request ne peut pas
alléger ses propres portes, et le code de sortie bloque quand il le faut."""
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
    CONFIG: dict | None = {"secu": {"exclure": ["tests/secrets/**"]}, "qa": {"commande": "python3 -m unittest discover -s tests", "passages": 2}}

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
            self.write("docs/agents/portes.json", json.dumps(self.CONFIG))
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
        self.assertEqual(gates["repete"]["status"], qa.OK)
        self.assertIn("2 passages sur 2", gates["repete"]["evidence"])
        text = ci.render_md(gates["_"])
        self.assertIn("rien en échec", text)   # la porte scanner reste non mesurée sans rapport
        self.assertIn("ni la revue", text)

    def test_a_secret_a_skipped_test_or_a_red_suite_blocks(self):
        cases = {"secrets": ("app/conf.py", f'CLE = "{AWS}"\n'),
                 "desactives": ("tests/test_calc.py", "import unittest\nfrom app.calc import double\n\n\nclass T(unittest.TestCase):\n"
                                                      "    @unittest." + "skip('plus tard')\n    def test_double(self):\n        self.assertEqual(double(2), 4)\n"),
                 "repete": ("app/calc.py", "def double(x):\n    return 3 * x\n")}
        for gate, (rel, text) in cases.items():
            with self.subTest(gate=gate):
                self.setUp()
                self.write(rel, text)
                self.commit()
                result = self.run_ci()["_"]
                self.assertIn(gate, result["failed"])
                self.assertFalse(result["pass"])
                self.assertIn("La fusion est bloquée", ci.render_md(result))
                self.assertNotIn(AWS, ci.render_md(result))

    def test_unmeasured_blocks_only_when_the_repo_asks_for_it(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        self.assertTrue(self.run_ci()["_"]["pass"])
        strict = self.run_ci(strict=True)["_"]
        self.assertFalse(strict["pass"])
        self.assertIn("les exige mesurées", ci.render_md(strict))

    def test_the_pipeline_tools_left_beside_the_code_do_not_stop_the_gates(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        self.write(".ai-sdlc/outil.py", "x = 1\n")   # le plugin récupéré par le pipeline, non suivi
        self.assertTrue(self.run_ci()["_"]["pass"])


class BaseBranchTests(Case):
    def test_a_folder_put_out_of_reading_on_the_base_branch_is_skipped_and_said(self):
        self.write("tests/secrets/faux.py", f'CLE = "{AWS}"\n')
        self.commit()
        result = self.run_ci()["_"]
        self.assertTrue(result["pass"])
        self.assertEqual(result["excluded"], ["tests/secrets/faux.py"])
        self.assertIn("Hors lecture", ci.render_md(result))
        self.assertIn("1 fichier(s) hors lecture.", ci.render_md(result).splitlines()[0])   # dit dès le titre

    def test_a_test_about_skipping_can_be_put_out_of_the_disabled_gate_from_the_base_branch_only(self):
        skipped = ("import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest." + "skip('exemple')\n    def test_x(self):\n"
                   "        self.assertTrue(True)\n")
        self.write("tests/test_exemples.py", skipped)
        self.commit()
        self.assertIn("desactives", self.run_ci()["_"]["failed"])
        git(self.repo, "checkout", "-q", "main")
        self.write("docs/agents/portes.json", json.dumps({**self.CONFIG, "qa": {**self.CONFIG["qa"], "exclure": ["tests/test_exemples.py"]}}))
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")
        result = self.run_ci()["_"]
        self.assertNotIn("desactives", result["failed"])
        self.assertIn("tests/test_exemples.py", result["excluded"])

    def test_a_pull_request_cannot_loosen_its_own_gates(self):
        self.write("docs/agents/portes.json", json.dumps({"secu": {"exclure": ["app/**"]}, "qa": {}}))
        self.write("app/conf.py", f'CLE = "{AWS}"\n')
        self.write("app/calc.py", "def double(x):\n    return 3 * x\n")
        self.commit()
        result = self.run_ci()["_"]
        self.assertIn("secrets", result["failed"])   # l'exclusion écrite par la PR n'est pas lue
        self.assertIn("repete", result["failed"])    # la commande retirée par la PR est encore jouée
        self.assertEqual(result["excluded"], [])

    def test_a_secret_added_then_removed_in_an_excluded_file_only_is_out_but_elsewhere_is_seen(self):
        self.write("app/conf.py", f'CLE = "{AWS}"\n')
        self.commit()
        self.write("app/conf.py", "CLE = None\n")
        self.commit()
        self.assertIn("secrets", self.run_ci()["_"]["failed"])   # l'historique de la branche se lit aussi en CI


class ConfigTests(Case):
    CONFIG = None

    def set_config(self, value) -> None:
        git(self.repo, "checkout", "-q", "main")
        self.write("docs/agents/portes.json", value if isinstance(value, str) else json.dumps(value))
        self.commit()
        git(self.repo, "checkout", "-q", "pr")
        git(self.repo, "merge", "-q", "main")

    def test_without_settings_the_suite_is_not_replayed_and_the_summary_says_so(self):
        self.write("app/calc.py", "def double(x):\n    return x + x\n")
        self.commit()
        gates = self.run_ci()
        self.assertNotIn("repete", gates)
        self.assertIn("ne donne pas de commande", ci.render_md(gates["_"]))

    def test_settings_that_put_everything_out_of_reading_or_are_malformed_are_refused(self):
        for bad in ({"secu": {"exclure": ["**"]}}, {"secu": {"exclure": ["*"]}}, {"secu": {"exclure": ["**/*.py"]}}, {"secu": {"exclure": ["/etc/**"]}},
                    {"secu": {"exclure": "tests/**"}}, {"secu": {"exclure": ["a/**"] * 21}}, {"secu": {"ignorer": []}}, {"autre": 1}, [], {"qa": {"exclure": ["**/test_*.py"]}}, {"qa": {"exclure": "tests/**"}},
                    {"qa": {"passages": 0}}, {"qa": {"passages": True}}, {"qa": {"commande": ""}}, {"qa": {"commande": 3}}, "{"):
            with self.subTest(bad=str(bad)[:40]):
                self.setUp()
                self.set_config(bad)
                self.write("app/calc.py", "def double(x):\n    return x + x\n")
                self.commit()
                with self.assertRaises(context.Refused):
                    self.run_ci()


class CliAndRepoTests(Case):
    def test_exit_codes_and_the_job_summary(self):
        summary = os.path.join(self.tmp.name, "resume.md")
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
            self.assertIn("### Portes", fh.read())
        self.write("app/conf.py", f'CLE = "{AWS}"\n')
        self.commit()
        code, out = call()
        self.assertEqual(code, 1)
        self.assertNotIn(AWS, out)
        git(self.repo, "checkout", "-q", "main")
        self.assertEqual(call()[0], 2)   # sur la branche de base elle-même : rien à vérifier

    def test_this_repository_settings_and_pipeline_files_hold_together(self):
        with open(os.path.join(ROOT, "docs", "agents", "portes.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertTrue(config["qa"]["commande"])
        for glob in config["secu"]["exclure"]:
            self.assertNotIn(glob, ci._TOO_WIDE)
        with open(os.path.join(ROOT, "scripts", "ci", "verifier.sh"), encoding="utf-8") as fh:
            script = fh.read()
        for expected in ("discover -s cli/tests", "discover -s plugins/ai-sdlc/cli/tests", "progress check", "ci pr"):
            self.assertIn(expected, script)
        for workflow in (".github/workflows/ci.yml", ".forgejo/workflows/ci.yml"):
            with open(os.path.join(ROOT, workflow), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("sh scripts/ci/verifier.sh", text)          # le YAML ne porte pas la logique
            self.assertIn("runs-on: [self-hosted, jre-server]", text)  # dépôt privé : jamais un runner facturé
            self.assertNotIn("ubuntu-latest", text)
            self.assertIn("fetch-depth: 0", text)
            self.assertIn("persist-credentials: false", text)
            self.assertIn("path: .cible", text)                        # les portes se jouent avec le code de la branche cible
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            self.assertIn("head.repo.full_name == github.repository", fh.read())   # jamais une PR de fork sur ce runner
        with open(os.path.join(ROOT, "plugins", "ai-sdlc", "ci", "portes.yml"), encoding="utf-8") as fh:
            template = fh.read()
        run_lines = [line for line in template.splitlines() if "ai_sdlc.py ci pr" in line]
        self.assertTrue(run_lines and all("${{" not in line for line in run_lines))   # un nom de branche n'entre pas dans une ligne de shell


if __name__ == "__main__":
    unittest.main()
