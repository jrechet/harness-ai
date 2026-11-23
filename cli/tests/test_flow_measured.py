"""Tests of `flow place --answers` and `flow status --answers` (docs/workflow-harness/flow-spec.md,
section 12.5): the symptoms a team measured on its own runs, recorded for `flow fit`, are read
beside the definition. A symptom that fired is never hidden behind "no step needs an engine", a
file of answers that are all "not measured" never reads as reassurance, and numbers measured on
something that is not a ticket workflow are refused, never dropped in silence. The level, `passed`
and the exit code do not change: a symptom is a fact about runs, the level is read from the file."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow, flow_fit, flow_place  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAMILY = os.path.join(ROOT, "fixtures", "flow")
FEATURE = os.path.join(FAMILY, "definitions", "feature.json")
BUG = os.path.join(FAMILY, "definitions", "bug.json")
FIRED = os.path.join(FAMILY, "fit", "symptom-fired", "answers.json")
NOTHING_ABOVE = os.path.join(FAMILY, "fit", "ticket-state-and-ci", "answers.json")
NOTHING_MEASURED = os.path.join(FAMILY, "fit", "nothing-measured", "answers.json")
OWN_APP = os.path.join(FAMILY, "fit", "own-agent-app", "answers.json")
REFUSED = os.path.join(FAMILY, "fit", "refused", "answers.json")
SYMPTOMS = ("runs_paid_twice", "double_runs", "silent_events", "agent_loops", "waits_inside_computation",
            "steps_with_own_retry_rule", "order_breaks", "tickets_without_cost")

SAID_FIRED = ("2 symptoms are measured above their threshold: double_runs is 2, above 0; agent_loops is 3, above 0. "
              "Not measured, so not counted as fine: order_breaks. No command can tell which step a symptom "
              "comes from.")
SAID_NOTHING_ABOVE = ("Measured on your own runs: 7 of the 8 symptoms, none above its threshold. Not measured, so not "
                      "counted as fine: tickets_without_cost. Listed for you to judge, no threshold is written for "
                      "it: steps_with_own_retry_rule is 4.")
SAID_NOTHING_MEASURED = ("Nothing was measured on your own runs, so nothing is known from them. Not measured, so not "
                         "counted as fine: " + ", ".join(SYMPTOMS) + ".")
NOT_READ = ("Measured symptoms were not read: this answer comes from the file alone. To read them, add --answers "
            "<the answers file given to flow fit>.")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return flow_fit.parse(fh.read())


def measured(path):
    return flow_fit.measured(load(path))


def answers(**symptoms):
    return {"building": "ticket_workflow", "tickets_per_week": 10, "chained_by_hand": "no",
            "symptoms": {**dict.fromkeys(SYMPTOMS, 0), **symptoms}}


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def engine_alone():
    definition = flow.load_definition(BUG)
    definition = copy.deepcopy(definition)
    definition["states"]["closure_check"]["survives"] = "midway"
    return definition


class MeasuredTest(unittest.TestCase):
    def test_measured_gives_what_fit_found(self):
        found = measured(FIRED)
        document = flow_fit.fit(load(FIRED))
        self.assertEqual(list(found), ["fired", "sentence", "not_deciding", "not_measured", "symptoms"])
        self.assertEqual(found["fired"], document["fired"])
        self.assertEqual(found["sentence"], document["verdict"]["sentence"])
        self.assertEqual((found["not_deciding"], found["not_measured"], found["symptoms"]), ([], ["order_breaks"], 8))
        quiet = measured(NOTHING_ABOVE)
        self.assertIsNone(quiet["sentence"])
        self.assertEqual([entry["key"] for entry in quiet["not_deciding"]], ["steps_with_own_retry_rule"])

    def test_answers_fit_refuses_or_that_describe_another_tool_raise(self):
        with self.assertRaises(ValueError) as refused:
            flow_fit.measured(load(REFUSED), "a.json", "f.json")
        self.assertEqual(str(refused.exception), "a.json: flow fit refuses these answers (4 to fix). Run flow fit a.json.")
        with self.assertRaises(ValueError) as tool:
            flow_fit.measured(load(OWN_APP), "a.json", "f.json")
        self.assertEqual(str(tool.exception),
                         "a.json: these answers describe your own agent application in Python or TypeScript, with a "
                         "known graph and pauses in the process, not a ticket workflow, and f.json is a ticket "
                         "workflow. Give the answers measured on the runs of this flow.")

    def test_what_is_said_of_the_runs_in_each_case(self):
        self.assertEqual(flow_fit.said_of_runs(measured(FIRED)), SAID_FIRED)
        self.assertEqual(flow_fit.said_of_runs(measured(NOTHING_ABOVE)), SAID_NOTHING_ABOVE)
        self.assertEqual(flow_fit.said_of_runs(measured(NOTHING_MEASURED)), SAID_NOTHING_MEASURED)
        self.assertEqual(flow_fit.said_of_runs(flow_fit.measured(answers())),
                         "None of the 8 symptoms measured on your own runs is above its threshold.")
        one = flow_fit.measured(answers(double_runs=1, steps_with_own_retry_rule=2, order_breaks=0.0))
        self.assertEqual(flow_fit.said_of_runs(one),
                         "A symptom is measured above its threshold: double_runs is 1, above 0. Listed for you to "
                         "judge, no threshold is written for it: steps_with_own_retry_rule is 2. No command can "
                         "tell which step a symptom comes from.")


class PlaceTest(unittest.TestCase):
    def test_a_symptom_on_a_flow_where_no_step_needs_an_engine(self):
        document = flow_place.place(flow.load_definition(FEATURE), measured(FIRED))
        self.assertEqual(document["verdict"], {"code": "symptom",
                                               "sentence": "No step is written as needing an engine. " + SAID_FIRED})
        self.assertIs(document["passed"], True)
        self.assertEqual(list(document)[-2:], ["passed", "measured"])
        self.assertEqual(document["measured"], measured(FIRED))

    def test_no_symptom_still_says_what_was_measured(self):
        definition = flow.load_definition(FEATURE)
        for path, said in ((NOTHING_ABOVE, SAID_NOTHING_ABOVE), (NOTHING_MEASURED, SAID_NOTHING_MEASURED)):
            with self.subTest(answers=os.path.basename(os.path.dirname(path))):
                verdict = flow_place.place(definition, measured(path))["verdict"]
                self.assertEqual(verdict, {"code": "no_engine",
                                           "sentence": "No step needs an engine, as the file is written. " + said})

    def test_an_engine_or_an_open_step_keeps_its_code_and_gains_what_was_measured(self):
        alone = flow_place.place(engine_alone())
        beside = flow_place.place(engine_alone(), measured(FIRED))
        self.assertEqual(beside["verdict"], {"code": "engine", "sentence": alone["verdict"]["sentence"] + " " + SAID_FIRED})
        opened = flow.new("bug")
        self.assertEqual(flow_place.place(opened, measured(FIRED))["verdict"]["code"], "open")
        self.assertTrue(flow_place.place(opened, measured(FIRED))["verdict"]["sentence"].endswith(" " + SAID_FIRED))

    def test_without_answers_nothing_changes_and_measured_is_null(self):
        document = flow_place.place(flow.load_definition(FEATURE))
        self.assertEqual(document["verdict"], {"code": "no_engine", "sentence": "No step needs an engine."})
        self.assertIsNone(document["measured"])


class StatusTest(unittest.TestCase):
    def test_the_status_document_ends_with_what_was_measured_and_the_level_does_not_move(self):
        definition = flow.load_definition(FEATURE)
        state = flow.status(definition, measured=measured(FIRED))
        self.assertEqual(list(state)[-3:], ["waiting", "bounds", "measured"])
        self.assertEqual(state["measured"], measured(FIRED))
        self.assertEqual(state["level"]["reached"], 1)
        self.assertIsNone(flow.status(definition)["measured"])


class WithFiles(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, name, text):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class CommandTest(WithFiles):
    def test_flow_place_with_answers_prints_the_verdict_of_the_contract(self):
        code, out, err = call("place", FEATURE, "--answers", FIRED)
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("\nVerdict: no step is written as needing an engine. " + SAID_FIRED + "\n"), out)
        self.assertIn(f"Symptoms read from {FIRED}: 2 above threshold, 0 listed without a threshold, 1 not measured "
                      f"(never counted as fine). flow fit {FIRED} gives the smallest fix to try first for each.",
                      err.splitlines())
        self.assertIn(f"Next: flow status {FEATURE} --map --answers {FIRED}", err.splitlines())
        for path, said in ((NOTHING_ABOVE, SAID_NOTHING_ABOVE), (NOTHING_MEASURED, SAID_NOTHING_MEASURED)):
            out = call("place", FEATURE, "--answers", path)[1]
            self.assertTrue(out.endswith("\nVerdict: no step needs an engine, as the file is written. " + said + "\n"))

    def test_flow_place_with_answers_as_json(self):
        code, out, err = call("place", FEATURE, "--answers", FIRED, "--format", "json")
        self.assertEqual((code, err), (0, ""))
        document = json.loads(out)
        self.assertEqual(document["verdict"]["code"], "symptom")
        self.assertEqual([entry["key"] for entry in document["measured"]["fired"]], ["double_runs", "agent_loops"])

    def test_without_answers_the_notes_say_the_symptoms_were_not_read(self):
        code, out, err = call("place", FEATURE)
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("\nVerdict: no step needs an engine.\n"))
        lines = err.splitlines()
        self.assertIn(NOT_READ, lines)
        self.assertLess(lines.index(NOT_READ), lines.index(f"Next: flow status {FEATURE} --map"))
        lines = call("status", FEATURE, "--map")[2].splitlines()
        self.assertIn(NOT_READ, lines)

    def test_flow_status_says_what_was_measured_after_the_bounds_and_last_without_the_map(self):
        code, out, _ = call("status", FEATURE, "--map", "--answers", FIRED)
        self.assertEqual(code, 0)
        lines = out.splitlines()
        said = "From your own runs: " + SAID_FIRED
        self.assertIn(said, lines)
        self.assertTrue(lines[lines.index(said) - 1].startswith("- The event deployed of delivery"), lines)
        self.assertEqual(call("status", FEATURE, "--answers", FIRED)[1].splitlines()[-1], said)
        self.assertNotIn("From your own runs", call("status", FEATURE, "--map")[1])

    def test_the_command_a_refusal_gives_is_safe_to_paste(self):
        # Section 12.4: a path inside a command is quoted for a shell, here as in every other note.
        with open(REFUSED, encoding="utf-8") as fh:
            spaced = self.write("my answers.json", fh.read())
        for command in ("place", "status"):
            with self.subTest(command=command):
                code, out, err = call(command, FEATURE, "--answers", spaced)
                self.assertEqual((code, out), (2, ""))
                self.assertEqual(err, f"flow: {spaced}: flow fit refuses these answers (4 to fix). "
                                      f"Run flow fit {shlex.quote(spaced)}.\n")

    def test_answers_that_cannot_be_read_or_are_refused_exit_2_with_nothing_on_stdout(self):
        broken = self.write("broken.json", "{not json")
        missing = os.path.join(self.folder, "nowhere.json")
        for command in ("place", "status"):
            for given in (broken, missing, "-"):
                with self.subTest(command=command, answers=given):
                    code, out, err = call(command, FEATURE, "--answers", given)
                    self.assertEqual((code, out), (2, ""))
                    self.assertTrue(err.startswith("flow: "), err)
            code, out, err = call(command, FEATURE, "--answers", REFUSED)
            self.assertEqual((code, out), (2, ""))
            self.assertEqual(err, f"flow: {REFUSED}: flow fit refuses these answers (4 to fix). Run flow fit {REFUSED}.\n")
            code, out, err = call(command, FEATURE, "--answers", OWN_APP)
            self.assertEqual((code, out), (2, ""))
            self.assertTrue(err.startswith(f"flow: {OWN_APP}: these answers describe your own agent application"), err)
            self.assertIn(f"and {FEATURE} is a ticket workflow.", err)

    def test_the_placement_module_takes_the_answers_in_its_arguments_and_prints_no_note(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = flow_place.main([FEATURE, "--answers", FIRED])
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertTrue(out.getvalue().endswith("\nVerdict: no step is written as needing an engine. " + SAID_FIRED + "\n"))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(flow_place.main([FEATURE, "--answers", OWN_APP]), 2)

    def test_the_standard_input_is_never_read_for_the_answers(self):
        with open(FIRED, encoding="utf-8") as fh:
            given = fh.read()
        for command in ("place", "status"):
            with self.subTest(command=command), mock.patch("sys.stdin", io.StringIO(given)):
                self.assertEqual(call(command, FEATURE, "--answers", "-"), (2, "", (
                    "flow: --answers -: the standard input is not read here; give the answers file of flow fit\n")))

    def test_the_numbers_listed_without_a_threshold_are_joined_by_a_semicolon(self):
        said = flow_fit.said_of_runs({"fired": [], "sentence": None, "not_measured": [], "symptoms": 8,
                                      "not_deciding": [{"key": "double_runs", "value": 3},
                                                       {"key": "steps_with_own_retry_rule", "value": 4}]})
        self.assertTrue(said.endswith(" Listed for you to judge, no threshold is written for it: double_runs is 3; "
                                      "steps_with_own_retry_rule is 4."), said)

    def test_flow_fit_never_reads_nothing_measured_as_reassurance(self):
        # Since the critics of section 12: flow fit and flow place say the same of answers that measure nothing.
        for chained in ("no", "yes"):
            given = {**load(NOTHING_MEASURED), "chained_by_hand": chained}
            with self.subTest(chained_by_hand=chained):
                why = flow_fit.fit(given)["why"]
                self.assertTrue(why.endswith("Nothing was measured on your own runs, so nothing is known from them."),
                                why)
                self.assertNotIn("measured symptom", why)
        self.assertIn("No measured symptom is above its threshold.", flow_fit.fit(load(NOTHING_ABOVE))["why"] + " "
                      + flow_fit.fit({**load(NOTHING_ABOVE), "chained_by_hand": "yes"})["why"])

    def test_a_key_written_twice_is_refused_as_flow_fit_refuses_it(self):
        text = json.dumps(answers()).replace('"tickets_per_week": 10', '"tickets_per_week": 10, "tickets_per_week": 3')
        code, out, err = call("place", FEATURE, "--answers", self.write("twice.json", text))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("flow fit refuses these answers (1 to fix)", err)


if __name__ == "__main__":
    unittest.main()
