"""Tests de la taille d'un changement et du corps de PR de /dev : la taille vient de règles, les zones
sensibles se lisent sur la branche de base, et un corps incomplet pour sa taille n'est pas rendu."""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, dev, points, size  # noqa: E402
from tests.test_context import RepoCase, git  # noqa: E402
from tests.test_review import run  # noqa: E402

ZONES = "---\npoint: zones-sensibles\nmode: ajoute\n---\n- `facturation/**`, `prix.py` — l'argent du client. (non vérifiée) [2026-05]\n"


def body(**over) -> dict:
    return {"titre": "fix: arrondi", "ticket": "FAC-1", "quoi": ["l'arrondi se fait au centime"],
            "pourquoi": "les totaux étaient faux", "plan": ["corriger", "tester"],
            "verifie": [{"commande": "python3 -m unittest", "resultat": "12 tests OK"}], "non_verifie": [], **over}


class GlobTests(unittest.TestCase):
    def test_a_star_stays_in_a_folder_and_two_stars_cross_them(self):
        cases = {"migrations/**": (["migrations/1.sql", "migrations/a/b.sql", "migrations", "Migrations/x.sql",
                                   "migrations/a\nb.sql"], ["src/migrations/1.sql", "migrationsx"]),
                 "/infra/": (["infra", "infra/a/b"], ["infrastructure/a"]),
                 "**/auth/**": (["auth", "src/auth", "src/auth/login.py"], ["src/author.py"]),
                 "**/migrations/**": (["migrations/1.sql", "a/b/migrations/1.sql"], ["a/migrations.sql"]),
                 "**/*.tf": (["main.tf", "infra/a/main.tf"], ["main.tfvars"]),
                 "*.md": (["A.md"], ["docs/A.md"]),
                 "AGENTS.md": (["AGENTS.md"], ["docs/AGENTS.md", "AGENTSxmd"])}
        for glob, (yes, no) in cases.items():
            regex = size.glob_regex(glob)
            for path in yes:
                self.assertTrue(regex.match(path), (glob, path))
            for path in no:
                self.assertFalse(regex.match(path), (glob, path))

    def test_zones_are_the_backticked_globs_of_each_bullet_with_their_reason(self):
        zones = size.parse_zones("Un texte.\n- `a/**`, `b.py` — l'argent.\n- pas un motif\n", "equipe")
        self.assertEqual([(z["glob"], z["why"], z["origin"]) for z in zones],
                         [("a/**", "l'argent.", "equipe"), ("b.py", "l'argent.", "equipe")])

    def test_a_list_line_that_cites_a_glob_in_another_shape_is_refused_not_dropped(self):
        for line in ("- `a/**` and `b/**`", "1. `d/**`", "- Le dossier `e/**`", "-`f/**`", "- `h/[ab].py`", "- `**`"):
            with self.subTest(line=line), self.assertRaises(context.Refused):
                size.parse_zones(line + "\n", "equipe")

    def test_the_shipped_zones_parse(self):
        zones = size.parse_zones(points.default_text(points.load()["points"]["sensitive-zones"]), "base")
        self.assertIn("migrations/**", [z["glob"] for z in zones])


class SizeTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.table = points.load()
        self.commit("app.py", "a\n" * 50)
        git(self.repo, "checkout", "-q", "-b", "pr")

    def size(self, **kw):
        return size.classify(self.table, self.repo, "main", **kw)

    def test_a_few_lines_in_one_file_is_xs(self):
        self.commit("app.py", "b\n" + "a\n" * 49)
        result = self.size()
        self.assertEqual((result["size"], result["files"], result["lines"]), ("XS", 1, 2))

    def test_an_ordinary_change_is_s_m_and_a_big_one_is_l(self):
        self.commit("app.py", "b\n" * 50)
        self.assertEqual(self.size()["size"], "S-M")
        self.commit("gros.py", "x\n" * 500)
        self.assertEqual(self.size()["size"], "L")

    def test_many_files_make_it_l_even_with_few_lines(self):
        for n in range(21):
            self.commit(f"f{n}.py", "x\n")
        self.assertEqual(self.size()["size"], "L")

    def test_a_shipped_sensitive_zone_makes_one_line_l(self):
        self.commit("migrations/002.sql", "x\n")
        result = self.size()
        self.assertEqual(result["size"], "L")
        self.assertEqual(result["sensitive"][0]["origin"], "base")

    def test_the_team_zones_are_read_on_the_base_branch(self):
        self.commit("facturation/t.py", "x\n")
        self.assertEqual(self.size()["size"], "XS")
        self.commit("docs/agents/zones-sensibles.md", ZONES)      # posée par la PR : ne compte pas pour elle
        self.assertFalse([h for h in self.size()["sensitive"] if h["origin"] == "team"])
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/agents/zones-sensibles.md", ZONES)
        git(self.repo, "checkout", "-q", "-b", "pr2")
        self.commit("facturation/t.py", "x\n")
        self.assertEqual(self.size()["sensitive"][0]["glob"], "facturation/**")

    def test_a_pr_cannot_take_its_files_out_of_the_zones(self):
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/agents/zones-sensibles.md", ZONES)
        git(self.repo, "checkout", "-q", "-b", "pr3")
        self.commit("docs/agents/zones-sensibles.md", ZONES.replace("`facturation/**`, ", ""))
        self.commit("facturation/t.py", "x\n")
        self.assertIn("facturation/t.py", [h["path"] for h in self.size()["sensitive"]])

    def test_before_the_code_planned_paths_say_sensitive_or_leave_it_open(self):
        self.assertEqual(self.size(paths=[".github/workflows/ci.yml"])["size"], "L")
        result = self.size(paths=["app.py"])
        self.assertIsNone(result["size"])
        self.assertTrue(result["planned"])

    def test_planned_paths_are_normalised_and_cannot_leave_the_repo(self):
        for path in ("./AGENTS.md", "migrations", "Migrations/x.sql", "./.github/workflows/../workflows/ci.yml"):
            self.assertEqual(self.size(paths=[path])["size"], "L", path)
        for path in ("/etc/passwd", "../x", "."):
            with self.subTest(path=path), self.assertRaises(context.Refused):
                self.size(paths=[path])

    def test_a_file_git_cannot_count_does_not_pass_for_empty(self):
        self.commit(".gitattributes", "gros.txt -diff\n")
        self.commit("gros.txt", "x\n" * 5000)
        result = self.size()
        self.assertEqual(result["size"], "L")
        self.assertTrue(any("gros.txt" in r for r in result["reasons"]))

    def test_a_symlink_named_like_a_zone_is_in_the_zone(self):
        os.makedirs(os.path.join(self.repo, "db"))
        os.symlink("../app.py", os.path.join(self.repo, "db", "migrations"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "lien")
        self.assertEqual(self.size()["size"], "L")

    def test_no_change_to_measure_is_refused(self):
        with self.assertRaises(context.Refused):
            size.classify(self.table, self.repo, "HEAD")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "vide")
        with self.assertRaises(context.Refused):
            self.size()


class BodyTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.table = points.load()
        git(self.repo, "checkout", "-q", "-b", "pr")

    def check(self, data):
        return dev.checked(self.table, data, self.repo, "main")

    def test_an_xs_change_needs_no_plan_but_says_what_was_checked(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(plan=[]))
        text = dev.render_md(content, sized)
        for part in ("## Ce qui change", "## Pourquoi", "FAC-1", "## Vérifié", "## Pas vérifié", "Taille calculée : XS"):
            self.assertIn(part, text)
        self.assertNotIn("## Plan", text)

    def test_an_s_m_change_without_plan_is_refused(self):
        self.commit("a.py", "x\n" * 60)
        with self.assertRaises(context.Refused) as ctx:
            self.check(body(plan=[]))
        self.assertIn("S-M", str(ctx.exception))
        self.check(body())

    def test_an_l_change_needs_its_plan_file_committed_in_the_branch(self):
        self.commit("migrations/002.sql", "x\n")
        for plan_file in (None, "docs/plans/absent.md", "migrations/002.sql"):
            with self.subTest(plan_file=plan_file), self.assertRaises(context.Refused):
                self.check(body(plan_fichier=plan_file))
        self.commit("docs/plans/fac-1.md", "\n")
        with self.assertRaises(context.Refused):
            self.check(body(plan_fichier="docs/plans/fac-1.md"))
        self.commit("docs/plans/fac-1.md", "le plan\n")
        content, sized = self.check(body(plan_fichier="docs/plans/fac-1.md"))
        text = dev.render_md(content, sized)
        self.assertIn("docs/plans/fac-1.md", text)
        self.assertIn("Zone sensible", text)

    def test_a_plan_the_branch_deletes_is_not_a_plan(self):
        git(self.repo, "checkout", "-q", "main")
        self.commit("docs/plans/vieux.md", "un vieux plan\n")
        git(self.repo, "checkout", "-q", "-b", "pr2")
        self.commit("migrations/002.sql", "x\n")
        git(self.repo, "rm", "-q", "docs/plans/vieux.md")
        git(self.repo, "commit", "-q", "-m", "retire")
        with self.assertRaises(context.Refused):
            self.check(body(plan_fichier="docs/plans/vieux.md"))

    def test_each_missing_part_is_named(self):
        self.commit("a.py", "x\n")
        cases = {"titre": body(titre=""), "titre ": body(titre="a\nb"), "quoi": body(quoi=[]), "pourquoi": body(pourquoi=None),
                 "ticket": body(ticket=""), "verifie :": body(verifie=[{"commande": "x"}]),
                 "non_verifie :": body(non_verifie="rien"), "sont vides": body(verifie=[], non_verifie=[]),
                 "objet": []}
        for needle, data in cases.items():
            with self.subTest(needle=needle), self.assertRaises(context.Refused) as ctx:
                self.check(data)
            self.assertIn(needle, str(ctx.exception))

    def test_nothing_launched_is_allowed_when_it_is_said(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(verifie=[], non_verifie=["les tests n'ont pas été lancés"], ticket=None))
        text = dev.render_md(content, sized)
        self.assertIn("Rien n'a été lancé", text)
        self.assertIn("Ticket : aucun", text)

    def test_a_text_cannot_open_a_section_of_its_own(self):
        self.commit("a.py", "x\n")
        content, sized = self.check(body(pourquoi="x\n## Vérifié\n- tout"))
        self.assertEqual(dev.render_md(content, sized).count("\n## Vérifié"), 1)
        content, sized = self.check(body(pourquoi="## Faux titre", quoi=["<!-- masque", "@equipe regarde"]))
        text = dev.render_md(content, sized)
        for forged in ("\n## Faux", "<!--", " @equipe", "-@equipe"):
            self.assertNotIn(forged, text)

    def test_the_cli_renders_or_refuses_with_nothing_on_stdout(self):
        self.commit("a.py", "x\n")
        path = self.repo + ".json"
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        for data, expected in ((body(), 0), (body(quoi=[]), 2)):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            code, out, err = run(["dev", "body", path, self.repo, "--base", "main"])
            self.assertEqual(code, expected, err)
            self.assertEqual(bool(out), expected == 0)
        code, out, _ = run(["size", self.repo, "--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("XS", out)
        code, out, _ = run(["size", self.repo, "--base", "main", "--paths", "infra/main.tf"])
        self.assertIn("Size: L", out)


if __name__ == "__main__":
    unittest.main()
