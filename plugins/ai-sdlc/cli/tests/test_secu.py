"""Tests des portes de /secu : chaque porte voit ce qu'elle annonce, ne recopie rien de ce qu'elle lit,
et refuse proprement une entrée hostile."""
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
from aisdlclib import context, points, secu  # noqa: E402

# assemblés à l'exécution : ce fichier ne doit pas porter lui-même la forme d'un secret
AWS = "AKIA" + "IOSFODNN7" + "EXAMPLE"
GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0" * 2
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----"
PASS = "hunter2-" + "Zq9vT4mLp0Xw"


def git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, check=True)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        self.write("app/service.py", "def lire(x):\n    return x\n")
        self.write("ailleurs/y.py", "a = 1\nb = 2\nc = 3\n")
        self.commit()
        git(self.repo, "checkout", "-q", "-b", "travail")
        self.table = points.load()

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "c")

    def gates(self, reports: list[str] | None = None) -> dict:
        result = secu.run_gates(self.table, self.repo, "main", reports)
        return {g["id"]: g for g in result["gates"]} | {"_": result}

    def change(self, rel: str, text: str, reports: list[str] | None = None) -> dict:
        self.write(rel, text)
        self.commit()
        return self.gates(reports)

    def sarif(self, results: list[dict], tool: str = "semgrep", rules: list[dict] | None = None) -> str:
        path = os.path.join(self.tmp.name, f"r{len(os.listdir(self.tmp.name))}.sarif")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": "2.1.0", "runs": [{"tool": {"driver": {"name": tool, "rules": rules or []}}, "results": results}]}, fh)
        return path

    @staticmethod
    def result(uri: str, line: int | None, level: str | None = "error", rule: str = "py.sqli") -> dict:
        region = {"startLine": line} if line else {}
        item = {"ruleId": rule, "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": region}}]}
        return item | ({"level": level} if level else {})


class SecretsTests(Case):
    def test_each_known_shape_fails_and_is_never_echoed(self):
        shapes = {"aws": f'CLE = "{AWS}"', "github": f"token: {GH}", "pem": PEM, "assign": f'db_password = "{PASS}"',
                  "url": f"DSN = 'postgres://admin:{PASS}@db.interne:5432/x'", "yaml": f'api_key: "{PASS}"'}
        for name, line in shapes.items():
            with self.subTest(name=name):
                self.setUp()
                gates = self.change("app/conf.py", f"# réglages\n{line}\n")
                self.assertEqual(gates["secrets"]["status"], secu.FAIL)
                self.assertIn("app/conf.py:2", gates["secrets"]["evidence"])
                text = secu.render_md(gates["_"]) + json.dumps(gates["_"], ensure_ascii=False)
                for secret in (AWS, GH, PASS):
                    self.assertNotIn(secret, text)

    def test_placeholders_and_lookups_are_not_secrets(self):
        lines = ['password = "changeme-please-now"', 'api_key = os.environ["API_KEY_PROD_VALUE"]', 'token = "${GITHUB_TOKEN_VALUE}"',
                 'secret = "<à-remplir-par-vous>"', 'password = "xxxxxxxxxxxxxxxx"', 'token = settings.TOKEN', 'mot = "un texte ordinaire"',
                 'api_key = "example-key-not-real"', 'DSN = f"postgres://app:{mot_de_passe}@db.interne/x"',
                 'URL = "https://user:${DB_PASSWORD}@hote.example/x"', "password_field_name = 'mot_de_passe_utilisateur'"]
        gates = self.change("app/conf.py", "\n".join(lines) + "\n")
        self.assertEqual(gates["secrets"]["status"], secu.OK, gates["secrets"]["evidence"])

    def test_a_key_file_added_fails_but_an_example_does_not(self):
        self.write(".env.example", "API_KEY=\n")
        self.assertEqual(self.change("docs/x.md", "x\n")["secrets"]["status"], secu.OK)
        for name in (".env", "deploy/id_rsa", "certs/prod.pem", ".env.production"):
            with self.subTest(name=name):
                self.assertEqual(self.change(name, "x\n")["secrets"]["status"], secu.FAIL)

    def test_a_secret_already_on_the_base_branch_is_not_this_change(self):
        git(self.repo, "checkout", "-q", "main")
        self.write("app/vieux.py", f'CLE = "{AWS}"\n')
        self.commit()
        git(self.repo, "checkout", "-q", "-b", "autre")
        self.assertEqual(self.change("app/neuf.py", "x = 1\n")["secrets"]["status"], secu.OK)

    def test_a_hostile_path_or_line_does_not_break_or_inject(self):
        gates = self.change("app/a`b|<x>.py", f'k = "{AWS}"\n' + "a" * 50_000 + "\n" + "(" * 5000 + "\n")
        evidence = gates["secrets"]["evidence"]
        self.assertEqual(gates["secrets"]["status"], secu.FAIL)
        for bad in ("`", "|", "<", "\n"):
            self.assertNotIn(bad, evidence)
        self.assertIn("app/a?b??x?.py:1", evidence)


class MutedTests(Case):
    def test_an_exception_written_in_the_code_fails(self):
        for marker in ("x = run(cmd)  # nosec", "// nosemgrep: rule", "q = 1 // NOSONAR", "key = v  # gitleaks:allow",
                       "# trivy:ignore:AVD-1", "x = 1  # noqa: S608"):
            with self.subTest(marker=marker):
                self.setUp()
                self.assertEqual(self.change("app/x.py", marker + "\n")["neutralises"]["status"], secu.FAIL)

    def test_a_scanner_configuration_change_is_unmeasured(self):
        for name in (".gitleaksignore", ".semgrepignore", ".github/dependabot.yml", ".trivyignore"):
            with self.subTest(name=name):
                self.setUp()
                self.assertEqual(self.change(name, "x\n")["neutralises"]["status"], secu.UNKNOWN)

    def test_prose_that_names_a_marker_mutes_nothing(self):
        self.assertEqual(self.change("docs/secu.md", "N'écrivez jamais `# nosec` ni `nosemgrep`.\n")["neutralises"]["status"], secu.OK)

    def test_ordinary_code_is_ok(self):
        self.assertEqual(self.change("app/x.py", "x = 1  # noqa: E501\n# pas de sécurité ici\n")["neutralises"]["status"], secu.OK)


class ScannerTests(Case):
    def test_without_a_report_the_gate_is_unmeasured(self):
        gates = self.change("app/x.py", "x = 1\n")
        self.assertEqual(gates["scanner"]["status"], secu.UNKNOWN)
        self.assertEqual(gates["_"]["unknown"], ["scanner"])

    def test_a_result_on_an_added_line_fails_and_one_elsewhere_does_not(self):
        self.write("app/service.py", "def lire(x):\n    return x\n\n\ndef ecrire(x):\n    return x\n")
        self.commit()
        ok = self.sarif([self.result("app/service.py", 1), self.result("ailleurs/y.py", 3)])
        self.assertEqual(self.gates([ok])["scanner"]["status"], secu.OK)
        root = os.path.realpath(self.repo)
        for uri in ("app/service.py", "./app/service.py", f"file://{root}/app/service.py"):
            with self.subTest(uri=uri):
                gate = self.gates([ok, self.sarif([self.result(uri, 5)])])["scanner"]
                self.assertEqual(gate["status"], secu.FAIL)
                self.assertIn("app/service.py:5", gate["evidence"])

    def test_levels_default_rules_and_suppressions(self):
        self.write("app/x.py", "a = 1\nb = 2\n")
        self.commit()
        note = self.sarif([self.result("app/x.py", 1, level="note")])
        self.assertEqual(self.gates([note])["scanner"]["status"], secu.OK)
        default = self.sarif([self.result("app/x.py", 1, level=None)])
        self.assertEqual(self.gates([default])["scanner"]["status"], secu.FAIL)   # sans niveau, SARIF dit « warning »
        ruled = self.sarif([self.result("app/x.py", 1, level=None)], rules=[{"id": "py.sqli", "defaultConfiguration": {"level": "note"}}])
        self.assertEqual(self.gates([ruled])["scanner"]["status"], secu.OK)
        hushed = self.sarif([self.result("app/x.py", 1) | {"suppressions": [{"kind": "inSource"}]}])
        self.assertEqual(self.gates([hushed])["scanner"]["status"], secu.OK)
        nowhere = self.sarif([{"ruleId": "x", "level": "error"}])
        self.assertEqual(self.gates([nowhere])["scanner"]["status"], secu.UNKNOWN)
        whole_file = self.sarif([self.result("app/x.py", None)])
        self.assertEqual(self.gates([whole_file])["scanner"]["status"], secu.FAIL)

    def test_an_empty_or_malformed_report_never_passes(self):
        self.change("app/x.py", "a = 1\n")
        empty = os.path.join(self.tmp.name, "vide.sarif")
        with open(empty, "w", encoding="utf-8") as fh:
            json.dump({"runs": []}, fh)
        self.assertEqual(self.gates([empty])["scanner"]["status"], secu.UNKNOWN)
        named = '{"runs": [{"tool": {"driver": {"name": "s"}}, "results": %s}]}'
        for unnamed in ('{"runs": [{}]}', '{"runs": [{"results": []}]}', '{"runs": [{"tool": null, "results": []}]}',
                        '{"runs": [{"tool": {"driver": {"name": " "}}, "results": []}]}', '{"runs": [{"tool": {"driver": {"name": "s"}}}]}'):
            path = os.path.join(self.tmp.name, "unnamed.sarif")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(unnamed)
            with self.subTest(unnamed=unnamed):   # sans outil nommé ni liste de résultats, rien ne dit qu'un scanner a tourné
                self.assertEqual(self.gates([path])["scanner"]["status"], secu.UNKNOWN)
        for bad in ("[]", "{}", "x", '{"runs": [1]}', named % "[1]", named % '"x"', "[" * 100_000,
                    "{"):
            path = os.path.join(self.tmp.name, "bad.sarif")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(bad)
            with self.subTest(bad=bad[:30]), self.assertRaises(context.Refused):
                self.gates([path])
        with self.assertRaises(context.Refused):
            self.gates([os.path.join(self.tmp.name, "absent.sarif")])

    def test_odd_but_valid_shapes_do_not_crash(self):
        self.change("app/x.py", "a = 1\n")
        odd = os.path.join(self.tmp.name, "odd.sarif")
        with open(odd, "w", encoding="utf-8") as fh:
            json.dump({"runs": [{"tool": {"driver": {"name": "![t](https://evil.example/t.png)", "rules": [
                {"id": ["a"], "defaultConfiguration": {"level": "error"}}, {"id": {"a": 1}}, 3]}}, "results": [{"ruleId": 3, "locations": "x"}, {"locations": [3]},
                                                           {"locations": [{"physicalLocation": {"artifactLocation": {"uri": 3}, "region": {"startLine": "1"}}}]},
                                                           self.result("app/x.py\n`|<b>", 1, rule="r`|\n<i>")]}]}, fh)
        gate = self.gates([odd])["scanner"]
        self.assertEqual(gate["status"], secu.UNKNOWN)
        for bad in ("<", "[", "]", "(http", "!", "`", "|", "\n"):
            self.assertNotIn(bad, gate["evidence"])


class ReviewFindingsTests(Case):
    """Un test par constat de la relecture de sécurité du 2026-11-16."""

    def test_no_line_separator_hides_the_rest_of_a_line(self):
        for sep in ("\x0c", "\x0b", "\x1c", "\x85", "\u2028", "\r"):
            with self.subTest(sep=repr(sep)):
                self.setUp()
                gates = self.change("app/a.py", f'x = 1{sep}y = "{AWS}"\nz = 2\nw = "{GH}"\n')
                self.assertEqual(gates["secrets"]["status"], secu.FAIL)
                self.assertIn("app/a.py:1", gates["secrets"]["evidence"])
                self.assertIn("app/a.py:3", gates["secrets"]["evidence"])   # les numéros ne glissent pas

    def test_an_added_line_that_looks_like_a_diff_header_stays_a_line(self):
        gates = self.change("app/a.py", f'++ b/README.md\n@@ -1 +900 @@\nk = "{AWS}"\n')
        self.assertIn("app/a.py:3", gates["secrets"]["evidence"])

    def test_scanner_results_on_dot_paths_and_encoded_uris_are_found(self):
        self.write(".github/workflows/ci.yml", "on: push\njobs: {}\n")
        self.write("src/dir/my file.py", "a = 1\nb = 2\n")
        self.commit()
        root = os.path.realpath(self.repo)
        for uri in (".github/workflows/ci.yml", f"{root}/.github/workflows/ci.yml", "/home/runner/work/x/x/.github/workflows/ci.yml",
                    "src/dir/my%20file.py", "file:///c:/w/repo/src/dir/my%20file.py"):
            with self.subTest(uri=uri):
                self.assertEqual(self.gates([self.sarif([self.result(uri, 2)])])["scanner"]["status"], secu.FAIL)

    def test_a_result_on_a_file_the_repo_does_not_have_is_unmeasured_not_elsewhere(self):
        self.change("app/x.py", "a = 1\n")
        gate = self.gates([self.sarif([self.result("APP/X.PY", 1), self.result("inconnu/z.py", 1)])])["scanner"]
        self.assertEqual(gate["status"], secu.UNKNOWN)
        self.assertIn("2 résultat(s) dont le fichier ne se retrouve pas", gate["evidence"])

    def test_any_location_of_a_result_counts_and_a_reversed_region_too(self):
        self.change("app/x.py", "a = 1\nb = 2\n")
        two = self.result("ailleurs/y.py", 1)
        two["locations"].append(self.result("app/x.py", 2)["locations"][0])
        self.assertEqual(self.gates([self.sarif([two])])["scanner"]["status"], secu.FAIL)
        reversed_region = self.result("app/x.py", 2)
        reversed_region["locations"][0]["physicalLocation"]["region"] = {"startLine": 2, "endLine": 1}
        self.assertEqual(self.gates([self.sarif([reversed_region])])["scanner"]["status"], secu.FAIL)
        passed = self.result("app/x.py", 1) | {"kind": "pass"}
        gate = self.gates([self.sarif([passed, self.result("app/x.py", 1) | {"suppressions": [{"status": "rejected"}]}])])["scanner"]
        self.assertEqual(gate["status"], secu.OK)
        self.assertIn("1 résultat(s) écarté(s) par l'outil", gate["evidence"])

    def test_a_report_with_a_bom_is_read(self):
        self.change("app/x.py", "a = 1\n")
        path = self.sarif([self.result("app/x.py", 1)])
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
        self.assertEqual(self.gates([path])["scanner"]["status"], secu.FAIL)

    def test_a_secret_added_then_removed_or_written_in_a_commit_message_is_seen(self):
        self.write("app/a.py", f'k = "{AWS}"\n')
        self.commit()
        gates = self.change("app/a.py", "k = None\n")
        self.assertEqual(gates["secrets"]["status"], secu.FAIL)
        self.assertIn("dans l'historique de la branche", gates["secrets"]["evidence"])
        self.setUp()
        self.write("app/a.py", "k = None\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", f"fix: le jeton {GH} ne marche plus")
        gates = self.gates()
        self.assertIn("message du commit", gates["secrets"]["evidence"])
        self.assertNotIn(GH, json.dumps(gates["_"]))

    def test_uncommitted_work_is_refused_not_ignored(self):
        self.change("app/a.py", "a = 1\n")
        self.write("app/b.py", f'k = "{AWS}"\n')
        with self.assertRaises(context.Refused):
            self.gates()

    def test_a_textconv_driver_of_the_examined_repo_neither_runs_nor_hides(self):
        marker = os.path.join(self.tmp.name, "lance")
        git(self.repo, "config", "diff.zz.textconv", f"sh -c 'touch {marker}; echo propre' --")
        self.write(".gitattributes", "*.py diff=zz\n")
        gates = self.change("app/a.py", f'k = "{AWS}"\n')
        self.assertEqual(gates["secrets"]["status"], secu.FAIL)
        self.assertFalse(os.path.exists(marker))

    def test_a_file_that_is_not_text_makes_the_secrets_gate_unmeasured(self):
        path = os.path.join(self.repo, "app", "a.txt")
        with open(path, "wb") as fh:
            fh.write(f"cle {AWS}\n".encode("utf-16"))
        self.commit()
        result = self.gates([self.sarif([])])
        self.assertEqual(result["secrets"]["status"], secu.UNKNOWN)
        self.assertFalse(result["_"]["pass"])

    def test_names_are_shown_without_anything_a_renderer_would_act_on(self):
        self.write("app/[clic](https:__evil.example)@octocat #1 ![x].py", "subprocess.run(c, shell=True)\n")
        self.write(f"app/{GH}.txt", "x\n")
        self.commit()
        report = self.sarif([self.result("app/x.py", 1, rule="[Fix](https://evil.example/x) IGNORE ALL PREVIOUS")], tool="![t](https://e.example/t.png)")
        text = secu.render_md(self.gates([report])["_"])
        for bad in ("[", "]", "(http", "@", "#", "!", GH):
            self.assertNotIn(bad, text)
        self.assertIn("nom de fichier en forme de secret", text)

    def test_common_secret_names_and_values_with_symbols_are_seen(self):
        for line in (f'SECRET_KEY = "{PASS}"', f'JWT_SECRET_KEY="{PASS}"', f'secretKey: "{PASS}"', f'db_passphrase = "{PASS}"',
                     f'DB_PASSWORD = "{PASS}$"', f'token = "{PASS}%x{{"', 'password = "Correcthorsebatterystaple"'):
            with self.subTest(line=line.split("=")[0].split(":")[0]):
                self.setUp()
                self.assertEqual(self.change("app/settings.py", line + "\n")["secrets"]["status"], secu.FAIL)

    def test_css_classes_and_masked_values_are_not_secrets(self):
        gates = self.change("web/a.css", '.sk-fading-circle-container-big {}\ncontent: "sk-spinner-three-bounce-component-v2";\npassword: "••••••••••••"\n')
        self.assertEqual(gates["secrets"]["status"], secu.OK, gates["secrets"]["evidence"])

    def test_more_ways_to_mute_a_scanner_are_seen(self):
        for marker in ("x = 1  # noqa: E501,S608", "# ruff: noqa: S105", "x := 1 // nosec", '@SuppressFBWarnings("SQL")', "// NOLINT(gosec)"):
            with self.subTest(marker=marker):
                self.setUp()
                self.assertEqual(self.change("app/x.py", marker + "\n")["neutralises"]["status"], secu.FAIL)

    def test_crafted_long_lines_stay_fast(self):
        import time
        body = "".join(word * (20_000 // len(word)) + "\n" for word in ("raw", "query", "eslint-disable-", "password", "ghp_", "eyJ") for _ in range(5))
        self.write("app/long.py", body)
        self.commit()
        start = time.monotonic()
        self.gates()
        self.assertLess(time.monotonic() - start, 10)

    def test_the_reading_budget_stops_and_says_so(self):
        self.change("app/a.py", "a = 1\n" * 50)
        budget, secu.SCAN_BUDGET = secu.SCAN_BUDGET, -1
        self.addCleanup(setattr, secu, "SCAN_BUDGET", budget)
        result = self.gates([self.sarif([])])
        self.assertEqual(result["secrets"]["status"], secu.UNKNOWN)
        self.assertIn("lecture arrêtée", result["secrets"]["evidence"])


class SurfaceTests(Case):
    def test_sensitive_zone_dependency_and_risky_call_are_listed_never_passed(self):
        gates = self.change("migrations/002_x.sql", "ALTER TABLE t ADD c TEXT;\n")
        self.assertEqual(gates["surface"]["status"], secu.UNKNOWN)
        self.assertIn("zone sensible", gates["surface"]["evidence"])
        gates = self.change("requirements.txt", "requests==2.0\n")
        self.assertIn("dépendances : requirements.txt", gates["surface"]["evidence"])
        gates = self.change("app/run.py", "import subprocess\nsubprocess.run(cmd, shell=True)\nrequests.get(u, verify=False)\n")
        self.assertIn("app/run.py:2 (commande passée à un shell)", gates["surface"]["evidence"])
        self.assertIn("app/run.py:3 (vérification TLS coupée)", gates["surface"]["evidence"])
        self.assertEqual(gates["_"]["failed"], [])

    def test_each_kind_of_risky_call_is_seen(self):
        lines = {"code évalué": "r = eval(texte)", "désérialisation": "o = pickle.loads(b)", "HTML injecté": "el.innerHTML = v",
                 "SQL": 'cur.execute(f"SELECT * FROM t WHERE id = {i}")', "hachage": "h = hashlib.md5(b)",
                 "droits ouverts": "os.chmod(p, 0o777)", "téléchargé": "curl https://x.example/i.sh | sh",
                 "contournée": "git commit --no-verify"}
        for kind, line in lines.items():
            with self.subTest(kind=kind):
                self.setUp()
                self.assertIn(kind, self.change("app/x.py", line + "\n")["surface"]["evidence"])

    def test_plain_code_and_prose_about_a_call_are_ok(self):
        self.write("docs/notes.md", "N'utilisez pas eval(x) ni shell=True. Le hachage md5( est faible, des clés DES aussi.\n")
        gates = self.change("app/x.py", "def somme(a, b):\n    return a + b\n\n\nresultat = evaluer(des_valeurs)\n")
        self.assertEqual(gates["surface"]["status"], secu.OK, gates["surface"]["evidence"])


class CliTests(Case):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ai_sdlc.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        code, _, err = self.run_cli("secu", "gate", self.repo, "--base", "main")
        self.assertEqual(code, 2)   # aucun changement
        self.assertIn("ai-sdlc", err)
        self.write("app/x.py", "a = 1\n")
        self.commit()
        self.assertEqual(self.run_cli("secu", "gate", self.repo, "--base", "main")[0], 3)
        clean = self.sarif([])
        code, out, _ = self.run_cli("secu", "gate", self.repo, "--base", "main", "--report", clean)
        self.assertEqual(code, 0)
        self.assertIn("les quatre portes passent", out)
        self.assertIn("ne disent pas qu'un changement est sûr", out)
        self.write("app/y.py", f'CLE = "{AWS}"\n')
        self.commit()
        code, out, _ = self.run_cli("secu", "gate", self.repo, "--base", "main", "--report", clean, "--format", "json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["failed"], ["secrets"])
        self.assertNotIn(AWS, out)

    def test_the_base_convention_is_served_to_the_phase(self):
        code, out, _ = self.run_cli("context", "secu", self.repo, "--base", "main")
        self.assertEqual(code, 0)
        self.assertIn("Secrets.", out)


if __name__ == "__main__":
    unittest.main()
