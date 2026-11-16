"""The body of a PR opened by `/dev`: what changes, why, the plan, what is verified and what is not.

The definition of done asks the description to say these things. They are required here, not in the
skill's text: an incomplete body is not rendered, and neither is a size L change without its plan in
the diff. The size shown is the one the CLI computes, not the one the agent estimates."""
from __future__ import annotations

from typing import Any

from . import size as size_mod
from .context import Refused, _read_at


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _texts(value: Any, empty_ok: bool = False) -> bool:
    return isinstance(value, list) and all(_text(v) for v in value) and (empty_ok or bool(value))


def validate(data: Any, sized: dict[str, Any], plans_dir: str) -> list[str]:
    """What the body lacks to be rendered, given the size of the change."""
    if not isinstance(data, dict):
        return ["the body is a JSON object: title, ticket, changes, why, plan, checked, not_verified"]
    errors = []
    if not _text(data.get("title")) or "\n" in data["title"].strip():
        errors.append("title: one line, only one")
    if data.get("ticket") is not None and not _text(data.get("ticket")):
        errors.append("ticket: its key or link, or null if there is none")
    if not _texts(data.get("changes")):
        errors.append("changes: the list of what changes, at least one line")
    if not _text(data.get("why")):
        errors.append("why: the reason for the change")
    checks = data.get("checked")
    if not isinstance(checks, list) or not all(
            isinstance(c, dict) and _text(c.get("command")) and _text(c.get("result")) for c in checks):
        errors.append("checked: a list of {command, result}, empty if nothing was run")
        checks = None
    unchecked = data.get("not_verified")
    if not _texts(unchecked, empty_ok=True):
        errors.append("not_verified: a list of sentences, empty if everything is verified")
    elif checks == [] and not unchecked:
        errors.append("checked and not_verified are empty: say what was run, or what was not")
    plan = data.get("plan", [])
    if not _texts(plan, empty_ok=True):
        errors.append("plan: a list of steps")
    elif sized["size"] == "S-M" and not plan:
        errors.append("plan: a size S-M change carries its plan in the description")
    if sized["size"] == "L":
        plan_file = data.get("plan_file")
        if not _text(plan_file) or not plan_file.startswith(plans_dir + "/") or plan_file not in sized["paths"]:
            errors.append(f"plan_file: a size L change has its plan in {plans_dir}/, committed in "
                          "this branch and approved by a human before the code")
    return errors


def checked(table: dict[str, Any], data: Any, repo: str, base: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sized = size_mod.classify(table, repo, base)
    errors = validate(data, sized, table["plans_dir"])
    if not errors and sized["size"] == "L":
        try:
            plan = _read_at(repo, "HEAD", data["plan_file"])
        except Refused:
            plan = None
        if not plan or not plan.strip():
            errors.append(f"plan_file: {data['plan_file']} is missing or empty in this branch")
    if errors:
        raise Refused("PR body refused:\n- " + "\n- ".join(errors))
    return data, sized


def _line(text: str) -> str:
    """One line and one only, with no HTML and no mention: a text can neither open a section of its
    own, nor hide the rest of the body, nor notify anyone."""
    return " ".join(text.split()).replace("&", "&amp;").replace("<", "&lt;").replace("@", "@​")


def render_md(data: dict[str, Any], sized: dict[str, Any]) -> str:
    out = ["## What changes", *[f"- {_line(q)}" for q in data["changes"]], "", "## Why", f"> {_line(data['why'])}", ""]
    out.append(f"Ticket: {_line(data['ticket'])}" if data.get("ticket") else "Ticket: none.")
    plan = [f"- {_line(p)}" for p in data.get("plan", [])]
    if data.get("plan_file") and sized["size"] == "L":
        plan.insert(0, f"Written plan: `{_line(data['plan_file'])}`.")
    if plan:
        out += ["", "## Plan", *plan]
    checks = [f"- `{_line(c['command']).replace('`', chr(39))}`: {_line(c['result'])}" for c in data["checked"]]
    out += ["", "## Verified", *(checks or ["Nothing was run."])]
    out += ["", "## Not verified", *([f"- {_line(u)}" for u in data["not_verified"]] or ["Nothing reported."])]
    out += ["", "---", f"Computed size: {sized['size']} — {sized['files']} files, {sized['lines']} lines changed."]
    out += [f"Sensitive zone: `{hit['path']}` (`{hit['glob']}`, {hit['origin']})." for hit in sized["sensitive"]]
    return "\n".join(out) + "\n"
