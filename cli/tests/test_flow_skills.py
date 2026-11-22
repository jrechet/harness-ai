"""The three flow skills (flow-why, flow-map, flow-place) keep the shape the others have: each one
guides the user, says in English and in French when it triggers and when it does not, calls a `flow`
sub-command that exists through the plugin root with flags that exist, promises no command that is
not built, names only pages and sections that exist, says what its result does not prove, copies
the words of the placement grid and of the `flow fit` verdicts to the letter, and stays short.
What the text makes an agent do is not checked here."""
from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS = ("flow-why", "flow-map", "flow-place")
DOCS = "docs/workflow-harness"
PLUGIN_CLI = 'python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow '
PLUGIN_DOCS = "${CLAUDE_PLUGIN_ROOT}/" + DOCS + "/"
# Commands of the proposal that no version ships: a skill that cites one as a command sends the user to an error.
NOT_BUILT = ("render", "claim", "run-step", "report", "sweep", "exits", "drill", "scope")
MIN_LINES, MAX_LINES = 60, 130
HELP_TIMEOUT_SECONDS = 60
NOT_PROVEN = {"flow-why": "Not measured", "flow-map": "What is not proven", "flow-place": "What is not proven"}
GRID_FILE = os.path.join(ROOT, "cli", "harnesslib", "flow_placement.json")
FIT_FILE = os.path.join(ROOT, "cli", "harnesslib", "flow_fit.json")
OTHER_MARKDOWN = {"SKILL.md", "AGENTS.md", "CLAUDE.md", "README.md"}   # files a skill may name that are not pages of DOCS

CODE_SPAN = re.compile(r"`([^`\n]+)`")
PAGE = re.compile(r"(?<![\w/-])([A-Za-z][\w-]*\.md)\b|/([A-Za-z][\w-]*\.md)\b")
SKILL_NAME = re.compile(r"\b((?:flow|harness)-[a-z]+)\b(?!\.md|/|\.json)")
ENGLISH_TRIGGER = re.compile(r'Use when[^«]*?"[^"]{8,}"')
FRENCH_TRIGGER = re.compile(r"also in French:\s*«[^»]{8,}»")
NEGATIVE = re.compile(r"Do not use [^.]*\([a-z-]+\)")
PLUGIN_CALL = re.compile(r'python3 "\$\{CLAUDE_PLUGIN_ROOT\}/cli/harness\.py" ((?:flow )?[a-z][a-z-]*)([^`\n]*)')
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z-]*")
SECTION = re.compile(r"([A-Za-z][\w-]*\.md)`?,? sections? (\d+)(?: and (\d+))?")


def skill_path(name: str, root: str = ROOT) -> str:
    return os.path.join(root, "skills", name, "SKILL.md")


def read_skill(name: str) -> str:
    with open(skill_path(name), encoding="utf-8") as fh:
        return fh.read()


def description(text: str) -> str:
    """The `description:` line of the header, or "" when the header has none."""
    header = text.split("\n---", 1)[0] if text.startswith("---") else ""
    for line in header.splitlines():
        if line.startswith("description:"):
            return line[len("description:"):].strip()
    return ""


def flow_calls(text: str) -> list[str]:
    """The `flow` sub-commands the text calls through the plugin root, in order."""
    return re.findall(re.escape(PLUGIN_CLI) + r"([a-z][a-z-]*)", text)


def harness_output(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(ROOT, "cli", "harness.py"), *args],
                          capture_output=True, text=True, timeout=HELP_TIMEOUT_SECONDS, check=False)


@functools.lru_cache(maxsize=None)
def built_commands() -> frozenset[str]:
    """The sub-commands `flow --help` lists between braces: the only ones a skill may write as a command."""
    listed = re.search(r"\{([a-z,-]+)\}", harness_output("flow", "--help").stdout)
    return frozenset(listed.group(1).split(",")) if listed else frozenset()


@functools.lru_cache(maxsize=None)
def help_text(command: str) -> str:
    """What `<command> --help` prints; `command` is "status" or "flow check"."""
    return harness_output(*command.split(), "--help").stdout


def unbuilt_commands(text: str) -> list[str]:
    """Each `flow <name>` written as a command (inside a code span) whose name `flow --help` does not list."""
    found = []
    for span in CODE_SPAN.findall(text):
        found.extend(f"flow {name}" for name in re.findall(r"\bflow ([a-z][a-z-]*)", span)
                     if name not in built_commands())
    return found


def unknown_flags(text: str) -> list[str]:
    """Each flag written after a call through the plugin root that the command's own help does not list."""
    return [f"{command} {flag}" for command, rest in PLUGIN_CALL.findall(text)
            for flag in FLAG.findall(rest) if flag not in help_text(command)]


def missing_sections(text: str) -> list[str]:
    """Each "<page>.md, section N" whose page has no heading "## N."."""
    found = []
    for page, *numbers in SECTION.findall(text):
        path = os.path.join(ROOT, DOCS, page)
        body = ""
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
        found.extend(f"{page} section {n}" for n in numbers if n and not re.search(rf"(?m)^## {n}\. ", body))
    return found


def table_first_cells(text: str, heading: str) -> list[str]:
    """The first cell of each row of the first table under a `### ` heading, without its header rows."""
    section = text.split(heading, 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    return [row.split("|")[1].strip() for row in rows[2:]]


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pages_named(text: str) -> list[str]:
    """Every Markdown file the text names, without its folder, each once, in order."""
    names = [a or b for a, b in PAGE.findall(text)]
    return list(dict.fromkeys(name for name in names if name not in OTHER_MARKDOWN))


def docs_paths_outside_the_plugin_root(text: str) -> list[str]:
    """Each mention of the docs folder that does not start at the plugin root: unreadable once installed."""
    return [text[max(0, at.start() - 25):at.end() + 20] for at in re.finditer(re.escape(DOCS + "/"), text)
            if not text[:at.end()].endswith(PLUGIN_DOCS)]


def skills_named(text: str) -> list[str]:
    return sorted(set(SKILL_NAME.findall(text)) - {"flow-format", "harness-flow"})


def flow_help_exit_code(name: str) -> int:
    """`flow <name> --help` exits 0 when the sub-command exists and 2 when it does not; it starts nothing."""
    done = subprocess.run([sys.executable, os.path.join(ROOT, "cli", "harness.py"), "flow", name, "--help"],
                          capture_output=True, timeout=HELP_TIMEOUT_SECONDS, check=False)
    return done.returncode


class FlowSkillsTests(unittest.TestCase):
    def test_each_skill_exists_under_its_own_name(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                self.assertTrue(os.path.isfile(skill_path(name)), f"{skill_path(name)} is missing")
                self.assertRegex(read_skill(name), rf"(?m)^name: {name}$")

    def test_each_skill_has_the_section_that_guides_the_user(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                self.assertRegex(read_skill(name), r"(?m)^## Guide the user$")

    def test_each_description_has_english_and_french_triggers_and_says_when_not_to_use_it(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                text = description(read_skill(name))
                self.assertTrue(text, "no description in the header")
                self.assertRegex(text, ENGLISH_TRIGGER, 'no English request in quotes after "Use when"')
                self.assertRegex(text, FRENCH_TRIGGER, 'no French request in « » after "also in French:"')
                self.assertRegex(text, NEGATIVE, 'no "Do not use …" that names the skill to use instead')

    def test_each_skill_calls_a_flow_command_that_exists_through_the_plugin_root(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                calls = flow_calls(read_skill(name))
                self.assertTrue(calls, f"the skill never calls {PLUGIN_CLI}…")
                for command in sorted(set(calls)):
                    self.assertEqual(flow_help_exit_code(command), 0, f"flow {command} does not exist")

    def test_no_skill_cites_as_a_command_one_that_is_not_built(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                self.assertEqual(unbuilt_commands(read_skill(name)), [])

    def test_every_flag_of_a_call_exists_and_none_replaces_a_file(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                text = read_skill(name)
                self.assertEqual(unknown_flags(text), [])
                forced = [rest for _, rest in PLUGIN_CALL.findall(text) if "--force" in rest]
                self.assertEqual(forced, [], "a call written with --force replaces the user's flow")

    def test_every_section_a_skill_cites_exists_in_its_page(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                self.assertEqual(missing_sections(read_skill(name)), [])

    def test_each_skill_says_what_its_result_does_not_prove(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                text = read_skill(name)
                self.assertRegex(text, r"(?m)^## What the result proves, and what it does not$")
                self.assertIn(NOT_PROVEN[name], text, "the report has no line for what is not proven or measured")

    def test_flow_place_copies_the_keys_and_the_places_of_the_grid(self):
        grid, text = load(GRID_FILE), read_skill("flow-place")
        keys = {question["from"]["key"] for question in grid["questions"].values()}
        asked = [cell.strip("`") for cell in table_first_cells(text, "### 3. ")]
        self.assertTrue(asked, "no table of keys under step 3")
        self.assertEqual([key for key in asked if key not in keys], [], "a key the grid does not read")
        says = sorted(place["says"] for place in grid["destinations"].values())
        self.assertEqual(sorted(table_first_cells(text, "### 5. ")), says, "the places of step 5 are not the grid's")

    def test_flow_why_copies_the_verdicts_of_flow_fit(self):
        sentences = [verdict["sentence"] for verdict in load(FIT_FILE)["verdicts"].values() if "sentence" in verdict]
        self.assertTrue(sentences, "flow_fit.json holds no verdict sentence")
        cells = table_first_cells(read_skill("flow-why"), "### 5. ")
        quoted = [quote for cell in cells for quote in re.findall(r'"([^"]+)"', cell)]
        self.assertTrue(quoted, "the table of step 5 quotes no verdict")
        for quote in quoted:
            parts = [part.strip() for part in quote.split("…")]
            self.assertTrue(any(all(part in sentence for part in parts) for sentence in sentences),
                            f'"{quote}" is not a verdict of flow fit')

    def test_the_commands_listed_as_not_built_are_not_built(self):
        # The day one of them ships, this fails: take it out of NOT_BUILT so the skills may cite it.
        for command in NOT_BUILT:
            with self.subTest(command=command):
                self.assertEqual(flow_help_exit_code(command), 2, f"flow {command} exists now")

    def test_every_page_a_skill_names_exists_and_is_reached_through_the_plugin_root(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                text = read_skill(name)
                pages = pages_named(text)
                self.assertTrue(pages, f"the skill names no page of {DOCS}")
                missing = [page for page in pages if not os.path.isfile(os.path.join(ROOT, DOCS, page))]
                self.assertEqual(missing, [], f"named by the skill, absent from {DOCS}")
                self.assertIn(PLUGIN_DOCS, text, "the skill never says where the pages are, from the plugin root")
                self.assertEqual(docs_paths_outside_the_plugin_root(text), [])

    def test_each_skill_is_60_to_130_lines(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                count = len(read_skill(name).splitlines())
                self.assertGreaterEqual(count, MIN_LINES, "too short to guide anyone")
                self.assertLessEqual(count, MAX_LINES, "too long: move detail to a page or to the command")

    def test_every_skill_they_hand_over_to_is_shipped_and_each_names_the_two_others(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                text = read_skill(name)
                for other in skills_named(text):
                    self.assertTrue(os.path.isfile(skill_path(other)), f"{name} names {other}, which is not shipped")
                refusal = description(text).split("Do not use", 1)[-1]
                for other in SKILLS:
                    if other != name:
                        self.assertIn(f"({other})", refusal, f'"Do not use" of {name} does not send to {other}')


class TheReadersTests(unittest.TestCase):
    """The functions above see what they must and leave the rest alone."""

    def test_a_flow_call_counts_only_through_the_plugin_root(self):
        self.assertEqual(flow_calls('`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow check x.json`'), ["check"])
        self.assertEqual(flow_calls("`python3 cli/harness.py flow check x.json`"), [])

    def test_an_unbuilt_command_counts_in_a_code_span_and_not_in_a_sentence(self):
        self.assertEqual(unbuilt_commands("run `flow sweep` then `harness.py flow run-step x`"), ["flow sweep", "flow run-step"])
        self.assertEqual(unbuilt_commands("a report, a sweep; the flow report is not built; `flow check`"), [])
        self.assertEqual(unbuilt_commands("`flow frobnicate x.json`"), ["flow frobnicate"])

    def test_a_flag_the_command_does_not_have_is_seen(self):
        call = '`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" %s`'
        self.assertEqual(unknown_flags(call % "flow status x.json --map" + " then `--ask`"), [])
        self.assertEqual(unknown_flags(call % "flow fit --ask"), ["flow fit --ask"])
        self.assertEqual(unknown_flags(call % "status --map --dry ."), ["status --dry"])

    def test_a_section_the_page_does_not_have_is_seen(self):
        self.assertEqual(missing_sections("decide.md, section 4; (flows.md, sections 2 and 3)"), [])
        self.assertEqual(missing_sections("`decide.md` section 14, flows.md, sections 2 and 9"),
                         ["decide.md section 14", "flows.md section 9"])

    def test_the_first_cells_of_a_table_are_read_under_their_heading_only(self):
        text = "### 1. A\n| K | V |\n|---|---|\n| `a` | x |\n\n### 2. B\n| K |\n|---|\n| b |\n"
        self.assertEqual(table_first_cells(text, "### 1. "), ["`a`"])
        self.assertEqual(table_first_cells(text, "### 2. "), ["b"])

    def test_pages_are_read_with_or_without_their_folder(self):
        text = "read `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/flows.md`, then `costs.md`, in this SKILL.md"
        self.assertEqual(pages_named(text), ["flows.md", "costs.md"])
        self.assertEqual(docs_paths_outside_the_plugin_root(text), [])
        self.assertEqual(len(docs_paths_outside_the_plugin_root("read docs/workflow-harness/flows.md")), 1)

    def test_the_description_is_read_from_the_header_only(self):
        self.assertEqual(description("---\nname: x\ndescription: Does it.\n---\ndescription: no\n"), "Does it.")
        self.assertEqual(description("# no header\ndescription: no\n"), "")

    def test_a_description_without_french_or_without_a_refusal_is_seen(self):
        full = 'Does it. Use when the user asks "where does this go?" — also in French: « où va cette étape ? ». Do not use to map (flow-map).'
        for pattern in (ENGLISH_TRIGGER, FRENCH_TRIGGER, NEGATIVE):
            self.assertRegex(full, pattern)
        self.assertNotRegex(full.replace("« où va cette étape ? »", "none"), FRENCH_TRIGGER)
        self.assertNotRegex(full.replace('"where does this go?"', "anything"), ENGLISH_TRIGGER)
        self.assertNotRegex(full.split(" Do not use")[0], NEGATIVE)


if __name__ == "__main__":
    unittest.main()
