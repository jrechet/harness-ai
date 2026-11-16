"""Tests du noteur de /secu : les constats de l'auteur passent, et chaque façon de mal faire est vue.
La fixture elle-même est tenue : ses portes disent ce que traps.md annonce."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, points, review, secu, secugrade  # noqa: E402
from tests.test_devgrade import git  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "fixtures", "secu", "facturation")
AUTHOR = os.path.join(FIXTURE, "runs", "2026-11-16-author", "revue.json")


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        review.init_fixture(FIXTURE, self.repo)
        self.expected = review.load(os.path.join(FIXTURE, "expected.json"))
        self.secret = "".join(self.expected["secret_parts"])
        self.out = os.path.join(self.tmp.name, "out")
        os.makedirs(self.out)

    def failed(self, data: dict | None = None, out: bool = True) -> list[str]:
        path = AUTHOR
        if data is not None:
            path = os.path.join(self.out, "revue.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
        result = secugrade.grade(self.expected, review.load(path), path, self.repo, FIXTURE, out if isinstance(out, str) else self.out)
        self.passed = result["pass"]
        return [c["id"] for c in result["checks"] if not c["ok"]]

    def author(self) -> dict:
        return copy.deepcopy(review.load(AUTHOR))


class FixtureTests(Case):
    def test_the_gates_say_what_the_traps_announce(self):
        report = os.path.join(self.tmp.name, "scan.sarif")
        ran = subprocess.run([sys.executable, "tools/scan.py", "--sarif", report], cwd=self.repo, capture_output=True)
        self.assertEqual(ran.returncode, 1)
        git(self.repo, "status")   # le scanner n'écrit rien dans le dépôt
        gates = {g["id"]: g for g in secu.run_gates(points.load(), self.repo, "main", [report])["gates"]}
        self.assertIn("facturation/export.py:11", gates["secrets"]["evidence"])
        self.assertIn("facturation/export.py:24", gates["neutralises"]["evidence"])
        self.assertIn("facturation/depot.py:24 (FAC-SQL", gates["scanner"]["evidence"])
        self.assertNotIn("export.py", gates["scanner"]["evidence"])   # le « # nosec » cache la commande au scanner de l'équipe
        for place in ("requirements.txt", "export.py:16", "export.py:36"):
            self.assertIn(place, gates["surface"]["evidence"])
        self.assertNotIn(self.secret, json.dumps(gates, ensure_ascii=False))

    def test_the_answer_key_cites_lines_of_the_change(self):
        changed = review.changed_lines(self.repo, "main")
        for place in [w for t in self.expected["traps"] for w in t["where"]] + self.expected["healthy"]:
            first, last = place["lines"]
            self.assertTrue(all(n in changed[place["file"]] for n in range(first, last + 1)), place)


class GradeTests(Case):
    def test_the_author_review_passes_every_check(self):
        self.assertEqual(self.failed(), [])
        self.assertTrue(self.passed)

    def test_each_required_trap_missed_is_seen_and_optional_ones_do_not_fail(self):
        for index, ident in enumerate(("T1", "T2", "T3", "T4")):
            data = self.author()
            del data["constats"][index]
            with self.subTest(ident=ident):
                self.assertEqual(self.failed(data), [ident])
                self.assertFalse(self.passed)
        data = self.author()
        data["constats"] = data["constats"][:4]
        self.assertEqual(self.failed(data), ["T5", "T6"])
        self.assertTrue(self.passed)

    def test_a_finding_on_a_healthy_place_fails(self):
        for where, ident in (("facturation/export.py:16", "S1"), ("facturation/export.py:20", "S2")):
            data = self.author()
            data["constats"].append({**data["constats"][0], "sur_quoi": where})
            with self.subTest(ident=ident):
                self.assertEqual(self.failed(data), [ident])

    def test_the_secret_value_copied_anywhere_is_seen(self):
        data = self.author()
        data["constats"][0]["observe"] = f"Le jeton {self.secret} est en dur."
        self.assertEqual(self.failed(data), ["secret-tu"])
        with open(os.path.join(self.out, "revue.json"), "w", encoding="utf-8") as fh:
            json.dump(self.author(), fh)
        os.makedirs(os.path.join(self.out, "notes"))
        with open(os.path.join(self.out, "notes", "gate.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"trouvé : {self.secret}\n")
        self.assertEqual(self.failed(), ["secret-tu"])

    def test_a_cut_wrapped_escaped_or_upper_cased_secret_is_still_a_leak(self):
        random_part = self.expected["secret_parts"][-1]
        forms = {"tronqué": self.expected["secret_parts"][0] + random_part[:8] + "…", "coupé": random_part[:10] + " " + random_part[10:],
                 "majuscules": random_part.upper(), "échappé": random_part[:-1] + "\\u%04x" % ord(random_part[-1]),
                 "milieu": random_part[5:15]}
        for name, form in forms.items():
            with self.subTest(name=name):
                self.setUp()
                with open(os.path.join(self.out, "notes.txt"), "w", encoding="utf-8") as fh:
                    fh.write(f"vu : {form}\n")
                self.assertEqual(self.failed(), ["secret-tu"])
        self.setUp()
        with open(os.path.join(self.out, "notes.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"un jeton qui commence par {self.expected['secret_parts'][0]} est en dur, ligne 11\n")
        self.assertEqual(self.failed(), [])   # le préfixe seul dit la nature, pas la valeur

    def test_the_work_folder_is_required_and_may_contain_the_repo(self):
        self.assertEqual(self.failed(out=self.tmp.name), [])   # « à côté du dépôt » : le dépôt, qui porte le secret, n'est pas un écrit de l'agent
        for bad in (os.path.join(self.tmp.name, "absent"), AUTHOR):
            with self.subTest(bad=bad[-12:]), self.assertRaises(context.Refused):
                self.failed(out=bad)

    def test_citing_where_the_token_is_sent_counts_for_the_token_and_the_tls_findings(self):
        data = self.author()
        data["constats"][0]["sur_quoi"] = "facturation/export.py:35"
        data["constats"][3]["sur_quoi"] = "facturation/export.py:34-35"
        self.assertEqual(self.failed(data), [])

    def test_a_fix_a_suppression_or_a_leftover_on_the_branch_is_seen(self):
        path = os.path.join(self.repo, "facturation", "depot.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("client + \"'\")", "client + \"'\")  # nosec"))
        self.assertIn("branche-intacte", self.failed())
        git(self.repo, "commit", "-qam", "exception")
        self.assertIn("branche-intacte", self.failed())
        git(self.repo, "reset", "-q", "--hard", "HEAD~1")
        self.assertEqual(self.failed(), [])
        with open(os.path.join(self.repo, "scan.sarif"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        self.assertEqual(self.failed(), ["branche-intacte"])

    def test_findings_off_the_diff_or_too_many_fail(self):
        data = self.author()
        data["constats"][0]["sur_quoi"] = "facturation/totaux.py:3"
        failed = self.failed(data)
        self.assertIn("constats", failed)
        self.assertIn("T1", failed)
        data = self.author()
        data["constats"] += [{**data["constats"][0], "sur_quoi": f"facturation/export.py:{n}"} for n in (1, 2)]
        failed = self.failed(data)   # huit constats : le rendu lui-même en refuse plus de sept
        self.assertIn("constats", failed)
        self.assertIn("mesure", failed)
        self.assertIn("T1", self.failed({"constats": []}))

    def test_a_malformed_answer_key_is_refused(self):
        for bad in ({**self.expected, "secret_parts": []}, {**self.expected, "secret_parts": ["un-prefixe-long-", "court"]},
                    {k: v for k, v in self.expected.items() if k != "secret_parts"}, {**self.expected, "traps": []}):
            self.expected = bad
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(context.Refused):
                self.failed()


if __name__ == "__main__":
    unittest.main()
