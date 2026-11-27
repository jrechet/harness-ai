"""Tests of the placement grid: each piece of a harness has a single place, the same for
everyone, and the grid says why and what would change it."""
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

# A piece, its answers, the expected destination. This is the grid's answer key: a change
# of the grid that moves one of these cases is a change of doctrine, not a detail.
CASES = [
    ("Never push to main", {"nature": "limit", "bypass_limit": "dev"}, "server_protection"),
    ("The agent does not read .env files", {"nature": "limit", "bypass_limit": "agent"}, "permission"),
    ("No team deploys to prod without approval",
     {"nature": "limit", "bypass_limit": "team"}, "managed"),
    ("Read the Jira ticket", {"nature": "action", "access": "consult"}, "mcp"),
    ("Post the announcement in the channel", {"nature": "action", "access": "write"}, "mcp"),
    ("Publish the package", {"nature": "action", "access": "deliver"}, "pipeline"),
    ("Every route has an authorisation test",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "dev"}, "ci_check"),
    ("Tests pass before handing back",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "agent"}, "hook_check"),
    ("Secret detection in every repository",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "team"}, "org_check"),
    ("Every published version has its changelog entry",
     {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "release"}, "release_gate"),
    ("No release with uncommitted files",
     {"nature": "rule", "incident": "forget", "checkable": "yes", "bypass_rule": "agent"}, "hook_check"),
    ("The PR description explains the why",
     {"nature": "rule", "incident": "yes", "checkable": "no"}, "judge"),
    ("Short functions are preferred", {"nature": "rule", "incident": "no", "scope": "always"}, "agents_md"),
    ("Compute the next version", {"nature": "compute", "when": "on_demand"}, "cli"),
    ("Format after each edit", {"nature": "compute", "when": "agent_loop"}, "hook_compute"),
    ("Update the changelog on each PR", {"nature": "compute", "when": "repo_event"}, "workflow"),
    ("Review the PR without the author's bias", {"nature": "judgment", "isolation": "independence"}, "subagent"),
    ("Explore 200 log files", {"nature": "judgment", "isolation": "context"}, "subagent"),
    ("Choose the release type", {"nature": "judgment", "isolation": "none"}, "session"),
    ("How to make a release", {"nature": "procedure"}, "skill"),
    ("The command that runs the integration tests", {"nature": "knowledge", "scope": "always"}, "agents_md"),
    ("Conventions of the migrations folder", {"nature": "knowledge", "scope": "zone"}, "agents_md_zone"),
    ("The detailed architecture", {"nature": "knowledge", "scope": "reference"}, "doc"),
    ("The list of the repository's folders", {"nature": "knowledge", "scope": "discoverable"}, "nothing"),
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
            place.walk(GRID, {"nature": "limit", "bypass_limit": "nobody"})
        self.assertIn("agent", str(ctx.exception))

    def test_an_unknown_question_is_refused(self):
        with self.assertRaises(ValueError):
            place.walk(GRID, {"nature": "procedure", "colour": "blue"})

    def test_an_answer_off_the_path_is_reported_as_unused(self):
        result = place.walk(GRID, {"nature": "procedure", "scope": "always"})
        self.assertEqual(result["destination"]["id"], "skill")
        self.assertEqual(result["unused"], ["scope"])

    def test_the_same_question_answered_twice_is_refused(self):
        # Otherwise the key order would decide: same answers, different destinations.
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
            self._verdict({"nature": "procedure"}, "a-wiki")

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
        except SystemExit as exc:  # argparse refuses invalid input with SystemExit(2)
            code = exc.code
    return code, out.getvalue()


FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "fixtures", "design")
EXPECTED = {
    "traps": [{"id": "T1", "what": "limit told in prose", "file": "skills/r/SKILL.md", "lines": [10, 12],
               "accept": ["server_protection", "managed"]}],
    "healthy": [{"id": "S1", "what": "procedure", "file": "skills/r/SKILL.md", "lines": [1, 5]}],
}
TRAP = {"piece": "Never push", "answers": {"nature": "limit", "bypass_limit": "dev"},
        "current": "skill", "evidence": ["skills/r/SKILL.md:11"]}
SOUND = {"piece": "The procedure", "answers": {"nature": "procedure"}, "current": "skill",
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
        # The answer key says which nature the healthy item is: a piece of another nature, cut from the
        # same line, is another piece.
        expected = json.loads(json.dumps(EXPECTED))
        expected["healthy"][0]["natures"] = ["procedure"]
        other = {"piece": "Publish", "answers": {"nature": "action", "access": "deliver"}, "current": "skill",
                 "evidence": ["skills/r/SKILL.md:2"]}
        result = place.check(GRID, expected, [TRAP, SOUND, other])
        self.assertEqual(result["healthy"][0]["status"], "kept")
        moved = {**SOUND, "answers": {"nature": "procedure"}, "current": "agents_md"}
        self.assertEqual(place.check(GRID, expected, [TRAP, moved])["healthy"][0]["status"], "flagged")

    def test_in_create_mode_a_piece_without_current_is_found_by_its_destination(self):
        expected = {"mode": "create", "traps": [{"id": "C1", "what": "computation", "file": "request.md",
                                                 "lines": [3, 3], "accept": ["cli"]}]}
        piece = {"piece": "Branch name", "answers": {"nature": "compute", "when": "on_demand"},
                 "evidence": ["request.md:3"]}
        self.assertTrue(place.check(GRID, expected, [piece])["passed"])
        wrong = {**piece, "answers": {"nature": "procedure"}}
        result = place.check(GRID, expected, [wrong])
        self.assertEqual((result["traps"][0]["status"], result["traps"][0]["got"]), ("wrong", ["skill"]))

    def test_in_review_mode_a_piece_without_current_finds_nothing(self):
        piece = {k: v for k, v in TRAP.items() if k != "current"}
        self.assertEqual(place.check(GRID, EXPECTED, [piece])["traps"][0]["status"], "wrong")

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            place.check(GRID, {**EXPECTED, "mode": "guess"}, [TRAP])

    def test_an_unknown_nature_in_the_expected_file_is_refused(self):
        broken = json.loads(json.dumps(EXPECTED))
        broken["healthy"][0]["natures"] = ["poetry"]
        with self.assertRaises(ValueError):
            place.check(GRID, broken, [TRAP])

    def test_an_expected_file_pointing_to_an_unknown_place_is_refused(self):
        broken = json.loads(json.dumps(EXPECTED))
        broken["traps"][0]["accept"] = ["a-wiki"]
        with self.assertRaises(ValueError):
            place.check(GRID, broken, [TRAP])


class DesignFixtureTests(unittest.TestCase):
    """Each harness-design fixture: its answer key holds up, and its author's plan passes it."""

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
                # Every workflow path cited by the artifact exists: otherwise the agent cannot check it.
                for folder, _, files in os.walk(os.path.join(root, "artifact")):
                    for name_ in files:
                        with open(os.path.join(folder, name_), encoding="utf-8") as fh:
                            for cited in re.findall(r"`(\.github/workflows/[^`]+)`", fh.read()):
                                self.assertTrue(os.path.isfile(os.path.join(root, "artifact", cited)), cited)
                runs = os.path.join(root, "runs")
                author = [r for r in sorted(os.listdir(runs)) if r.endswith("-author")]
                self.assertTrue(author, "no author plan")
                pieces = place.load_pieces(os.path.join(runs, author[-1], "pieces.json"))
                result = place.check(GRID, expected, pieces)
                # A known gap of the grid is declared; the author does not force an answer to hide it.
                gaps_file = os.path.join(runs, author[-1], "known-gaps.json")
                known = []
                if os.path.isfile(gaps_file):
                    with open(gaps_file, encoding="utf-8") as fh:
                        known = json.load(fh)
                missed = sorted(t["id"] for t in result["traps"] if t["status"] != "found")
                self.assertEqual(missed, sorted(known), result)
                self.assertEqual(result["flagged"], 0, result)


# One piece per concept the review can name: where it is held today, its answers, the concept expected.
# A change that moves one of these cases changes what the review tells a user.
RULE_CI = {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "dev"}
CONCEPT_CASES = [
    ("Refuse to release with uncommitted files", RULE_CI, "skill", "skippable_condition"),
    ("Compute the next version", {"nature": "compute", "when": "on_demand"}, "skill", "determinism"),
    ("Never push to main", {"nature": "limit", "bypass_limit": "dev"}, "agents_md", "limit_only_asked"),
    ("Publish the package", {"nature": "action", "access": "deliver"}, "skill", "unguarded_action"),
    ("Nothing merges without tests", RULE_CI, "hook_check", "weak_guard"),
    ("Choose the release type", {"nature": "judgment", "isolation": "none"}, "cli", "frozen_judgment"),
    ("Summarise the diff", {"nature": "judgment", "isolation": "none"}, "subagent", "tidy_helper"),
    ("The list of folders", {"nature": "knowledge", "scope": "discoverable"}, "agents_md", "dead_weight"),
    ("Conventions of the migrations folder", {"nature": "knowledge", "scope": "zone"}, "agents_md", "wrong_place"),
]
# Pieces a review must not flag, or must not flag under a flattering name: where it is held, its answers,
# the concept expected (None: well placed).
RULE_AGENT = {"nature": "rule", "incident": "forget", "checkable": "yes", "bypass_rule": "agent"}
CONCEPT_EDGES = [
    ("Choose the release type", {"nature": "judgment", "isolation": "none"}, "skill", None),
    ("Choose the wording", {"nature": "judgment", "isolation": "none"}, "agents_md", None),
    ("Judge readability", {"nature": "rule", "incident": "yes", "checkable": "no"}, "subagent", None),
    ("Compute the next version", {"nature": "compute", "when": "on_demand"}, "workflow", "wrong_place"),
    ("The agent does not read .env", {"nature": "limit", "bypass_limit": "agent"}, "managed", "wrong_place"),
    ("Tests pass before handing back", RULE_AGENT, "ci_check", "wrong_place"),
    ("Never push to main", {"nature": "limit", "bypass_limit": "dev"}, "managed", "wrong_place"),
    ("Never push to main", {"nature": "limit", "bypass_limit": "dev"}, "permission", "weak_guard"),
    ("Short functions are preferred", {"nature": "rule", "incident": "no", "scope": "always"}, "ci_check",
     "frozen_judgment"),
]
LEVEL_OR_CODE = re.compile(r"\bL[1-4]\b|\b[Ll]evel [0-4]\b|\b[Ll]ayers?\b|KEEP|PUSH_DOWN|PROMOTE|\bMOVE\b|REMOVE")


def as_pieces(cases):
    return [{"piece": text, "answers": answers, "current": current, "evidence": [f"SKILL.md:{i}"]}
            for i, (text, answers, current, _) in enumerate(cases, 1)]


class ConceptReviewTests(unittest.TestCase):
    """`place review`: the same placement, told as named concepts, with no level and no verdict code."""

    def test_the_shipped_concepts_are_complete(self):
        self.assertEqual(sorted(GRID["concepts"]), sorted(place.CONCEPTS))
        for cid, concept in GRID["concepts"].items():
            with self.subTest(concept=cid):
                self.assertTrue(concept["name"].strip() and concept["definition"].strip())

    def test_a_concept_without_definition_is_reported(self):
        grid = json.loads(json.dumps(GRID))
        grid["concepts"]["determinism"]["definition"] = " "
        del grid["concepts"]["dead_weight"]
        errors = "\n".join(place.validate(grid))
        self.assertIn("concept determinism", errors)
        self.assertIn("concept dead_weight", errors)

    def test_each_weakness_gets_the_concept_the_doctrine_names(self):
        for text, answers, current, expected in CONCEPT_CASES:
            with self.subTest(piece=text):
                row = place.place_piece(GRID, {"piece": text, "answers": answers, "current": current})
                self.assertEqual(place.concept(GRID, row), expected)

    def test_a_piece_held_where_the_grid_means_it_is_not_a_weakness_and_code_is_not_called_judgement(self):
        for text, answers, current, expected in CONCEPT_EDGES:
            with self.subTest(piece=text, current=current):
                row = place.place_piece(GRID, {"piece": text, "answers": answers, "current": current})
                self.assertEqual(place.concept(GRID, row), expected)

    def test_a_skill_with_its_procedure_and_a_choice_left_to_the_agent_has_no_finding(self):
        result = place.review(GRID, [
            {"piece": "How to release", "answers": {"nature": "procedure"}, "current": "skill"},
            {"piece": "Choose the release type", "answers": {"nature": "judgment", "isolation": "none"},
             "current": "skill"}])
        self.assertEqual((len(result["good"]), result["findings"], result["notes"]), (2, [], []))

    def test_no_review_of_any_piece_anywhere_shows_a_level_a_code_or_an_id(self):
        def paths(qid, answers):
            for opt, option in GRID["questions"][qid]["options"].items():
                kind, target = place._target(option)
                if kind == "place":
                    yield {**answers, qid: opt}
                else:
                    yield from paths(target, {**answers, qid: opt})
        currents = [d for d in GRID["destinations"] if d != "nothing"]
        pieces = [{"piece": "p", "answers": a, "current": c, "evidence": ["f.md:1"]}
                  for a in paths(GRID["root"], {}) for c in currents]
        self.assertGreater(len(pieces), 400)
        out = place.render_review_md(GRID, place.review(GRID, pieces))
        leak = re.compile(LEVEL_OR_CODE.pattern + r"|\blevels?\b")
        self.assertEqual(sorted(set(leak.findall(out))), [])
        for did in GRID["destinations"]:
            self.assertNotIn(f"`{did}`", out)

    def test_the_well_placed_pieces_say_why_they_hold(self):
        out = place.render_review_md(GRID, place.review(GRID, [
            {"piece": "How to release", "answers": {"nature": "procedure"}, "current": "skill"}]))
        self.assertIn(GRID["destinations"]["skill"]["why"], out)
        self.assertIn("1 piece read", out)

    def test_an_evidence_cannot_break_the_page_and_must_be_text(self):
        piece = {"piece": "x", "answers": {"nature": "procedure"}, "current": "skill"}
        out = place.render_review_md(GRID, place.review(GRID, [{**piece, "evidence": ["a\n## Injected", None]}]))
        self.assertNotIn("\n## Injected", out)
        self.assertNotIn("None", out)
        with self.assertRaises(ValueError):
            place.review(GRID, [{**piece, "evidence": {"a": 1}}])

    def test_every_concept_but_the_note_has_a_case(self):
        self.assertEqual({c for *_, c in CONCEPT_CASES} | {"two_in_one"}, set(place.CONCEPTS))

    def test_a_piece_in_its_place_has_no_concept(self):
        row = place.place_piece(GRID, {"piece": "How to release", "answers": {"nature": "procedure"},
                                       "current": "skill"})
        self.assertIsNone(place.concept(GRID, row))

    def test_the_review_groups_by_concept_and_says_what_is_good(self):
        pieces = as_pieces(CONCEPT_CASES) + [{"piece": "How to release", "answers": {"nature": "procedure"},
                                              "current": "skill", "evidence": ["SKILL.md:40"]}]
        result = place.review(GRID, pieces)
        out = place.render_review_md(GRID, result)
        self.assertEqual([r["piece"] for r in result["good"]], ["How to release"])
        self.assertIn("## Well placed", out)
        self.assertIn("How to release", out)
        for cid in {c for *_, c in CONCEPT_CASES}:
            with self.subTest(concept=cid):
                self.assertIn(f"## {GRID['concepts'][cid]['name']}", out)
                self.assertIn(GRID["concepts"][cid]["definition"], out)
        self.assertIn("SKILL.md:2", out)                      # the evidence of each finding is cited
        self.assertIn(GRID["destinations"]["cli"]["name"], out)   # and where it would hold

    def test_the_review_shows_no_level_and_no_verdict_code(self):
        out = place.render_review_md(GRID, place.review(GRID, as_pieces(CONCEPT_CASES)))
        self.assertIsNone(LEVEL_OR_CODE.search(out), LEVEL_OR_CODE.findall(out))
        for did in GRID["destinations"]:
            self.assertNotIn(f"`{did}`", out)

    def test_a_skill_that_carries_its_procedure_and_something_else_is_two_things_in_one(self):
        pieces = [{"piece": "How to release", "answers": {"nature": "procedure"}, "current": "skill"},
                  {"piece": "Compute the next version", "answers": {"nature": "compute", "when": "on_demand"},
                   "current": "skill"}]
        result = place.review(GRID, pieces)
        self.assertEqual(result["notes"], ["two_in_one"])
        out = place.render_review_md(GRID, result)
        self.assertIn(GRID["concepts"]["two_in_one"]["name"], out)
        self.assertEqual(out.count("Compute the next version"), 2)   # under its concept, and named by the note
        self.assertEqual(place.review(GRID, pieces[:1])["notes"], [])

    def test_a_piece_without_a_current_place_is_refused_in_review(self):
        with self.assertRaises(ValueError):
            place.review(GRID, [{"piece": "New thing", "answers": {"nature": "procedure"}}])

    def test_a_missing_answer_is_asked_in_plain_words_and_exits_3(self):
        pieces = [{"piece": "Tests pass", "answers": {"nature": "rule"}, "current": "skill"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(pieces, fh)
            code, out = run_cli("place", "review", path)
        self.assertEqual(code, 3)
        self.assertIn(GRID["questions"]["incident"]["text"], out)
        self.assertNotIn("`incident`", out)

    def test_the_review_of_a_fixture_plan_names_its_concepts(self):
        plan = os.path.join(FIXTURES, "release-skill", "runs", "2026-11-15-author", "pieces.json")
        code, out = run_cli("place", "review", plan)
        code_json, out_json = run_cli("place", "review", plan, "--format", "json")
        self.assertEqual((code, code_json), (0, 0))
        self.assertIsNone(LEVEL_OR_CODE.search(out), LEVEL_OR_CODE.findall(out))
        data = json.loads(out_json)
        self.assertIn("determinism", [f["concept"] for f in data["findings"]])
        self.assertIn("dead_weight", [f["concept"] for f in data["findings"]])

    def test_a_review_of_invalid_input_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"piece": "x", "answers": {"nature": "procedure"}}], fh)
            code, _ = run_cli("place", "review", path)
        self.assertEqual(code, 2)


class DecisionTests(unittest.TestCase):
    """`place review --decisions`: what every other option would give, for the answers that are the
    author's to give. It says what an answer moves; whether to ask for it stays the coach's reading."""

    RULE = {"piece": "Tests pass before a release", "current": "skill", "evidence": ["SKILL.md:9"],
            "answers": {"nature": "rule", "incident": "yes", "checkable": "yes", "bypass_rule": "release"}}

    def _decisions(self, *pieces):
        return place.decisions(GRID, list(pieces))

    def _others(self, entry):
        return {o["answer"]: o for o in entry["others"]}

    def test_only_the_decision_questions_are_listed(self):
        entries = self._decisions(self.RULE)
        self.assertEqual([e["question"] for e in entries], ["incident", "bypass_rule"])
        self.assertEqual({e["piece"] for e in entries}, {self.RULE["piece"]})

    def test_a_cost_that_leads_to_the_same_place_changes_nothing(self):
        cost = self._decisions(self.RULE)[0]
        self.assertEqual(self._others(cost)["forget"]["outcome"], "same")

    def test_a_cost_that_opens_another_question_says_which(self):
        other = self._others(self._decisions(self.RULE)[0])["no"]
        self.assertEqual(other["outcome"], "opens")
        self.assertEqual(other["question"], GRID["questions"]["scope"]["text"])

    def test_who_must_not_skip_it_moves_the_piece_and_names_where(self):
        who = self._decisions(self.RULE)[1]
        agent = self._others(who)["agent"]
        self.assertEqual((agent["outcome"], agent["destination"]), ("moves", "hook_check"))
        self.assertEqual(agent["concept"], "skippable_condition")

    def test_an_answer_that_would_leave_the_piece_well_placed_says_so(self):
        held = {**self.RULE, "current": "ci_check"}
        dev = self._others(self._decisions(held)[1])["dev"]
        self.assertEqual((dev["outcome"], dev["destination"], dev["concept"]), ("moves", "ci_check", None))

    def test_an_answer_the_piece_never_used_is_not_read_by_the_other_options(self):
        for unused in ("always", "bogus"):
            piece = {**self.RULE, "answers": {**self.RULE["answers"], "scope": unused}}
            other = self._others(self._decisions(piece)[0])["no"]
            self.assertEqual(other["outcome"], "opens", unused)

    def test_the_flag_never_refuses_a_file_the_plain_review_accepts(self):
        piece = {**self.RULE, "answers": {**self.RULE["answers"], "scope": "bogus"}}
        self.assertEqual((self._review([piece])[0], self._review([piece], "--decisions")[0]), (0, 0))

    def test_every_decision_of_the_shipped_grid_has_an_option_that_changes_the_result(self):
        """Why the command cannot say "assume this one": the skill's text decides what to ask."""
        for qid in place.DECISIONS:
            targets = {place._target(o) for o in GRID["questions"][qid]["options"].values()}
            self.assertGreater(len(targets), 1, qid)

    def test_a_piece_with_no_decision_or_still_waiting_is_not_listed(self):
        procedure = {"piece": "The steps", "answers": {"nature": "procedure"}, "current": "skill"}
        waiting = {"piece": "Tests pass", "answers": {"nature": "rule"}, "current": "skill"}
        self.assertEqual(self._decisions(procedure, waiting), [])

    def test_the_pieces_given_are_not_changed(self):
        before = json.dumps(self.RULE, sort_keys=True)
        self._decisions(self.RULE)
        self.assertEqual(json.dumps(self.RULE, sort_keys=True), before)

    def _review(self, pieces, *flags):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pieces.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(pieces, fh)
            return run_cli("place", "review", path, *flags)

    def test_the_flag_adds_a_section_in_plain_words_after_the_same_review(self):
        code_plain, plain = self._review([self.RULE])
        code, out = self._review([self.RULE], "--decisions")
        self.assertEqual((code_plain, code), (0, 0))
        self.assertTrue(out.startswith(plain))
        added = out[len(plain):]
        self.assertIn(GRID["questions"]["bypass_rule"]["text"], added)
        self.assertIn(GRID["questions"]["bypass_rule"]["options"]["agent"]["label"], added)
        self.assertIn(GRID["destinations"]["hook_check"]["name"], added)
        self.assertNotIn("bypass_rule", added)
        self.assertNotIn("hook_check", added)
        self.assertIsNone(LEVEL_OR_CODE.search(added), LEVEL_OR_CODE.findall(added))

    def test_without_the_flag_the_json_review_has_no_decisions(self):
        _, plain = self._review([self.RULE], "--format", "json")
        _, flagged = self._review([self.RULE], "--decisions", "--format", "json")
        self.assertNotIn("decisions", json.loads(plain))
        self.assertEqual([d["question"] for d in json.loads(flagged)["decisions"]], ["incident", "bypass_rule"])

    def test_the_flag_keeps_the_exit_code_of_a_review_that_waits(self):
        waiting = {"piece": "Tests pass", "answers": {"nature": "rule"}, "current": "skill"}
        code, _ = self._review([self.RULE, waiting], "--decisions")
        self.assertEqual(code, 3)

    def test_the_decision_questions_exist_in_the_grid(self):
        self.assertEqual(set(place.DECISIONS) - set(GRID["questions"]), set())


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
        pieces = [{"piece": "Never push to main", "answers": {"nature": "limit", "bypass_limit": "dev"},
                   "current": "agents_md"},
                  {"piece": "Review the PR", "answers": {"nature": "judgment"}}]
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
