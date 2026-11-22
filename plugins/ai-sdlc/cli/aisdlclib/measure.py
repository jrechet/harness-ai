"""A team's pull-request signals over a period: what the proposal asks to read "before and after".

Read from the merged pull requests of the repository's forge, listed by `gh pr list --json`, or from a
folder of recorded answers (`--from`: the same listing, saved as prs.json). Read-only: nothing is written on
the forge or in the repository.

Per kind of author (agent or human):
- open to merge: the hours between the opening of the pull request and its merge;
- first review: the hours until the first review submitted by someone other than its author, before the merge;
- followed: the pull requests a later one fixed or reverted within N days of their merge.

How each is recognised, so that a figure can be argued with:
- agent: a commit of the pull request carries a `Co-Authored-By:` trailer that one of the markers recognises; a
  pull request listed without its commits is "unknown", never human by default. A marker is matched as a whole
  word, never as a part of one ("aider" is not in "Raider"). The default markers are also first names (Devin,
  Claude), so a name alone is not enough for them: the address of the trailer has to be an agent's (see
  `_agent_address`). A marker given by the team is matched as a whole word anywhere in the trailer: the team
  chose it. What is still misread: a person whose GitHub login is a default marker and who co-authors with
  their GitHub no-reply address is counted as an agent; an agent that signs with an ordinary address on a domain
  that does not carry its name is counted as human, unless the team gives its marker;
- revert: a later pull request titled "Revert …" whose body says "Reverts #N", or, when its body names no
  number, whose title quotes the title of the reverted one;
- fix: a later pull request, opened after the merge, whose title starts with "fix" or whose branch starts with
  fix/, hotfix/ or bugfix/, and which names #N in its title or body. A fix that does not name what it fixes
  is not seen; a fix that names a pull request for another reason is counted.

The cost per merged pull request is not in a pull-request history: it is said "unmeasured"."""
from __future__ import annotations

import datetime
import json
import math
import os
import re
import statistics
import subprocess
from typing import Any

from . import context
from .context import Refused

FIELDS = ("number", "title", "body", "author", "createdAt", "mergedAt", "headRefName", "reviews", "commits")
LIMIT = 1000            # pull requests read for one measure; a listing that reaches it is said cut
PAGE = 40               # pull requests per request: with their commits and reviews, GitHub refuses 50 (500,000 nodes at most)
LIST_TIMEOUT = 120      # seconds per request
RECORDING = "prs.json"
MAX_RECORDING = 200 * 1024 * 1024
DEFAULT_WINDOW = 7
MAX_WINDOW = 90
DEFAULT_MARKERS = ("claude", "copilot", "cursor", "codex", "devin", "aider")
KINDS = ("agent", "human", "unknown")
UNMEASURED = "unmeasured"

TRAILER = re.compile(r"^co-authored-by:(.*)$", re.I | re.M)
ADDRESS = re.compile(r"^(?P<name>[^<]*)<(?P<local>[^<>@\s]*)@(?P<domain>[^<>@\s]+)>\s*$")
GITHUB_NOREPLY = "users.noreply.github.com"   # people have such an address too: there, the login decides
AUTOMATED = re.compile(r"(?<![a-z])(?:no-?reply|bot)(?![a-z])")   # the mailbox of a no-reply or bot address
REVERT_TITLE = re.compile(r"^revert\b", re.I)
REVERTS = re.compile(r"\breverts\s+(?:[\w.-]+/[\w.-]+)?#(\d+)\b", re.I)
FIX_TITLE = re.compile(r"^(?:hot|bug)?fix(?:es|ed)?\b", re.I)
FIX_BRANCH = ("fix/", "hotfix/", "bugfix/")
MENTION = re.compile(r"(?<![\w/.-])#(\d+)\b")   # #12, not other/repo#12


# --- Reading ---------------------------------------------------------------------------------------

def _day(value: str, option: str) -> datetime.datetime:
    try:
        day = datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise Refused(f"{option}: a date as YYYY-MM-DD is expected") from None
    return datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)


def _instant(value: Any) -> datetime.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        when = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=datetime.timezone.utc)


def load_recorded(directory: str) -> list:
    """The listing saved in a folder: the output of the `gh pr list` command of `fetch`, as prs.json."""
    path = os.path.join(directory, RECORDING)
    try:
        if os.path.getsize(path) > MAX_RECORDING:
            raise Refused(f"{path} is too large to be a listing of pull requests")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused(f"no readable {RECORDING} in {directory}: the JSON printed by "
                      f"`gh pr list --state merged --limit {PAGE} --json {','.join(FIELDS)}` is expected there ({type(exc).__name__})") from exc


def _forge(repo: str) -> tuple[str, str]:
    """The host and owner/name of the repository's forge, from its origin remote (or its only one)."""
    code, out = context._git(repo, "remote")
    remotes = out.decode("utf-8", "replace").split() if code == 0 else []
    if not remotes:
        raise Refused("the repository has no remote, so no forge to ask; give recorded answers with --from")
    remote = "origin" if "origin" in remotes else remotes[0]
    code, out = context._git(repo, "remote", "get-url", remote)
    url = context.REMOTE_URL.match(out.decode("utf-8", "replace").strip()) if code == 0 else None
    if not url or {url["owner"], url["name"]} & {".", ".."}:
        raise Refused(f"the remote {remote} cannot be turned into a forge request")
    return url["host"], f"{url['owner']}/{url['name']}"


def _page(host: str, source: str, search: str, size: int) -> list:
    """One `gh pr list`: at most `size` merged pull requests matching the search. Refused if `gh` does not answer a list."""
    try:
        out = subprocess.run([context.GH, "pr", "list", "--repo", source, "--state", "merged", "--search", search,
                              "--limit", str(size), "--json", ",".join(FIELDS)],
                             capture_output=True, timeout=LIST_TIMEOUT, env=context._gh_env(host), stdin=subprocess.DEVNULL)
    except OSError as exc:
        raise Refused("gh is not installed: the pull requests cannot be listed; give recorded answers with --from") from exc
    except subprocess.TimeoutExpired as exc:
        raise Refused(f"gh did not list the pull requests of {source} in {LIST_TIMEOUT} seconds") from exc
    try:
        prs = json.loads(out.stdout.decode("utf-8", "replace")) if out.returncode == 0 else None
    except json.JSONDecodeError:
        prs = None
    if not isinstance(prs, list):
        raise Refused(f"gh could not list the pull requests of {source} (not GitHub, not signed in, or no such repository)")
    return prs


def fetch(repo: str, since: str, until: str | None, window: int) -> tuple[list, str, bool]:
    """The merged pull requests of the period, and those merged in the window after it (what may have fixed
    them), asked to `gh pr list` page by page: most recently opened first, each page starting again at the oldest
    opening seen, since `gh pr list` has no cursor. Returns the listing, the repository it comes from, and
    whether the listing is complete (False: cut at LIMIT, or a page brought nothing new)."""
    start = _day(since, "--since")
    if until is None:
        period = f"merged:>={start.date().isoformat()}"
    else:
        last = _day(until, "--until") + datetime.timedelta(days=window)
        period = f"merged:{start.date().isoformat()}..{last.date().isoformat()}"
    host, slug = _forge(repo)
    source = f"{host}/{slug}"
    prs: list = []
    seen: set = set()
    oldest = None
    while True:
        size = min(PAGE, LIMIT - len(prs))
        page = _page(host, source, f"{period}{f' created:<={oldest}' if oldest else ''} sort:created-desc", size)
        new = [item for item in page if not isinstance(item, dict) or item.get("number") not in seen]
        prs += new   # an entry that is not a pull request is kept: `measure` refuses it by its position
        seen |= {item.get("number") for item in new if isinstance(item, dict)}
        if len(page) < size:
            return prs, source, True
        openings = [item["createdAt"] for item in page if isinstance(item, dict) and _instant(item.get("createdAt"))]
        if len(prs) >= LIMIT or not new or not openings:
            return prs, source, False
        oldest = min(openings, key=_instant)


# --- Measuring -------------------------------------------------------------------------------------

def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _login(holder: Any) -> str:
    author = holder.get("author") if isinstance(holder, dict) else None
    return _text(author.get("login")).lower() if isinstance(author, dict) else ""


def _word(marker: str, text: str) -> bool:
    """The marker as a whole word of the text: not a part of a longer word ("aider" in "raider")."""
    before = r"(?<!\w)" if re.match(r"\w", marker) else ""   # an edge that is not a letter ("[bot]") bounds itself
    after = r"(?!\w)" if re.search(r"\w$", marker) else ""
    return re.search(before + re.escape(marker) + after, text) is not None


def _agent_address(marker: str, trailer: str) -> bool:
    """A default marker recognises a trailer by its address, since the name may be a person's ("Devin Smith"):
    the marker is a word of the address's domain (cursor.com), or a word of the name on a no-reply or bot
    address (Claude <noreply@anthropic.com>); on GitHub's no-reply domain, which people use too, the marker
    has to be a word of the login (175728472+Copilot, devin-ai-integration[bot])."""
    address = ADDRESS.match(trailer)
    if not address:
        return False
    name, local, domain = address["name"], address["local"], address["domain"]
    if domain == GITHUB_NOREPLY:
        return _word(marker, local.rpartition("+")[2])
    return _word(marker, domain) or (_word(marker, name) and AUTOMATED.search(local) is not None)


def _kind(item: dict, markers: list[str], own: bool) -> str:
    commits = item.get("commits")
    if not isinstance(commits, list) or not commits:
        return "unknown"
    recognises = _word if own else _agent_address
    for commit in (c for c in commits if isinstance(c, dict)):
        for trailer in TRAILER.findall(_text(commit.get("messageBody"))):
            if any(recognises(marker, trailer.strip().lower()) for marker in markers):
                return "agent"
    return "human"


def _first_review(item: dict, opened: datetime.datetime, merged: datetime.datetime) -> float | None:
    """Hours until the first review by someone else, submitted before the merge; None if there is none."""
    author, times = _login(item), []
    reviews = item.get("reviews") if isinstance(item.get("reviews"), list) else []
    for review in (r for r in reviews if isinstance(r, dict)):
        when = _instant(review.get("submittedAt"))
        if when is None or _text(review.get("state")).upper() == "PENDING" or _login(review) == author:
            continue
        if opened <= when <= merged:
            times.append(when)
    return _hours(min(times) - opened) if times else None


def _hours(span: datetime.timedelta) -> float:
    return round(span.total_seconds() / 3600, 1)


def _parse(prs: Any, markers: list[str], own: bool) -> list[dict[str, Any]]:
    """The merged pull requests of a listing, each with its dates read and its kind. Refuses what is not a listing."""
    if not isinstance(prs, list):
        raise Refused("the listing of pull requests is not a list: the JSON of `gh pr list --json` is expected")
    parsed = []
    for position, item in enumerate(prs, 1):
        if not isinstance(item, dict) or not isinstance(item.get("number"), int) or isinstance(item.get("number"), bool):
            raise Refused(f"entry {position} of the listing is not a pull request with its number")
        if item.get("mergedAt") is None:
            continue
        opened, merged = _instant(item.get("createdAt")), _instant(item.get("mergedAt"))
        if opened is None or merged is None or merged < opened:
            raise Refused(f"pull request #{item['number']} of the listing has no readable createdAt and mergedAt")
        parsed.append({"number": item["number"], "kind": _kind(item, markers, own), "opened": opened, "merged": merged,
                       "title": _text(item.get("title")).strip(), "body": _text(item.get("body")),
                       "branch": _text(item.get("headRefName")).lower(),
                       "open_to_merge_hours": _hours(merged - opened), "first_review_hours": _first_review(item, opened, merged)})
    return sorted(parsed, key=lambda p: (p["merged"], p["number"]))


def _targets(follower: dict[str, Any], by_number: dict[int, dict], by_title: dict[str, list[dict]]) -> list[tuple[dict, str]]:
    """The pull requests a later one says it reverts or fixes."""
    title, body = follower["title"], follower["body"]
    if REVERT_TITLE.match(title):
        named = [int(n) for n in REVERTS.findall(body)]
        if named:
            return [(by_number[n], "revert") for n in named if n in by_number]
        quoted = re.match(r'^revert\s+"(.*)"$', title, re.I | re.S)
        return [(target, "revert") for target in by_title.get(quoted.group(1).strip(), [])] if quoted else []
    if FIX_TITLE.match(title) or follower["branch"].startswith(FIX_BRANCH):
        named = dict.fromkeys(int(n) for n in MENTION.findall(title + "\n" + body))
        return [(by_number[n], "fix") for n in named if n in by_number]
    return []


def _followed(listed: list[dict], measured: list[dict], window: int) -> list[dict[str, Any]]:
    """Each measured pull request with the first later one that fixed or reverted it within the window."""
    by_number = {p["number"]: p for p in measured}
    by_title: dict[str, list[dict]] = {}
    for p in measured:
        by_title.setdefault(p["title"], []).append(p)
    limit, found = datetime.timedelta(days=window), {}
    for follower in listed:   # sorted by merge date: the first follower of a pull request is the one kept
        for target, how in _targets(follower, by_number, by_title):
            late = follower["merged"] - target["merged"]
            if target["number"] in found or follower["opened"] < target["merged"] or late > limit:
                continue
            found[target["number"]] = {"number": target["number"], "kind": target["kind"], "by": follower["number"], "how": how,
                                       "days": round(late.total_seconds() / 86400, 1)}
    return [found[number] for number in sorted(found)]


def _spread(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "median": None, "p90": None}
    ordered = sorted(values)
    return {"n": len(ordered), "median": round(statistics.median(ordered), 1), "p90": ordered[math.ceil(0.9 * len(ordered)) - 1]}


def _group(prs: list[dict], followed: list[dict]) -> dict[str, Any]:
    numbers = {p["number"] for p in prs}
    reviewed = [p["first_review_hours"] for p in prs if p["first_review_hours"] is not None]
    return {"merged": len(prs), "open_to_merge_hours": _spread([p["open_to_merge_hours"] for p in prs]),
            "first_review_hours": _spread(reviewed), "no_review": len(prs) - len(reviewed),
            "followed": sum(1 for f in followed if f["number"] in numbers)}


def measure(prs: Any, since: str, until: str | None = None, window: int | None = None,
            markers: list[str] | None = None) -> dict[str, Any]:
    """The signals of the pull requests merged from `since` (included) to `until` (excluded), by kind of author."""
    window = DEFAULT_WINDOW if window is None else window
    if not 1 <= window <= MAX_WINDOW:
        raise Refused(f"--window: between 1 and {MAX_WINDOW} days")
    start, end = _day(since, "--since"), _day(until, "--until") if until is not None else None
    if end is not None and end <= start:
        raise Refused("--until: a date after --since is expected")
    used = [m.strip().lower() for m in (markers or DEFAULT_MARKERS) if m.strip()]
    if not used:
        raise Refused("--agent-trailer: an empty marker would make every co-authored pull request an agent's")
    listed = _parse(prs, used, own=bool(markers))
    measured = [p for p in listed if p["merged"] >= start and (end is None or p["merged"] < end)]
    followed = _followed(listed, measured, window)
    groups = {kind: _group([p for p in measured if p["kind"] == kind], followed) for kind in KINDS}
    return {"since": since, "until": until, "window_days": window, "markers": used, "own_markers": bool(markers),
            "groups": {**groups, "all": _group(measured, followed)}, "followed": followed,
            "cost_per_merged_pr": UNMEASURED,
            "prs": [{key: p[key] for key in ("number", "kind", "open_to_merge_hours", "first_review_hours")} for p in measured]}


def run(repo: str, since: str, until: str | None, window: int | None, markers: list[str] | None,
        recorded: str | None) -> dict[str, Any]:
    """`measure`, on the recorded answers of a folder or on what `gh` lists for the repository."""
    checked = measure([], since, until, window, markers)   # the options are refused before the forge is asked
    warnings = []
    if recorded:
        prs, source = load_recorded(recorded), f"recorded answers in {recorded}"
    else:
        prs, source, complete = fetch(repo, since, until, checked["window_days"])
        if not complete:
            warnings.append(f"the listing stops at {len(prs)} pull requests: the period is cut, measure a shorter one")
    return {"source": source, "warnings": warnings, **measure(prs, since, until, window, markers)}


# --- Rendering -------------------------------------------------------------------------------------

def _cell(spread: dict[str, Any]) -> str:
    if not spread["n"]:
        return UNMEASURED
    return f"{spread['median']} h ({spread['p90']} h)"


def _rule(result: dict[str, Any]) -> str:
    markers = ", ".join(result["markers"])
    if result.get("own_markers"):
        return f"that holds, as a whole word, one of the team's markers: {markers}."
    return (f"whose address is an agent's, for one of: {markers}. The marker is a word of the address's domain, or of the "
            "co-author's name on a no-reply or bot address, or of the login on a GitHub no-reply address; a person named "
            "like an agent stays human, an agent signing with an ordinary address is not seen.")


def render_md(result: dict[str, Any]) -> str:
    window = result["window_days"]
    period = f"from {result['since']}" + (f" to {result['until']} (excluded)" if result["until"] else "")
    out = ["# Pull-request signals", "", f"Pull requests merged {period}."]
    if result.get("source"):
        out.append(f"Source: {result['source']}.")
    out += [f"Warning: {warning}" for warning in result.get("warnings", [])]
    out += ["", "| Author | Merged | Open to merge, median (p90) | First review, median (p90) | Merged without a review "
                f"| Fixed or reverted within {window} days |", "|---|---|---|---|---|---|"]
    for kind in (*KINDS, "all"):
        group = result["groups"][kind]
        if kind == "unknown" and not group["merged"]:
            continue
        counted = UNMEASURED if not group["merged"] else str(group["no_review"])
        fixed = UNMEASURED if not group["merged"] else f"{group['followed']} of {group['merged']}"
        out.append(f"| {kind} | {group['merged']} | {_cell(group['open_to_merge_hours'])} | {_cell(group['first_review_hours'])} "
                   f"| {counted} | {fixed} |")
    out += ["", f"Cost per merged PR: {UNMEASURED} (a pull-request history does not carry it)."]
    if result["followed"]:
        out += ["", "## Fixed or reverted", ""]
        out += [f"- #{f['number']} ({f['kind']}): {f['how']} #{f['by']}, {f['days']} days after its merge" for f in result["followed"]]
    out += ["", "## How this is read", "",
            f"- agent: a commit of the pull request carries a `Co-Authored-By:` trailer {_rule(result)} "
            "A pull request listed without its commits is \"unknown\".",
            "- first review: the first one submitted by someone other than the author, before the merge.",
            f"- fixed or reverted: a later pull request, merged within {window} days, that says \"Reverts #N\", quotes the title "
            "in a \"Revert …\" title, or is a fix (title or branch) naming #N. A fix that names nothing is not seen.",
            f"- a pull request merged less than {window} days before the listing was taken may still be fixed.", ""]
    return "\n".join(out)
