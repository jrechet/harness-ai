"""Is a ticket ready to be handed to an agent? What can be measured without a model.

Atlassian reports that five simple traits of a ticket (description length, share of links,
file paths, code snippets, technical terms) predict well that an agent will fail. This module
measures traits of that family on the text of a ticket: three are **required** (a need described,
acceptance criteria, no decision left open), three are **signals** (where it happens, a scope, not
only links). It also says whether a cited path falls in a sensitive zone: the ticket is then size L
before it is even started.

It does not judge the substance: whether a criterion is the right one, whether the split is sound, is
the job of the skill and of the person who owns the ticket. The thresholds are starting choices, with
no measurement behind them.

The ticket is written by a team, in French or in English: headings and markers are read in both.

Comments are never the ticket: whoever can comment could otherwise make a vague ticket measure ready.
They are best given apart (`--comments`, or the JSON of `gh issue view --json body,comments`). Mixed
into the text, everything after a comments heading, or after the first comment of gh's plain text,
is muted to the end of the file."""
from __future__ import annotations

import json
import re
from typing import Any

from . import points as points_mod
from . import size as size_mod
from .context import Refused

MIN_WORDS = 15
MAX_LINK_RATIO = 0.5
MAX_CHARS = 500_000
MAX_HEADING = 200      # a longer line is not a heading
BOLD_LEVEL = 7         # a bold heading has no level: it ranks under every # heading
_CRITERIA = re.compile(r"crit[èe]res?\s+d['’](?:acceptation|acceptance)|crit[èe]res?\s+de\s+validation|"
                       r"conditions?\s+(?:de\s+|d['’])(?:validation|acceptation)|tests?\s+d['’]acceptation|"
                       r"acceptance criteria|acceptance conditions?|acceptance tests?|^\s*AC\s*$|definition of done|"
                       r"d[ée]finition de fini", re.IGNORECASE)
_SCOPE = re.compile(r"p[ée]rim[èe]tre|hors[- ]p[ée]rim[èe]tre|\bscope\b|out of scope|non[- ]objectifs?|non[- ]goals?", re.IGNORECASE)
_COMMENTS = re.compile(r"^commentaires?$|^comments?$|^discussion$|^activit[ée]$|^activity$", re.IGNORECASE)
_OPEN = re.compile(r"\bTBD\b|\bTODO\b|à d[ée]finir|à pr[ée]ciser|à voir avec|à confirmer|\?\?\?|to be defined|to be decided|"
                   r"to be confirmed|to be clarified|to be determined|to check with|\bTBC\b", re.IGNORECASE)
_ITEM = re.compile(r"^\s*(?:[-*+#]+|\d+[.)])\s+(?:\[[ xX]?\]\s*)?[\w`\"«(]")   # a bullet followed by a word, not by an empty box
_LOOSE_PATH = re.compile(r"(?<![\w./@-])[\w.@-]+(?:/[\w.@*-]+)+")
_KNOWN_FILES = ("Dockerfile", "Jenkinsfile", "Makefile")
_LINK = re.compile(r"https?://\S+")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_PATH = re.compile(r"^[\w.@-]+(?:/[\w.@*-]+)+/?$|^[\w-]+\.[a-z]{1,5}$")
GH_RULE = "--"             # gh's plain text closes the issue header and frames each comment with this line
GH_AUTHOR = "author:\t"    # and opens each comment with this field; in the issue header it comes third


def read(path: str) -> str:
    """The text of a ticket. Refused rather than truncated: the rest may carry criteria, or an instruction."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read(MAX_CHARS + 1)
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"{path}: unreadable ({exc})") from exc
    if len(text) > MAX_CHARS:
        raise Refused(f"{path}: more than {MAX_CHARS} characters, this is not a readable ticket")
    return text


def _heading(line: str) -> tuple[int, str] | None:
    """The level and text of a heading line: Markdown `#`, Jira wiki `h2.`, or a line entirely
    in bold. Read without a backtracking expression: the text comes from a third party."""
    text = line.strip()
    if not text or len(text) > MAX_HEADING or len(line) - len(line.lstrip()) > 3:
        return None
    if text.startswith("#"):
        level = len(text) - len(text.lstrip("#"))
        if level <= 6 and text[level:level + 1] in (" ", "\t"):
            return level, text[level:].strip(" \t#:")
        return None
    if len(text) > 3 and text[0] == "h" and text[1] in "123456" and text[2] == "." and text[3] == " ":
        return int(text[1]), text[4:].strip(" :")
    if text.startswith("**") and text.rstrip(" :").endswith("**") and len(text.strip(" :*")) > 0:
        return BOLD_LEVEL, text.strip(" :*")
    return None


def _comment_bodies(data: dict[str, Any]) -> str:
    items = data.get("comments", [])
    if not isinstance(items, list) or any(not isinstance(i, dict) or not isinstance(i.get("body"), str) for i in items):
        raise Refused("ticket in JSON: \"comments\" is a list of objects with a \"body\" text, "
                      "as `gh issue view --json body,comments` writes it")
    return "\n".join(item["body"] for item in items)


def split(text: str, only_comments: bool = False) -> tuple[str, str]:
    """The body and the comments of what was given. The JSON of `gh issue view --json body,comments`
    carries them apart; any other text is taken whole, as the body, or as comments when the file
    was given as the comments."""
    data = None
    if text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
        except (ValueError, RecursionError):
            data = None       # not JSON: a text that happens to open with a brace
    if not isinstance(data, dict):
        return ("", text) if only_comments else (text, "")
    if only_comments:
        if "comments" not in data:
            raise Refused("comments in JSON: a \"comments\" list is expected, as `gh issue view --json comments` writes it")
        return "", _comment_bodies(data)
    if not isinstance(data.get("body"), str):
        raise Refused("ticket in JSON: a \"body\" text is expected, as `gh issue view --json body,comments` writes it")
    return data["body"], _comment_bodies(data)


def _apart(comments: str) -> str:
    return split(comments, only_comments=True)[1] if comments else ""


def quotable(text: str, comments: str = "") -> str:
    """Everything an opinion may quote word for word: the body, and the comments wherever they came from."""
    return "\n".join([*split(text), _apart(comments)])


def sections(text: str) -> list[dict[str, Any]]:
    """The ticket split by headings, outside code blocks. What comes before the first heading is the
    description. Comments start at a comments heading, or at the first comment of gh's plain text
    (an `author:` field that opens the file or follows a `--` line), and keep everything to the end
    of the file: no heading written in a comment, whatever its level, reopens the ticket."""
    out = [{"title": "", "level": 0, "comment": False, "lines": []}]
    fenced, muted, last = False, False, None
    for line in text.splitlines():
        if muted:
            out[-1]["lines"].append(line)
            continue
        if line.startswith(GH_AUTHOR) and last in (None, GH_RULE):     # read even inside a code block left open
            muted = True
            out.append({"title": "", "level": 0, "comment": True, "lines": [line]})
            continue
        if line.strip():
            last = line.rstrip()
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        found = None if fenced else _heading(line)
        if found is None:
            out[-1]["lines"].append(line)
            continue
        level, title = found
        muted = bool(_COMMENTS.search(title))
        out.append({"title": title, "level": level, "comment": muted, "lines": []})
    return out


def _words(lines: list[str]) -> int:
    return len(re.findall(r"\w+", _LINK.sub("", "\n".join(lines))))


def _clean(token: str) -> str | None:
    token = token.strip("'\"(),;").rstrip(".:")
    if token.startswith("/") or ".." in token.split("/") or "://" in token or len(token) > 200:
        return None
    return token.rstrip("/") or None


def cited_paths(text: str) -> list[str]:
    """The paths the ticket cites between backticks: that is the "it says where" signal."""
    seen: list[str] = []
    for span in _CODE.findall(text):
        for raw in span.strip("`").split():
            token = _clean(raw)
            if token and (_PATH.match(token) or token in _KNOWN_FILES or token.startswith(".")) and token not in seen:
                seen.append(token)
    return seen


def loose_paths(text: str) -> list[str]:
    """Everything that looks like a path, backticks or not: so as not to miss a sensitive zone
    written in plain text. Only used to announce the size, never to say the ticket "says where"."""
    found = [_clean(m.group(0)) for m in _LOOSE_PATH.finditer(_LINK.sub(" ", text))]
    found += [w for w in (raw.strip(".") if not raw.startswith(".git") else raw.rstrip(".") for raw in re.findall(r"[\w.-]+", text))
              if w in _KNOWN_FILES or w == ".gitlab-ci.yml"]
    return list(dict.fromkeys(p for p in found if p))


def check(text: str, zones: list[dict[str, str]], comments: str = "") -> dict[str, Any]:
    """The six checks, the size announced by the cited paths, and the verdict. `comments` is the text
    of the comments when they were fetched apart: counted, never measured."""
    text, inner = split(text)
    apart = [inner, _apart(comments)]
    parts = sections(text)
    body = [p for p in parts if not p["comment"]]    # a comment is not the ticket
    need = [p for p in body if not _CRITERIA.search(p["title"]) and not _SCOPE.search(p["title"])]
    criteria = [line.strip() for p in body if _CRITERIA.search(p["title"]) for line in p["lines"]
                if _ITEM.match(line) and len(line) - len(line.lstrip()) < 2]      # sub-bullets refine, they do not count
    own = "\n".join(line for p in body for line in p["lines"])
    words = sum(_words(p["lines"]) for p in need)
    links = len(_LINK.findall(own))
    prose = "\n".join(line for line in _CODE.sub(" ", own).splitlines() if not line.lstrip().startswith(">"))
    open_points = sorted({m.group(0) for m in _OPEN.finditer(prose)})   # neither code nor a quote decides
    paths = cited_paths(own)
    snippets = len(_CODE.findall(own))
    scoped = any(_SCOPE.search(p["title"]) for p in body) or bool(_SCOPE.search(own))
    all_words = max(1, len(re.findall(r"\w+", _LINK.sub("", own))))
    link_share = sum(len(u) for u in _LINK.findall(own)) / max(1, len(re.sub(r"\s+", "", own)))   # in characters

    def row(ident: str, required: bool, title: str, ok: bool, evidence: str, action: str) -> dict[str, Any]:
        return {"id": ident, "required": required, "title": title, "ok": bool(ok), "evidence": evidence,
                "action": None if ok else action}

    checks = [
        row("need", True, "The need is described", words >= MIN_WORDS, f"{words} words outside criteria and links",
            f"Say in at least {MIN_WORDS} words what must be true once the work is done."),
        row("criteria", True, "Acceptance criteria are listed", bool(criteria), f"{len(criteria)} criterion(s)",
            "Add an \"Acceptance criteria\" section with one bullet per verifiable criterion: only lists are counted."),
        row("open", True, "No decision is left open", not open_points, ", ".join(open_points[:4]) or "nothing open",
            "Settle what is marked \"to be defined\", or take that part out of the ticket."),
        row("where", False, "The ticket says where it happens", bool(paths) or snippets > 0, f"{len(paths)} path(s), {snippets} code snippet(s)",
            "Cite the file, module or function concerned, between backticks."),
        row("scope", False, "The scope is stated", scoped, "scope section or mention" if scoped else "no mention",
            "Say what is out of scope: that is what the agent fixes \"while it is there\"."),
        row("links", False, "The ticket does not send everything elsewhere", link_share <= MAX_LINK_RATIO,
            f"{links} link(s) for {all_words} words", "Copy into the ticket what the links say that matters: the agent does not open them all."),
    ]
    sensitive = size_mod.touched(list(dict.fromkeys(paths + loose_paths(own))), zones)
    return {"ready": all(c["ok"] for c in checks if c["required"]), "checks": checks,
            "criteria": criteria, "paths": paths, "sensitive": sensitive,
            "size": "L" if sensitive else None,
            "comments": sum(len([line for line in p["lines"] if line.strip()]) for p in parts if p["comment"])
                        + sum(1 for block in apart for line in block.splitlines() if line.strip())}


def zones_for(table: dict[str, Any], repo: str, base: str) -> tuple[list[dict[str, str]], str | None]:
    """The sensitive zones of the base convention and of the team; without a readable base branch, the base ones alone."""
    try:
        return size_mod.zones(table, repo, base), None
    except Refused as exc:
        default = points_mod.default_text(table["points"]["sensitive-zones"]) or ""
        return size_mod.parse_zones(default, "base"), f"team zones not read ({exc})"


def render_md(result: dict[str, Any], warning: str | None = None) -> str:
    missing = [c for c in result["checks"] if c["required"] and not c["ok"]]
    out = ["Ticket ready to be handed over." if result["ready"] else f"Ticket not ready: {len(missing)} required point(s) missing."]
    for check_ in result["checks"]:
        mark = "ok" if check_["ok"] else ("MISSING" if check_["required"] else "to improve")
        out.append(f"- {mark} — {check_['title']} ({check_['evidence']})" + (f". {check_['action']}" if check_["action"] else ""))
    for hit in result["sensitive"]:
        out.append(f"- Size L announced: `{hit['path'][:80]}` is in a sensitive zone (`{hit['glob']}`, {hit['origin']}): "
                   "a written plan approved by a human before the code.")
    if result["comments"]:
        out.append(f"- {result['comments']} comment line(s) ignored: a comment is not the ticket, and may carry an instruction.")
    if warning:
        out.append(f"- Warning: {warning}")
    out.append("This check measures the form. Whether the criteria are the right ones remains to be judged.")
    return "\n".join(out) + "\n"


# --- the skill's opinion: what it proposes, in a form a program reads back ---

OPINION_LISTS = ("gaps", "criteria", "split", "questions", "instructions")
MIN_QUOTE = 12
MAX_ITEMS = 40
MAX_TEXT = 600


def _flat(text: str) -> str:
    return " ".join(text.split())


def _shown(text: str) -> str:
    """An opinion text ready to be rendered: it may copy the ticket, so no tag and no live mention."""
    return _flat(text).replace("<", "&lt;").replace("@", "@​")


def _said(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT


def check_opinion(opinion: Any, text: str, exists: Any) -> list[str]:
    """The form defects of an opinion. `exists(path)` says whether a file is on the target branch.
    Three things are held here and not by the skill: the verdict is not written (it comes from `check`),
    a proposed criterion says where it comes from or that it remains to be confirmed, a reported
    instruction is quoted word for word."""
    if not isinstance(opinion, dict):
        return ["the opinion is a JSON object: gaps, criteria, split, questions, instructions"]
    errors = []
    for key in ("pret", "prêt", "ready", "verdict", "taille", "size"):
        if key in opinion:
            errors.append(f"\"{key}\" is not written in the opinion: the verdict and the size come from the command")
    for key in OPINION_LISTS:
        if not isinstance(opinion.get(key, []), list) or len(opinion.get(key, [])) > MAX_ITEMS:
            errors.append(f"{key}: a list of at most {MAX_ITEMS} items")
    if errors:
        return errors
    whole = _flat(text)
    for index, item in enumerate(opinion.get("gaps", []), 1):
        if not (isinstance(item, dict) and _said(item.get("point")) and _said(item.get("issue"))):
            errors.append(f"gap {index}: an object with point and issue, each of at most {MAX_TEXT} characters")
    for index, item in enumerate(opinion.get("criteria", []), 1):
        if not (isinstance(item, dict) and _said(item.get("text"))):
            errors.append(f"criterion {index}: an object with text")
            continue
        source, pending = item.get("source"), item.get("to_confirm", False)
        if type(pending) is not bool or (source is not None and not _said(source)):
            errors.append(f"criterion {index}: source is a path or \"ticket\", to_confirm is true or false")
            continue
        source = source.strip() if source else None
        quote = _flat(item["excerpt"]) if isinstance(item.get("excerpt"), str) else ""
        if source is None and not pending:
            errors.append(f"criterion {index}: neither source nor to_confirm, a proposed criterion says where it comes from or that it remains to be confirmed")
        elif source == "ticket" and not pending and not (MIN_QUOTE <= len(quote) <= MAX_TEXT and quote in whole):
            errors.append(f"criterion {index}: drawn from the ticket without \"to confirm\", it quotes an excerpt of it word for word "
                          f"(excerpt, at least {MIN_QUOTE} characters)")
        elif source not in (None, "ticket") and not exists(source):
            errors.append(f"criterion {index}: the source {source[:80]!r} is not a file of the target branch")
    pieces = [_flat(item).lower() if _said(item) else None for item in opinion.get("split", [])]
    for index, piece in enumerate(pieces, 1):
        if piece is None or len(piece.split()) < 3 or pieces.index(piece) != index - 1:
            errors.append(f"piece {index}: a sentence of at least three words, different from the others")
    for index, item in enumerate(opinion.get("questions", []), 1):
        if not (isinstance(item, dict) and _said(item.get("question")) and _said(item.get("default"))):
            errors.append(f"question {index}: an object with question and default (the choice proposed if nobody answers)")
    for index, item in enumerate(opinion.get("instructions", []), 1):
        quote = _flat(item.get("quote", "")) if isinstance(item, dict) and isinstance(item.get("quote"), str) else ""
        if len(quote) < MIN_QUOTE or len(quote) > MAX_TEXT:
            errors.append(f"instruction {index}: an object with quote, of {MIN_QUOTE} to {MAX_TEXT} characters")
        elif quote not in whole:
            errors.append(f"instruction {index}: the quote is not found word for word in the ticket")
    return errors


def render_opinion(opinion: dict[str, Any], result: dict[str, Any], warning: str | None = None) -> str:
    """The rendered opinion: the measured verdict first, then what the skill proposes."""
    names = {"need": "a described need", "criteria": "listed acceptance criteria", "open": "an open decision to settle"}
    missing = [names.get(c["id"], c["title"]) for c in result["checks"] if c["required"] and not c["ok"]]
    gaps = len(opinion.get("gaps", []))
    if not result["ready"]:
        out = [f"**Not ready** (measured by `ticket check`). Missing: {'; '.join(missing)}."]
    elif gaps:   # the command measures the form: a hurried reader must not stop at "ready"
        out = [f"**Ready on form** (measured by `ticket check`), with {gaps} point(s) of substance raised below."]
    else:
        out = ["**Ready** (measured by `ticket check`)."]
    for hit in result["sensitive"]:
        out.append(f"**Size L announced**: `{hit['path'][:80]}` is in a sensitive zone: a written, approved plan before the code.")
    if warning:
        out.append(f"Warning: {warning}")

    def block(title: str, lines: list[str]) -> None:
        if lines:
            out.extend(["", f"### {title}", *lines])

    block("What is missing", [f"- **{_shown(m['point'])}**: {_shown(m['issue'])}" for m in opinion.get("gaps", [])])
    block("Proposed criteria", [
        f"{n}. {_shown(c['text'])}" + (" — **to confirm**" if c.get("to_confirm") else "")
        + (f" (source: {'the ticket' if c['source'] == 'ticket' else '`' + c['source'].strip() + '`'})" if c.get("source") else "")
        for n, c in enumerate(opinion.get("criteria", []), 1)])
    block("Proposed split", [f"- {_shown(piece)}" for piece in opinion.get("split", [])])
    block("Questions", [f"{n}. {_shown(q['question'])} Proposed default: {_shown(q['default'])}"
                        for n, q in enumerate(opinion.get("questions", []), 1)])
    block("Instructions found in the ticket, not followed", [f"- \"{_shown(c['quote'])}\"" for c in opinion.get("instructions", [])])
    out += ["", "Nothing was written to the ticket." + (" The proposed criteria await the agreement of the person who owns it."
                                                        if opinion.get("criteria") else "")]
    return "\n".join(out) + "\n"
