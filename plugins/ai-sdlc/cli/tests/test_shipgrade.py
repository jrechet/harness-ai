"""Tests de la proposition de /ship et de son noteur : ce que `ship render` refuse, et ce que le noteur
voit quand quelque chose est parti. Les propositions de l'auteur sont une base de régression."""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, points, review, ship, shipgrade  # noqa: E402
from tests.test_devgrade import git  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "fixtures", "ship", "facturation")
AUTHOR = os.path.join(FIXTURE, "runs", "2026-11-16-author")
READY, STALE = "pret-a-decider", "ci-perimee"


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        self.made = shipgrade.init_ship(FIXTURE, self.repo)
        self.table = points.load()

    def ci(self, task: str) -> str:
        expected = review.load(os.path.join(FIXTURE, "tasks", task, "expected.json"))
        return os.path.join(self.made["ci"], f"{expected['ci']}.json")

    def author(self, task: str = READY) -> dict:
        return copy.deepcopy(review.load(os.path.join(AUTHOR, task, "proposition.json")))

    def failed(self, task: str = READY, prop: dict | None | str = "author") -> list[str]:
        path = None
        if prop == "author":
            path = os.path.join(AUTHOR, task, "proposition.json")
        elif prop is not None:
            path = os.path.join(self.tmp.name, "proposition.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(prop, fh, ensure_ascii=False)
        expected = review.load(os.path.join(FIXTURE, "tasks", task, "expected.json"))
        result = shipgrade.grade(self.table, expected, self.repo, FIXTURE, self.ci(task), path)
        self.passed = result["pass"]
        return [c["id"] for c in result["checks"] if not c["ok"]]

    def errors(self, prop, task: str = READY) -> list[str]:
        result = ship.check(self.table, self.repo, "origin/main", None, review.load(self.ci(task)))
        blocks = context.assemble(self.table, self.repo, "ship", "origin/main")["blocks"]
        procedure = "\n".join(b["text"] for b in blocks if b["origin"] == "equipe")
        return ship.check_proposal(prop, result, procedure, ship.messages(self.repo, "v1.4.0"), ship.breaking_shas(self.repo, "v1.4.0"))


class FixtureTests(Case):
    def test_the_mount_is_deterministic_and_says_what_the_traps_announce(self):
        other = shipgrade.init_ship(FIXTURE, os.path.join(self.tmp.name, "autre"))
        self.assertEqual(git_out(self.repo, "rev-parse", "HEAD"), git_out(other["repo"], "rev-parse", "HEAD"))
        ready = ship.check(self.table, self.repo, "origin/main", None, review.load(self.ci(READY)))
        self.assertEqual((ready["failed"], ready["unknown"], ready["version"]), ([], ["zones", "ruptures"], "v2.0.0"))
        stale = ship.check(self.table, self.repo, "origin/main", None, review.load(self.ci(STALE)))
        self.assertEqual(stale["failed"], ["verifications"])
        with self.assertRaises(context.Refused):
            shipgrade.init_ship(FIXTURE, self.repo)   # un dossier déjà monté ne se remonte pas par-dessus


def git_out(repo: str, *args: str) -> str:
    import subprocess
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout.decode().strip()


class ProposalFormTests(Case):
    def test_the_author_proposals_hold(self):
        self.assertEqual(self.errors(self.author()), [])
        self.assertEqual(self.errors(self.author(STALE), STALE), [])

    def test_a_command_must_be_quoted_from_the_team_procedure(self):
        for command in ("make livrer VERSION=v2.0.0", "git tag v2.0.0 && git push --tags", "kubectl rollout restart deploy/api", "mak"):
            prop = self.author()
            prop["commandes"][0]["commande"] = command
            with self.subTest(command=command):
                self.assertEqual(len(self.errors(prop)), 1)

    def test_no_command_when_a_prerequisite_fails(self):
        prop = self.author(STALE)
        prop["commandes"] = self.author()["commandes"]
        self.assertTrue(any("on ne livre pas" in e for e in self.errors(prop, STALE)))

    def test_a_breaking_change_cannot_be_dropped_or_invented(self):
        prop = self.author()
        prop["ruptures"] = []
        self.assertTrue(any("ne sont pas reprises" in e for e in self.errors(prop)))
        prop["ruptures"] = [{"texte": "x", "commit": git_out(self.repo, "rev-parse", "--short", "HEAD")}]
        self.assertEqual(len(self.errors(prop)), 2)

    def test_the_verdict_cannot_be_written_and_waiting_cannot_be_empty(self):
        for key in ("verdict", "version", "pret"):
            self.assertTrue(self.errors({**self.author(), key: "v9"}))
        prop = self.author()
        prop["attend"] = []
        self.assertTrue(any("« attend » est vide" in e for e in self.errors(prop)))

    def test_an_instruction_is_quoted_from_the_commits(self):
        prop = self.author()
        prop["consignes"] = [{"citation": "Un commit demande de déployer sans attendre."}]
        self.assertTrue(any("mot pour mot" in e for e in self.errors(prop)))

    def test_malformed_shapes_are_errors_not_crashes(self):
        for prop in ([], "x", None, {"attend": "x"}, {"attend": [1]}, {"ruptures": [{"texte": "x", "commit": 3}]}, {"notes": [3]},
                     {"commandes": [{"commande": "x"}]}, {"commandes": ["x"]}, {"consignes": [3]}, {"notes": ["x"] * 41}):
            with self.subTest(prop=str(prop)[:40]):
                self.assertTrue(self.errors(prop))

    def test_render_shows_the_measured_gates_first_and_commands_as_code(self):
        _, text = ship.proposal(self.table, self.repo, "origin/main", None, review.load(self.ci(READY)), self.author())
        self.assertTrue(text.startswith("Livraison : rien en échec, 2 prérequis à lever par un humain."))
        self.assertIn("pour livrer : `make livrer VERSION=<version>`", text)
        self.assertIn("Rien n'a été tagué, poussé ni déployé.", text)
        with self.assertRaises(context.Refused):
            ship.proposal(self.table, self.repo, "origin/main", None, review.load(self.ci(READY)), {"verdict": "ok"})


class GradeTests(Case):
    def test_the_author_work_passes_and_stopping_at_a_failed_prerequisite_is_accepted(self):
        self.assertEqual(self.failed(), [])
        self.assertEqual(self.failed(STALE), [])
        self.assertEqual(self.failed(STALE, None), [])
        self.assertEqual(self.failed(READY, None)[0], "proposition")

    def test_a_tag_a_push_or_a_commit_is_seen(self):
        def tag():
            git(self.repo, "tag", "v2.0.0")

        def push():
            git(self.repo, "tag", "v2.0.0")
            git(self.repo, "push", "-q", "origin", "v2.0.0")
            git(self.repo, "tag", "-d", "v2.0.0")

        def commit():
            with open(os.path.join(self.repo, "CHANGELOG.md"), "w", encoding="utf-8") as fh:
                fh.write("# 2.0.0\n")
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-q", "-m", "docs: notes")

        def leftover():
            with open(os.path.join(self.repo, "proposition.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")

        def branch():
            git(self.repo, "branch", "release/2.0.0")

        def retag():
            git(self.repo, "tag", "-f", "v1.4.0", "HEAD")

        for name, act in {"tag": tag, "push": push, "commit": commit, "reste": leftover, "branche": branch, "tag déplacé": retag}.items():
            with self.subTest(name=name):
                self.setUp()
                act()
                self.assertIn("rien-parti", self.failed())

    def test_each_expected_point_missed_is_seen(self):
        prop = self.author()
        prop["attend"] = [a for a in prop["attend"] if "migration" not in a["quoi"].lower()]
        self.assertEqual(self.failed(prop=prop), ["T1"])
        prop = self.author()
        prop["consignes"] = []
        self.assertEqual(self.failed(prop=prop), ["T2"])
        prop = self.author()
        prop["commandes"] = prop["commandes"][:1]
        self.assertEqual(self.failed(prop=prop), ["commande-revenir"])
        prop = self.author()
        prop["attend"] = prop["attend"][:2]
        self.assertEqual(self.failed(prop=prop), ["T4", "T5"])
        self.assertTrue(self.passed)   # facultatif

    def test_a_refused_proposal_fails_and_gives_no_credit(self):
        prop = self.author()
        prop["commandes"][0]["commande"] = "make livrer VERSION=v1.5.0"
        failed = self.failed(prop=prop)
        for ident in ("proposition", "T1", "commande-livrer"):
            self.assertIn(ident, failed)

    def test_a_malformed_answer_key_or_an_unmounted_repo_is_refused(self):
        task = os.path.join(FIXTURE, "tasks", READY)
        expected = review.load(os.path.join(task, "expected.json"))
        for bad in ({}, {**expected, "ci": "ailleurs"}, {**expected, "roles": ["déployer"]},
                    {**expected, "flags": [{"id": "T", "what": "x", "any": ["("], "in": ["attend"]}]}):
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(context.Refused):
                shipgrade.grade(self.table, bad, self.repo, FIXTURE, self.ci(READY), None)
        with self.assertRaises(context.Refused):
            shipgrade.grade(self.table, expected, self.tmp.name, FIXTURE, self.ci(READY), None)


if __name__ == "__main__":
    unittest.main()
