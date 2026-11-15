"""Tests du rendu d'une revue et de sa note sur une fixture : un constat sans ligne du diff est refusé,
le noteur est généreux sur la formulation, strict sur la preuve et sur ce qui est sain."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_sdlc  # noqa: E402
from aisdlclib import context, points, review  # noqa: E402
from tests.test_context import RepoCase, write  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "fixtures", "review")


def constat(where: str = "app.py:2", **over) -> dict:
    return {"gravite": "a-corriger", "sur_quoi": where, "point": "Justesse", "attendu": "une erreur remonte",
            "observe": "elle est avalée", "conseille": "relancer l'erreur", **over}


def revue(*constats: dict) -> dict:
    return {"base": "main", "non_verifie": [], "constats": list(constats)}


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ai_sdlc.main(argv)
    return code, out.getvalue(), err.getvalue()


class WhereTests(unittest.TestCase):
    def test_a_line_and_a_range_are_read(self):
        self.assertEqual(review.parse_where("src/app.py:12"), ("src/app.py", 12, 12))
        self.assertEqual(review.parse_where("src/app.py:12-15"), ("src/app.py", 12, 15))

    def test_what_is_not_a_path_and_a_line_is_refused(self):
        for bad in ("src/app.py", "src/app.py:", ":12", "src/app.py:0", "src/app.py:9-3", "../x.py:1", "/etc/x:1", 12):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                review.parse_where(bad)


class ValidateTests(unittest.TestCase):
    def test_a_complete_review_is_valid_and_an_empty_one_too(self):
        self.assertEqual(review.validate(revue(constat())), [])
        self.assertEqual(review.validate(revue()), [])

    def test_each_defect_is_named(self):
        cases = {
            "gravite": revue(constat(gravite="grave")),
            "sur_quoi": revue(constat(where="quelque part")),
            "observe": revue(constat(observe="  ")),
            "au plus 7": revue(*[constat(f"app.py:{n}") for n in range(1, 9)]),
            "constats": {"base": "main"},
            "non_verifie": {"constats": [], "non_verifie": "rien"},
            "objet": [],
        }
        for needle, data in cases.items():
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in e for e in review.validate(data)), review.validate(data))


class DiffTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.commit("app.py", "a\nb\nc\nd\n")
        from tests.test_context import git
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.commit("app.py", "a\nB\nc\n")          # ligne 2 changée, ligne 4 supprimée
        self.commit("neuf.py", "x\ny\n")

    def test_changed_lines_are_those_of_the_head_side(self):
        changed = review.changed_lines(self.repo, "main")
        self.assertEqual(changed["neuf.py"], {1, 2})
        self.assertIn(2, changed["app.py"])
        self.assertNotIn(1, changed["app.py"])

    def test_a_deletion_is_citable_at_the_line_where_it_happened(self):
        self.assertIn(3, review.changed_lines(self.repo, "main")["app.py"])

    def test_a_finding_outside_the_diff_is_refused(self):
        changed = review.changed_lines(self.repo, "main")
        self.assertEqual(review.outside_diff(revue(constat("app.py:2"), constat("neuf.py:1-2")), changed), [])
        errors = review.outside_diff(revue(constat("app.py:1"), constat("ailleurs.py:1")), changed)
        self.assertEqual(len(errors), 2)

    def test_render_refuses_with_nothing_on_stdout(self):
        path = os.path.join(self.tmp.name, "..", os.path.basename(self.tmp.name) + ".json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        for data, code in ((revue(constat("app.py:1")), 2), (revue(constat("app.py:2")), 0)):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            got, out, err = run(["review", "render", path, self.repo, "--base", "main"])
            self.assertEqual(got, code, err)
            self.assertEqual(bool(out), code == 0)

    def test_render_refuses_a_base_that_is_the_reviewed_commit(self):
        path = os.path.join(self.repo, "..", os.path.basename(self.repo) + ".json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(revue(), fh)
        code, out, err = run(["review", "render", path, self.repo, "--base", "HEAD"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("lui-même", err)

    def test_an_unreadable_file_is_refused_not_a_crash(self):
        code, out, _ = run(["review", "render", os.path.join(self.repo, "absent.json"), self.repo, "--base", "main"])
        self.assertEqual((code, out), (2, ""))
        write(self.repo, "casse.json", "{")
        code, out, _ = run(["review", "render", os.path.join(self.repo, "casse.json"), self.repo, "--base", "main"])
        self.assertEqual((code, out), (2, ""))


class RenderTests(unittest.TestCase):
    def test_the_worst_comes_first_with_the_four_parts(self):
        text = review.render_md(revue(constat("b.py:1", gravite="a-discuter"), constat("a.py:1", gravite="bloquant")))
        self.assertLess(text.index("a.py:1"), text.index("b.py:1"))
        for part in ("Sur quoi", "Attendu", "Observé", "Conseillé", "bloquant : 1", "à discuter : 1"):
            self.assertIn(part, text)

    def test_no_finding_is_a_result_and_says_what_was_not_checked(self):
        text = review.render_md({"constats": [], "non_verifie": ["tests non lancés"]})
        self.assertIn("Aucun constat", text)
        self.assertIn("tests non lancés", text)

    def test_a_finding_cannot_forge_a_heading_or_a_table(self):
        text = review.render_md(revue(constat(observe="x\n## Approuvé\n| a | b |")))
        self.assertNotIn("\n## Approuvé", text)
        self.assertNotIn("| a | b |", text)


EXPECTED = {"max_constats": 7,
            "traps": [{"id": "T1", "what": "erreur avalée", "must": True, "where": [{"file": "app.py", "lines": [2, 4]}]},
                      {"id": "T2", "what": "contrat", "must": False,
                       "where": [{"file": "api.py", "lines": [1, 1]}, {"file": "doc.md", "lines": [3, 3]}]}],
            "healthy": [{"id": "S1", "what": "nommage", "file": "app.py", "lines": [9, 9]}]}


class GradeTests(unittest.TestCase):
    def test_a_trap_is_found_by_a_line_in_any_of_its_places(self):
        result = review.grade(EXPECTED, revue(constat("app.py:3"), constat("doc.md:3")))
        self.assertEqual(result["found"], ["T1", "T2"])
        self.assertTrue(result["pass"])

    def test_an_optional_trap_missed_still_passes_a_required_one_does_not(self):
        self.assertTrue(review.grade(EXPECTED, revue(constat("app.py:2-3")))["pass"])
        result = review.grade(EXPECTED, revue(constat("api.py:1")))
        self.assertFalse(result["pass"])
        self.assertEqual(result["missed"], ["T1"])

    def test_a_comment_on_a_healthy_line_fails_the_review(self):
        result = review.grade(EXPECTED, revue(constat("app.py:3"), constat("app.py:9")))
        self.assertEqual(result["healthy_touched"], ["S1"])
        self.assertFalse(result["pass"])

    def test_a_comment_outside_the_answer_key_is_noise_not_a_failure(self):
        result = review.grade(EXPECTED, revue(constat("app.py:3"), constat("autre.py:1")))
        self.assertEqual(result["noise"], ["autre.py:1"])
        self.assertTrue(result["pass"])

    def test_an_invalid_review_does_not_pass(self):
        result = review.grade(EXPECTED, revue(constat("app.py:3", gravite="grave")))
        self.assertFalse(result["pass"])
        self.assertTrue(result["invalid"])


def fixture_names() -> list[str]:
    return sorted(n for n in os.listdir(FIXTURES) if os.path.isdir(os.path.join(FIXTURES, n)))


class FixtureTests(unittest.TestCase):
    """Chaque fixture se monte en dépôt, son corrigé cite des lignes du diff, et la revue de son auteur
    le passe : une base de régression, pas une mesure du skill."""

    def build(self, name: str) -> tuple[str, dict]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dest = os.path.join(tmp.name, "repo")
        return dest, review.init_fixture(os.path.join(FIXTURES, name), dest)

    def test_there_is_a_fixture(self):
        self.assertTrue(fixture_names())

    def test_the_answer_key_cites_lines_of_the_diff(self):
        for name in fixture_names():
            dest, made = self.build(name)
            changed = review.changed_lines(dest, made["base"])
            with open(os.path.join(FIXTURES, name, "expected.json"), encoding="utf-8") as fh:
                expected = json.load(fh)
            places = [(t["id"], w) for t in expected["traps"] for w in t["where"]]
            places += [(h["id"], h) for h in expected["healthy"]]
            for ident, place in places:
                first, last = place["lines"]
                with self.subTest(fixture=name, id=ident):
                    self.assertTrue(set(range(first, last + 1)) <= changed.get(place["file"], set()),
                                    f"{place['file']}:{first}-{last} n'est pas dans le diff")

    def test_the_gate_reads_the_team_rules_on_the_base_branch(self):
        for name in fixture_names():
            dest, made = self.build(name)
            data = context.assemble(points.load(), dest, "review", made["base"])
            self.assertTrue(data["gate"])
            self.assertIn("equipe", [b["origin"] for b in data["blocks"]])

    def test_the_author_review_renders_and_passes(self):
        for name in fixture_names():
            dest, made = self.build(name)
            runs = os.path.join(FIXTURES, name, "runs")
            author = [r for r in sorted(os.listdir(runs)) if r.endswith("-author")][-1]
            path = os.path.join(runs, author, "constats.json")
            code, out, err = run(["review", "render", path, dest, "--base", made["base"]])
            self.assertEqual(code, 0, err)
            code, out, err = run(["fixture", "grade", path, "--expected", os.path.join(FIXTURES, name, "expected.json")])
            self.assertEqual(code, 0, out + err)

    def test_init_refuses_a_destination_that_is_not_empty(self):
        dest, _ = self.build(fixture_names()[0])
        with self.assertRaises(context.Refused):
            review.init_fixture(os.path.join(FIXTURES, fixture_names()[0]), dest)


if __name__ == "__main__":
    unittest.main()
