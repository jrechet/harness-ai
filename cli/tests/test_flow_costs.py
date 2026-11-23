"""Tests of the cost entries `flow fit` prints (docs/workflow-harness/flow-spec.md, section 12.3).

Every figure comes from a data file, `cli/harnesslib/flow_costs.json`, and every figure of that file
is checked here against the page it cites: the strings under `found` must be in the cited section
of `report.md` or `costs.md`, read with the bold marks removed. The command adds, multiplies, rounds
and converts nothing: what it prints is the file, word for word."""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import flow_fit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = os.path.join(ROOT, "docs", "workflow-harness")
DATA = os.path.join(ROOT, "cli", "harnesslib", "flow_costs.json")
SYMPTOMS = ("runs_paid_twice", "double_runs", "silent_events", "agent_loops", "waits_inside_computation",
            "steps_with_own_retry_rule", "order_breaks", "tickets_without_cost")
IDS = ("agent_pass", "whole_ticket", "ticket_estimate", "ci_minute", "engine_fee", "engine_workflow",
       "engine_staffing", "this_tool")
TICKET = ["agent_pass", "whole_ticket", "ticket_estimate"]
ENGINE = ["engine_fee", "engine_workflow", "engine_staffing"]
# The table of section 12.3, column by column.
TABLE = {
    "agent_pass": ("One agent pass", "published", "[V] [V] [M]", "report §5.4; costs.md §1"),
    "whole_ticket": ("One ticket from start to end", "none", None, "report §5.4; report §9.1, item 2"),
    "ticket_estimate": ("One ticket, estimated", "arithmetic", None, "report §5.4; costs.md §2"),
    "ci_minute": ("One CI minute", "published", "[V]", "costs.md §1"),
    "engine_fee": ("The fee of a managed engine", "published", "[V]", "report §3.5; costs.md §3"),
    "engine_workflow": ("Writing one workflow for an engine", "published", "[V, self-reported]", "report §5.2"),
    "engine_staffing": ("The people to host an engine yourself", "none", None, "report §3.5; report §9.1, item 5"),
    "this_tool": (None, "none", None, "report §8: the table gives no price"),
}
AGENT_PASS_FOUND = {"report.md": ["near one dollar", "$1.19", "131,246", "$1.00 flat", "$1.20"],
                    "costs.md": ["$1.19", "131,246", "$1.00 flat", "$1.20"]}
EXAMPLE_1_COST = """Cost, from the pages, facts of 2026-11-21 (nothing here is measured on your runs):
- One agent pass: near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, $1.00 flat; GitHub's heavy runs, about $1.20. Published [V] [V] [M] (report §5.4; costs.md §1).
- One ticket from start to end: no published figure (report §5.4; report §9.1, item 2).
- One ticket, estimated: $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix. Arithmetic of the notes, not a measurement (report §5.4; costs.md §2).
- One CI minute: $0.006 on a GitHub Actions Linux runner with 2 cores. Published [V] (costs.md §1).
"""
ENGINE_LINES = """- The fee of a managed engine: about $50 per million actions on Temporal Cloud, with no base fee. Published [V] (report §3.5; costs.md §3).
- Writing one workflow for an engine: "1-2 days" on average for a custom Temporal workflow at Duolingo. Published [V, self-reported] (report §5.2).
- The people to host an engine yourself: no published figure (report §3.5; report §9.1, item 5).
"""
FIGURE = re.compile(r"\$?\d(?:[\d,.\-]*\d)?")


def data() -> dict:
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def page(name: str) -> str:
    with open(os.path.join(PAGES, name), encoding="utf-8") as fh:
        return fh.read()


def section(text: str, number: str) -> str:
    """The text under the heading whose number is `number` ("5.4", "1"), up to the next heading of
    the same level or above, bold marks removed. Empty when no heading has that number."""
    lines, out, level = text.splitlines(), [], None
    for line in lines:
        heading = re.match(r"^(#+) (\d+(?:\.\d+)*)\.? ", line)
        if level is not None and heading and len(heading.group(1)) <= level:
            break
        if level is not None:
            out.append(line)
        elif heading and heading.group(2) == number:
            level = len(heading.group(1))
    return "\n".join(out).replace("**", "")


def cited(where: str) -> list[tuple[str, str]]:
    """The pages and the section numbers a `where` cites: "report §5.4; costs.md §1" gives
    [("report.md", "5.4"), ("costs.md", "1")]. An item number is not a section."""
    out = []
    for part in where.split(";"):
        found = re.match(r"\s*(report|costs\.md) §(\d+(?:\.\d+)*)", part)
        if found is None:
            raise ValueError(f"{where!r}: no page and section in {part!r}")
        out.append(("report.md" if found.group(1) == "report" else "costs.md", found.group(2)))
    return out


def answers(building="ticket_workflow", tickets=12, by_hand="yes", **symptoms):
    return {"building": building, "tickets_per_week": tickets, "chained_by_hand": by_hand,
            "symptoms": {**dict.fromkeys(SYMPTOMS, 0), **symptoms}}


class DataFileTest(unittest.TestCase):
    def test_the_entries_are_those_of_the_contract_table(self):
        entries = data()["entries"]
        self.assertEqual(list(entries), list(IDS))
        for ident, (about, kind, label, where) in TABLE.items():
            with self.subTest(entry=ident):
                entry = entries[ident]
                self.assertEqual(set(entry), {"about", "figure", "kind", "label", "where", "found"})
                self.assertEqual((entry["about"], entry["kind"], entry["label"], entry["where"]),
                                 (about, kind, label, where))
                self.assertEqual(entry["figure"] is None, kind == "none")
                if kind == "none":
                    self.assertEqual(entry["found"], {})

    def test_the_date_of_the_facts_is_the_one_of_the_cost_page(self):
        self.assertIn(f"Date of the facts: {data()['facts_date']},", page("costs.md"))

    def test_every_cited_section_exists(self):
        for ident, entry in data()["entries"].items():
            for name, number in cited(entry["where"]):
                with self.subTest(entry=ident, page=name, section=number):
                    self.assertTrue(section(page(name), number).strip())

    def test_every_figure_is_found_in_the_section_it_cites(self):
        for ident, entry in data()["entries"].items():
            if entry["kind"] == "none":
                continue
            pages = {name: number for name, number in cited(entry["where"])}
            self.assertEqual(sorted(entry["found"]), sorted(pages), f"{ident}: found names the cited pages")
            for name, strings in entry["found"].items():
                text = section(page(name), pages[name])
                with self.subTest(entry=ident, page=name):
                    self.assertTrue(strings)
                    for string in strings:
                        self.assertIn(string, entry["figure"])
                        self.assertIn(string, text)
                    joined = " ".join(strings)
                    for figure in FIGURE.findall(entry["figure"]):
                        self.assertIn(figure, joined, f"{figure} of {ident} is not checked on {name}")

    def test_the_evidence_labels_are_those_of_the_cited_sections(self):
        for ident, entry in data()["entries"].items():
            if entry["kind"] != "published":
                continue
            for name, number in cited(entry["where"]):
                text = section(page(name), number)
                for label in re.findall(r"\[[^\]]+\]", entry["label"]):
                    with self.subTest(entry=ident, page=name, label=label):
                        self.assertIn(label, text)

    def test_the_figure_of_one_agent_pass_leads_with_the_words_of_the_report(self):
        entry = data()["entries"]["agent_pass"]
        self.assertTrue(entry["figure"].startswith("near one dollar: "))
        self.assertEqual(entry["found"], AGENT_PASS_FOUND)

    def test_the_entries_of_each_verdict_are_those_of_the_contract(self):
        self.assertEqual(data()["by_verdict"], {
            "by_hand": TICKET, "ticket_state_and_ci": TICKET + ["ci_minute"], "symptom": TICKET,
            "symptom_an_engine_removes": ENGINE,
            "tool": {"own_agent_app": ["this_tool", "agent_pass"], "agent_product": ENGINE,
                     "many_repositories": ["this_tool", "agent_pass"], "long_lived_orchestrator": ["this_tool"]}})


class FitCostTest(unittest.TestCase):
    def ids(self, given):
        return [entry["id"] for entry in flow_fit.fit(given)["cost"]["entries"]]

    def test_each_verdict_carries_its_entries_in_order(self):
        self.assertEqual(self.ids(answers(tickets=0)), TICKET)
        self.assertEqual(self.ids(answers()), TICKET + ["ci_minute"])
        self.assertEqual(self.ids(answers(double_runs=1)), TICKET + ENGINE)
        self.assertEqual(self.ids(answers(agent_loops=1)), TICKET, "an engine does not remove a loop")
        self.assertEqual(self.ids(answers(agent_loops=1, silent_events=2)), TICKET + ENGINE)
        for case, expected in (("own_agent_app", ["this_tool", "agent_pass"]), ("agent_product", ENGINE),
                               ("many_repositories", ["this_tool", "agent_pass"]),
                               ("long_lived_orchestrator", ["this_tool"])):
            with self.subTest(case=case):
                self.assertEqual(self.ids(answers(building=case, double_runs=4)), expected)

    def test_an_entry_is_copied_from_the_file_without_its_evidence_strings(self):
        cost = flow_fit.fit(answers())["cost"]
        self.assertEqual(cost["facts_date"], data()["facts_date"])
        entries = data()["entries"]
        for entry in cost["entries"]:
            self.assertEqual(list(entry), ["id", "about", "figure", "kind", "label", "where"])
            source = entries[entry["id"]]
            self.assertEqual({key: entry[key] for key in ("about", "figure", "kind", "label", "where")},
                             {key: source[key] for key in ("about", "figure", "kind", "label", "where")})

    def test_the_entry_of_the_tool_is_about_the_choice_of_its_case(self):
        entry = flow_fit.fit(answers(building="long_lived_orchestrator"))["cost"]["entries"][0]
        self.assertEqual(entry["about"], "Rust is reasonable")
        printed = flow_fit.render_md(flow_fit.fit(answers(building="long_lived_orchestrator")))
        self.assertIn("- Rust is reasonable: no published figure (report §8: the table gives no price).\n", printed)

    def test_a_refusal_has_no_cost(self):
        self.assertNotIn("cost", flow_fit.fit({}))
        self.assertNotIn("Cost, from the pages", flow_fit.render_md(flow_fit.fit({})))

    def test_a_person_reads_the_cost_between_the_source_and_what_was_not_measured(self):
        printed = flow_fit.render_md(flow_fit.fit(answers(runs_paid_twice="not measured")))
        self.assertIn("Source: report §8, first row; report §7, last table.\n" + EXAMPLE_1_COST
                      + "Not measured, so not counted as fine: ", printed)
        printed = flow_fit.render_md(flow_fit.fit(answers(double_runs=3)))
        self.assertIn(EXAMPLE_1_COST.split("- One CI minute")[0] + ENGINE_LINES + "Not measured: nothing.", printed)


if __name__ == "__main__":
    unittest.main()
