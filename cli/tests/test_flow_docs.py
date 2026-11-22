"""The form of the seven explanation pages of docs/workflow-harness/: a date, a last section that
names symptoms, links and citations that lead somewhere, and no `flow` command shown as built
when the parser does not know it. What a page says is reviewed by a reader; this only checks
that each place it points to exists."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(ROOT, "docs", "workflow-harness")
NOTES_DIR = os.path.join(DOCS_DIR, "research_notes")
HARNESS = os.path.join(ROOT, "cli", "harness.py")

DOCS = ("langchain.md", "langgraph.md", "engines.md", "ci-as-engine.md", "rust.md", "flows.md", "costs.md")
DATE_PREFIX = "Date of the facts:"
DATE_WITHIN_LINES = 5
LAST_SECTION = "The symptom that would make you need it"
MIN_LINES, MAX_LINES = 100, 300
PLANNED = "planned"

FENCE = re.compile(r"^\s*```")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
NOT_A_FILE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)")
CODE_SPAN = re.compile(r"`([^`]*)`")
FLOW_COMMAND = re.compile(r"(?<![\w-])flow ([a-z][a-z-]*)")
NOTE_NAMED = re.compile(r"\bnote ([A-Za-z0-9_-]+\.md)\b")
SENTENCE_END = re.compile(r"(?<=[.?!])\s+")
HEADING_NUMBER = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)[. ]")
NUMBER_LIST = r"\d+(?:\.\d+)*(?:(?:, | and | to )\d+(?:\.\d+)*)*"
# What a citation is read from, left to right: a file named, the word "report" or "note",
# a bracket that closes the citation, then the numbers after "§" or "section".
CITATION_TOKEN = re.compile(
    r"(?P<file>[A-Za-z0-9_-]+\.md)"
    r"|(?P<report>\breport\b)"
    r"|(?P<proposal>\bproposal\b)"
    r"|(?P<note>\bnote\b)"
    r"|(?P<reset>[()|])"
    r"|§\s?(?P<para>" + NUMBER_LIST + r")"
    r"|\bsections? (?P<section>" + NUMBER_LIST + r")")


def read(path: str) -> str:
    if not os.path.isfile(path):
        raise AssertionError(f"{path} does not exist")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def split_fences(text: str) -> list[tuple[int, str, bool]]:
    """Every line as (number, line, in a fenced block); the fence lines themselves are dropped."""
    lines, fenced = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        lines.append((number, line, fenced))
    return lines


def heading_numbers(path: str) -> set[str]:
    return {match.group(1) for line in read(path).splitlines() if (match := HEADING_NUMBER.match(line))}


def date_problems(text: str) -> list[str]:
    head = text.splitlines()[:DATE_WITHIN_LINES]
    if any(line.startswith(DATE_PREFIX) for line in head):
        return []
    return [f"no line starting with {DATE_PREFIX!r} in the first {DATE_WITHIN_LINES} lines"]


def last_section_problems(text: str) -> list[str]:
    lines = [line for _, line, fenced in split_fences(text) if not fenced]
    headings = [index for index, line in enumerate(lines) if line.startswith("## ")]
    if not headings:
        return ["no second-level section at all"]
    title = lines[headings[-1]][3:].strip()
    if title != LAST_SECTION:
        return [f"the last second-level section is {title!r}, not {LAST_SECTION!r}"]
    if not any(line.strip() for line in lines[headings[-1] + 1:]):
        return [f"the section {LAST_SECTION!r} is empty"]
    return []


def link_problems(text: str, doc_dir: str) -> list[str]:
    problems = []
    for number, line, fenced in split_fences(text):
        if fenced:
            continue
        for target in LINK.findall(line):
            if NOT_A_FILE.match(target):
                continue
            path = os.path.normpath(os.path.join(doc_dir, target.split("#")[0]))
            if not os.path.isfile(path):
                problems.append(f"line {number}: the link to {target} leads to no file")
    return problems


def note_problems(text: str, notes_dir: str) -> list[str]:
    return [f"line {number}: note {name} is not in research_notes/"
            for number, line, _ in split_fences(text)
            for name in NOTE_NAMED.findall(line)
            if not os.path.isfile(os.path.join(notes_dir, name))]


def numbers_of(listed: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)*", listed)


def citation_problems(text: str, docs_dir: str, notes_dir: str) -> list[str]:
    """Every "§N" must be a heading number of the document it cites: report.md by default and
    after the word "report", the note named before it otherwise ("same note" is the last note
    named on the page). "section N" is checked the same way after a report, a note or the
    proposal; with no document named before it, it is this page's own section and is not read."""
    numbered = {"report": heading_numbers(os.path.join(docs_dir, "report.md"))}
    problems, last_note = [], None

    def known(source: str) -> set[str] | None:
        if source not in numbered:
            path = os.path.join(docs_dir, "proposal.md") if source == "proposal" else os.path.join(notes_dir, source)
            numbered[source] = heading_numbers(path) if os.path.isfile(path) else None
        return numbered[source]

    for number, line, fenced in split_fences(text):
        if fenced:
            continue
        source = None  # None: nothing named yet; "": a document whose sections are not read
        for token in CITATION_TOKEN.finditer(LINK.sub(lambda m: m.group(0).replace("(", "<").replace(")", ">"), line)):
            if token.group("reset"):
                source = None
            elif token.group("report") or token.group("file") == "report.md":
                source = "report"
            elif token.group("proposal") or token.group("file") == "proposal.md":
                source = "proposal"
            elif token.group("file"):
                is_note = os.path.isfile(os.path.join(notes_dir, token.group("file")))
                source = token.group("file") if is_note else ""
                last_note = source if is_note else last_note
            elif token.group("note"):
                source = last_note if last_note else "?"
            else:
                cited = token.group("para") or token.group("section")
                if token.group("section") and source is None:
                    continue
                if source == "":
                    continue
                if source == "?":
                    problems.append(f"line {number}: §{cited} follows \"note\" and no note was named before it")
                    continue
                document = source or "report"
                headings = known(document)
                for one in numbers_of(cited):
                    if headings is None or one not in headings:
                        problems.append(f"line {number}: {document} has no heading numbered {one}")
    return problems


_KNOWN_COMMANDS: dict[str, bool] = {}


def parser_knows(word: str) -> bool:
    """True when `harness flow <word> --help` exits 0: the real parser has that sub-command."""
    if word not in _KNOWN_COMMANDS:
        done = subprocess.run([sys.executable, HARNESS, "flow", word, "--help"], capture_output=True, cwd=ROOT)
        _KNOWN_COMMANDS[word] = done.returncode == 0
    return _KNOWN_COMMANDS[word]


def flow_commands(text: str) -> list[tuple[int, str, str]]:
    """Every `flow <word>` written as code, as (line number, word, the sentence or table row or
    code line it sits in)."""
    found = []
    for number, line, fenced in split_fences(text):
        if fenced or line.lstrip().startswith("|"):
            pieces = [line]
        else:
            pieces = SENTENCE_END.split(line)
        for piece in pieces:
            code = [piece] if fenced else CODE_SPAN.findall(piece)
            for chunk in code:
                for word in FLOW_COMMAND.findall(chunk):
                    found.append((number, word, piece))
    return found


def command_problems(text: str) -> list[str]:
    return [f"line {number}: `flow {word}` is not a sub-command the parser knows, and its sentence does not say {PLANNED!r}"
            for number, word, where in flow_commands(text)
            if not parser_knows(word) and PLANNED not in where.lower()]


def length_problems(text: str) -> list[str]:
    count = len(text.splitlines())
    if MIN_LINES <= count <= MAX_LINES:
        return []
    return [f"{count} lines, outside {MIN_LINES} to {MAX_LINES}"]


class FlowDocsTest(unittest.TestCase):
    def check_each(self, problems_of):
        for name in DOCS:
            with self.subTest(doc=name):
                self.assertEqual(problems_of(read(os.path.join(DOCS_DIR, name))), [], name)

    def test_each_page_gives_the_date_of_its_facts_in_its_first_lines(self):
        self.check_each(date_problems)

    def test_each_page_ends_with_the_symptom_that_would_make_you_need_it(self):
        self.check_each(last_section_problems)

    def test_every_relative_link_leads_to_a_file(self):
        self.check_each(lambda text: link_problems(text, DOCS_DIR))

    def test_every_note_named_is_in_research_notes(self):
        self.check_each(lambda text: note_problems(text, NOTES_DIR))

    def test_every_section_cited_is_a_heading_of_the_document_cited(self):
        self.check_each(lambda text: citation_problems(text, DOCS_DIR, NOTES_DIR))

    def test_every_flow_command_is_built_or_said_planned(self):
        self.check_each(command_problems)

    def test_each_page_is_between_100_and_300_lines(self):
        self.check_each(length_problems)

    def test_the_pages_do_write_flow_commands_and_cite_the_report_and_the_notes(self):
        """Guards the readers above: a pattern that matched nothing would let every page through."""
        texts = {name: read(os.path.join(DOCS_DIR, name)) for name in DOCS}
        written = {word for text in texts.values() for _, word, _ in flow_commands(text)}
        self.assertLessEqual({"new", "check", "next", "report"}, written)
        for name, text in texts.items():
            with self.subTest(doc=name):
                self.assertRegex(text, r"report §\d", "no report section cited")
                self.assertTrue(NOTE_NAMED.search(text), "no note named")
                self.assertTrue(LINK.search(text), "no link read")


class ChecksRefuseTest(unittest.TestCase):
    """Each check, given a page broken in one way, says so. The base page is a real one."""

    def setUp(self):
        self.text = read(os.path.join(DOCS_DIR, "ci-as-engine.md"))

    def test_the_real_page_passes_every_check_used_below(self):
        self.assertEqual(date_problems(self.text) + last_section_problems(self.text)
                         + link_problems(self.text, DOCS_DIR) + note_problems(self.text, NOTES_DIR)
                         + citation_problems(self.text, DOCS_DIR, NOTES_DIR) + command_problems(self.text)
                         + length_problems(self.text), [])

    def test_a_date_pushed_below_the_fifth_line_is_refused(self):
        lines = self.text.splitlines()
        date = next(line for line in lines if line.startswith(DATE_PREFIX))
        lines.remove(date)
        lines.insert(DATE_WITHIN_LINES, date)
        self.assertTrue(date_problems("\n".join(lines)))
        self.assertTrue(date_problems(self.text.replace(DATE_PREFIX, "Date:")))

    def test_a_last_section_renamed_emptied_or_followed_by_another_is_refused(self):
        heading = f"## {LAST_SECTION}"
        self.assertIn(heading, self.text)
        self.assertTrue(last_section_problems(self.text.replace(heading, heading + " most")))
        self.assertTrue(last_section_problems(self.text.replace(heading, "## the symptom that would make you need it")))
        self.assertTrue(last_section_problems(self.text.split(heading)[0] + heading + "\n\n"))
        self.assertTrue(last_section_problems(self.text + "\n## See also\n\nMore.\n"))

    def test_a_link_to_a_missing_file_is_refused_and_a_web_link_is_not_read(self):
        self.assertTrue(link_problems(self.text + "\nSee [nowhere](no-such-page.md).\n", DOCS_DIR))
        self.assertTrue(link_problems(self.text + "\nSee [it](engines.md#part) and [x](../no/such.md).\n", DOCS_DIR))
        self.assertEqual(link_problems(self.text + "\nSee [the web](https://example.org/a.md) and [here](#top).\n",
                                       DOCS_DIR), [])

    def test_a_note_that_does_not_exist_is_refused(self):
        self.assertTrue(note_problems(self.text + "\nA fact (note no_such_note.md, section 2).\n", NOTES_DIR))

    def test_a_section_the_cited_document_does_not_have_is_refused(self):
        for cited in ("(report §3.9)", "(report §2.4; §12)", "A fact (§3.9).", "(report §3.3 and §88.1)",
                      "(note orchestration_alternatives.md, section 5.9)",
                      "(note orchestration_alternatives.md §4.1 and §7.7)",
                      "(note orchestration_alternatives.md, section 4.1; same note, sections 5.3 and 6.6)",
                      "(proposal.md, section 42)"):
            with self.subTest(cited=cited):
                self.assertTrue(citation_problems(self.text + "\n" + cited + "\n", DOCS_DIR, NOTES_DIR))

    def test_a_section_that_exists_and_a_section_of_this_page_are_accepted(self):
        for cited in ("(report §3.3; §9.1, item 7)", "(note orchestration_alternatives.md, sections 4.1 and 5.3)",
                      "See section 42 of this page.", "([flow-spec.md](flow-spec.md), section 42)"):
            with self.subTest(cited=cited):
                self.assertEqual(citation_problems(self.text + "\n" + cited + "\n", DOCS_DIR, NOTES_DIR), [])

    def test_a_section_after_a_bare_note_on_a_page_that_names_none_is_refused(self):
        self.assertTrue(citation_problems("A fact (same note, §2).\n", DOCS_DIR, NOTES_DIR))

    def test_a_command_that_is_not_built_is_refused_unless_its_sentence_says_planned(self):
        self.assertTrue(command_problems(self.text + "\nRun `flow sweep` every night. It is planned.\n"))
        self.assertTrue(command_problems(self.text + "\n| `python3 cli/harness.py flow render` | writes the CI file |\n"))
        self.assertTrue(command_problems(self.text + "\n```\npython3 cli/harness.py flow drill x.json\n```\n"))
        self.assertEqual(command_problems(self.text + "\nRun `flow sweep` (planned, not built). Then `flow check`.\n"), [])
        self.assertEqual(command_problems(self.text + "\n| `flow render` | Planned, not built |\n"), [])
        self.assertEqual(command_problems(self.text + "\nOne flow run at a time, and a workflow sweep.\n"), [])

    def test_the_parser_is_really_asked(self):
        for word in ("new", "check", "place", "status", "next", "fit"):
            self.assertTrue(parser_knows(word), word)
        for word in ("render", "claim", "run-step", "report", "sweep", "exits", "drill", "scope"):
            self.assertFalse(parser_knows(word), word)

    def test_a_page_too_short_or_too_long_is_refused(self):
        self.assertTrue(length_problems("\n".join(self.text.splitlines()[:MIN_LINES - 1])))
        self.assertTrue(length_problems(self.text + "\nline" * MAX_LINES))


if __name__ == "__main__":
    unittest.main()
