"""The guide docs/workflow-harness/decide.md says what `flow place` says: the seven questions
and the nine places to the letter, and the two templates placed as the command places them.
The literals are the contract's (docs/workflow-harness/flow-spec.md, sections 6 and 9)."""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import flow, flow_place  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUIDE = os.path.join(ROOT, "docs", "workflow-harness", "decide.md")

QUESTIONS = {
    "who": "Who performs this step?",
    "judge": "Can the person who approves really judge what they approve?",
    "survive": "How long does it live, and what must survive?",
    "spread": "Does the work split into many independent units?",
    "repos": "How many repositories need this step?",
    "determined": "Is the right output determined by the inputs?",
    "weakness": "Is this step here because today's model is weak?",
}
PLACES = {
    "code": "this is code",
    "skill": "a skill is enough",
    "dated_skill": "a skill is enough, with its date",
    "ticket_state": "the ticket holds this",
    "human_gate": "this is a human gate",
    "no_gate": "no gate here",
    "reusable_workflow": "this is a shared CI workflow",
    "campaign": "this is a fan-out by script",
    "durable_engine": "this would need an engine",
}
HEADINGS = ["The seven questions for one step", "The nine places", "When a step really needs an engine",
            "Reading what `flow place` prints", "Three examples"]
# A row of the guide's step-by-step tables: | `state` | report step | who | what flow place says | why |
STEP_ROW = re.compile(r"^\| `([a-z][a-z0-9_]*)` \| [^|]* \| ([^|]+) \| ([^|]+) \|[^|]*\|$")


def guide() -> str:
    if not os.path.isfile(GUIDE):
        raise AssertionError(f"the guide {GUIDE} does not exist")
    with open(GUIDE, encoding="utf-8") as fh:
        return fh.read()


def placed_tables(text: str) -> list[list[tuple[str, str, str]]]:
    """The step-by-step tables of the guide, each a list of (state, who, says), in page order."""
    tables, current = [], []
    for line in text.splitlines():
        row = STEP_ROW.match(line.strip())
        cells = tuple(cell.strip() for cell in row.groups()) if row else ()
        if cells and cells[1] in flow.TYPE_WORDS.values():
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables + ([current] if current else [])


class GuideTest(unittest.TestCase):
    def test_the_seven_questions_are_there_to_the_letter_with_their_id(self):
        text = guide()
        for ident, sentence in QUESTIONS.items():
            with self.subTest(question=ident):
                self.assertIn(sentence, text, f"decide.md lacks the question {sentence!r}")
                self.assertIn(f"`{ident}`", text, f"decide.md lacks the id `{ident}` of {sentence!r}")

    def test_the_nine_places_are_there_with_what_flow_place_says(self):
        text = guide()
        for ident, says in PLACES.items():
            with self.subTest(place=ident):
                self.assertIn(f"`{ident}`", text, f"decide.md lacks the place `{ident}`")
                self.assertIn(f'"{says}"', text, f"decide.md lacks what flow place says for `{ident}`: {says!r}")

    def test_the_literals_here_are_the_ones_of_the_grid(self):
        grid = flow_place.load_grid()
        self.assertEqual({ident: q["text"] for ident, q in grid["questions"].items()}, QUESTIONS)
        self.assertEqual({ident: d["says"] for ident, d in grid["destinations"].items()}, PLACES)

    def test_the_five_headings_come_in_the_order_of_the_contract(self):
        text = guide()
        found = [text.find(f". {heading}\n") for heading in HEADINGS]
        self.assertNotIn(-1, found, f"a heading is missing; positions of {HEADINGS}: {found}")
        self.assertEqual(found, sorted(found))

    def test_the_page_ends_with_the_symptom_that_would_make_you_need_it(self):
        last_heading = [line for line in guide().splitlines() if line.startswith("## ")][-1]
        self.assertIn("symptom that would make you need it", last_heading.lower())

    def test_the_two_templates_are_placed_in_the_guide_as_flow_place_places_them(self):
        tables = placed_tables(guide())
        self.assertEqual(len(tables), 2, "decide.md must hold one step-by-step table per template")
        for kind, table in zip(flow.TEMPLATES, tables):
            with self.subTest(template=kind):
                real = [(step["state"], flow.TYPE_WORDS[step["type"]], step["says"])
                        for step in flow_place.place(flow.new(kind))["steps"]]
                self.assertEqual(table, real)

    def test_the_example_lines_of_the_guide_are_lines_flow_place_prints(self):
        text = guide()
        for line in ('- coding (an agent): a skill is enough. Decided by "Is this step here because today\'s '
                     'model is weak?": no.',
                     "Verdict: no step needs an engine."):
            self.assertIn(line, text)


if __name__ == "__main__":
    unittest.main()
