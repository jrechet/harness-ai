"""Tests de la grille de placement : chaque morceau d'un harness a une seule place, la même pour
tout le monde, et la grille dit pourquoi et ce qui la ferait changer."""
from __future__ import annotations

import contextlib
import io
import json
import os
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
    ("Publier le paquet", {"nature": "action", "access": "deliver"}, "pipeline"),
    ("Toute route a un test d'autorisation",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "dev"}, "ci_check"),
    ("Les tests passent avant de rendre la main",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "agent"}, "hook_check"),
    ("Détection de secrets dans tous les dépôts",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "team"}, "org_check"),
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


if __name__ == "__main__":
    unittest.main()
