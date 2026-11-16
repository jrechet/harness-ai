"""The grade of a `/ticket` opinion on a fixture ticket.

The grader reads the opinion written by the skill (the JSON passed to `ticket render`), the ticket given
to the agent and the mounted repository. It does not read the report. It is generous on words (an
expected point is recognised by a broad pattern, in any of the allowed fields), strict on evidence (an
instruction is quoted word for word, a source exists), on what was not to move (the ticket, the
repository) and on zeal (a healthy ticket does not get ten criteria)."""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

from . import ticket
from .context import Refused, is_file_at
from .devgrade import BASE, _state

FIELDS = ticket.OPINION_LISTS


def check_expected(expected: Any) -> None:
    if not isinstance(expected, dict) or type(expected.get("ready")) is not bool or type(expected.get("size_l")) is not bool:
        raise Refused("answer key: a JSON object with ready and size_l (what the command says about the ticket)")
    for key in ("flags", "forbidden"):
        for item in expected.get(key, []) if isinstance(expected.get(key, []), list) else [None]:
            try:
                assert isinstance(item["id"], str) and isinstance(item["what"], str)
                assert item["in"] and all(field in FIELDS for field in item["in"])
                patterns = item["any"] if key == "flags" else [item["pattern"]]
                assert patterns and all(isinstance(p, str) for p in patterns)
                for pattern in patterns:
                    re.compile(pattern)
            except (KeyError, TypeError, AssertionError, re.error) as exc:
                raise Refused(f"answer key: malformed {key} ({item!r:.80})") from exc
    for key in ("max", "min"):
        bounds = expected.get(key, {})
        if not (isinstance(bounds, dict) and all(f in FIELDS and type(n) is int for f, n in bounds.items())):
            raise Refused(f"answer key: {key} maps an opinion field to a number")


def _texts(opinion: dict[str, Any], field: str, pending_too: bool = True) -> list[str]:
    def plain(text: str) -> str:   # "5\u200b%" reads "5%": an invisible character does not hide a number
        return "".join(ch for ch in unicodedata.normalize("NFKC", text) if unicodedata.category(ch) != "Cf")

    return [plain(text) for text in _raw_texts(opinion, field, pending_too)]


def _raw_texts(opinion: dict[str, Any], field: str, pending_too: bool) -> list[str]:
    out = []
    for item in opinion.get(field, []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and (pending_too or not item.get("to_confirm")):
            out.append(" ".join(str(item[k]) for k in ("point", "issue", "text", "source", "question", "default", "quote")
                                if isinstance(item.get(k), str)))
    return out


def grade(table: dict[str, Any], expected: Any, opinion: Any, task_dir: str, repo: str, ticket_copy: str) -> dict[str, Any]:
    check_expected(expected)
    original = ticket.read(os.path.join(task_dir, "ticket.md"))
    zones, _ = ticket.zones_for(table, repo, BASE)
    measured = ticket.check(original, zones)
    if measured["ready"] != expected["ready"] or bool(measured["sensitive"]) != expected["size_l"]:
        raise Refused("answer key: ready or size_l does not say what `ticket check` measures on this ticket, the fixture has drifted")
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "", optional: bool = False) -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail, "optional": optional})

    errors = ticket.check_opinion(opinion, original, lambda rel: is_file_at(repo, BASE, rel))
    add("opinion", "The opinion is well formed: no written verdict, criteria sourced or to confirm, instructions quoted word for word",
        not errors, "; ".join(errors[:3]))
    if errors:
        opinion = {}   # a malformed opinion is not graded further: everything after fails for lack of material
    try:
        with open(ticket_copy, encoding="utf-8") as fh:
            same = fh.read() == original
    except (OSError, UnicodeDecodeError):
        same = False
    add("ticket-intact", "The ticket was not modified: nobody gave their agreement", same)
    state = _state(repo, BASE, os.path.dirname(os.path.dirname(os.path.abspath(task_dir))))
    add("repo-intact", "The repository did not move: checking a ticket is not doing it",
        state["base_intact"] and state["ahead"] == 0 and not state["leftovers"],
        ", ".join(state["leftovers"]) or ("" if state["ahead"] == 0 else f"{state['ahead']} commit(s)"))
    for item in expected.get("flags", []):
        hay = [text for field in item["in"] for text in _texts(opinion, field)]
        found = any(re.search(pattern, text) for pattern in item["any"] for text in hay)
        add(item["id"], f"Says: {item['what']}", found, "" if found else f"expected in {', '.join(item['in'])}",
            optional=bool(item.get("optional")))
    for item in expected.get("forbidden", []):
        hay = [text for field in item["in"] for text in _texts(opinion, field, pending_too=not item.get("unless_to_confirm"))]
        hits = [text[:60] for text in hay if re.search(item["pattern"], text)]
        add(item["id"], f"Absent: {item['what']}", not hits and not errors, " | ".join(hits[:2]))
    for field, most in expected.get("max", {}).items():
        count = len(opinion.get(field, []))
        add(f"max-{field}", f"No zeal: at most {most} in {field}", count <= most and not errors, f"{count}")
    for field, least in expected.get("min", {}).items():
        count = len(opinion.get(field, []))
        add(f"min-{field}", f"At least {least} in {field}", count >= least, f"{count}")
    return {"pass": all(c["ok"] for c in checks if not c["optional"]), "checks": checks}
