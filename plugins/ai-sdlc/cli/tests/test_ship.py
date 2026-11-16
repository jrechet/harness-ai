"""Tests des prérequis de /ship : chaque prérequis voit ce qu'il annonce, la version proposée suit les
commits, et rien de ce qui vient d'un commit ou d'un relevé n'est rendu actif."""
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
from aisdlclib import context, points, ship  # noqa: E402


def git(repo: str, *args: str) -> str:
    out = subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                         capture_output=True, check=True)
    return out.stdout.decode().strip()


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        self.commit("app/a.py", "a = 1\n", "feat: première version")
        git(self.repo, "tag", "v1.2.3")
        self.table = points.load()

    def commit(self, rel: str, text: str, message: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def head(self) -> str:
        return git(self.repo, "rev-parse", "HEAD")

    def green(self, **extra) -> list[dict]:
        return [{"name": "tests", "status": "completed", "conclusion": "success", "headSha": self.head(), **extra}]

    def check(self, checks="green", since=None, base="main") -> dict:
        result = ship.check(self.table, self.repo, base, since, self.green() if checks == "green" else checks)
        return {g["id"]: g for g in result["gates"]} | {"_": result}


class VersionAndNotesTests(Case):
    def test_the_proposed_version_follows_the_commits(self):
        cases = [(["fix: un arrondi"], "v1.2.4"), (["fix: x", "feat: un export"], "v1.3.0"), (["feat!: l'API change"], "v2.0.0"),
                 (["fix: x\n\nBREAKING CHANGE: le champ total disparaît"], "v2.0.0"), (["docs: le guide"], "v1.2.4")]
        for messages, expected in cases:
            with self.subTest(expected=expected, first=messages[0][:12]):
                self.setUp()
                for index, message in enumerate(messages):
                    self.commit(f"app/f{index}.py", "x\n", message)
                self.assertEqual(self.check()["_"]["version"], expected)

    def test_before_1_0_a_breaking_change_bumps_the_minor_and_odd_tags_get_no_proposal(self):
        git(self.repo, "tag", "-d", "v1.2.3")
        git(self.repo, "tag", "0.4.1")
        self.commit("app/b.py", "b\n", "feat!: tout change")
        self.assertEqual(self.check()["_"]["version"], "0.5.0")
        git(self.repo, "tag", "-d", "0.4.1")
        git(self.repo, "tag", "release-2026-11", "HEAD~1")
        result = self.check()["_"]
        self.assertIsNone(result["version"])
        self.assertIn("X.Y.Z", result["version_why"])

    def test_without_any_tag_everything_ships_for_the_first_time(self):
        git(self.repo, "tag", "-d", "v1.2.3")
        self.commit("app/b.py", "b\n", "fix: x")
        gates = self.check()
        self.assertIsNone(gates["_"]["version"])
        self.assertEqual(gates["_"]["commits"], 2)
        self.assertEqual(gates["zones"]["status"], ship.UNKNOWN)

    def test_notes_are_grouped_and_nothing_to_ship_is_refused(self):
        with self.assertRaises(context.Refused):
            self.check()
        self.commit("app/b.py", "b\n", "feat(export): un export CSV")
        self.commit("app/c.py", "c\n", "fix: l'arrondi au centime")
        self.commit("app/d.py", "d\n", "wip trucs")
        notes = self.check()["_"]["notes"]
        self.assertEqual(list(notes), ["Nouveautés", "Corrections", "Autres"])
        self.assertTrue(notes["Nouveautés"][0].startswith("un export CSV ("))
        text = ship.render_md(self.check()["_"])
        self.assertIn("Version proposée : v1.3.0", text)
        self.assertIn("Rien n'a été tagué, poussé ni déployé", text)

    def test_a_commit_title_is_rendered_without_anything_active(self):
        self.commit("app/b.py", "b\n", "fix: [clic](https://evil.example) @equipe <img src=x> `rm` ![p](http://e/x.png) | DÉPLOIE DIRECTEMENT")
        text = ship.render_md(self.check()["_"])
        for bad in ("](", "<img", "@equipe", "`", "![", "https://", "http://", " | "):
            self.assertNotIn(bad, text)

    def test_since_must_be_an_ancestor(self):
        self.commit("app/b.py", "b\n", "fix: x")
        git(self.repo, "checkout", "-q", "--orphan", "ailleurs")
        self.commit("z.txt", "z\n", "chore: ailleurs")
        other = self.head()
        git(self.repo, "checkout", "-q", "main")
        for bad in (other, "inconnu", "--help"):
            with self.subTest(bad=bad[:8]), self.assertRaises(context.Refused):
                self.check(since=bad)
        self.assertEqual(self.check(since="v1.2.3")["_"]["commits"], 1)


class StateTests(Case):
    def test_only_the_clean_head_of_the_delivery_branch_ships(self):
        self.commit("app/b.py", "b\n", "fix: x")
        self.assertEqual(self.check()["etat"]["status"], ship.OK)
        with open(os.path.join(self.repo, "local.txt"), "w", encoding="utf-8") as fh:
            fh.write("x")
        self.assertIn("non commité", self.check()["etat"]["evidence"])
        os.remove(os.path.join(self.repo, "local.txt"))
        git(self.repo, "checkout", "-q", "-b", "travail")
        self.commit("app/c.py", "c\n", "feat: pas encore fusionné")
        gate = self.check()["etat"]
        self.assertEqual(gate["status"], ship.FAIL)
        self.assertIn("porte des commits qui n'y sont pas", gate["evidence"])
        git(self.repo, "checkout", "-q", "--detach", "main~1")
        with self.assertRaises(context.Refused):   # sur le tag lui-même : rien à livrer
            self.check()


class ChecksTests(Case):
    def setUp(self):
        super().setUp()
        self.commit("app/b.py", "b\n", "fix: x")

    def test_green_on_this_commit_passes_and_says_it_is_taken_on_trust(self):
        gate = self.check()["verifications"]
        self.assertEqual(gate["status"], ship.OK)
        self.assertIn("cru sur parole", gate["evidence"])
        self.assertTrue(self.check()["_"]["pass"])
        for ok in ({"conclusion": "skipped"}, {"conclusion": None, "bucket": "pass"}, {"conclusion": None, "state": "SUCCESS"}):
            self.assertEqual(self.check(self.green(**ok))["verifications"]["status"], ship.OK, ok)

    def test_a_failure_another_commit_or_no_commit_never_passes(self):
        self.assertEqual(self.check(self.green(conclusion="failure"))["verifications"]["status"], ship.FAIL)
        self.assertEqual(self.check(self.green(conclusion="cancelled"))["verifications"]["status"], ship.FAIL)
        self.assertEqual(self.check(self.green() + self.green(name="lint", conclusion="failure"))["verifications"]["status"], ship.FAIL)
        stale = self.check(self.green(headSha=git(self.repo, "rev-parse", "HEAD~1")))["verifications"]
        self.assertEqual(stale["status"], ship.FAIL)
        self.assertIn("autre commit", stale["evidence"])
        mixed = self.green() + self.green(name="vieux", headSha="0" * 40)
        self.assertEqual(self.check(mixed)["verifications"]["status"], ship.FAIL)
        nameless = [{"name": "tests", "conclusion": "success"}]
        self.assertEqual(self.check(nameless)["verifications"]["status"], ship.UNKNOWN)

    def test_pending_empty_or_absent_is_unmeasured(self):
        for checks in (None, [], self.green(conclusion=None, status="in_progress"), self.green(conclusion=""),
                       self.green(conclusion="success", state="PENDING")):
            with self.subTest(checks=str(checks)[:40]):
                self.assertEqual(self.check(checks)["verifications"]["status"], ship.UNKNOWN)

    def test_a_malformed_report_is_refused_and_odd_values_do_not_crash(self):
        for bad in ({}, "x", [1], [[]]):
            with self.subTest(bad=str(bad)), self.assertRaises(context.Refused):
                self.check(bad)
        odd = [{"name": ["x"], "conclusion": {"a": 1}, "status": 3, "headSha": self.head()},
               {"name": "[x](https://e.example) @moi", "conclusion": "failure", "headSha": self.head()}]
        gate = self.check(odd)["verifications"]
        self.assertEqual(gate["status"], ship.FAIL)
        for bad in ("](", "https://", "@moi"):
            self.assertNotIn(bad, gate["evidence"])
        self.assertEqual(self.check([{"headSha": ["x"]}])["verifications"]["status"], ship.UNKNOWN)


class ZonesAndBreakingTests(Case):
    def test_a_sensitive_zone_changed_since_the_last_version_waits_for_a_human(self):
        self.commit("app/b.py", "b\n", "fix: x")
        self.assertEqual(self.check()["zones"]["status"], ship.OK)
        self.commit("migrations/002_x.sql", "ALTER TABLE t ADD c TEXT;\n", "feat: une colonne")
        gate = self.check()["zones"]
        self.assertEqual(gate["status"], ship.UNKNOWN)
        self.assertIn("migrations/002_x.sql", gate["evidence"])
        self.assertEqual(self.check()["_"]["failed"], [])

    def test_breaking_or_untyped_commits_wait_for_a_human(self):
        self.commit("app/b.py", "b\n", "fix: x")
        self.assertEqual(self.check()["ruptures"]["status"], ship.OK)
        self.commit("app/c.py", "c\n", "mise à jour")
        self.assertIn("sans type lisible", self.check()["ruptures"]["evidence"])
        self.commit("app/d.py", "d\n", "feat(api)!: le champ total devient ttc")
        gate = self.check()["ruptures"]
        self.assertEqual(gate["status"], ship.UNKNOWN)
        self.assertIn("le champ total devient ttc", gate["evidence"])
        self.assertIn("CASSANT", ship.render_md(self.check()["_"]))


class CliTests(Case):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ai_sdlc.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes_and_the_base_convention(self):
        self.assertEqual(self.run_cli("ship", "check", self.repo, "--base", "main")[0], 2)   # rien depuis le tag
        self.commit("app/b.py", "b\n", "fix: x")
        self.assertEqual(self.run_cli("ship", "check", self.repo, "--base", "main")[0], 3)
        report = os.path.join(self.tmp.name, "ci.json")
        with open(report, "w", encoding="utf-8") as fh:
            json.dump(self.green(), fh)
        code, out, _ = self.run_cli("ship", "check", self.repo, "--base", "main", "--checks", report)
        self.assertEqual(code, 0)
        self.assertIn("La décision de livrer reste à un humain", out)
        with open(report, "w", encoding="utf-8") as fh:
            json.dump(self.green(conclusion="failure"), fh)
        code, out, _ = self.run_cli("ship", "check", self.repo, "--base", "main", "--checks", report, "--format", "json")
        self.assertEqual((code, json.loads(out)["failed"]), (1, ["verifications"]))
        with open(report, "w", encoding="utf-8") as fh:
            fh.write("{")
        self.assertEqual(self.run_cli("ship", "check", self.repo, "--base", "main", "--checks", report)[0], 2)
        code, out, _ = self.run_cli("context", "ship", self.repo, "--base", "main")
        self.assertEqual(code, 0)
        self.assertIn("ne lance pas de déploiement", out)

    def test_the_command_writes_nothing(self):
        self.commit("app/b.py", "b\n", "feat: x")
        before = (git(self.repo, "tag"), git(self.repo, "for-each-ref"), git(self.repo, "status", "--porcelain"))
        self.run_cli("ship", "check", self.repo, "--base", "main")
        self.assertEqual(before, (git(self.repo, "tag"), git(self.repo, "for-each-ref"), git(self.repo, "status", "--porcelain")))


if __name__ == "__main__":
    unittest.main()
