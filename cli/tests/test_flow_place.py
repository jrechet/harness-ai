"""Tests of `flow place`: each step of a team's flow has one place, read from the definition
file alone, and the answer says which question decided. Needing a workflow engine is an answer;
a gate nobody can judge and a step with a missing answer are failures."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import flow_place, place  # noqa: E402

LIB = os.path.dirname(os.path.abspath(flow_place.__file__))

# The contract (docs/workflow-harness/flow-spec.md, section 6), to the letter: the guide
# decide.md copies the same sentences, so a change here is a change of both.
QUESTIONS = {
    "who": ("Who performs this step?", "type"),
    "judge": ("Can the person who approves really judge what they approve?", "can_judge"),
    "survive": ("How long does it live, and what must survive?", "survives"),
    "spread": ("Does the work split into many independent units?", "units"),
    "repos": ("How many repositories need this step?", "repositories"),
    "determined": ("Is the right output determined by the inputs?", "type"),
    "weakness": ("Is this step here because today's model is weak?", "weak_model"),
}
DESTINATIONS = {
    "code": ("L3", "this is code"),
    "skill": ("L2", "a skill is enough"),
    "dated_skill": ("L2", "a skill is enough, with its date"),
    "ticket_state": ("L4", "the ticket holds this"),
    "human_gate": ("L4", "this is a human gate"),
    "no_gate": ("-", "no gate here"),
    "reusable_workflow": ("L4", "this is a shared CI workflow"),
    "campaign": ("L4", "this is a fan-out by script"),
    "durable_engine": ("L4", "this would need an engine"),
}
# Question → step value → where it leads: ("ask", question) or ("place", destination).
TREE = {
    "who": {"code": ("ask", "survive"), "agent": ("ask", "survive"), "human": ("place", "ticket_state"),
            "wait": ("place", "ticket_state"), "gate": ("ask", "judge")},
    "judge": {"yes": ("place", "human_gate"), "no": ("place", "no_gate")},
    "survive": {"restart": ("ask", "spread"), "midway": ("place", "durable_engine")},
    "spread": {"one": ("ask", "repos"), "many": ("place", "campaign")},
    "repos": {"one": ("ask", "determined"), "several": ("place", "reusable_workflow")},
    "determined": {"code": ("place", "code"), "agent": ("ask", "weakness")},
    "weakness": {"yes": ("place", "dated_skill"), "no": ("place", "skill")},
}
DETERMINED_ANSWERS = {"code": "yes", "agent": "no"}

RUNS = {"survives": "restart", "units": "one", "repositories": "one"}


def step(kind, **keys):
    return {"type": kind, "does": f"Does the work of a {kind} step", "on": {"ok": {"to": "done"}}, **keys}


def flow_of(**states):
    return {"format": 1, "name": "tiny", "start": next(iter(states)), "stop_at": "end",
            "budget": {"dollars": 1, "minutes": 10}, "states": states}


# One small step per destination, with the question that must have decided and its answer.
REACH = [
    ("code", step("code", **RUNS), "determined", "yes"),
    ("skill", step("agent", weak_model="no", **RUNS), "weakness", "no"),
    ("dated_skill", step("agent", weak_model="yes", **RUNS), "weakness", "yes"),
    ("ticket_state", step("wait", deadline_hours=6), "who", "wait"),
    ("ticket_state", step("human", deadline_hours=6), "who", "human"),
    ("human_gate", step("gate", judge="a maintainer", shows="the branch", can_judge="yes"), "judge", "yes"),
    ("no_gate", step("gate", judge="the product owner", shows="the diff", can_judge="no"), "judge", "no"),
    ("reusable_workflow", step("code", survives="restart", units="one", repositories="several"),
     "repos", "several"),
    ("campaign", step("agent", survives="restart", units="many"), "spread", "many"),
    ("durable_engine", step("code", survives="midway"), "survive", "midway"),
]

# The small flow of the contract's section 1, reduced to what `flow place` reads.
SMALL = flow_of(
    ready=step("code", **RUNS),
    coding={"type": "agent", "does": "Implements the ticket and its tests", "cap": 3, "weak_model": "no",
            "on": {"code_written": {"to": "approval"}}, **RUNS},
    approval={"type": "gate", "does": "A maintainer reads the branch and says whether a PR may be opened",
              "judge": "a maintainer of the repository", "shows": "the branch", "deadline_hours": 48,
              "can_judge": "yes", "on": {"approved": {"to": "done"}}},
    ci_wait=step("wait", deadline_hours=6),
)
SMALL["name"] = "small"


def one(state_step):
    """The placement of a flow of one step: its only entry."""
    return flow_place.place(flow_of(only=state_step))["steps"][0]


def run_main(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = flow_place.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class WithFiles(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write(self, value, name="flow.json"):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value if isinstance(value, str) else json.dumps(value))
        return path


class TestGridFile(unittest.TestCase):
    def setUp(self):
        self.grid = flow_place.load_grid()

    def test_the_grid_is_sound_for_the_existing_placement_module(self):
        self.assertEqual(place.validate(self.grid), [])

    def test_the_seven_questions_have_the_contract_text_and_step_key(self):
        self.assertEqual(self.grid["root"], "who")
        self.assertEqual(list(self.grid["questions"]), list(QUESTIONS))
        for qid, (text, key) in QUESTIONS.items():
            with self.subTest(question=qid):
                self.assertEqual(self.grid["questions"][qid]["text"], text)
                self.assertEqual(self.grid["questions"][qid]["from"]["key"], key)

    def test_the_nine_destinations_have_the_contract_layer_and_sentence(self):
        self.assertEqual(set(self.grid["destinations"]), set(DESTINATIONS))
        for did, (layer, says) in DESTINATIONS.items():
            with self.subTest(destination=did):
                self.assertEqual(self.grid["destinations"][did]["layer"], layer)
                self.assertEqual(self.grid["destinations"][did]["says"], says)

    def test_each_step_value_leads_where_the_contract_says(self):
        for qid, expected in TREE.items():
            question = self.grid["questions"][qid]
            with self.subTest(question=qid):
                self.assertEqual(set(question["from"]["map"]), set(expected))
                for value, target in expected.items():
                    option = question["options"][question["from"]["map"][value]]
                    self.assertEqual((("ask", option["ask"]) if "ask" in option else ("place", option["place"])),
                                     target, f"{qid}, step value {value}")

    def test_every_mapped_answer_is_an_option_and_every_option_is_mapped(self):
        for qid, question in self.grid["questions"].items():
            with self.subTest(question=qid):
                self.assertEqual(set(question["from"]["map"].values()), set(question["options"]))

    def test_determined_answers_yes_for_a_program_and_no_for_an_agent(self):
        self.assertEqual(self.grid["questions"]["determined"]["from"]["map"], DETERMINED_ANSWERS)

    def test_no_destination_for_a_graph_framework(self):
        text = json.dumps(self.grid["destinations"]).lower()
        self.assertNotIn("graph", text)

    def test_the_existing_grid_file_is_untouched(self):
        # The extension is a separate file: placement.json keeps its own tree, and the new
        # destinations do not leak into it.
        old = place.load_grid()
        self.assertEqual(place.validate(old), [])
        self.assertEqual(old["root"], "nature")
        for did in ("durable_engine", "no_gate", "campaign", "ticket_state", "human_gate", "reusable_workflow"):
            self.assertNotIn(did, old["destinations"])
        self.assertNotEqual(os.path.abspath(flow_place.GRID_FILE), os.path.abspath(place.GRID_FILE))
        self.assertEqual(os.path.dirname(os.path.abspath(flow_place.GRID_FILE)), LIB)


class TestEachDestination(unittest.TestCase):
    def test_each_destination_is_reachable_from_a_step(self):
        reached = set()
        for destination, state_step, question, answer in REACH:
            with self.subTest(destination=destination, type=state_step["type"]):
                entry = one(state_step)
                self.assertEqual(entry["status"], "placed")
                self.assertEqual(entry["destination"], destination)
                self.assertEqual(entry["says"], DESTINATIONS[destination][1])
                self.assertIsNone(entry["missing"])
                reached.add(entry["destination"])
        self.assertEqual(reached, set(DESTINATIONS))

    def test_the_question_that_decided_is_reported_with_its_text(self):
        for destination, state_step, question, answer in REACH:
            with self.subTest(destination=destination, type=state_step["type"]):
                entry = one(state_step)
                self.assertEqual(entry["decided_by"],
                                 {"question": question, "text": QUESTIONS[question][0], "answer": answer})
                self.assertEqual(entry["path"][-1], {"question": question, "answer": answer})
                self.assertEqual(entry["path"][0]["question"], "who")

    def test_a_placed_step_carries_the_name_and_the_reason_of_its_destination(self):
        grid = flow_place.load_grid()
        for destination, state_step, _, _ in REACH:
            with self.subTest(destination=destination):
                entry = one(state_step)
                self.assertEqual(entry["name"], grid["destinations"][destination]["name"])
                self.assertEqual(entry["reason"], grid["destinations"][destination]["why"])
                self.assertTrue(entry["reason"].strip())

    def test_the_path_of_an_agent_step_is_the_one_of_the_contract(self):
        entry = flow_place.place(SMALL)["steps"][1]
        self.assertEqual(entry, {
            "state": "coding", "type": "agent", "does": "Implements the ticket and its tests", "shows": None,
            "status": "placed", "destination": "skill", "name": entry["name"], "says": "a skill is enough",
            "path": [{"question": "who", "answer": "agent"}, {"question": "survive", "answer": "restart"},
                     {"question": "spread", "answer": "one"}, {"question": "repos", "answer": "one"},
                     {"question": "determined", "answer": "no"}, {"question": "weakness", "answer": "no"}],
            "decided_by": {"question": "weakness", "text": "Is this step here because today's model is weak?",
                           "answer": "no"},
            "reason": entry["reason"], "missing": None})

    def test_keys_off_the_path_do_not_move_a_step(self):
        # A wait that says it survives midway is still a ticket state: nothing runs while it lasts.
        self.assertEqual(one(step("wait", survives="midway", can_judge="no"))["destination"], "ticket_state")
        self.assertEqual(one(step("code", weak_model="yes", can_judge="no", **RUNS))["destination"], "code")

    def test_a_gate_reports_what_its_judge_is_shown(self):
        self.assertEqual(one(REACH[5][1])["shows"], "the branch")
        self.assertIsNone(one(step("gate", can_judge="yes", shows=""))["shows"])
        self.assertIsNone(one(step("gate", can_judge="yes", shows=3))["shows"])
        self.assertIsNone(one(step("code", **RUNS))["shows"])


class TestOpenSteps(unittest.TestCase):
    def assert_open(self, state_step, question, key, path_length):
        entry = one(state_step)
        self.assertEqual(entry["status"], "open")
        for field in ("destination", "name", "says", "decided_by", "reason"):
            self.assertIsNone(entry[field], field)
        self.assertEqual(entry["missing"], {"question": question, "text": QUESTIONS[question][0], "key": key})
        self.assertEqual(len(entry["path"]), path_length)
        return entry

    def test_a_gate_that_does_not_say_whether_it_can_be_judged_is_open(self):
        entry = self.assert_open(step("gate", judge="a maintainer", shows="the branch"), "judge", "can_judge", 1)
        self.assertEqual(entry["path"], [{"question": "who", "answer": "gate"}])

    def test_a_program_step_with_a_missing_answer_is_open_at_that_question(self):
        self.assert_open(step("code"), "survive", "survives", 1)
        self.assert_open(step("code", survives="restart"), "spread", "units", 2)
        self.assert_open(step("code", survives="restart", units="one"), "repos", "repositories", 3)
        self.assert_open(step("agent", **RUNS), "weakness", "weak_model", 5)

    def test_an_unknown_type_leaves_the_step_open_at_the_first_question(self):
        for kind in ("robot", None, 3, ["code"], {"a": 1}, True):
            with self.subTest(type=kind):
                state_step = step("code", **RUNS)
                state_step["type"] = kind
                self.assert_open(state_step, "who", "type", 0)
        missing = step("code", **RUNS)
        del missing["type"]
        self.assert_open(missing, "who", "type", 0)

    def test_a_value_outside_the_answers_is_no_answer(self):
        for value in ("maybe", "Yes", "YES", " yes", True, 1, None, ["yes"]):
            with self.subTest(can_judge=value):
                self.assert_open(step("gate", can_judge=value), "judge", "can_judge", 1)
        self.assert_open(step("code", survives="forever"), "survive", "survives", 1)

    def test_an_open_step_makes_the_verdict_open_and_fails(self):
        result = flow_place.place(flow_of(a=step("code", **RUNS), b=step("agent", **RUNS),
                                          c=step("code", survives="midway"), d=step("gate")))
        self.assertEqual(result["open"], ["b", "d"])
        self.assertEqual(result["engine"], ["c"])
        self.assertEqual(result["verdict"]["code"], "open")
        self.assertFalse(result["passed"])
        sentence = result["verdict"]["sentence"]
        self.assertIn("2 steps cannot be placed yet", sentence)
        self.assertIn('b has no answer to "Is this step here because today\'s model is weak?" (key weak_model)',
                      sentence)
        self.assertIn("(key can_judge)", sentence)


class TestVerdict(unittest.TestCase):
    def test_no_step_needs_an_engine(self):
        result = flow_place.place(SMALL)
        self.assertEqual(result["flow"], "small")
        self.assertEqual([s["state"] for s in result["steps"]], ["ready", "coding", "approval", "ci_wait"])
        self.assertEqual([s["destination"] for s in result["steps"]],
                         ["code", "skill", "human_gate", "ticket_state"])
        self.assertEqual((result["engine"], result["refused_gates"], result["open"]), ([], [], []))
        self.assertEqual(result["verdict"], {"code": "no_engine", "sentence": "No step needs an engine."})
        self.assertIs(result["passed"], True)
        self.assertEqual(list(result), ["flow", "steps", "engine", "refused_gates", "open", "verdict", "passed"])

    def test_a_step_that_truly_needs_an_engine_is_an_answer_not_a_failure(self):
        flow = copy.deepcopy(SMALL)
        flow["states"]["settle"] = {"type": "code", "does": "Pays the supplier, once and only once.",
                                    "survives": "midway", "on": {"paid": {"to": "done"}}}
        result = flow_place.place(flow)
        self.assertEqual(result["engine"], ["settle"])
        self.assertEqual(result["steps"][-1]["destination"], "durable_engine")
        self.assertEqual(result["verdict"]["code"], "engine")
        self.assertIs(result["passed"], True)
        sentence = result["verdict"]["sentence"]
        self.assertTrue(sentence.startswith(
            "One step would need an engine: settle, Pays the supplier, once and only once. "), sentence)
        self.assertTrue(sentence.endswith(result["steps"][-1]["reason"]), sentence)
        self.assertNotIn("once..", sentence)

    def test_decoys_do_not_need_an_engine(self):
        # They look long, they are not: a wait of a week, a gate with a long deadline, an agent of
        # a few hours that may start again.
        result = flow_place.place(flow_of(
            week=step("wait", deadline_hours=168),
            board=step("gate", can_judge="yes", deadline_hours=720, judge="the board", shows="the plan"),
            long_agent=step("agent", weak_model="no", deadline_hours=5, **RUNS)))
        self.assertEqual(result["engine"], [])
        self.assertEqual(result["verdict"]["code"], "no_engine")

    def test_several_steps_that_need_an_engine_are_all_named(self):
        result = flow_place.place(flow_of(a=step("code", survives="midway"), b=step("code", **RUNS),
                                          c=step("agent", survives="midway")))
        self.assertEqual(result["engine"], ["a", "c"])
        sentence = result["verdict"]["sentence"]
        self.assertTrue(sentence.startswith("2 steps would need an engine: a, "), sentence)
        self.assertIn("; c, ", sentence)

    def test_a_gate_nobody_can_judge_fails_the_placement(self):
        flow = copy.deepcopy(SMALL)
        flow["states"]["approval"]["can_judge"] = "no"
        result = flow_place.place(flow)
        gate = result["steps"][2]
        self.assertEqual((gate["status"], gate["destination"], gate["says"]), ("placed", "no_gate", "no gate here"))
        self.assertEqual(result["refused_gates"], ["approval"])
        self.assertEqual(result["open"], [])
        # A refused gate is placed: the verdict speaks of engines only, `passed` carries the failure.
        self.assertEqual(result["verdict"]["code"], "no_engine")
        self.assertIs(result["passed"], False)

    def test_the_lists_follow_the_file_order(self):
        result = flow_place.place(flow_of(
            z=step("gate", can_judge="no"), y=step("code", survives="midway"), x=step("code"),
            w=step("gate", can_judge="no"), v=step("agent", survives="midway"), u=step("gate")))
        self.assertEqual([s["state"] for s in result["steps"]], ["z", "y", "x", "w", "v", "u"])
        self.assertEqual(result["refused_gates"], ["z", "w"])
        self.assertEqual(result["engine"], ["y", "v"])
        self.assertEqual(result["open"], ["x", "u"])


class TestWhatPlaceAccepts(unittest.TestCase):
    def test_a_value_that_is_not_a_flow_is_refused(self):
        for value in (None, [], "flow", 3, {}, {"states": []}, {"states": "x"}, {"states": {"a": "code"}},
                      {"states": {"a": step("code"), "b": None}}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as caught:
                    flow_place.place(value)
                self.assertTrue(str(caught.exception).strip())

    def test_it_places_what_it_finds_without_checking_the_flow(self):
        # No format, no start, no budget, a step with no sentence: `flow check` would refuse it,
        # `flow place` still says where its steps go.
        result = flow_place.place({"states": {"a": {"type": "code", **RUNS}}})
        self.assertIsNone(result["flow"])
        self.assertIsNone(result["steps"][0]["does"])
        self.assertEqual(result["steps"][0]["destination"], "code")
        self.assertEqual(flow_place.place({"name": 3, "states": {}})["flow"], None)

    def test_a_flow_with_no_step_has_nothing_to_refuse(self):
        result = flow_place.place({"name": "empty", "states": {}})
        self.assertEqual((result["steps"], result["verdict"]["code"], result["passed"]), ([], "no_engine", True))

    def test_the_definition_is_not_changed(self):
        before = copy.deepcopy(SMALL)
        flow_place.place(SMALL)
        self.assertEqual(SMALL, before)

    def test_the_same_definition_gives_the_same_document(self):
        self.assertEqual(flow_place.place(SMALL), flow_place.place(copy.deepcopy(SMALL)))
        json.dumps(flow_place.place(SMALL))


class TestCommand(WithFiles):
    def test_a_person_reads_one_line_per_step_then_the_verdict(self):
        code, out, err = run_main(self.write(SMALL))
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), [
            '- ready (a program): this is code. Decided by "Is the right output determined by the inputs?": yes.',
            '- coding (an agent): a skill is enough. Decided by "Is this step here because today\'s model is '
            'weak?": no.',
            '- approval (a person decides): this is a human gate. Decided by "Can the person who approves really '
            'judge what they approve?": yes. Shown to a maintainer of the repository: the branch.',
            '- ci_wait (waits): the ticket holds this. Decided by "Who performs this step?": wait.',
            "",
            "Verdict: no step needs an engine."])

    def test_the_words_for_a_step_type_are_the_ones_of_the_contract(self):
        self.assertEqual(flow_place.TYPE_WORDS, {"code": "a program", "agent": "an agent",
                                                 "human": "a person works", "gate": "a person decides",
                                                 "wait": "waits"})

    def test_no_internal_id_is_printed_without_its_meaning(self):
        _, out, _ = run_main(self.write(SMALL))
        for internal in ("human_gate", "ticket_state", "no_engine", "weak_model", "L2", "L4"):
            self.assertNotIn(internal, out)

    def test_json_is_the_place_document(self):
        code, out, _ = run_main(self.write(SMALL), "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), flow_place.place(SMALL))

    def test_an_engine_is_said_and_exits_zero(self):
        flow = flow_of(settle={"type": "code", "does": "Pays the supplier once", "survives": "midway",
                               "on": {"paid": {"to": "done"}}})
        code, out, _ = run_main(self.write(flow))
        self.assertEqual(code, 0)
        self.assertIn("- settle (a program): this would need an engine. Decided by "
                      '"How long does it live, and what must survive?": midway.', out)
        self.assertIn("\nVerdict: one step would need an engine: settle, Pays the supplier once. ", out)

    def test_a_gate_nobody_can_judge_is_said_and_exits_one(self):
        flow = copy.deepcopy(SMALL)
        flow["states"]["approval"]["can_judge"] = "no"
        code, out, _ = run_main(self.write(flow))
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertIn('- approval (a person decides): no gate here. Decided by "Can the person who approves '
                      'really judge what they approve?": no. Shown to a maintainer of the repository: the branch.',
                      lines)
        self.assertEqual(lines[-2:], [
            "Verdict: no step needs an engine.",
            "A gate nobody can judge: approval. Remove it, or give a maintainer of the repository something "
            "they can read and refuse."])

    def test_a_refused_gate_with_no_judge_named_still_reads_as_a_sentence(self):
        code, out, _ = run_main(self.write(flow_of(sign_off=step("gate", can_judge="no"))))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1],
                         "A gate nobody can judge: sign_off. Remove it, or give its judge something "
                         "they can read and refuse.")
        self.assertNotIn("Shown to", out)

    def test_a_step_that_cannot_be_placed_is_said_with_the_key_to_add_and_exits_one(self):
        flow = copy.deepcopy(SMALL)
        del flow["states"]["coding"]["weak_model"]
        code, out, _ = run_main(self.write(flow))
        self.assertEqual(code, 1)
        self.assertIn('- coding (an agent): cannot be placed yet. No answer to "Is this step here because '
                      'today\'s model is weak?" (key weak_model).', out.splitlines())
        self.assertEqual(out.splitlines()[-1],
                         'Verdict: 1 step cannot be placed yet: coding has no answer to "Is this step here '
                         'because today\'s model is weak?" (key weak_model).')

    def test_an_unknown_type_is_printed_as_written(self):
        code, out, _ = run_main(self.write(flow_of(odd=step("robot"))))
        self.assertEqual(code, 1)
        self.assertIn('- odd (robot): cannot be placed yet. No answer to "Who performs this step?" (key type).',
                      out.splitlines())

    def test_a_missing_file_or_a_file_that_is_not_json_is_a_usage_error(self):
        for path in (os.path.join(self.folder, "absent.json"), self.write("{not json", "broken.json")):
            with self.subTest(path=os.path.basename(path)):
                code, out, err = run_main(path)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("flow: "), err)
                self.assertIn(path, err)

    def test_json_that_is_not_a_flow_is_exit_two(self):
        for value in ([], "text", {"states": [1]}, {"name": "x"}):
            with self.subTest(value=value):
                code, out, err = run_main(self.write(value), "--format", "json")
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("flow: "), err)


if __name__ == "__main__":
    unittest.main()
