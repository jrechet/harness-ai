"""Tests de la grille de placement : chaque morceau d'un harness a une seule place, la même pour
tout le monde, et la grille dit pourquoi et ce qui la ferait changer."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import place  # noqa: E402

GRID = place.load_grid()

# Un morceau, ses réponses, la destination attendue. C'est le corrigé de la grille : un changement
# de la grille qui déplace l'un de ces cas est un changement de doctrine, pas un détail.
CASES = [
    ("Ne jamais pousser sur main", {"nature": "limit", "bypass_limit": "dev"}, "server_protection"),
    ("L'agent ne lit pas les fichiers .env", {"nature": "limit", "bypass_limit": "agent"}, "permission"),
    ("Aucune équipe ne déploie en prod sans validation",
     {"nature": "limit", "bypass_limit": "team"}, "managed"),
    ("Lire le ticket Jira", {"nature": "action", "access": "consult"}, "mcp"),
    ("Poster l'annonce dans le canal", {"nature": "action", "access": "write"}, "mcp"),
    ("Publier le paquet", {"nature": "action", "access": "deliver"}, "pipeline"),
    ("Toute route a un test d'autorisation",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "dev"}, "ci_check"),
    ("Les tests passent avant de rendre la main",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "agent"}, "hook_check"),
    ("Détection de secrets dans tous les dépôts",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "team"}, "org_check"),
    ("Toute version publiée a son entrée de changelog",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "release"}, "release_gate"),
    ("Pas de release avec des fichiers non commités",
     {"nature": "rule", "incident": "forget", "checkable": "yes", "bypass_rule": "agent"}, "hook_check"),
    ("La description de PR explique le pourquoi",
     {"nature": "rule", "incident": "yes", "checkable": "no"}, "judge"),
    ("On préfère les fonctions courtes", {"nature": "rule", "incident": "no", "scope": "always"}, "agents_md"),
    ("Calculer la prochaine version", {"nature": "compute", "when": "on_demand"}, "cli"),
    ("Formater après chaque édition", {"nature": "compute", "when": "agent_loop"}, "hook_compute"),
    ("Mettre à jour le changelog à chaque PR", {"nature": "compute", "when": "repo_event"}, "workflow"),
    ("Relire la PR sans le biais de l'auteur", {"nature": "judgment", "isolation": "independence"}, "subagent"),
    ("Explorer 200 fichiers de logs", {"nature": "judgment", "isolation": "context"}, "subagent"),
    ("Choisir le type de release", {"nature": "judgment", "isolation": "none"}, "session"),
    ("Comment faire une release", {"nature": "procedure"}, "skill"),
    ("La commande qui lance les tests d'intégration", {"nature": "knowledge", "scope": "always"}, "agents_md"),
    ("Conventions du dossier migrations", {"nature": "knowledge", "scope": "zone"}, "agents_md_zone"),
    ("L'architecture détaillée", {"nature": "knowledge", "scope": "reference"}, "doc"),
    ("La liste des dossiers du dépôt", {"nature": "knowledge", "scope": "discoverable"}, "nothing"),
]


class GridTests(unittest.TestCase):
    def test_the_shipped_grid_is_valid(self):
        self.assertEqual(place.validate(GRID), [])

    def test_every_destination_has_an_example(self):
        reached = {expected for _, _, expected in CASES}
        self.assertEqual(set(GRID["destinations"]) - reached, set())

    def test_an_option_pointing_nowhere_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["questions"]["access"]["options"]["consult"] = {"label": "x", "place": "nowhere"}
        self.assertTrue(any("nowhere" in e for e in place.validate(broken)))

    def test_an_unreachable_question_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["questions"]["orphan"] = {"text": "?", "options": {"a": {"label": "a", "place": "cli"}}}
        self.assertTrue(any("orphan" in e for e in place.validate(broken)))

    def test_a_destination_without_why_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["destinations"]["cli"]["why"] = ""
        self.assertTrue(any("cli" in e and "why" in e for e in place.validate(broken)))

    def test_a_cycle_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["questions"]["access"]["options"]["consult"] = {"label": "x", "ask": "nature"}
        self.assertTrue(any(e.startswith("cycle") for e in place.validate(broken)))

    def test_an_uppercase_id_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["questions"]["access"]["options"]["Consult"] = broken["questions"]["access"]["options"]["consult"]
        self.assertTrue(any("Consult" in e for e in place.validate(broken)))

    def test_an_unknown_layer_is_reported(self):
        broken = json.loads(json.dumps(GRID))
        broken["destinations"]["cli"]["layer"] = "L5"
        self.assertTrue(any("L5" in e for e in place.validate(broken)))


class WalkTests(unittest.TestCase):
    def test_each_example_lands_where_the_doctrine_says(self):
        for piece, answers, expected in CASES:
            with self.subTest(piece=piece):
                result = place.walk(GRID, answers)
                self.assertEqual(result["status"], "placed")
                self.assertEqual(result["destination"]["id"], expected)

    def test_a_missing_answer_returns_the_next_question_with_its_options(self):
        result = place.walk(GRID, {"nature": "limit"})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["next"]["id"], "bypass_limit")
        self.assertEqual(set(result["next"]["options"]), {"agent", "dev", "team"})

    def test_no_answer_at_all_starts_with_the_root_question(self):
        self.assertEqual(place.walk(GRID, {})["next"]["id"], GRID["root"])

    def test_an_invalid_option_is_refused_with_the_valid_ones(self):
        with self.assertRaises(ValueError) as ctx:
            place.walk(GRID, {"nature": "limit", "bypass_limit": "personne"})
        self.assertIn("agent", str(ctx.exception))

    def test_an_unknown_question_is_refused(self):
        with self.assertRaises(ValueError):
            place.walk(GRID, {"nature": "procedure", "couleur": "bleu"})

    def test_an_answer_off_the_path_is_reported_as_unused(self):
        result = place.walk(GRID, {"nature": "procedure", "scope": "always"})
        self.assertEqual(result["destination"]["id"], "skill")
        self.assertEqual(result["unused"], ["scope"])

    def test_the_same_question_answered_twice_is_refused(self):
        # Sinon l'ordre des clés déciderait : mêmes réponses, destinations différentes.
        with self.assertRaises(ValueError):
            place.walk(GRID, {"Nature": "procedure", "nature": "limit", "bypass_limit": "dev"})

    def test_case_and_accents_do_not_matter(self):
        result = place.walk(GRID, {"Nature": "LIMIT", "bypass_limit": "Dév"})
        self.assertEqual(result["destination"]["id"], "server_protection")

    def test_the_path_lists_each_question_and_answer_in_order(self):
        result = place.walk(GRID, {"nature": "rule", "incident": "yes", "checkable": "no"})
        self.assertEqual([(s["question"], s["answer"]) for s in result["path"]],
                         [("nature", "rule"), ("incident", "yes"), ("checkable", "no")])

    def test_the_alternatives_say_where_the_last_other_answers_lead(self):
        result = place.walk(GRID, {"nature": "limit", "bypass_limit": "dev"})
        alts = {a["answer"]: a["leads_to"] for a in result["alternatives"]}
        self.assertEqual(alts, {"agent": "permission", "team": "managed"})


class ReviewTests(unittest.TestCase):
    def _verdict(self, answers, current):
        return place.place_piece(GRID, {"piece": "x", "answers": answers, "current": current})["verdict"]

    def test_a_piece_already_in_place_is_kept(self):
        self.assertEqual(self._verdict({"nature": "procedure"}, "skill"), "KEEP")

    def test_a_guarantee_written_in_agents_md_goes_down(self):
        answers = {"nature": "limit", "bypass_limit": "dev"}
        self.assertEqual(self._verdict(answers, "agents_md"), "PUSH_DOWN")

    def test_a_judgment_hard_coded_in_a_script_goes_up(self):
        self.assertEqual(self._verdict({"nature": "judgment", "isolation": "none"}, "cli"), "PROMOTE")

    def test_same_layer_elsewhere_is_moved(self):
        self.assertEqual(self._verdict({"nature": "knowledge", "scope": "reference"}, "agents_md"), "MOVE")

    def test_what_the_agent_finds_alone_is_removed(self):
        self.assertEqual(self._verdict({"nature": "knowledge", "scope": "discoverable"}, "agents_md"), "REMOVE")

    def test_an_unknown_current_place_is_refused(self):
        with self.assertRaises(ValueError):
            self._verdict({"nature": "procedure"}, "un-wiki")

    def test_nothing_is_not_a_current_place(self):
        with self.assertRaises(ValueError):
            self._verdict({"nature": "procedure"}, "nothing")

    def test_a_piece_must_be_a_text(self):
        with self.assertRaises(ValueError):
            place.place_piece(GRID, {"piece": ["a"], "answers": {"nature": "procedure"}})

    def test_an_incomplete_piece_keeps_its_current_place_and_waits_for_a_verdict(self):
        row = place.place_piece(GRID, {"piece": "x", "answers": {"nature": "judgment"}, "current": "cli"})
        self.assertIsNone(row["verdict"])
        self.assertIn(GRID["destinations"]["cli"]["name"], place.render_piece_md(GRID, row))

    def test_no_current_place_means_no_verdict(self):
        self.assertIsNone(place.place_piece(GRID, {"piece": "x", "answers": {"nature": "procedure"}})["verdict"])


def run_cli(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = harness.main(list(argv))
        except SystemExit as exc:  # argparse refuse une saisie invalide par SystemExit(2)
            code = exc.code
    return code, out.getvalue()


FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "fixtures", "design")
EXPECTED = {
    "traps": [{"id": "T1", "what": "limite racontée", "file": "skills/r/SKILL.md", "lines": [10, 12],
               "accept": ["server_protection", "managed"]}],
    "healthy": [{"id": "S1", "what": "procédure", "file": "skills/r/SKILL.md", "lines": [1, 5]}],
}
TRAP = {"piece": "Ne jamais pousser", "answers": {"nature": "limit", "bypass_limit": "dev"},
        "current": "skill", "evidence": ["skills/r/SKILL.md:11"]}
SOUND = {"piece": "La procédure", "answers": {"nature": "procedure"}, "current": "skill",
         "evidence": ["./skills/r/SKILL.md:2"]}


class CheckTests(unittest.TestCase):
    def _check(self, *pieces):
        return place.check(GRID, EXPECTED, list(pieces))

    def test_a_trap_moved_to_an_accepted_place_with_its_line_is_found(self):
        result = self._check(TRAP, SOUND)
        self.assertEqual((result["found"], result["expected"], result["flagged"]), (1, 1, 0))
        self.assertTrue(result["passed"])

    def test_a_trap_nobody_cites_is_missed(self):
        result = self._check(SOUND)
        self.assertEqual(result["traps"][0]["status"], "missed")
        self.assertFalse(result["passed"])

    def test_the_right_place_without_the_right_line_is_not_found(self):
        result = self._check({**TRAP, "evidence": ["skills/r/SKILL.md:40"]})
        self.assertEqual(result["traps"][0]["status"], "missed")

    def test_a_trap_sent_to_a_place_not_accepted_is_wrong_and_says_where(self):
        result = self._check({**TRAP, "answers": {"nature": "limit", "bypass_limit": "agent"}})
        self.assertEqual(result["traps"][0]["status"], "wrong")
        self.assertEqual(result["traps"][0]["got"], ["permission"])

    def test_a_trap_kept_where_it_is_is_wrong(self):
        result = self._check({**TRAP, "answers": {"nature": "procedure"}})
        self.assertEqual(result["traps"][0]["status"], "wrong")

    def test_a_healthy_element_that_gets_moved_is_flagged(self):
        result = self._check(TRAP, {**SOUND, "answers": {"nature": "compute", "when": "on_demand"}})
        self.assertEqual(result["healthy"][0]["status"], "flagged")
        self.assertFalse(result["passed"])

    def test_a_healthy_element_nobody_mentions_is_not_a_fault(self):
        result = self._check(TRAP)
        self.assertEqual(result["healthy"][0]["status"], "absent")
        self.assertTrue(result["passed"])

    def test_another_piece_cut_from_the_same_line_does_not_flag_a_healthy_element(self):
        # Le corrigé dit de quelle nature est l'élément sain : un morceau d'une autre nature, tiré de la
        # même ligne, est un autre morceau.
        expected = json.loads(json.dumps(EXPECTED))
        expected["healthy"][0]["natures"] = ["procedure"]
        other = {"piece": "Publier", "answers": {"nature": "action", "access": "deliver"}, "current": "skill",
                 "evidence": ["skills/r/SKILL.md:2"]}
        result = place.check(GRID, expected, [TRAP, SOUND, other])
        self.assertEqual(result["healthy"][0]["status"], "kept")
        moved = {**SOUND, "answers": {"nature": "procedure"}, "current": "agents_md"}
        self.assertEqual(place.check(GRID, expected, [TRAP, moved])["healthy"][0]["status"], "flagged")

    def test_in_create_mode_a_piece_without_current_is_found_by_its_destination(self):
        expected = {"mode": "create", "traps": [{"id": "C1", "what": "calcul", "file": "demande.md",
                                                 "lines": [3, 3], "accept": ["cli"]}]}
        piece = {"piece": "Nom de branche", "answers": {"nature": "compute", "when": "on_demand"},
                 "evidence": ["demande.md:3"]}
        self.assertTrue(place.check(GRID, expected, [piece])["passed"])
        wrong = {**piece, "answers": {"nature": "procedure"}}
        result = place.check(GRID, expected, [wrong])
        self.assertEqual((result["traps"][0]["status"], result["traps"][0]["got"]), ("wrong", ["skill"]))

    def test_in_review_mode_a_piece_without_current_finds_nothing(self):
        piece = {k: v for k, v in TRAP.items() if k != "current"}
        self.assertEqual(place.check(GRID, EXPECTED, [piece])["traps"][0]["status"], "wrong")

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            place.check(GRID, {**EXPECTED, "mode": "devine"}, [TRAP])

    def test_an_unknown_nature_in_the_expected_file_is_refused(self):
        broken = json.loads(json.dumps(EXPECTED))
        broken["healthy"][0]["natures"] = ["poesie"]
        with self.assertRaises(ValueError):
            place.check(GRID, broken, [TRAP])

    def test_an_expected_file_pointing_to_an_unknown_place_is_refused(self):
        broken = json.loads(json.dumps(EXPECTED))
        broken["traps"][0]["accept"] = ["un-wiki"]
        with self.assertRaises(ValueError):
            place.check(GRID, broken, [TRAP])


class DesignFixtureTests(unittest.TestCase):
    """Chaque fixture de harness-design : son corrigé tient debout, et le plan de son auteur le passe."""

    def test_every_fixture_cites_real_lines_and_its_author_run_passes(self):
        names = sorted(n for n in os.listdir(FIXTURES) if os.path.isdir(os.path.join(FIXTURES, n)))
        self.assertTrue(names)
        for name in names:
            with self.subTest(fixture=name):
                root = os.path.join(FIXTURES, name)
                with open(os.path.join(root, "expected.json"), encoding="utf-8") as fh:
                    expected = json.load(fh)
                for spec in expected["traps"] + expected.get("healthy", []):
                    with open(os.path.join(root, "artifact", spec["file"]), encoding="utf-8") as fh:
                        self.assertLessEqual(spec["lines"][1], len(fh.readlines()), spec["id"])
                # Tout chemin de workflow cité par l'artefact existe : sinon l'agent ne peut pas le vérifier.
                for folder, _, files in os.walk(os.path.join(root, "artifact")):
                    for name_ in files:
                        with open(os.path.join(folder, name_), encoding="utf-8") as fh:
                            for cited in re.findall(r"`(\.github/workflows/[^`]+)`", fh.read()):
                                self.assertTrue(os.path.isfile(os.path.join(root, "artifact", cited)), cited)
                runs = os.path.join(root, "runs")
                author = [r for r in sorted(os.listdir(runs)) if r.endswith("-author")]
                self.assertTrue(author, "pas de plan d'auteur")
                pieces = place.load_pieces(os.path.join(runs, author[-1], "pieces.json"))
                result = place.check(GRID, expected, pieces)
                # Un trou connu de la grille se déclare ; l'auteur ne force pas une réponse pour le masquer.
                gaps_file = os.path.join(runs, author[-1], "known-gaps.json")
                known = []
                if os.path.isfile(gaps_file):
                    with open(gaps_file, encoding="utf-8") as fh:
                        known = json.load(fh)
                missed = sorted(t["id"] for t in result["traps"] if t["status"] != "found")
                self.assertEqual(missed, sorted(known), result)
                self.assertEqual(result["flagged"], 0, result)


class CliTests(unittest.TestCase):
    def test_one_piece_placed_prints_destination_and_why(self):
        code, out = run_cli("place", "one", "nature=limit", "bypass_limit=dev")
        self.assertEqual(code, 0)
        self.assertIn(GRID["destinations"]["server_protection"]["name"], out)
        self.assertIn(GRID["destinations"]["server_protection"]["why"], out)

    def test_one_piece_incomplete_exits_3_and_asks_the_next_question(self):
        code, out = run_cli("place", "one", "nature=rule", "--format", "json")
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["next"]["id"], "incident")

    def test_a_malformed_answer_exits_2(self):
        code, _ = run_cli("place", "one", "nature")
        self.assertEqual(code, 2)

    def test_the_grid_lists_every_question(self):
        code, out = run_cli("place", "grid", "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out)["questions"]), set(GRID["questions"]))

    def test_a_plan_places_each_piece_and_flags_the_incomplete_ones(self):
        pieces = [{"piece": "Ne jamais pousser sur main", "answers": {"nature": "limit", "bypass_limit": "dev"},
                   "current": "agents_md"},
                  {"piece": "Relire la PR", "answers": {"nature": "judgment"}}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(pieces, fh)
            code, out = run_cli("place", "plan", path)
            code_json, out_json = run_cli("place", "plan", path, "--format", "json")
        self.assertEqual(code, 3)
        self.assertIn("PUSH_DOWN", out)
        self.assertIn(GRID["questions"]["isolation"]["text"], out)
        rows = json.loads(out_json)
        self.assertEqual(code_json, 3)
        self.assertEqual([r["status"] for r in rows], ["placed", "incomplete"])

    def test_a_plan_with_a_piece_without_answers_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"piece": "x"}], fh)
            code, _ = run_cli("place", "plan", path)
        self.assertEqual(code, 2)

    def test_check_scores_a_plan_against_a_fixture(self):
        root = os.path.join(FIXTURES, "release-skill")
        plan = os.path.join(root, "runs", "2026-11-15-author", "pieces.json")
        code, out = run_cli("place", "check", plan, "--expected", os.path.join(root, "expected.json"), "--format", "json")
        self.assertIn(code, (0, 1))
        self.assertEqual(json.loads(out)["expected"], 7)

    def test_check_exits_1_when_a_trap_is_missed(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, exp = os.path.join(tmp, "p.json"), os.path.join(tmp, "e.json")
            with open(plan, "w", encoding="utf-8") as fh:
                json.dump([SOUND], fh)
            with open(exp, "w", encoding="utf-8") as fh:
                json.dump(EXPECTED, fh)
            code, out = run_cli("place", "check", plan, "--expected", exp)
        self.assertEqual(code, 1)
        self.assertIn("T1", out)


if __name__ == "__main__":
    unittest.main()
