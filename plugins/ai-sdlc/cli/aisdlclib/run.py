"""The investigation of `/run` into an incident: what a program can enforce before it becomes a ticket.

`/run` investigates and proposes; it does not act in production. This module enforces four things the skill
can only promise:
- **a fact is quoted**: each fact of the timeline points to a piece of evidence (a log, an alert export, a file
  or a commit of the repository) and repeats an excerpt of it word for word;
- **a cause is a hypothesis**: it says which facts support it, and "confirmed" is not written without them;
- **a command is not made up**: the one an action proposes is written in the team's runbook, and a human
  runs it;
- **the ticket carries no recognisable secret or personal data**: all the text of the investigation is read,
  and a known shape (token, authentication header, password, address, number) gets it refused. An excerpt
  can replace it with `[redacted]` and remain verifiable. The shapes are few: a person's name or an in-house
  identifier pass. Nothing that comes from a piece of evidence is rendered active.

It renders the investigation as a ticket, and says whether that ticket would pass `ticket check`."""
from __future__ import annotations

import os
import re
import stat
from typing import Any

from . import guard, secu, ship, size, ticket
from .context import Refused, _git, _read_at, is_file_at, resolve_base

LISTS = ("facts", "hypotheses", "criteria", "actions", "not_verified", "instructions")
STATES = ("ongoing", "mitigated", "resolved")
VERDICTS = ("confirmed", "probable", "ruled-out")
ROLES = ("mitigate", "fix", "prevent")
MAX_ITEMS = 40
MAX_TEXT = 600
MAX_EVIDENCE = 20
MAX_EVIDENCE_SIZE = 20_000_000
MIN_QUOTE = 16          # "ERROR: x" is in every log: a shorter excerpt proves nothing
MASK = "[redacted]"
MAX_MASKS = 6
MIN_SENTENCE = 20
MAX_COMMITS = 200
# a key that names the cause outside the hypotheses; the former French keys are still refused
_CAUSE_KEYS = ("cause", "root_cause", "culprit", "responsible", "cause_racine", "coupable", "responsable")
_SHA = re.compile(r"[0-9a-f]{7,40}")
_PERSONAL = [
    ("email address", re.compile(r"[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,4}")),
    ("IP address", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])|(?<![\w:])(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}(?![\w:])")),
    ("phone number", re.compile(r"(?<![\w+])\+\d{1,3}(?:[ .-]?\d){7,12}(?!\d)|(?<![\w.])0[1-9](?:[ .]?\d{2}){4}(?![\d.])")),
    ("IBAN", re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?(?![A-Za-z0-9])")),
]
_CARD = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])")
# what a log carries and a diff does not: headers, cookies, unquoted key=value pairs
_LOG_SECRETS = [
    ("authentication header", re.compile(r"(?i)\b(?:proxy-)?authorization\s?[:=]\s?(?:bearer|basic|digest|token)?\s?[\w.~+/=-]{8,}")),
    ("session cookie", re.compile(r"(?i)\b(?:set-)?cookie\s?:\s?[^\s;=]{1,60}=[^\s;]{8,}")),
    ("value under a secret name", re.compile(
        r"(?i)(?<![a-z0-9])[a-z0-9_.-]{0,30}(?:passw(?:or)?d|pwd|passphrase|secret|token|api[_-]?key|apikey|access[_-]?key|"
        r"session[_-]?id|\bsid|credential)[a-z0-9_-]{0,20}[\"']?\s{0,2}[=:]\s{0,2}[\"']?(?!\[redacted\])([^\s\"'&;,]{6,200})")),
]


def _luhn(digits: str) -> bool:
    total = 0
    for index, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if index % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def sensitive(text: str) -> list[str]:
    """The kinds of sensitive content a text carries: secrets (the shapes of a diff and the shapes of a log) and
    recognisable personal data. The value is never returned."""
    found = list(secu._secret_kinds(text))
    for kind, pattern in _LOG_SECRETS:
        match = pattern.search(text)
        value = match[1] if match and match.groups() else None
        # a short value without a digit is prose ("the token: expired"), not a secret value
        if match and not (value is not None and (secu._placeholder(value) or (len(value) < 16 and not any(ch.isdigit() for ch in value)))):
            found.append(kind)
    found += [kind for kind, pattern in _PERSONAL if pattern.search(text)]
    if any(_luhn(re.sub(r"\D", "", m.group(0))) for m in _CARD.finditer(text)):
        found.append("card number")
    return list(dict.fromkeys(found))


def _strings(value: Any, where: str = "") -> list[tuple[str, str]]:
    """Each text of the investigation, with where it is."""
    if isinstance(value, str):
        return [(where, value)]
    if isinstance(value, dict):
        return [pair for key, item in value.items() for pair in _strings(item, f"{where}.{key}" if where else str(key)[:40])]
    if isinstance(value, list):
        return [pair for index, item in enumerate(value[:MAX_ITEMS * 2], 1) for pair in _strings(item, f"{where} {index}")]
    return []


def quoted_in(quote: str, lines: list[str]) -> bool:
    """Is the excerpt found word for word in a single line of the evidence? Two distant lines do not make a
    quote. `[redacted]` stands for a removed word (a secret, an address): the rest must match."""
    parts = quote.split(MASK)
    if len(parts) == 1:
        return any(quote in line for line in lines)
    if len(parts) - 1 > MAX_MASKS or sum(len(p.strip()) for p in parts) < MIN_QUOTE:
        return False
    pattern = re.compile(r"\S{1,300}?".join(re.escape(p) for p in parts))
    anchor = max(parts, key=len)
    return any(anchor in line and len(line) <= 20_000 and pattern.search(line) for line in lines)


def _flat(text: str) -> str:
    return " ".join(text.split())


def _said(value: Any, least: int = 1) -> bool:
    return isinstance(value, str) and least <= len(_flat(value)) and len(value) <= MAX_TEXT


def read_evidence(paths: list[str], repo: str) -> dict[str, list[str]]:
    """The evidence of the investigation, by file name, line by line. It lives outside the repository: it is
    production data."""
    if len(paths) > MAX_EVIDENCE:
        raise Refused(f"--evidence: at most {MAX_EVIDENCE} pieces of evidence")
    root = os.path.realpath(repo)
    found: dict[str, list[str]] = {}
    for path in paths:
        name = os.path.basename(path)
        real = os.path.realpath(path)
        if real == root or real.startswith(root + os.sep):
            raise Refused(f"--evidence {name}: production evidence is not stored in the repository")
        if name in found:
            raise Refused(f"--evidence: two pieces of evidence are named {name}")
        try:
            if not stat.S_ISREG(os.stat(path).st_mode):
                raise Refused(f"--evidence {name}: a regular file, not a folder or a pipe")
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read(MAX_EVIDENCE_SIZE + 1)
        except OSError as exc:
            raise Refused(f"--evidence {name}: unreadable ({type(exc).__name__})") from exc
        if len(text) > MAX_EVIDENCE_SIZE:
            raise Refused(f"--evidence {name}: more than {MAX_EVIDENCE_SIZE} characters, give the useful excerpt")
        found[name] = [_flat(line) for line in text.split("\n") if line.strip()]
    return found


def _commit(repo: str, sha: str, commit: str) -> list[str] | None:
    """The lines of the message of a commit reachable from the base branch or HEAD, or None."""
    if not _SHA.fullmatch(sha):
        return None
    if all(_git(repo, "merge-base", "--is-ancestor", sha, ref)[0] != 0 for ref in (commit, "HEAD")):
        return None
    code, out = _git(repo, "log", "-1", "--format=%B", f"{sha}^{{commit}}")
    return [_flat(line) for line in out.decode("utf-8", "replace").split("\n") if line.strip()] if code == 0 else None


def check(data: Any, evidence: dict[str, list[str]], repo: str, commit: str, runbook: list[str]) -> list[str]:
    """The defects of an investigation; an empty list if it holds."""
    if not isinstance(data, dict):
        return ["the investigation is a JSON object: title, impact, state, facts, hypotheses, criteria, actions, not_verified, instructions"]
    errors = [f"\"{key}\" is not written on its own: a cause is a hypothesis, with the facts that support it"
              for key in data if isinstance(key, str) and key.strip().lower() in _CAUSE_KEYS]
    for key in LISTS:
        if not isinstance(data.get(key, []), list) or len(data.get(key, [])) > MAX_ITEMS:
            errors.append(f"{key}: a list of at most {MAX_ITEMS} items")
    if errors:
        return errors
    if not _said(data.get("title"), 10):
        errors.append("title: what is broken for whom, in one line of at least 10 characters")
    if not _said(data.get("impact"), MIN_SENTENCE):
        errors.append(f"impact: who is affected, how, since when, in at least {MIN_SENTENCE} characters")
    if data.get("state") not in STATES:
        errors.append(f"state: {', '.join(STATES)}")
    facts = data.get("facts", [])
    if not facts:
        errors.append("facts: at least one quoted fact, an investigation without evidence is an opinion")
    for index, item in enumerate(facts, 1):
        if not (isinstance(item, dict) and _said(item.get("what"), 10) and _said(item.get("when")) and _said(item.get("source"))):
            errors.append(f"fact {index}: an object with when, what and source")
            continue
        source, quote = item["source"].strip(), _flat(item["excerpt"]) if isinstance(item.get("excerpt"), str) else ""
        if source.startswith("commit:"):
            lines, where = _commit(repo, source[7:].strip().lower(), commit), "the message of this commit"
            if lines is None:
                errors.append(f"fact {index}: the quoted commit does not exist in the history of the branch")
                continue
        elif source.startswith("repo:"):
            path = source[5:].strip()
            text = _read_at(repo, commit, path) if is_file_at(repo, commit, path) else None
            lines, where = ([_flat(line) for line in text.split("\n")] if text is not None else None), f"the file {path[:60]} of the base branch"
            if lines is None:
                errors.append(f"fact {index}: {where} does not exist")
                continue
        else:
            lines, where = evidence.get(source), f"the evidence {source[:60]}"
            if lines is None:
                errors.append(f"fact {index}: the evidence {source[:60]!r} was not given by --evidence"
                              + (f" (given: {', '.join(sorted(evidence))[:200]})" if evidence else ""))
                continue
        if not MIN_QUOTE <= len(quote) <= MAX_TEXT:
            errors.append(f"fact {index}: an excerpt of {MIN_QUOTE} to {MAX_TEXT} characters, taken word for word from one line of the source")
        elif not quoted_in(quote, lines):
            errors.append(f"fact {index}: the excerpt is not found word for word in one line of {where} "
                          f"(a removed word is written {MASK})")
    for index, item in enumerate(data.get("hypotheses", []), 1):
        refs = item.get("facts") if isinstance(item, dict) else None
        if not (isinstance(item, dict) and _said(item.get("text"), MIN_SENTENCE) and item.get("status") in VERDICTS
                and isinstance(refs, list) and all(type(n) is int and 1 <= n <= len(facts) for n in refs)):
            errors.append(f"hypothesis {index}: an object with text, status ({', '.join(VERDICTS)}) and facts (numbers of existing facts)")
        elif item["status"] in ("confirmed", "ruled-out") and not refs:
            errors.append(f"hypothesis {index}: \"{item['status']}\" without a fact that supports it: it is a probable hypothesis, no more")
        elif item["status"] == "probable" and not _said(item.get("verify"), 10):
            errors.append(f"hypothesis {index}: a probable hypothesis says how to verify it (verify)")
    criteria = data.get("criteria", [])
    if not criteria or not all(_said(c, MIN_SENTENCE) for c in criteria):
        errors.append(f"criteria: at least one acceptance criterion, each in a sentence of at least {MIN_SENTENCE} characters")
    for index, item in enumerate(data.get("actions", []), 1):
        if not (isinstance(item, dict) and _said(item.get("what"), 10) and item.get("role") in ROLES and _said(item.get("who"))):
            errors.append(f"action {index}: an object with what, role ({', '.join(ROLES)}) and who (the role that decides it)")
        elif item.get("command") is not None and (not isinstance(item["command"], str) or _flat(item["command"]) not in runbook):
            known = (" The ones it writes: " + "; ".join(f"`{ship._code(c)}`" for c in runbook[:8]) + ". A value between angle brackets "
                     "(<previous version>) stays written as is: the human replaces it.") if runbook else \
                " It writes none: describe the action, without a command."
            errors.append(f"action {index}: the command is not, in full and word for word, a command of the team's runbook "
                          f"(docs/agents/operations.md).{known}")
    for index, item in enumerate(data.get("not_verified", []), 1):
        if not _said(item, 10):
            errors.append(f"not_verified {index}: a sentence")
    pieces = [line for lines in evidence.values() for line in lines]
    for index, item in enumerate(data.get("instructions", []), 1):
        quote = _flat(item["quote"]) if isinstance(item, dict) and isinstance(item.get("quote"), str) else ""
        if not 12 <= len(quote) <= MAX_TEXT:
            errors.append(f"instruction {index}: an object with quote, of 12 to {MAX_TEXT} characters")
        elif not quoted_in(quote, pieces):
            errors.append(f"instruction {index}: the quote is not found word for word in one line of a piece of evidence")
    leaks = [(where, kinds) for where, text in _strings(data) for kinds in [sensitive(text)] if kinds]
    for where, kinds in leaks[:10]:
        errors.append(f"{where}: carries {' and '.join(kinds[:3])}: remove it, or replace it with {MASK} in an excerpt. "
                      "A secret seen in a log is reported to its owner.")
    return errors


def render(data: dict[str, Any]) -> str:
    """The investigation as a ticket: the headings `ticket check` recognises, and nothing active from the evidence."""
    plain = ship._plain
    out = [f"# Incident — {plain(data['title'], 160)}", "", f"**State**: {data['state']}", "", "## Impact", plain(data["impact"], MAX_TEXT), "",
           "## What we know"]
    for number, fact in enumerate(data["facts"], 1):
        quote = f": \"{plain(fact['excerpt'], MAX_TEXT)}\"" if isinstance(fact.get("excerpt"), str) and fact["excerpt"].strip() else ""
        out.append(f"{number}. {plain(fact['when'], 40)} — {plain(fact['what'], MAX_TEXT)} ({plain(fact['source'], 80)}{quote})")
    if data.get("hypotheses"):
        out += ["", "## Hypotheses"]
        for item in data["hypotheses"]:
            refs = ", ".join(str(n) for n in item["facts"]) or "none"
            check_ = f" To decide: {plain(item['verify'], MAX_TEXT)}" if isinstance(item.get("verify"), str) and item["verify"].strip() else ""
            out.append(f"- **{item['status']}** — {plain(item['text'], MAX_TEXT)} (facts: {refs}).{check_}")
    out += ["", "## Acceptance criteria", *(f"- {plain(c, MAX_TEXT)}" for c in data["criteria"])]
    if data.get("actions"):
        out += ["", "## Proposed actions, for a human to decide"]
        for item in data["actions"]:
            command = f": `{ship._code(item['command'])}`" if isinstance(item.get("command"), str) else ""
            out.append(f"- to {item['role']} — {plain(item['what'], MAX_TEXT)}{command} (decided by: {plain(item['who'], 80)})")
    if data.get("instructions"):
        out += ["", "## Instructions found in the evidence, not followed", *(f"- \"{plain(c['quote'], MAX_TEXT)}\"" for c in data["instructions"])]
    if data.get("not_verified"):
        out += ["", "## Not verified", *(f"- {plain(n, MAX_TEXT)}" for n in data["not_verified"])]
    return "\n".join(out) + "\n"


def investigation(table: dict[str, Any], repo: str, base: str, data: Any, evidence_paths: list[str]) -> tuple[dict[str, Any], str]:
    """The investigation, checked and rendered as a ticket; Refused if it does not hold."""
    from . import context as context_mod
    commit = resolve_base(repo, base)
    blocks = context_mod.assemble(table, repo, "run", base)["blocks"]
    runbook = guard.team_commands("\n".join(b["text"] for b in blocks if b["origin"] == "team"))
    evidence = read_evidence(evidence_paths, repo)
    errors = check(data, evidence, repo, commit, runbook)
    if errors:
        raise Refused("investigation refused:\n- " + "\n- ".join(errors[:20]))
    body = render(data)
    measured = ticket.check(body, [])
    missing = [c["title"] for c in measured["checks"] if c["required"] and not c["ok"]]
    notes = ["Ticket ready to go through the ticket skill." if measured["ready"]
             else "Ticket not yet ready for the ticket skill: " + "; ".join(missing) + ".",
             "No known shape of secret or personal data in this text; a person's name or an in-house identifier "
             "are not recognised: reread before publishing.",
             "A \"confirmed\" hypothesis quotes its facts; whether those facts prove it is for a human to judge.",
             "Nothing was run in production. The ticket is not created: it is created on agreement."]
    return {"investigation": data, "ready": measured["ready"]}, body + "\n---\n" + "\n".join(notes) + "\n"


def changes(table: dict[str, Any], repo: str, base: str, since: str, until: str = "HEAD") -> dict[str, Any]:
    """What shipped between two versions: the commits, and the files in a sensitive zone. Material for an
    investigation, not a culprit: a change in the window is not the cause."""
    for ref in (since, until):
        if ref.startswith("-") or _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")[0] != 0:
            raise Refused(f"{ship._plain(ref, 60)}: neither a tag nor a commit of this repository")
    if _git(repo, "merge-base", "--is-ancestor", since, until)[0] != 0:
        raise Refused(f"{ship._plain(since, 60)} is not an ancestor of {ship._plain(until, 60)}")
    code, out = _git(repo, "log", "--no-merges", f"--max-count={MAX_COMMITS + 1}", "--format=%h%x00%cI%x00%s%x01", f"{since}..{until}")
    if code != 0:
        raise Refused("unreadable history")
    rows = [entry.strip("\n").split("\0") for entry in out.decode("utf-8", "replace").split("\x01")]
    commits = [{"sha": r[0], "date": r[1][:16], "subject": "(subject redacted: it carries " + sensitive(r[2])[0] + ")" if sensitive(r[2]) else ship._plain(r[2])}
               for r in rows if len(r) == 3 and r[0]]
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", f"{since}..{until}")
    paths = [p for p in out.decode("utf-8", "replace").split("\0") if p] if code == 0 else []
    hits = size.touched(paths, size.zones(table, repo, base))
    return {"since": ship._plain(since, 60), "until": ship._plain(until, 60), "commits": commits[:MAX_COMMITS],
            "truncated": len(commits) > MAX_COMMITS, "files": len(paths),
            "sensitive": [{"path": ship._plain(h["path"], 100), "glob": ship._plain(h["glob"], 40)} for h in hits[:MAX_ITEMS]]}


def render_changes(result: dict[str, Any]) -> str:
    out = [f"Between {result['since']} and {result['until']}: {len(result['commits'])} commit(s)"
           + (", the oldest not read" if result["truncated"] else "") + f", {result['files']} file(s) changed."]
    out += [f"- {c['date']} {c['sha']} {c['subject']}" for c in result["commits"]]
    if result["sensitive"]:
        out += ["", "In a sensitive zone:", *(f"- {s['path']} ({s['glob']})" for s in result["sensitive"])]
    out += ["", "The dates are those of the commits, not of their release to production.",
            "A change in the window is not a cause: it is a lead, to check against the evidence."]
    return "\n".join(out) + "\n"
