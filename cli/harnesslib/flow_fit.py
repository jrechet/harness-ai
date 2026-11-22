"""`flow fit`: before any definition exists, does this team need a flow at all, and which tool?

A person, or the skill flow-why, records a few answers in a JSON file: what is being built, how
many tickets a week go through the path, whether the phases are chained by hand, and the
symptoms measured on the team's own runs, each a number or "not measured". This program gives
the verdict; nothing here measures anything.

  harness flow fit answers.json     the verdict ("-" reads the answers on the standard input)
  harness flow fit --questions      the questions and the allowed values

The rules and every sentence are data (`flow_fit.json`), taken from the report's sections 7 and 8
(docs/workflow-harness/report.md). The contract is section 11 of docs/workflow-harness/flow-spec.md.
A missing or unknown answer, or a key written twice, is refused with the key to fix, never guessed.
A symptom "not measured" never fires and is never counted as fine: every verdict lists it. A number
that is above its threshold but does not decide is listed too, with the reason.

Exit codes: 0 a verdict (or the questions), 1 refused answers, 2 wrong usage or an input that is
missing or is not JSON."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

from .flow import _show

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_fit.json")
LIST_THEM = "(flow fit --questions lists them)"
NUMBER = "a number, 0 or more"
WHOLE = "a whole number, 0 or more"
TOO_LARGE = "a number too large to print"
ENTRY = ("key", "symptom", "above", "written", "smallest_fix", "removed_by", "engine")
NOT_A_TICKET_FLOW = "The symptoms describe a ticket workflow: they did not decide here."
USAGE = ("give the answers file (or - for the standard input); to see the questions and the allowed values: "
         "flow fit --questions")


def load_rules(path: str = RULES_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _listed(words: list[str], last: str = "or") -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} {last} {words[-1]}"


class Answers(dict):
    """A JSON object as it was written: the keys that appear more than once are kept in `repeated`."""

    def __init__(self, pairs: list[tuple[str, Any]]):
        super().__init__(pairs)
        seen: set[str] = set()
        self.repeated = list(dict.fromkeys(key for key, _ in pairs if key in seen or seen.add(key)))


def parse(text: str) -> Any:
    """The answers a JSON text holds. Raises ValueError if it is not JSON. A key written twice is
    kept as a refusal for `fit`: the plain `json.loads` would keep its last value without a word."""
    try:
        return json.loads(text, object_pairs_hook=Answers)
    except RecursionError as exc:
        raise ValueError(f"the brackets are nested too deep ({exc})") from exc


def _quoted(value: Any) -> str:
    """A key or a value as the file would write it, on one line, with nothing a terminal would obey."""
    try:
        text = json.dumps(value, ensure_ascii=False)
    except ValueError:  # Python refuses to print a whole number of several thousand digits
        return TOO_LARGE
    return "".join(ch if ch.isprintable() else (f"\\u{ord(ch):04x}" if ord(ch) < 0x10000 else f"\\U{ord(ch):08x}")
                   for ch in text)


def _is_number(value: Any) -> bool:
    """A finite JSON number, 0 or more, of any size. A boolean is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value >= 0 and (isinstance(value, int) or math.isfinite(value))


def _is_whole(value: Any) -> bool:
    """A count: 3 or 3.0, never 0.5."""
    return _is_number(value) and (isinstance(value, int) or value.is_integer())


def _choices(rules: dict[str, Any], key: str) -> dict[str, str]:
    """The allowed values of a question with a fixed list, each with its plain words."""
    if key == "building":
        return {case: entry["label"] for case, entry in rules["cases"].items()}
    return dict(rules["questions"][key]["values"])


def _allowed(rules: dict[str, Any], key: str) -> str:
    """What may be written at a top-level key, in the words of a refusal."""
    kind = rules["questions"][key]["kind"]
    if kind == "number":
        return NUMBER
    if kind == "symptoms":
        return f"an object with one entry per symptom {LIST_THEM}"
    return _listed([json.dumps(value) for value in _choices(rules, key)])


def _symptom_allowed(rules: dict[str, Any], symptom: dict[str, Any]) -> str:
    number = "a number from 0 to 1" if symptom["unit"] == "share" else WHOLE
    return f"{number}, or {json.dumps(rules['not_measured'])}"


def _symptom_fits(rules: dict[str, Any], symptom: dict[str, Any], value: Any) -> bool:
    if isinstance(value, str):
        return value == rules["not_measured"]
    return _is_number(value) and value <= 1 if symptom["unit"] == "share" else _is_whole(value)


# --- Refusals --------------------------------------------------------------------------------------

def _problem(code: str, key: str, message: str) -> dict[str, str]:
    return {"code": code, "key": key, "message": message}


def _top_problem(rules: dict[str, Any], answers: dict[str, Any], key: str) -> dict[str, str] | None:
    allowed = _allowed(rules, key)
    if key not in answers:
        return _problem("missing", key, f'Add "{key}": {allowed}.')
    value, kind = answers[key], rules["questions"][key]["kind"]
    if kind == "number":
        fits = _is_number(value)
    elif kind == "symptoms":
        fits = isinstance(value, dict)
    else:
        fits = isinstance(value, str) and value in _choices(rules, key)
    if fits:
        return None
    return _problem("unknown_value", key, f'"{key}" is {_quoted(value)}: write {allowed}.')


def _symptom_problems(rules: dict[str, Any], given: dict[str, Any]) -> list[dict[str, str]]:
    problems = []
    for symptom in rules["symptoms"]:
        key, allowed = symptom["key"], _symptom_allowed(rules, symptom)
        if key not in given:
            problems.append(_problem("missing", f"symptoms.{key}", f'Add "{key}" under "symptoms": {allowed}.'))
        elif not _symptom_fits(rules, symptom, given[key]):
            problems.append(_problem("unknown_value", f"symptoms.{key}",
                                     f'"{key}" under "symptoms" is {_quoted(given[key])}: write {allowed}.'))
    return problems


def _key_problems(rules: dict[str, Any], answers: dict[str, Any], given: dict[str, Any]) -> list[dict[str, str]]:
    """The keys nobody reads, then the keys written more than once."""
    under = ' under "symptoms"'
    known = {symptom["key"] for symptom in rules["symptoms"]}
    unknown = [(key, _quoted(key)) for key in answers if key not in rules["questions"]]
    unknown += [(f"symptoms.{key}", _quoted(key) + under) for key in given if key not in known]
    repeated = [(key, _quoted(key)) for key in getattr(answers, "repeated", ())]
    repeated += [(f"symptoms.{key}", _quoted(key) + under) for key in getattr(given, "repeated", ())]
    return [_problem("unknown_key", key, f"{shown} is not an answer this command reads: remove it, or rename it "
                     "(flow fit --questions lists the keys).") for key, shown in unknown] + [
        _problem("duplicate_key", key, f"{shown} is written more than once: keep one.") for key, shown in repeated]


def problems_of(rules: dict[str, Any], answers: Any) -> list[dict[str, str]]:
    """Every answer to fix, in the order of the keys; the keys nobody reads and the repeated keys come last."""
    if not isinstance(answers, dict):
        return [_problem("not_an_object", "", "The answers must be one JSON object with the keys "
                         f"{_listed([json.dumps(key) for key in rules['questions']], 'and')} {LIST_THEM}.")]
    problems = [found for key in rules["questions"] if (found := _top_problem(rules, answers, key))]
    given = answers.get("symptoms")
    if isinstance(given, dict):
        problems += _symptom_problems(rules, given)
    else:
        given = {}
    return problems + _key_problems(rules, answers, given)


# --- The rules -------------------------------------------------------------------------------------

def _above(rules: dict[str, Any], given: dict[str, Any]) -> list[dict[str, Any]]:
    """The symptoms whose number is above its threshold, in table order. The row with no threshold
    (`above` is null) is here as soon as its number is above zero."""
    return [{**{name: symptom[name] for name in ENTRY}, "value": given[symptom["key"]]}
            for symptom in rules["symptoms"]
            if not isinstance(given[symptom["key"]], str) and given[symptom["key"]] > (symptom["above"] or 0)]


def _sorted_out(above: list[dict[str, Any]], ticket_flow: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The symptoms that fired, then those listed without deciding, each with the reason."""
    if not ticket_flow:
        return [], [{**entry, "reason": "not_a_ticket_workflow"} for entry in above]
    return ([entry for entry in above if entry["above"] is not None],
            [{**entry, "reason": "no_threshold"} for entry in above if entry["above"] is None])


def _measure(entry: dict[str, Any]) -> str:
    measured = f"{entry['key']} is {_show(entry['value'])}"
    return measured if entry["above"] is None else f"{measured}, above {_show(entry['above'])}"


def _symptom_verdict(rules: dict[str, Any], fired: list[dict[str, Any]]) -> dict[str, Any]:
    words = rules["verdicts"]["symptom"]
    count = ("A symptom is measured above its threshold" if len(fired) == 1
             else f"{len(fired)} symptoms are measured above their threshold")
    change = [words["would_change"]]
    if any(entry["engine"] for entry in fired):
        change.append(words["engine"])
    stays = [entry["key"] for entry in fired if not entry["engine"]]
    if stays:
        change.append(words["no_engine"].format(keys=_listed(stays)))
    return {"verdict": {"code": "symptom", "sentence": f"{count}: {'; '.join(_measure(e) for e in fired)}."},
            "tool": None, "why": words["why"], "would_change": " ".join(change), "source": words["source"]}


def _decide(rules: dict[str, Any], answers: dict[str, Any], fired: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules 1 to 4 of the contract, in order: the first that applies decides."""
    case, verdicts = rules["cases"][answers["building"]], rules["verdicts"]
    if "choice" in case:
        return {"verdict": {"code": "tool", "sentence": f"For {case['label']}: {case['choice']}."},
                "tool": case["choice"], "why": f"{case['why']} {NOT_A_TICKET_FLOW}", "would_change": case["would_change"],
                "source": case["source"]}
    if fired:
        return _symptom_verdict(rules, fired)
    by_hand = answers["chained_by_hand"] == "yes"
    if by_hand and answers["tickets_per_week"] == 0:
        words = verdicts["by_hand"]
        return {"verdict": {"code": "by_hand", "sentence": words["sentence"]}, "tool": None, "why": words["why"],
                "would_change": words["would_change"], "source": words["source"]}
    words = verdicts["ticket_state_and_ci"]
    why = words["why_by_hand"].format(tickets=_show(answers["tickets_per_week"])) if by_hand else words["why_chained"]
    return {"verdict": {"code": "ticket_state_and_ci", "sentence": words["sentence"]}, "tool": None, "why": why,
            "would_change": words["would_change"], "source": words["source"]}


def fit(answers: Any) -> dict[str, Any]:
    """The `fit` document of an answers value: one verdict, or the answers to fix. Never raises."""
    rules = load_rules()
    problems = problems_of(rules, answers)
    if problems:
        return {"passed": False, "problems": problems, "verdict": None}
    given = answers["symptoms"]
    fired, not_deciding = _sorted_out(_above(rules, given), "choice" not in rules["cases"][answers["building"]])
    unmeasured = [{"key": symptom["key"], "symptom": symptom["symptom"]} for symptom in rules["symptoms"]
                  if isinstance(given[symptom["key"]], str)]
    return {"passed": True, "problems": [], "building": answers["building"], "fired": fired,
            "not_deciding": not_deciding, "not_measured": unmeasured, **_decide(rules, answers, fired)}


def questions() -> dict[str, Any]:
    """What `flow fit --questions` prints: every key, its allowed values, and a file to start from."""
    rules = load_rules()
    asked = [{"key": key, "text": question["text"], "kind": question["kind"], "allowed": _allowed(rules, key),
              "values": _choices(rules, key) if question["kind"] == "choice" else None}
             for key, question in rules["questions"].items()]
    symptoms = [{**{name: symptom[name] for name in ("key", "symptom", "counts", "above", "written")},
                 "allowed": _symptom_allowed(rules, symptom)} for symptom in rules["symptoms"]]
    example = {"building": "ticket_workflow", "tickets_per_week": 12, "chained_by_hand": "yes",
               "symptoms": {symptom["key"]: rules["not_measured"] for symptom in rules["symptoms"]}}
    return {"facts_date": rules["facts_date"], "not_measured": rules["not_measured"], "questions": asked,
            "symptoms": symptoms, "example": example}


# --- Rendering -------------------------------------------------------------------------------------

def _threshold_words(entry: dict[str, Any]) -> str:
    if entry["written"]:
        return f'the report says "{entry["written"]}"'
    return "the report writes no threshold, so any measured occurrence above zero is named"


def _listed_line(rules: dict[str, Any], entry: dict[str, Any]) -> str:
    """One number above zero or above its threshold that did not decide, and why it did not."""
    head = f"- {_measure(entry)}: listed, it did not decide."
    if entry["reason"] != "no_threshold":
        return f"{head} {entry['symptom']}."
    left = next(symptom["left_to_you"] for symptom in rules["symptoms"] if symptom["key"] == entry["key"])
    return (f"{head} {left.format(value=_show(entry['value']))}. {entry['symptom']}. If it is many, first try: "
            f"{entry['smallest_fix']}. What removes it by design: {entry['removed_by']}.")


def render_md(document: dict[str, Any]) -> str:
    """What a person reads: the verdict, why, what would change it, its source, what was not measured."""
    if not document["passed"]:
        count = len(document["problems"])
        head = f"Refused: {count} answer{'' if count == 1 else 's'} to fix. No verdict is given on a guess."
        return "\n".join([head, *(f"- {problem['message']}" for problem in document["problems"])]) + "\n"
    lines = [f"Verdict: {document['verdict']['sentence']}", f"Why: {document['why']}"]
    lines += [f"- {_measure(entry)}: {_threshold_words(entry)}. {entry['symptom']}. First try: "
              f"{entry['smallest_fix']}. What removes it by design: {entry['removed_by']}."
              for entry in document["fired"]]
    rules = load_rules()
    lines += [_listed_line(rules, entry) for entry in document["not_deciding"]]
    lines += [f"What would change this answer: {document['would_change']}", f"Source: {document['source']}."]
    unmeasured = "; ".join(f"{entry['key']} ({entry['symptom']})" for entry in document["not_measured"])
    lines.append(f"Not measured, so not counted as fine: {unmeasured}." if unmeasured
                 else "Not measured: nothing. Every symptom has a number.")
    return "\n".join(lines) + "\n"


def render_questions(document: dict[str, Any]) -> str:
    unmeasured = json.dumps(document["not_measured"])
    lines = ["Before any definition exists, answer these in one JSON file, then run: flow fit <file> "
             f"(or flow fit - to read the standard input). Facts dated {document['facts_date']}.", ""]
    for question in document["questions"]:
        if question["kind"] == "choice":
            lines.append(f"- {question['key']}: {question['text']} One of:")
            lines += [f"    {json.dumps(value)}: {label}" for value, label in question["values"].items()]
        elif question["kind"] == "number":
            lines.append(f"- {question['key']}: {question['text']} {NUMBER[0].upper()}{NUMBER[1:]}.")
        else:
            lines.append(f"- {question['key']}: {question['text']} One entry per symptom below, each a whole number (a share "
                         f"from 0 to 1 for the first) or "
                         f"{unmeasured}. {unmeasured} is listed in the answer, never counted as fine.")
    for symptom in document["symptoms"]:
        if symptom["above"] is None:
            named = ('Never named as a symptom: the report says "many steps" and gives no number. A number above 0 '
                     "is listed for you to judge")
        else:
            named = f'Named above {_show(symptom["above"])}' + (f': the report says "{symptom["written"]}"'
                                                                if symptom["written"] else "")
        lines.append(f"    {symptom['key']}: {symptom['symptom']}. Write {symptom['counts']}. {named}.")
    lines += ["  Where the report writes no threshold, any measured occurrence above zero is named; "
              "steps_with_own_retry_rule is the one exception.", "",
              "A file to start from:", json.dumps(document["example"], indent=2)]
    return "\n".join(lines) + "\n"


# --- CLI -------------------------------------------------------------------------------------------

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", nargs="?", help='the answers, a JSON file; "-" reads the standard input')
    parser.add_argument("--questions", action="store_true",
                        help="prints the questions and the allowed values instead of a verdict")


def _read(path: str) -> Any:
    """The answers of a file, or of the standard input for "-". Raises ValueError when there are none to read."""
    if path == "-":
        try:
            return parse(sys.stdin.read())
        except ValueError as exc:
            raise ValueError(f"the standard input is not JSON ({exc})") from exc
    try:
        with open(path, encoding="utf-8") as fh:
            return parse(fh.read())
    except OSError as exc:
        raise ValueError(f"{path}: the file cannot be read ({exc.strerror or exc})") from exc
    except ValueError as exc:
        raise ValueError(f"{path}: the file is not JSON ({exc})") from exc


def _emit(fmt: str, document: dict[str, Any], markdown: str) -> None:
    if fmt == "json":
        text = json.dumps(document, ensure_ascii=False, indent=2)
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:  # a key holds half a character: only the escaped form can be printed
            text = json.dumps(document, indent=2)
        sys.stdout.write(text + "\n")
    else:
        sys.stdout.write(markdown)


def command(args: argparse.Namespace) -> int:
    """`flow fit`, from parsed arguments. Raises ValueError for a wrong usage or an unreadable input."""
    if args.questions:
        document = questions()
        _emit(args.format, document, render_questions(document))
        return 0
    if not args.file:
        raise ValueError(USAGE)
    document = fit(_read(args.file))
    _emit(args.format, document, render_md(document))
    note = ""
    if not document["passed"]:
        note = "The questions and the allowed values: flow fit --questions"
    elif document["verdict"]["code"] == "ticket_state_and_ci":
        note = "Next: flow new feature or flow new bug writes a starting definition."
    if note and args.format == "md":
        sys.stdout.flush()
        print(note, file=sys.stderr)
    return 0 if document["passed"] else 1
