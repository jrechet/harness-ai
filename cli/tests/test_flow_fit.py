"""Tests of `flow fit`: before any definition exists, a few recorded answers get one verdict from
a program. A missing or unknown answer is refused with the key to write, never guessed; a
symptom "not measured" is listed, never counted as fine. The contract is section 11 of
docs/workflow-harness/flow-spec.md; its three examples are held here word for word."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow_fit, flow_notes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "docs", "workflow-harness", "flow-spec.md")
FAMILY = os.path.join(ROOT, "fixtures", "flow", "fit")
NOT_MEASURED = "not measured"
SYMPTOMS = ("runs_paid_twice", "double_runs", "silent_events", "agent_loops", "waits_inside_computation",
            "steps_with_own_retry_rule", "order_breaks", "tickets_without_cost")
NO_ENGINE = ("agent_loops", "tickets_without_cost")
# What the report's table (section 8) names for each case that is not a ticket workflow.
TOOLS = {"own_agent_app": "LangGraph, or an agent SDK plus an engine",
         "agent_product": "A durable engine under a plain loop",
         "many_repositories": "A script and a CI matrix, one PR per repository",
         "long_lived_orchestrator": "Rust is reasonable"}
BUILDING = '"ticket_workflow", "own_agent_app", "agent_product", "many_repositories" or "long_lived_orchestrator"'
DOCUMENT_KEYS = {"passed", "problems", "verdict", "building", "tool", "why", "fired", "not_deciding", "not_measured",
                 "would_change", "source", "cost"}
# The one row of the table whose own wording is a quantity ("Many steps") with no number: it never fires.
NO_THRESHOLD = "steps_with_own_retry_rule"
COUNT = 'a whole number, 0 or more, or "not measured"'
HUGE = 10 ** 400

# The cost lines of section 12.3, which every verdict prints between its source and what was not measured.
COST_HEAD = "Cost, from the pages, facts of 2026-11-21 (nothing here is measured on your runs):\n"
AGENT_PASS = ("- One agent pass: near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, "
              "$1.00 flat; GitHub's heavy runs, about $1.20. Published [V] [V] [M] (report §5.4; costs.md §1).\n")
TICKET_COST = AGENT_PASS + """- One ticket from start to end: no published figure (report §5.4; report §9.1, item 2).
- One ticket, estimated: $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix. Arithmetic of the notes, not a measurement (report §5.4; costs.md §2).
"""
CI_MINUTE = "- One CI minute: $0.006 on a GitHub Actions Linux runner with 2 cores. Published [V] (costs.md §1).\n"
ENGINE_COST = """- The fee of a managed engine: about $50 per million actions on Temporal Cloud, with no base fee. Published [V] (report §3.5; costs.md §3).
- Writing one workflow for an engine: "1-2 days" on average for a custom Temporal workflow at Duolingo. Published [V, self-reported] (report §5.2).
- The people to host an engine yourself: no published figure (report §3.5; report §9.1, item 5).
"""


def tool_cost(choice):
    return f"- {choice}: no published figure (report §8: the table gives no price).\n"


EXAMPLE_1 = """Verdict: Ticket state and CI are enough.
Why: 12 tickets a week go through this path and the phases are chained by hand. The ticket or the pull request holds the state, and a short CI job runs each step. No measured symptom is above its threshold.
What would change this answer: One symptom measured above its threshold on your own runs: runs_paid_twice above 0.1, any other above 0, except steps_with_own_retry_rule, which has no threshold and is yours to judge.
Source: report §8, first row; report §7, last table.
""" + COST_HEAD + TICKET_COST + CI_MINUTE + """Not measured, so not counted as fine: runs_paid_twice (Runs die far in and pay their tokens twice); agent_loops (An agent loops and burns tokens); tickets_without_cost (You cannot say what a ticket cost).
"""
EXAMPLE_2 = """Verdict: A symptom is measured above its threshold: double_runs is 3, above 0.
Why: On a ticket workflow, a measured symptom is the only thing that calls for more than ticket state and CI. Try the smallest fix first; move on only when the symptom is still there.
- double_runs is 3, above 0: the report writes no threshold, so any measured occurrence above zero is named. Two runs on one ticket. First try: One run at a time per ticket; keys derived from the ticket, never random. What removes it by design: An engine with one workflow per ticket.
What would change this answer: Each symptom named above back at or under its threshold after its smallest fix: then ticket state and CI are enough. If one stays, the report's choice is a managed engine (Temporal Cloud), one workflow per ticket; the worker can be Rust.
Source: report §7, last table; report §8, second row; decide.md §3.
""" + COST_HEAD + TICKET_COST + ENGINE_COST + """Not measured: nothing. Every symptom has a number.
"""
EXAMPLE_3 = f"""Refused: 3 answers to fix. No verdict is given on a guess.
- "building" is "chatbot": write {BUILDING}.
- Add "tickets_per_week": a number, 0 or more.
- Add "double_runs" under "symptoms": a whole number, 0 or more, or "not measured".
"""

# What a person reads for the verdicts the three examples of the contract do not show, word for word.
PRINTED = {
    "own_agent_app": """Verdict: For your own agent application in Python or TypeScript, with a known graph and pauses in the process: LangGraph, or an agent SDK plus an engine.
Why: You write the agent application yourself, the graph is known, and a run must pause inside the process. The symptoms describe a ticket workflow: they did not decide here.
What would change this answer: The number of runs that must pause for a person inside the process. At zero, or when the flow is a straight line, a script is enough; when the step already runs inside a coding agent, use skills and hooks.
Source: report §8, fourth row; report §2.7.
""" + COST_HEAD + tool_cost(TOOLS["own_agent_app"]) + AGENT_PASS + """Not measured: nothing. Every symptom has a number.
""",
    "agent_product": """Verdict: For an agent product for users, with sessions that resume mid-run: A durable engine under a plain loop.
Why: Sessions of your users must resume mid-run. That is where Cursor and Replit use an engine. The symptoms describe a ticket workflow: they did not decide here.
What would change this answer: The number of sessions that must resume mid-run. At zero, this row of the table no longer describes you: answer again.
Source: report §8, third row; report §5.2.
""" + COST_HEAD + ENGINE_COST + """Not measured: nothing. Every symptom has a number.
""",
    "many_repositories": """Verdict: For the same change across hundreds of repositories: A script and a CI matrix, one PR per repository.
Why: It is a different job from one ticket to one pull request: a script fans out, with one writer per repository. The symptoms describe a ticket workflow: they did not decide here.
What would change this answer: The number of repositories that get the change. The report says "hundreds" in its table and "tens or hundreds of independent units" in its grid: it gives no lower bound. For "several" repositories its grid names something else, a versioned plugin and a reusable CI workflow.
Source: report §8, fifth row; report §7, questions 5 and 7.
""" + COST_HEAD + tool_cost(TOOLS["many_repositories"]) + AGENT_PASS + """Not measured: nothing. Every symptom has a number.
""",
    "long_lived_orchestrator": """Verdict: For a long-lived orchestrator, a tool server or a binary for many teams: Rust is reasonable.
Why: The code part is a program worth compiling: a binary handed to many repositories, or an orchestrator that lives long. Rust buys nothing on the duration or the model cost of a ticket. The symptoms describe a ticket workflow: they did not decide here.
What would change this answer: The number of teams or repositories the binary is handed to. For one team whose runners have Python, standard-library Python is the cheapest to change.
Source: report §8, sixth row; report §4.5.
""" + COST_HEAD + tool_cost(TOOLS["long_lived_orchestrator"]) + """Not measured: nothing. Every symptom has a number.
""",
    "by_hand": """Verdict: By hand with the ai-sdlc skills may be enough: no ticket goes through this path yet.
Why: No ticket goes through this path in a week and the phases are chained by hand: there is nothing to chain yet. The ai-sdlc skills, run one after the other by a person, can do the work.
What would change this answer: tickets_per_week above 0. Zero is this command's own rule: neither the guide nor the report gives a number of tickets a week under which by hand is enough.
Source: decide.md §7 ("Chaining the steps by hand may be enough").
""" + COST_HEAD + TICKET_COST + """Not measured: nothing. Every symptom has a number.
""",
}
LISTED = """Verdict: For your own agent application in Python or TypeScript, with a known graph and pauses in the process: LangGraph, or an agent SDK plus an engine.
Why: You write the agent application yourself, the graph is known, and a run must pause inside the process. The symptoms describe a ticket workflow: they did not decide here.
- runs_paid_twice is 0.9, above 0.1: listed, it did not decide. Runs die far in and pay their tokens twice.
- double_runs is 7, above 0: listed, it did not decide. Two runs on one ticket.
- steps_with_own_retry_rule is 2: listed, it did not decide. Many steps, each with its own retry and timeout rule.
What would change this answer: The number of runs that must pause for a person inside the process. At zero, or when the flow is a straight line, a script is enough; when the step already runs inside a coding agent, use skills and hooks.
Source: report §8, fourth row; report §2.7.
""" + COST_HEAD + tool_cost(TOOLS["own_agent_app"]) + AGENT_PASS + """Not measured, so not counted as fine: agent_loops (An agent loops and burns tokens).
"""


def answers(building="ticket_workflow", tickets=12, by_hand="yes", **symptoms):
    """A complete answers file: every symptom measured at 0 unless given."""
    return {"building": building, "tickets_per_week": tickets, "chained_by_hand": by_hand,
            "symptoms": {**dict.fromkeys(SYMPTOMS, 0), **symptoms}}


def without(value, *path):
    """A copy of the answers with one key removed."""
    copy = json.loads(json.dumps(value))
    holder = copy
    for key in path[:-1]:
        holder = holder[key]
    del holder[path[-1]]
    return copy


EXAMPLE_ANSWERS = (
    (answers(runs_paid_twice=NOT_MEASURED, agent_loops=NOT_MEASURED, tickets_without_cost=NOT_MEASURED), 0, EXAMPLE_1),
    (answers(tickets=40, by_hand="no", runs_paid_twice=0.05, double_runs=3), 0, EXAMPLE_2),
    (without(without(answers(building="chatbot"), "tickets_per_week"), "symptoms", "double_runs"), 1, EXAMPLE_3),
)


def call(*argv, stdin=None):
    """`harness flow fit …` through the real command line: exit code, stdout, stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
            mock.patch("sys.stdin", io.StringIO(stdin or "")):
        try:
            code = harness.main(["flow", "fit", *argv])
        except SystemExit as exc:  # argparse refuses a wrong usage by exiting
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def codes_and_keys(document):
    return [(problem["code"], problem["key"]) for problem in document["problems"]]


class WithFiles(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write(self, value, name="answers.json"):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value if isinstance(value, str) else json.dumps(value))
        return path


class RulesDataTest(unittest.TestCase):
    def setUp(self):
        self.rules = flow_fit.load_rules()

    def test_the_eight_symptoms_of_the_report_in_its_order(self):
        self.assertEqual(tuple(s["key"] for s in self.rules["symptoms"]), SYMPTOMS)
        self.assertEqual(tuple(s["key"] for s in self.rules["symptoms"] if not s["engine"]), NO_ENGINE)

    def test_one_threshold_is_written_in_the_report_one_row_has_none_and_the_others_are_zero(self):
        written = {s["key"]: (s["above"], s["written"]) for s in self.rules["symptoms"]}
        self.assertEqual(written.pop("runs_paid_twice"), (0.1, "more than about one run in ten"))
        self.assertEqual(written.pop(NO_THRESHOLD), (None, None))
        self.assertEqual(len(written), 6)
        self.assertEqual(set(written.values()), {(0, None)})
        left = {s["key"]: s["left_to_you"] for s in self.rules["symptoms"] if s.get("left_to_you")}
        self.assertEqual(list(left), [NO_THRESHOLD])
        self.assertIn('"many steps"', left[NO_THRESHOLD])
        self.assertIn("gives no number", left[NO_THRESHOLD])

    def test_the_five_cases_of_the_report_and_the_tool_it_names(self):
        self.assertEqual(list(self.rules["cases"]), ["ticket_workflow", *TOOLS])
        for case, tool in TOOLS.items():
            self.assertEqual(self.rules["cases"][case]["choice"], tool)

    def test_the_symptom_sentences_are_those_of_the_guide(self):
        with open(os.path.join(ROOT, "docs", "workflow-harness", "decide.md"), encoding="utf-8") as fh:
            guide = fh.read()
        for symptom in self.rules["symptoms"]:
            with self.subTest(symptom=symptom["key"]):
                self.assertIn(f"| {symptom['symptom']}", guide)
                self.assertIn(f"| {symptom['smallest_fix']} |", guide)
                row = next(line for line in guide.splitlines() if line.startswith(f"| {symptom['symptom']}"))
                self.assertEqual(row.split("|")[3].strip().strip("*"), symptom["removed_by"])

    def test_what_each_number_counts_is_written_in_the_contract(self):
        with open(SPEC, encoding="utf-8") as fh:
            section = fh.read().split("## 11. `flow fit`")[1].split("\n## ")[0]
        for symptom in self.rules["symptoms"]:
            with self.subTest(symptom=symptom["key"]):
                self.assertIn(f"| `{symptom['key']}` | {symptom['counts']} |", section)

    def test_the_source_of_each_case_names_its_row_and_its_section(self):
        self.assertEqual({case: entry["source"] for case, entry in self.rules["cases"].items() if case in TOOLS}, {
            "own_agent_app": "report §8, fourth row; report §2.7",
            "agent_product": "report §8, third row; report §5.2",
            "many_repositories": "report §8, fifth row; report §7, questions 5 and 7",
            "long_lived_orchestrator": "report §8, sixth row; report §4.5"})

    def test_the_case_of_many_repositories_keeps_the_words_of_the_report(self):
        case = self.rules["cases"]["many_repositories"]
        self.assertEqual(case["label"], "the same change across hundreds of repositories")
        self.assertIn("gives no lower bound", case["would_change"])
        self.assertNotIn("At one", case["would_change"])
        with open(os.path.join(ROOT, "docs", "workflow-harness", "report.md"), encoding="utf-8") as fh:
            self.assertIn("| The same change across hundreds of repositories |", fh.read())


class RulesTest(unittest.TestCase):
    def test_rule_1_another_case_gets_the_tool_of_the_report_whatever_the_symptoms(self):
        for case, tool in TOOLS.items():
            with self.subTest(case=case):
                document = flow_fit.fit(answers(building=case, tickets=0, double_runs=9, agent_loops=NOT_MEASURED))
                self.assertEqual((document["passed"], document["verdict"]["code"], document["tool"]), (True, "tool", tool))
                self.assertTrue(document["verdict"]["sentence"].endswith(f": {tool}."))
                self.assertEqual(document["fired"], [])
                self.assertEqual([(entry["key"], entry["value"], entry["reason"]) for entry in document["not_deciding"]],
                                 [("double_runs", 9, "not_a_ticket_workflow")])
                self.assertIn("- double_runs is 9, above 0: listed, it did not decide.", flow_fit.render_md(document))
                self.assertEqual([entry["key"] for entry in document["not_measured"]], ["agent_loops"])
                self.assertIn("report §8", document["source"])

    def test_rule_2_each_symptom_fires_above_its_threshold_and_not_on_it(self):
        for symptom in flow_fit.load_rules()["symptoms"]:
            key, above = symptom["key"], symptom["above"]
            if key == NO_THRESHOLD:  # held by the test of the row with no threshold, below
                self.assertIsNone(above)
                continue
            with self.subTest(symptom=key):
                on_it = flow_fit.fit(answers(**{key: above}))
                self.assertEqual((on_it["verdict"]["code"], on_it["fired"], on_it["not_deciding"]),
                                 ("ticket_state_and_ci", [], []))
                value = 0.11 if key == "runs_paid_twice" else 1
                fired = flow_fit.fit(answers(**{key: value}))
                self.assertEqual((fired["verdict"]["code"], fired["tool"]), ("symptom", None))
                self.assertEqual(fired["fired"], [{name: symptom[name] for name in (
                    "key", "symptom", "above", "written", "smallest_fix", "removed_by", "engine")} | {"value": value}])
                self.assertIn(f"{key} is {value}, above {above}", fired["verdict"]["sentence"])

    def test_the_row_with_no_threshold_never_fires_and_is_listed_for_the_person_to_judge(self):
        for value in (1, 3, HUGE):
            with self.subTest(value=value):
                document = flow_fit.fit(answers(tickets=1, **{NO_THRESHOLD: value}))
                self.assertEqual((document["verdict"]["code"], document["fired"]), ("ticket_state_and_ci", []))
                self.assertEqual([(e["key"], e["value"], e["above"], e["reason"]) for e in document["not_deciding"]],
                                 [(NO_THRESHOLD, value, None, "no_threshold")])
        text = flow_fit.render_md(flow_fit.fit(answers(tickets=1, **{NO_THRESHOLD: 3})))
        self.assertIn('- steps_with_own_retry_rule is 3: listed, it did not decide. The report says "many steps" and '
                      "gives no number, so this command names no threshold: whether 3 is many is yours to judge. Many "
                      "steps, each with its own retry and timeout rule. If it is many, first try: Reusable CI workflows. "
                      "What removes it by design: An engine; count one to two days per workflow.\n", text)
        with_another = flow_fit.fit(answers(double_runs=1, **{NO_THRESHOLD: 3}))
        self.assertEqual([entry["key"] for entry in with_another["fired"]], ["double_runs"])
        self.assertEqual([entry["key"] for entry in with_another["not_deciding"]], [NO_THRESHOLD])
        self.assertEqual(flow_fit.fit(answers(**{NO_THRESHOLD: 0}))["not_deciding"], [])

    def test_rule_2_comes_before_rule_3_and_names_every_symptom_in_table_order(self):
        document = flow_fit.fit(answers(tickets=0, order_breaks=2, runs_paid_twice=0.5, agent_loops=4))
        self.assertEqual(document["verdict"]["code"], "symptom")
        self.assertEqual([entry["key"] for entry in document["fired"]], ["runs_paid_twice", "agent_loops", "order_breaks"])
        self.assertTrue(document["verdict"]["sentence"].startswith("3 symptoms are measured above their threshold: "))

    def test_an_engine_is_named_only_for_a_symptom_it_removes(self):
        engine = flow_fit.fit(answers(silent_events=1))["would_change"]
        self.assertTrue("managed engine (Temporal Cloud)" in engine and "does not remove" not in engine, engine)
        neither = flow_fit.fit(answers(agent_loops=1, tickets_without_cost=2))["would_change"]
        self.assertNotIn("managed engine", neither)
        self.assertIn("An engine does not remove agent_loops or tickets_without_cost.", neither)
        both = flow_fit.fit(answers(silent_events=1, agent_loops=1))["would_change"]
        self.assertIn("managed engine", both)
        self.assertIn("An engine does not remove agent_loops.", both)

    def test_rule_3_by_hand_only_when_no_ticket_goes_through_a_path_chained_by_hand(self):
        document = flow_fit.fit(answers(tickets=0))
        self.assertEqual(document["verdict"], {"code": "by_hand", "sentence": "By hand with the ai-sdlc skills may be "
                                               "enough: no ticket goes through this path yet."})
        self.assertEqual(flow_fit.fit(answers(tickets=0, by_hand="no"))["verdict"]["code"], "ticket_state_and_ci")
        self.assertIn("tickets_per_week above 0", document["would_change"])
        self.assertIn("this command's own rule", document["would_change"])
        self.assertEqual(document["source"], 'decide.md §7 ("Chaining the steps by hand may be enough")')
        with open(os.path.join(ROOT, "docs", "workflow-harness", "decide.md"), encoding="utf-8") as fh:
            self.assertIn("Chaining the steps by hand may be enough", fh.read())

    def test_rule_4_ticket_state_and_ci_otherwise(self):
        for tickets, by_hand in ((0.5, "yes"), (12, "yes"), (0, "no"), (30, "no")):
            with self.subTest(tickets=tickets, by_hand=by_hand):
                document = flow_fit.fit(answers(tickets=tickets, by_hand=by_hand))
                self.assertEqual(document["verdict"], {"code": "ticket_state_and_ci",
                                                       "sentence": "Ticket state and CI are enough."})
                self.assertIn("runs_paid_twice above 0.1", document["would_change"])
        self.assertIn("already chained", flow_fit.fit(answers(by_hand="no"))["why"])

    def test_the_other_verdicts_word_for_word(self):
        for name, printed in PRINTED.items():
            with self.subTest(verdict=name):
                given = answers(tickets=0) if name == "by_hand" else answers(building=name)
                self.assertEqual(flow_fit.render_md(flow_fit.fit(given)), printed)
        listed = answers(building="own_agent_app", by_hand="no", runs_paid_twice=0.9, double_runs=7, agent_loops=NOT_MEASURED,
                         **{NO_THRESHOLD: 2})
        self.assertEqual(flow_fit.render_md(flow_fit.fit(listed)), LISTED)
        self.assertEqual([(entry["key"], entry["reason"]) for entry in flow_fit.fit(listed)["not_deciding"]],
                         [(key, "not_a_ticket_workflow") for key in ("runs_paid_twice", "double_runs", NO_THRESHOLD)])

    def test_not_measured_never_fires_and_is_listed_with_every_verdict(self):
        unmeasured = dict.fromkeys(SYMPTOMS, NOT_MEASURED)
        cases = (("ticket_state_and_ci", answers(**unmeasured)), ("by_hand", answers(tickets=0, **unmeasured)),
                 ("tool", answers(building="agent_product", **unmeasured)),
                 ("symptom", answers(**{**unmeasured, "double_runs": 1})))
        for code, given in cases:
            with self.subTest(verdict=code):
                document = flow_fit.fit(given)
                self.assertEqual(document["verdict"]["code"], code)
                expected = [key for key in SYMPTOMS if given["symptoms"][key] == NOT_MEASURED]
                self.assertEqual([entry["key"] for entry in document["not_measured"]], expected)
                self.assertIn("Not measured, so not counted as fine: ", flow_fit.render_md(document))

    def test_every_verdict_says_what_would_change_it_and_its_source(self):
        for given in (answers(), answers(tickets=0), answers(double_runs=1), *(answers(building=c) for c in TOOLS)):
            document = flow_fit.fit(given)
            self.assertEqual(set(document), DOCUMENT_KEYS)
            for key in ("why", "would_change", "source"):
                self.assertTrue(document[key].strip(), key)
            self.assertIn("§", document["source"])


class RefusalTest(unittest.TestCase):
    def test_a_value_that_is_not_an_object_is_refused(self):
        for value in (None, [], "ticket_workflow", 3, True):
            with self.subTest(value=value):
                document = flow_fit.fit(value)
                self.assertEqual((document["passed"], document["verdict"]), (False, None))
                self.assertEqual(codes_and_keys(document), [("not_an_object", "")])

    def test_each_missing_key_is_named_with_what_to_write(self):
        missing = {("building",): f'Add "building": {BUILDING}.',
                   ("tickets_per_week",): 'Add "tickets_per_week": a number, 0 or more.',
                   ("chained_by_hand",): 'Add "chained_by_hand": "yes" or "no".',
                   ("symptoms",): 'Add "symptoms": an object with one entry per symptom (flow fit --questions lists them).',
                   ("symptoms", "runs_paid_twice"):
                       'Add "runs_paid_twice" under "symptoms": a number from 0 to 1, or "not measured".'}
        missing.update({("symptoms", key): f'Add "{key}" under "symptoms": {COUNT}.'
                        for key in SYMPTOMS[1:]})
        self.assertEqual(len(missing), 12)
        for path, message in missing.items():
            with self.subTest(key=".".join(path)):
                document = flow_fit.fit(without(answers(), *path))
                self.assertEqual(document, {"passed": False, "verdict": None, "problems": [
                    {"code": "missing", "key": ".".join(path), "message": message}]})

    def test_a_value_that_is_not_allowed_is_named_never_guessed(self):
        nan, infinite = float("nan"), float("inf")
        wrong = [("building", "chatbot"), ("building", None), ("chained_by_hand", True), ("chained_by_hand", "sometimes"),
                 ("symptoms", [])]
        wrong += [("tickets_per_week", value) for value in (-1, True, "many", None, nan, infinite, NOT_MEASURED)]
        for key, value in wrong:
            with self.subTest(key=key, value=value):
                document = flow_fit.fit({**answers(), key: value})
                self.assertEqual(codes_and_keys(document), [("unknown_value", key)])
                self.assertIn(f'"{key}" is ', document["problems"][0]["message"])
        for key, value in (("double_runs", -1), ("double_runs", True), ("double_runs", "none"), ("agent_loops", None),
                           ("order_breaks", nan), ("silent_events", infinite), ("runs_paid_twice", 1.5),
                           ("runs_paid_twice", 12), ("double_runs", "Not measured"), ("runs_paid_twice", HUGE),
                           ("double_runs", 0.5), ("tickets_without_cost", 0.0001), ("agent_loops", 1e-300),
                           ("double_runs", -HUGE)):
            with self.subTest(symptom=key, value=value):
                document = flow_fit.fit(answers(**{key: value}))
                self.assertEqual(codes_and_keys(document), [("unknown_value", f"symptoms.{key}")])
                self.assertIn(f'"{key}" under "symptoms" is ', document["problems"][0]["message"])
        self.assertEqual(flow_fit.fit(answers(double_runs=-1))["problems"][0]["message"],
                         f'"double_runs" under "symptoms" is -1: write {COUNT}.')

    def test_a_whole_number_of_any_size_is_read_as_it_is_never_a_crash(self):
        for given in (answers(tickets=HUGE), answers(double_runs=HUGE), answers(tickets=10 ** 5000, double_runs=10 ** 5000)):
            document = flow_fit.fit(given)
            self.assertTrue(document["passed"])
            self.assertTrue(flow_fit.render_md(document).startswith("Verdict: "))
        self.assertEqual(flow_fit.fit(answers(tickets=HUGE))["verdict"]["code"], "ticket_state_and_ci")
        self.assertEqual(flow_fit.fit(answers(double_runs=HUGE))["fired"][0]["value"], HUGE)
        refused = flow_fit.fit(answers(runs_paid_twice=10 ** 5000, tickets=-(10 ** 5000)))
        self.assertEqual(codes_and_keys(refused), [("unknown_value", "tickets_per_week"),
                                                   ("unknown_value", "symptoms.runs_paid_twice")])
        self.assertIn("a number too large to print", refused["problems"][0]["message"])
        self.assertEqual(flow_fit.fit(answers(double_runs=3.0))["fired"][0]["value"], 3.0)
        self.assertEqual(flow_fit.fit(answers(tickets=0.5))["verdict"]["code"], "ticket_state_and_ci")

    def test_a_key_written_twice_is_refused_not_read_as_its_last_value(self):
        text = json.dumps(answers(building="own_agent_app", tickets=0))[:-1] + ', "building": "ticket_workflow"}'
        document = flow_fit.fit(flow_fit.parse(text))
        self.assertEqual((document["passed"], document["verdict"]), (False, None))
        self.assertEqual(document["problems"], [{"code": "duplicate_key", "key": "building", "message":
                                                 '"building" is written more than once: keep one.'}])
        inner = json.dumps(answers()).replace('"double_runs": 0', '"double_runs": 0, "double_runs": 4, "double_runs": 0')
        document = flow_fit.fit(flow_fit.parse(inner))
        self.assertEqual(document["problems"], [{"code": "duplicate_key", "key": "symptoms.double_runs", "message":
                                                 '"double_runs" under "symptoms" is written more than once: keep one.'}])
        self.assertTrue(flow_fit.fit(flow_fit.parse(json.dumps(answers())))["passed"])
        self.assertEqual(flow_fit.parse(json.dumps(answers())), answers())

    def test_a_key_is_shown_on_one_line_with_nothing_the_terminal_would_obey(self):
        for key in ("sym\nptoms\x1b[31m", "a\x9b31m\x7f", "b\ud800"):
            with self.subTest(key=key):
                message = flow_fit.fit({**answers(), key: 1})["problems"][0]["message"]
                self.assertTrue(message.isprintable(), repr(message))
                self.assertTrue(message.isascii(), repr(message))
        self.assertTrue(flow_fit.fit({**answers(), "sym\nptoms\x1b[31m": 1})["problems"][0]["message"].startswith(
            '"sym\\nptoms\\u001b[31m" is not an answer this command reads'))
        value = flow_fit.fit(answers(building="x\x9b\x1b[2J"))["problems"][0]["message"]
        self.assertTrue(value.startswith('"building" is "x\\u009b\\u001b[2J": write '), value)
        self.assertEqual(flow_fit.fit(answers(building="café"))["problems"][0]["message"][:22], '"building" is "café": ')

    def test_a_key_the_format_does_not_know_is_refused(self):
        document = flow_fit.fit({**answers(double_run=2), "team": "payments"})
        self.assertEqual(codes_and_keys(document), [("unknown_key", "team"), ("unknown_key", "symptoms.double_run")])
        self.assertEqual(document["problems"][0]["message"], '"team" is not an answer this command reads: remove it, '
                         "or rename it (flow fit --questions lists the keys).")

    def test_the_problems_come_in_the_order_of_the_keys_unknown_keys_last(self):
        given = without(answers(building="chatbot", note="x", agent_loops="often"), "symptoms", "double_runs")
        del given["tickets_per_week"]
        self.assertEqual(codes_and_keys(flow_fit.fit(given)), [
            ("unknown_value", "building"), ("missing", "tickets_per_week"), ("missing", "symptoms.double_runs"),
            ("unknown_value", "symptoms.agent_loops"), ("unknown_key", "symptoms.note")])

    def test_one_answer_to_fix_is_said_in_the_singular(self):
        text = flow_fit.render_md(flow_fit.fit(without(answers(), "building")))
        self.assertTrue(text.startswith("Refused: 1 answer to fix. No verdict is given on a guess.\n- Add "), text)


class CommandLineTest(WithFiles):
    def test_the_three_examples_of_the_contract_word_for_word(self):
        with open(SPEC, encoding="utf-8") as fh:
            contract = fh.read()
        for number, (given, exit_code, printed) in enumerate(EXAMPLE_ANSWERS, start=1):
            with self.subTest(example=number):
                code, out, _ = call(self.write(given))
                self.assertEqual((code, out), (exit_code, printed))
                self.assertIn(f"```\n{printed}```", contract)

    def test_the_contract_names_every_key_and_every_allowed_value(self):
        with open(SPEC, encoding="utf-8") as fh:
            section = fh.read().split("## 11. `flow fit`")[1].split("\n## ")[0]
        rules = flow_fit.load_rules()
        for name in (*rules["questions"], *SYMPTOMS, "by_hand", "ticket_state_and_ci", "tool", "symptom", "not_an_object",
                     "missing", "unknown_value", "unknown_key", "duplicate_key", "not_deciding", "no_threshold",
                     "not_a_ticket_workflow"):
            self.assertIn(f"`{name}`", section)
        for value in (*rules["cases"], "yes", "no", NOT_MEASURED):
            self.assertIn(f'`"{value}"`', section)
        self.assertLessEqual(len(section.splitlines()), 100)

    def test_the_json_format_prints_the_document_and_nothing_else(self):
        path = self.write(EXAMPLE_ANSWERS[1][0])
        code, out, err = call(path, "--format", "json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out), flow_fit.fit(EXAMPLE_ANSWERS[1][0]))
        code, out, err = call(self.write(EXAMPLE_ANSWERS[2][0], "refused.json"), "--format", "json")
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(json.loads(out), flow_fit.fit(EXAMPLE_ANSWERS[2][0]))

    def test_a_note_says_what_comes_next(self):
        """Since section 12.4: the "Next:" note names where flow new writes, and the closing note ends every note."""
        closing = flow_notes.closing()
        _, _, err = call(self.write(answers()))
        self.assertEqual(err, flow_notes.fit_next(os.path.abspath(os.getcwd())) + "\n" + closing + "\n")
        self.assertIn("Next: flow new feature --out .harness/flow/feature.json writes a starting definition", err)
        # Since the critics of section 12, a symptom verdict says which commands read these answers beside a flow.
        path = self.write(answers(double_runs=1))
        _, _, err = call(path)
        self.assertEqual(err, flow_notes.fit_next_symptom(path) + "\n" + closing + "\n")
        self.assertEqual(call("-", stdin=json.dumps(answers(double_runs=1)))[2], closing + "\n")
        _, _, err = call(self.write({}))
        self.assertEqual(err, "The questions and the allowed values: flow fit --questions\n" + closing + "\n")

    def test_the_answers_can_come_on_the_standard_input(self):
        code, out, _ = call("-", stdin=json.dumps(EXAMPLE_ANSWERS[0][0]))
        self.assertEqual((code, out), (0, EXAMPLE_1))
        code, out, err = call("-", stdin="{not json")
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("flow: the standard input is not JSON"), err)

    def test_a_key_written_twice_is_refused_through_the_command_line(self):
        text = ('{"building": "own_agent_app", "building": "ticket_workflow", "tickets_per_week": 0, "tickets_per_week": 5, '
                '"chained_by_hand": "yes", "symptoms": ' + json.dumps(dict.fromkeys(SYMPTOMS, 0)) + "}")
        printed = ("Refused: 2 answers to fix. No verdict is given on a guess.\n"
                   '- "building" is written more than once: keep one.\n'
                   '- "tickets_per_week" is written more than once: keep one.\n')
        self.assertEqual(call("-", stdin=text)[:2], (1, printed))
        self.assertEqual(call(self.write(text))[:2], (1, printed))

    def test_a_number_of_four_hundred_digits_gets_a_verdict_or_a_refusal_never_a_traceback(self):
        text = json.dumps(answers()).replace('"tickets_per_week": 12', f'"tickets_per_week": {HUGE}')
        code, out, _ = call("-", stdin=text)
        self.assertEqual(code, 0)
        self.assertIn(f"{HUGE} tickets a week go through this path", out)
        code, out, _ = call("-", stdin=json.dumps(answers()).replace('"runs_paid_twice": 0', f'"runs_paid_twice": {HUGE}'))
        self.assertEqual(code, 1)
        self.assertIn(f'"runs_paid_twice" under "symptoms" is {HUGE}: write a number from 0 to 1', out)

    def test_a_key_no_terminal_could_print_is_still_refused_in_both_formats(self):
        text = json.dumps({**answers(), "team\ud800": 1})
        code, out, _ = call("-", stdin=text)
        self.assertEqual(code, 1)
        self.assertIn('- "team\\ud800" is not an answer this command reads', out)
        code, out, err = call("-", "--format", "json", stdin=text)
        self.assertEqual((code, err), (1, ""))
        out.encode("utf-8")
        self.assertEqual(json.loads(out)["problems"][0]["key"], "team\ud800")

    def test_a_file_that_cannot_be_read_says_which_and_why(self):
        missing = os.path.join(self.folder, "nowhere.json")
        self.assertTrue(call(missing)[2].startswith(f"flow: {missing}: the file cannot be read ("))
        broken = self.write("{not json", "broken.json")
        self.assertTrue(call(broken)[2].startswith(f"flow: {broken}: the file is not JSON ("))
        with open(os.path.join(self.folder, "latin.json"), "wb") as fh:
            fh.write(b'{"building": "caf\xe9"}')
        code, out, err = call(os.path.join(self.folder, "latin.json"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("the file is not JSON", err)
        self.assertEqual(call(self.folder)[0], 2)

    def test_the_command_has_one_way_in(self):
        self.assertFalse(hasattr(flow_fit, "main"))
        with open(flow_fit.__file__, encoding="utf-8") as fh:
            self.assertNotIn("__main__", fh.read())

    def test_exit_2_for_a_wrong_usage_or_a_file_that_cannot_be_read(self):
        missing = os.path.join(self.folder, "nowhere.json")
        for argv in ((), (missing,), (self.write("{not json", "broken.json"),), (missing, "--format", "yaml")):
            with self.subTest(argv=argv):
                code, out, err = call(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.strip())
        self.assertIn("flow fit --questions", call()[2])

    def test_the_questions_list_every_key_and_allowed_value(self):
        code, out, err = call("--questions")
        self.assertEqual((code, err), (0, flow_notes.closing() + "\n"))  # since section 12.4, the closing note
        rules = flow_fit.load_rules()
        for name in (*rules["questions"], *rules["cases"], *SYMPTOMS, '"yes"', '"no"', '"not measured"'):
            self.assertIn(name, out)
        for question in rules["questions"].values():
            self.assertIn(question["text"], out)
        self.assertIn("any measured occurrence above zero is named", out)
        self.assertIn("more than about one run in ten", out)
        self.assertIn('steps_with_own_retry_rule: Many steps, each with its own retry and timeout rule. Write the number of '
                      'steps that need a retry or timeout rule of their own. Never named as a symptom: the report says '
                      '"many steps" and gives no number. A number above 0 is listed for you to judge.\n', out)
        self.assertNotIn("above None", out)
        self.assertIn("a whole number", out)

    def test_the_questions_as_json_carry_an_example_that_gets_a_verdict(self):
        document = json.loads(call("--questions", "--format", "json")[1])
        self.assertEqual(set(document), {"facts_date", "not_measured", "questions", "symptoms", "example"})
        self.assertEqual([question["key"] for question in document["questions"]],
                         ["building", "tickets_per_week", "chained_by_hand", "symptoms"])
        self.assertEqual(list(document["questions"][0]["values"]), ["ticket_workflow", *TOOLS])
        self.assertEqual([symptom["key"] for symptom in document["symptoms"]], list(SYMPTOMS))
        self.assertTrue(flow_fit.fit(document["example"])["passed"])
        self.assertEqual(call(self.write(document["example"]))[0], 0)

    def test_the_help_of_flow_names_flow_fit_before_any_definition(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            harness.main(["flow", "--help"])
        block = out.getvalue()[out.getvalue().index("In order"):]
        self.assertNotEqual(block.find("flow fit"), -1)
        self.assertLess(block.find("flow fit"), block.find("flow new"))


class FixtureTest(unittest.TestCase):
    """fixtures/flow/fit/<name>/: an answers file the command reads as it is, and what it must answer."""
    KINDS = {"by_hand", "ticket_state_and_ci", "tool", "symptom", None}

    def folders(self):
        return sorted(name for name in os.listdir(FAMILY) if os.path.isdir(os.path.join(FAMILY, name)))

    def expected(self, name):
        with open(os.path.join(FAMILY, name, "expected.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_six_fixtures_one_per_verdict_one_unmeasured_one_refused(self):
        """Since section 12.3: seven folders, the seventh a symptom no engine removes, each with its cost entries."""
        expected = [self.expected(name) for name in self.folders()]
        self.assertEqual(len(expected), 7)
        self.assertTrue(any(entry["verdict"] == "symptom" and "engine_fee" not in entry["cost"] for entry in expected))
        self.assertEqual({entry["verdict"] for entry in expected}, self.KINDS)
        self.assertTrue(any(entry["not_measured"] == list(SYMPTOMS) for entry in expected))
        self.assertEqual(sorted(tuple(entry["not_deciding"]) for entry in expected if entry["not_deciding"]),
                         [("double_runs",), (NO_THRESHOLD,)])
        for entry in expected:
            self.assertEqual(set(entry), {"about", "exit", "verdict", "tool", "fired", "not_deciding", "not_measured",
                                          "refused", "cost"})
            self.assertEqual(entry["exit"], 1 if entry["verdict"] is None else 0)
            self.assertEqual(entry["cost"] == [], entry["verdict"] is None, "a refusal, and only a refusal, has no cost")

    def test_each_fixture_gets_its_expected_answer_through_the_command_line(self):
        for name in self.folders():
            with self.subTest(fixture=name):
                expected = self.expected(name)
                code, out, _ = call(os.path.join(FAMILY, name, "answers.json"), "--format", "json")
                document = json.loads(out)
                self.assertEqual(code, expected["exit"])
                self.assertEqual([problem["key"] for problem in document["problems"]], expected["refused"])
                if expected["verdict"] is None:
                    self.assertIsNone(document["verdict"])
                    self.assertNotIn("cost", document)
                    continue
                self.assertEqual([entry["id"] for entry in document["cost"]["entries"]], expected["cost"])
                self.assertEqual((document["verdict"]["code"], document["tool"]), (expected["verdict"], expected["tool"]))
                self.assertEqual([entry["key"] for entry in document["fired"]], expected["fired"])
                self.assertEqual([entry["key"] for entry in document["not_deciding"]], expected["not_deciding"])
                self.assertEqual([entry["key"] for entry in document["not_measured"]], expected["not_measured"])

    def test_the_page_of_the_family_names_every_fixture(self):
        with open(os.path.join(os.path.dirname(FAMILY), "README.md"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertEqual([name for name in self.folders() if f"`{name}`" not in page], [])


if __name__ == "__main__":
    unittest.main()
