"""The notes of `harness flow`: what helps a person go on, printed on the standard error with
`--format md` only, one note per line. `flow_cli` prints them; this module only writes the
sentences (docs/workflow-harness/flow-spec.md, section 12). Nothing here decides anything."""
from __future__ import annotations

import os
import shlex
from typing import Any

from . import flow, flow_paths

PAGES = ("flow-format.md", "decide.md", "costs.md", "report.md", "flow-spec.md")
HELP_LAST = ("With --format md, every flow command that exits 0 or 1 ends, on stderr, with the full command as this "
             "installation runs it and the folder of the pages.")
NOT_READ = ("Measured symptoms were not read: this answer comes from the file alone. To read them, add --answers "
            "<the answers file given to flow fit>.")

CANNOT_SEE = ("flow check reads the file, not the programs: it cannot see a write a step does not declare, nor a step "
              "given the wrong type. The full list is in the page flow-spec.md, section 12.")
WAITING_REST = ("Nothing is wrong with these steps: a judge says whether they can really read what they are shown and "
                'refuse it, and the answer is written "can_judge": "yes" or "no" in the step. Until then flow place '
                "leaves such a step open and the flow stays under level 1 (Mapped).")


def waiting(definition: Any, gates: list[str]) -> str:
    """The waiting note (section 12.1): the approvals that wait for their judge, and those of them
    no run asks yet because they are behind the stop point. Empty when none waits."""
    if not gates:
        return ""
    head = (f"1 approval waits for its judge's answer: {gates[0]}." if len(gates) == 1
            else f"{len(gates)} approvals wait for their judge's answer: {', '.join(gates)}.")
    behind = [name for name in flow.beyond_stop(definition) if name in gates]
    tail = (f" Behind the point where a run stops as written, so asked by no run yet: {', '.join(behind)}. Level 1 "
            "needs an answer there too: moving stop_at must not be what answers for the judge." if behind else "")
    return f"{head} {WAITING_REST}{tail}"


def q(path: str) -> str:
    """A path inside a command of a note, quoted for a shell so that the command is safe to paste;
    a plain name is printed as it is (section 12.4)."""
    return shlex.quote(path)


def check_next_waiting(path: str) -> str:
    """`flow check`, on a flow that holds and whose placement fails only because gates wait."""
    return (f"Next: flow place {q(path)} says where each step belongs and which approvals still wait. This command "
            "does not look at that.")


def place_next_waiting(path: str, answers: str | None = None) -> str:
    """`flow place`, when it fails only because gates wait."""
    return f"Next: flow status {q(path)} --map{with_answers(answers)} shows what level 1 still needs."


def with_answers(answers: str | None) -> str:
    """The option a "Next: flow status …" note carries when the answers were given."""
    return f" --answers {q(answers)}" if answers else ""


def _counted(number: int, word: str) -> str:
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


def _careful(definition: Any, guard: dict[str, Any], keep: dict[str, Any] | None, refused: list[str]) -> str:
    """The "Careful:" note of one write whose last gate `flow place` refuses (section 12.2). A gate the
    flow cannot lose (`keep`, its `flow_paths.gate_keeps` entry), whichever write it keeps, is never
    offered for removal."""
    gate, stop = guard["last_gate"], guard["stop_point"]
    where = f"states.{guard['state']}.on.{guard['event']}"
    if keep is not None:
        judge = definition["states"][gate].get("judge")
        judge = judge if isinstance(judge, str) and judge.strip() else "its judge"
        with_others = keep["with"]
        then = " then" if with_others else ""
        dont = f"Do not remove it{flow_paths.together_with(with_others)}: flow check would{then} refuse the file"
        if where in keep["wheres"]:
            return (f'Careful: {gate} is the last gate before "{stop}", which cannot be taken back. {dont}. Give '
                    f"{judge} something they can read and refuse.")
        return (f'Careful: {gate} is the last gate before "{stop}". {dont}, for "{keep["stop"]}", which cannot be '
                f"taken back. Give {judge} something they can read and refuse.")
    struck = flow_paths.struck_with(definition, refused, gate)  # with the gates offered before it
    then = flow_paths.guard_of(definition, (guard["state"], guard["event"], stop), struck)
    return (f'Careful: {gate} is the last gate before "{stop}". Removed, the last one would be {then["last_gate"]}, '
            f"{_counted(then['steps_between'], 'step')} and {_counted(then['agents_between'], 'agent')} before the "
            "write.")


def last_gate(definition: Any, refused: list[str], found: dict[str, Any] | None) -> list[str]:
    """One "Careful:" note per write whose last gate is one `flow place` refuses (section 12.2): do not
    remove it when the flow cannot lose it, for this write or another, otherwise what the last gate
    would become."""
    if not found:
        return []
    out, keeps = [], flow_paths.gate_keeps(definition, refused)
    kept = flow_paths.kept_writes(definition, refused) if keeps else {}
    for guard in found["guards"]:
        gate = guard["last_gate"]
        if gate not in refused:
            continue
        keep = {**keeps[gate], "wheres": kept[gate]} if gate in keeps else None
        note = _careful(definition, guard, keep, refused)
        if note not in out:
            out.append(note)
    return out


def closing(root: str | None = None) -> str:
    """The closing note (section 12.4): how "flow" is typed with this copy, and where its pages are.
    `root` is the folder that holds the `cli/` of the running copy, links not resolved, never the
    current folder; only the path of harness.py is quoted for a shell."""
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    command = shlex.quote(os.path.join(root, "cli", "harness.py"))
    pages = os.path.join(root, "docs", "workflow-harness")
    where = (f"The pages ({', '.join(PAGES)}) are in {pages}." if os.path.isdir(pages)
             else "The pages are not installed with this copy.")
    return f'Here "flow" is typed: python3 {command} flow. {where}'


def fit_next(folder: str) -> str:
    """`flow fit`, after the verdict "ticket state and CI": where `flow new` writes, as it is typed."""
    return (f"Next: flow new feature --out .harness/flow/feature.json writes a starting definition under the current "
            f"folder, {folder}, and never replaces a file. For a bug flow: flow new bug --out .harness/flow/bug.json.")


def new_next(path: str) -> str:
    """`flow new`, once the file is written."""
    return (f"Next: edit {path} (every key is explained in the page flow-format.md), then flow check {q(path)}, "
            f"flow place {q(path)}, flow status {q(path)} --map.")


def fit_next_symptom(answers: str) -> str:
    """`flow fit`, after a symptom verdict: the two commands that read these answers beside a definition."""
    return (f"Next: with a flow definition, flow place <file> --answers {q(answers)} reads these symptoms beside it; "
            "flow new feature --out .harness/flow/feature.json writes one.")


def symptoms_read(path: str | None, measured: dict[str, Any] | None) -> str:
    """The note of section 12.5: whether the symptoms measured on the team's runs were read, and how many."""
    if measured is None:
        return NOT_READ
    said = (f"Symptoms read from {path}: {len(measured['fired'])} above threshold, {len(measured['not_deciding'])} "
            f"listed without a threshold, {len(measured['not_measured'])} not measured (never counted as fine).")
    return said + (f" flow fit {q(path)} gives the smallest fix to try first for each." if measured["fired"] else "")
