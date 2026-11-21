#!/usr/bin/env python3
"""GitHub adapter of harness-harvest.

Writes to stdout the evidence JSON described in references/signals.md,
without an LLM: it spots, dates, links and proposes a grouping key. It
decides neither the verdict nor the wording of a rule.

Reads team-written text in French and in English: `rule:` comments, the
AGENTS.md section headings it skips, the sentences where an agent says it
guessed.

Transport: `gh api` (already authenticated on a dev machine and in
Claude Code sessions). Errors go to stderr; the exit code is 2 if at
least one source could not be read, 0 otherwise.

Example:
  python3 cli/harness.py harvest github --repo owner/repo --since 2026-10-08 \
      --agent-login claude --agent-branch-prefix claude/ --agents-md AGENTS.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

Fetcher = Callable[[str, dict[str, Any] | None], Any]

# ---------------------------------------------------------------- transport


class GhError(RuntimeError):
    pass


def gh_api(path: str, params: dict[str, Any] | None = None) -> Any:
    """One `gh api` call, without pagination. Raises GhError if gh fails."""
    query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    url = f"{path}?{query}" if query else path
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github+json", url],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GhError(proc.stderr.strip() or f"gh api {url} failed")
    return json.loads(proc.stdout or "null")


def paginate(fetch: Fetcher, path: str, params: dict[str, Any] | None = None,
             stop: Callable[[dict], bool] | None = None, cap: int = 2000) -> list[dict]:
    """Paginates a list endpoint. `stop(item)` true stops the reading."""
    out: list[dict] = []
    page = 1
    while len(out) < cap:
        batch = fetch(path, {**(params or {}), "per_page": 100, "page": page})
        if not batch:
            break
        for item in batch:
            if stop and stop(item):
                return out
            out.append(item)
        if len(batch) < 100:
            break
        page += 1
    return out


# ------------------------------------------------------------------- utils

ISO = "%Y-%m-%dT%H:%M:%SZ"


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, ISO).replace(tzinfo=timezone.utc)


def day(value: str | None) -> str | None:
    return value[:10] if value else None


STOPWORDS = set("""
dans pour avec sans sous cette celui celle leurs votre notre toute toutes tous
jamais toujours doit doivent être avoir faire quand comme plus moins aussi
the and for with from that this these those have must never always should
should not into onto over under when then than
""".split())


def keywords(text: str, min_len: int = 5) -> set[str]:
    words = re.findall(r"[a-zà-ÿ0-9_./-]+", text.lower())
    return {w for w in words if len(w) >= min_len and w not in STOPWORDS}


def comment_words(text: str) -> set[str]:
    """Keywords of a comment, without code or links, to detect a recurrence (S3)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return keywords(text)


def title_words(title: str) -> set[str]:
    """Significant words of a PR title, to detect a type of task (S6)."""
    t = title.lower()
    t = re.sub(r"\[[^\]]*\]", " ", t)                      # [JIRA-12]
    t = re.sub(r"\b[a-z]+-\d+\b", " ", t)                   # abc-123
    t = re.sub(r"`[^`]*`|\"[^\"]*\"|'[^']*'", " ", t)         # quotes
    t = re.sub(r"\bv?\d+(\.\d+)*\b", " ", t)                 # versions, numbers
    t = re.sub(r"[^a-zà-ÿ ]", " ", t)
    return {w for w in t.split() if len(w) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


TITLE_THRESHOLD = 0.6      # S6: two titles are "the same task"
COMMENT_THRESHOLD = 0.6    # S3: two comments are "the same correction"
QUESTION_THRESHOLD = 0.5   # S7: two sentences are about "the same subject"


def cluster(sets: list[set[str]], threshold: float) -> list[dict]:
    """Greedy grouping: an element joins the first group whose anchor is similar
    enough, otherwise it opens a group. Deterministic, no learning.
    Returns [{"idx": [i…], "common": set}]; `common` is the group's intersection."""
    groups: list[dict] = []
    for i, s in enumerate(sets):
        if not s:
            continue
        for grp in groups:
            if jaccard(grp["anchor"], s) >= threshold:
                grp["idx"].append(i)
                grp["common"] &= s
                break
        else:
            groups.append({"anchor": set(s), "idx": [i], "common": set(s)})
    return groups


def label(common: set[str], limit: int = 60) -> str:
    return " ".join(sorted(common))[:limit]


RULE_PREFIX = re.compile(r"^\s*rule\s*:\s*(.+)", re.I | re.S)
# The forms an agent uses to say it guessed, in French and in English.
QUESTION_PATTERNS = re.compile(
    r"(j'ai suppos|je n'ai pas trouv|hypoth[èe]se|je ne sais pas|pas s[ûu]r|"
    r"i assumed|assum(ed|ing) that|could not find|couldn't find|not sure|unclear|"
    r"i guessed|unsure|hypothesis|assumption|i don['’]?t know|i do not know)",
    re.I,
)


def sentences(text: str) -> list[str]:
    text = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


# ------------------------------------------------------------- agent rules


class AgentMarkers:
    def __init__(self, logins: Iterable[str], branch_prefixes: Iterable[str],
                 labels: Iterable[str], trailers: Iterable[str],
                 automation_prefixes: Iterable[str] = ("renovate/", "dependabot/")):
        self.automation_prefixes = [p.lower() for p in automation_prefixes]
        self.logins = {l.lower() for l in logins}
        self.branch_prefixes = [p.lower() for p in branch_prefixes]
        self.labels = {l.lower() for l in labels}
        self.trailers = [t.lower() for t in trailers]

    def login_is_agent(self, login: str | None) -> bool:
        if not login:
            return False
        l = login.lower()
        return l in self.logins or l.endswith("[bot]")

    def message_is_agent(self, message: str | None) -> bool:
        m = (message or "").lower()
        return any(t in m for t in self.trailers)

    def pr_is_automation(self, pr: dict) -> bool:
        """PR from a dependency bot: neither an agent nor a recurring human task."""
        ref = ((pr.get("head") or {}).get("ref") or "").lower()
        return any(ref.startswith(p) for p in self.automation_prefixes)

    def pr_is_agent(self, pr: dict, commits: list[dict]) -> bool:
        if self.login_is_agent((pr.get("user") or {}).get("login")):
            return True
        ref = ((pr.get("head") or {}).get("ref") or "").lower()
        if any(ref.startswith(p) for p in self.branch_prefixes):
            return True
        if {(l.get("name") or "").lower() for l in pr.get("labels") or []} & self.labels:
            return True
        return any(self.message_is_agent((c.get("commit") or {}).get("message")) for c in commits)


# ------------------------------------------------------------- collection


class Evidence:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.counter = 0

    def add(self, signal: str, *, url: str, date: str | None, author: str | None,
            agent_authored: bool, files: list[str], text: str,
            related_rule: str | None, group_key: str) -> dict:
        self.counter += 1
        item = {
            "id": f"github-{self.counter}",
            "signal": signal,
            "source": "github",
            "url": url,
            "date": date,
            "author": author,
            "agent_authored": agent_authored,
            "files": sorted(set(files)),
            "text": text.strip()[:500],
            "related_rule": related_rule,
            "group_key": group_key,
        }
        self.items.append(item)
        return item


class Harvester:
    def __init__(self, repo: str, since: datetime, markers: AgentMarkers, fetch: Fetcher,
                 fix_window_hours: int = 48, min_recurrence: int = 2, min_task_count: int = 3,
                 burst_commits: int = 3, burst_minutes: int = 60, max_prs: int = 200,
                 agents_md: str | None = None):
        self.repo = repo
        self.since = since
        self.markers = markers
        self.fetch = fetch
        self.fix_window = timedelta(hours=fix_window_hours)
        self.min_recurrence = min_recurrence
        self.min_task_count = min_task_count
        self.burst_commits = burst_commits
        self.burst_minutes = burst_minutes
        self.max_prs = max_prs
        self.agents_md = agents_md
        self.errors: list[str] = []
        self.ev = Evidence()
        self.prs: list[dict] = []           # enriched PRs: _commits, _files, _agent, _reviews…
        self.default_branch = "main"

    # -- error-tolerant API access
    def get(self, path: str, params: dict | None = None, default: Any = None,
            paginated: bool = False, stop: Callable[[dict], bool] | None = None) -> Any:
        try:
            if paginated:
                return paginate(self.fetch, path, params, stop=stop)
            return self.fetch(path, params)
        except Exception as exc:  # noqa: BLE001 — we want to go on with what we have
            self.errors.append(f"{path}: {exc}")
            return default

    # -- step 1: PRs of the window
    def load_prs(self) -> None:
        repo_info = self.get(f"repos/{self.repo}", default={}) or {}
        self.default_branch = repo_info.get("default_branch") or "main"
        since_s = self.since.strftime(ISO)
        prs = self.get(
            f"repos/{self.repo}/pulls",
            {"state": "all", "sort": "updated", "direction": "desc"},
            default=[], paginated=True,
            stop=lambda pr: (pr.get("updated_at") or "") < since_s,
        )
        for pr in prs[: self.max_prs]:
            n = pr["number"]
            base = f"repos/{self.repo}"
            pr["_commits"] = self.get(f"{base}/pulls/{n}/commits", default=[], paginated=True) or []
            pr["_files"] = [f["filename"] for f in self.get(f"{base}/pulls/{n}/files", default=[], paginated=True) or []]
            pr["_review_comments"] = self.get(f"{base}/pulls/{n}/comments", default=[], paginated=True) or []
            pr["_issue_comments"] = self.get(f"{base}/issues/{n}/comments", default=[], paginated=True) or []
            pr["_reviews"] = self.get(f"{base}/pulls/{n}/reviews", default=[], paginated=True) or []
            pr["_automated"] = self.markers.pr_is_automation(pr)
            pr["_agent"] = not pr["_automated"] and self.markers.pr_is_agent(pr, pr["_commits"])
            if pr["_agent"]:
                sha = (pr.get("head") or {}).get("sha")
                runs = self.get(f"{base}/commits/{sha}/check-runs", default={}) if sha else {}
                pr["_check_runs"] = (runs or {}).get("check_runs", [])
            else:
                pr["_check_runs"] = []
            self.prs.append(pr)

    def all_comments(self, pr: dict) -> list[dict]:
        out = []
        for c in pr["_review_comments"]:
            out.append({"body": c.get("body") or "", "url": c.get("html_url"), "date": c.get("created_at"),
                        "author": (c.get("user") or {}).get("login"), "files": [c["path"]] if c.get("path") else []})
        for c in pr["_issue_comments"]:
            out.append({"body": c.get("body") or "", "url": c.get("html_url"), "date": c.get("created_at"),
                        "author": (c.get("user") or {}).get("login"), "files": []})
        for r in pr["_reviews"]:
            if r.get("body"):
                out.append({"body": r["body"], "url": r.get("html_url"), "date": r.get("submitted_at"),
                            "author": (r.get("user") or {}).get("login"), "files": []})
        return [c for c in out if (c["date"] or "") >= self.since.strftime(ISO)]

    # -- S1: explicit rules
    def s1_explicit_rules(self) -> None:
        for pr in self.prs:
            for c in self.all_comments(pr):
                m = RULE_PREFIX.match(c["body"])
                if not m:
                    continue
                rule = m.group(1).strip().splitlines()[0]
                self.ev.add("S1", url=c["url"], date=day(c["date"]), author=c["author"],
                            agent_authored=self.markers.login_is_agent(c["author"]),
                            files=c["files"] or pr["_files"], text=rule, related_rule=None,
                            group_key=f"rule:{label(comment_words(rule))}")

    # -- S2: after-the-fact corrections
    def s2_after_the_fact(self) -> None:
        agent_prs = [p for p in self.prs if p["_agent"]]
        if not agent_prs:
            return
        # agent PR closed without merge
        for pr in agent_prs:
            if pr.get("closed_at") and not pr.get("merged_at"):
                self.ev.add("S2", url=pr["html_url"], date=day(pr["closed_at"]),
                            author=(pr.get("user") or {}).get("login"), agent_authored=True,
                            files=pr["_files"], text=f"Agent PR closed without merge: {pr['title']}",
                            related_rule=None, group_key=f"zone:{self.zone(pr['_files'])}")
        # burst of commits after a review
        for pr in agent_prs:
            commit_times = sorted(t for t in (parse_ts(((c.get("commit") or {}).get("committer") or {}).get("date"))
                                              for c in pr["_commits"]) if t)
            for r in pr["_reviews"]:
                start = parse_ts(r.get("submitted_at"))
                if not start:
                    continue
                window = [t for t in commit_times if start < t <= start + timedelta(minutes=self.burst_minutes)]
                if len(window) >= self.burst_commits:
                    self.ev.add("S2", url=r.get("html_url") or pr["html_url"], date=day(r.get("submitted_at")),
                                author=(r.get("user") or {}).get("login"), agent_authored=True,
                                files=pr["_files"],
                                text=f"{len(window)} commits in {self.burst_minutes} min after the review by "
                                     f"{(r.get('user') or {}).get('login')} on: {pr['title']}",
                                related_rule=None, group_key=f"zone:{self.zone(pr['_files'])}")
                    break
        # fix commits and reverts on the default branch
        merged = [p for p in agent_prs if p.get("merged_at")]
        if not merged:
            return
        commits = self.get(f"repos/{self.repo}/commits",
                           {"sha": self.default_branch, "since": self.since.strftime(ISO)},
                           default=[], paginated=True) or []
        merged_shas = {p.get("merge_commit_sha"): p for p in merged if p.get("merge_commit_sha")}
        by_number = {p["number"]: p for p in self.prs}
        for c in commits:
            msg = (c.get("commit") or {}).get("message") or ""
            author = (c.get("author") or {}).get("login") or ((c.get("commit") or {}).get("author") or {}).get("name")
            when = parse_ts(((c.get("commit") or {}).get("committer") or {}).get("date"))
            if not when or msg.startswith("Merge pull request") or c.get("sha") in merged_shas:
                continue
            if self.markers.login_is_agent(author) or self.markers.message_is_agent(msg):
                continue
            # revert ?
            if msg.lower().startswith("revert"):
                target = None
                for p in merged:
                    if f"#{p['number']}" in msg or (p.get("merge_commit_sha") and p["merge_commit_sha"][:7] in msg):
                        target = p
                        break
                if target:
                    self.ev.add("S2", url=c.get("html_url"), date=day(when.strftime(ISO)), author=author,
                                agent_authored=False, files=target["_files"],
                                text=f"Revert of an agent PR: {target['title']}", related_rule=None,
                                group_key=f"zone:{self.zone(target['_files'])}")
                    continue
            # squash-merge of another PR of the window: a correction only if it is a fix/revert
            # or if it cites an agent PR; a Renovate PR that touches build.gradle is not one
            ref_pr = None
            m_ref = re.search(r"\(#(\d+)\)\s*$", msg.splitlines()[0])
            if m_ref:
                ref_pr = by_number.get(int(m_ref.group(1)))
            if ref_pr is not None:
                title = (ref_pr.get("title") or "").lower()
                cites_agent = any(f"#{p['number']}" in (ref_pr.get("title") or "") + (ref_pr.get("body") or "")
                                  for p in merged)
                if ref_pr.get("_automated") or not (re.match(r"^(fix|hotfix|revert)\b", title) or cites_agent):
                    continue
            # fix within the window after merge, on the same files
            candidates = [p for p in merged
                          if parse_ts(p["merged_at"]) and parse_ts(p["merged_at"]) < when <= parse_ts(p["merged_at"]) + self.fix_window]
            if not candidates:
                continue
            detail = self.get(f"repos/{self.repo}/commits/{c['sha']}", default={}) or {}
            touched = {f["filename"] for f in detail.get("files", [])}
            for p in candidates:
                overlap = touched & set(p["_files"])
                if overlap:
                    self.ev.add("S2", url=c.get("html_url"), date=day(when.strftime(ISO)), author=author,
                                agent_authored=False, files=sorted(overlap),
                                text=f"Fix {msg.splitlines()[0][:120]!r} on files of agent PR "
                                     f"#{p['number']} ({p['title']}) {self.hours_after(p, when)} h after its merge",
                                related_rule=None, group_key=f"zone:{self.zone(sorted(overlap))}")

    @staticmethod
    def hours_after(pr: dict, when: datetime) -> int:
        return int((when - parse_ts(pr["merged_at"])).total_seconds() // 3600)

    @staticmethod
    def zone(files: list[str]) -> str:
        """Zone key: the deepest folder the files share."""
        if not files:
            return "?"
        parts = [f.split("/")[:-1] for f in files]
        common: list[str] = []
        for level in zip(*parts):
            if len(set(level)) == 1:
                common.append(level[0])
            else:
                break
        return "/".join(common) or "."

    # -- S3: recurring corrections
    def s3_recurring_comments(self) -> None:
        per_author: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
        for pr in self.prs:
            for c in self.all_comments(pr):
                if RULE_PREFIX.match(c["body"]) or self.markers.login_is_agent(c["author"]):
                    continue
                if c["author"] and c["author"] == (pr.get("user") or {}).get("login"):
                    continue  # the author's note on their own PR, not a correction
                per_author[c["author"] or "?"].append((pr, c))
        for author, hits in per_author.items():
            sets = [comment_words(c["body"]) for _, c in hits]
            for grp in cluster(sets, COMMENT_THRESHOLD):
                members = [hits[i] for i in grp["idx"]]
                if len({pr["number"] for pr, _ in members}) < self.min_recurrence or len(grp["common"]) < 3:
                    continue
                for pr, c in members:
                    self.ev.add("S3", url=c["url"], date=day(c["date"]), author=author, agent_authored=False,
                                files=c["files"] or pr["_files"], text=c["body"], related_rule=None,
                                group_key=f"reviewer:{author}:{label(grp['common'])}")

    # -- S4: ignored guardrails
    def s4_ignored_checks(self) -> None:
        by_check: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
        for pr in self.prs:
            if not pr["_agent"]:
                continue
            for run in pr["_check_runs"]:
                if run.get("conclusion") in ("failure", "timed_out", "action_required"):
                    by_check[run.get("name") or "?"].append((pr, run))
        for name, hits in by_check.items():
            if len({pr["number"] for pr, _ in hits}) < self.min_recurrence:
                continue
            for pr, run in hits:
                self.ev.add("S4", url=run.get("html_url") or pr["html_url"], date=day(run.get("completed_at")),
                            author=(pr.get("user") or {}).get("login"), agent_authored=True, files=pr["_files"],
                            text=f"Check '{name}' failing ({run.get('conclusion')}) on agent PR #{pr['number']}",
                            related_rule=None, group_key=f"check:{name}")

    # -- S5: orphan rules
    def s5_orphan_rules(self) -> None:
        if not self.agents_md:
            return
        try:
            with open(self.agents_md, encoding="utf-8") as fh:
                rules = parse_rules(fh.read())
        except OSError as exc:
            self.errors.append(f"{self.agents_md}: {exc}")
            return
        others = [e for e in self.ev.items if e["signal"] in ("S1", "S2", "S3", "S4")]
        for rule in rules:
            kw = keywords(rule)
            paths = [p for p in re.findall(r"`([^`]+)`", rule) if "/" in p or "." in p]
            linked = []
            for e in others:
                if len(kw & keywords(e["text"])) >= 2 or any(
                        f.startswith(p.rstrip("/")) for f in e["files"] for p in paths):
                    linked.append(e)
                    e["related_rule"] = e["related_rule"] or rule[:200]
            if not linked:
                self.ev.add("S5", url=self.agents_md, date=None, author=None, agent_authored=False,
                            files=paths, text=rule, related_rule=rule[:200],
                            group_key=f"orphan:{' '.join(sorted(kw))[:60]}")

    # -- S6: recurring tasks
    def s6_recurring_tasks(self) -> None:
        emitted: set[tuple[int, str]] = set()

        def emit(pr: dict, kind: str, key: str) -> None:
            if (pr["number"], kind) in emitted:
                return
            emitted.add((pr["number"], kind))
            self.ev.add("S6", url=pr["html_url"], date=day(pr.get("created_at")),
                        author=(pr.get("user") or {}).get("login"), agent_authored=pr["_agent"],
                        files=pr["_files"], text=pr.get("title") or "", related_rule=None,
                        group_key=f"task:{kind}:{key}")

        candidates = [pr for pr in self.prs if not pr.get("_automated")]
        sets = [title_words(pr.get("title") or "") for pr in candidates]
        grouped: set[int] = set()
        for grp in cluster(sets, TITLE_THRESHOLD):
            if len(grp["idx"]) >= self.min_task_count and len(grp["common"]) >= 2:
                for i in grp["idx"]:
                    emit(candidates[i], "title", label(grp["common"]))
                    grouped.add(candidates[i]["number"])
        by_label: dict[str, list[dict]] = defaultdict(list)
        for pr in candidates:
            if pr["number"] in grouped:
                continue
            for lab in pr.get("labels") or []:
                name = (lab.get("name") or "").lower()
                if name:
                    by_label[name].append(pr)
        for name, prs in by_label.items():
            if len(prs) >= self.min_task_count:
                for pr in prs:
                    emit(pr, "label", name)

    # -- S7: undiscoverable information asked for
    def s7_repeated_questions(self) -> None:
        hits: list[tuple[dict, str]] = []
        for pr in self.prs:
            if not pr["_agent"]:
                continue
            for sent in sentences(pr.get("body") or ""):
                if QUESTION_PATTERNS.search(sent) or (sent.endswith("?") and len(sent) > 20):
                    hits.append((pr, sent))
        sets = [keywords(sent) for _, sent in hits]
        for grp in cluster(sets, QUESTION_THRESHOLD):
            members = [hits[i] for i in grp["idx"]]
            if len({pr["number"] for pr, _ in members}) < self.min_recurrence or not grp["common"]:
                continue
            for pr, sent in members:
                self.ev.add("S7", url=pr["html_url"], date=day(pr.get("created_at")),
                            author=(pr.get("user") or {}).get("login"), agent_authored=True,
                            files=pr["_files"], text=sent, related_rule=None,
                            group_key=f"question:{label(grp['common'])}")

    # -- orchestration
    def run(self) -> dict:
        self.load_prs()
        self.s1_explicit_rules()
        self.s2_after_the_fact()
        self.s3_recurring_comments()
        self.s4_ignored_checks()
        self.s5_orphan_rules()   # after S1–S4: it relies on them
        self.s6_recurring_tasks()
        self.s7_repeated_questions()
        counts = defaultdict(int)
        for e in self.ev.items:
            counts[e["signal"]] += 1
        return {
            "source": "github",
            "repo": self.repo,
            "since": self.since.strftime("%Y-%m-%d"),
            "default_branch": self.default_branch,
            "prs_scanned": len(self.prs),
            "agent_prs": sum(1 for p in self.prs if p["_agent"]),
            "counts": dict(sorted(counts.items())),
            "errors": self.errors,
            "evidence": self.ev.items,
        }


# Sections that hold no rule, in French and in English.
NON_RULE_HEADINGS = re.compile(r"^#{1,6}\s+(maintenance|maintaining|t[âa]ches|tasks|delegated tasks|ce que fait|what this|"
                               r"installation|commandes|commands|processus|working process|workflow|"
                               r"available ci/cd|ci/cd (?:disponibles?|available))", re.I)
# Sections that say they hold rules. When a file has one, only their bullets are rules.
RULE_HEADINGS = re.compile(r"^#{1,6}\s+(?:.*\b)?(rules?|r[èe]gles?|forbidden|interdit(?:e?s)?)\b", re.I)
# A bullet that names its guardrail is a rule wherever it sits. Same wording as `facts.GUARDED_RE`,
# which cannot be imported here: `facts` imports this module.
ENFORCED_RE = re.compile(r"v[ée]rifi[ée]e?\s+par\s*:|guarded\s+by\s*:|enforced\s+by\s*:", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s")
BULLET_RE = re.compile(r"^\s*[-*]\s+")


def has_rule_headings(agents_md: str) -> bool:
    """True when the file has a section that announces rules ("Rules", "Forbidden", "Règles",
    "Interdits"). Without one, what `iter_rules` returns are lines, not known rules."""
    return any(RULE_HEADINGS.match(line) and not NON_RULE_HEADINGS.match(line)
               for line in agents_md.splitlines())


def iter_rules(agents_md: str) -> list[tuple[int, str]]:
    """The rules of an AGENTS.md with their line number (1 = first line), continuation lines joined.
    A bullet that says "Enforced by:" is a rule in any section. For the others: when the file has
    "Rules" or "Forbidden" sections, only the bullets under them (subsections included) count;
    otherwise every bullet outside the maintenance, tasks, commands, CI/CD and working-process
    sections does, because real files keep their rules under "Pitfalls", "Database", etc. — the caller
    can tell the two cases apart with `has_rule_headings`."""
    strict = has_rule_headings(agents_md)
    rules: list[tuple[int, str]] = []
    non_rule = False                 # the current section is one of NON_RULE_HEADINGS
    rule_level: int | None = None    # the level of the rule heading we are under, if any
    current: list[str] | None = None
    keep = False
    start = 0

    def flush() -> None:
        nonlocal current
        if current:
            text = " ".join(part.strip() for part in current)
            if keep or ENFORCED_RE.search(text):
                rules.append((start, text))
        current = None

    for number, line in enumerate(agents_md.splitlines(), 1):
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            if rule_level is not None and level <= rule_level:
                rule_level = None
            non_rule = bool(NON_RULE_HEADINGS.match(line))
            if rule_level is None and not non_rule and RULE_HEADINGS.match(line):
                rule_level = level
            continue
        if BULLET_RE.match(line):
            flush()
            current = [BULLET_RE.sub("", line)]
            start = number
            keep = not non_rule and (rule_level is not None or not strict)
        elif current is not None and line.startswith("  ") and line.strip():
            current.append(line)
        else:
            flush()
    flush()
    return rules


def parse_rules(agents_md: str) -> list[str]:
    """The text of the rules, without their line: see `iter_rules`."""
    return [text for _, text in iter_rules(agents_md)]


# --------------------------------------------------------------------- CLI


def read_marker(agents_md: str | None) -> str | None:
    """The date of the last harvest. A marker set by harness-init (`ref=init`)
    is not a harvest: it is ignored, the default window (30 days) applies."""
    if not agents_md:
        return None
    try:
        with open(agents_md, encoding="utf-8") as fh:
            m = re.search(r"<!--\s*harvest:\s*last=(\d{4}-\d{2}-\d{2})(?:\s+ref=(\S+))?", fh.read())
        if not m or (m.group(2) or "").rstrip("->").strip() == "init":
            return None
        return m.group(1)
    except OSError:
        return None


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", required=True, help="owner/repo")
    p.add_argument("--since", help="YYYY-MM-DD; default: harvest marker of --agents-md, otherwise 30 days")
    p.add_argument("--agents-md", help="path of the AGENTS.md (S5 and window marker)")
    p.add_argument("--agent-login", action="append", default=[], help="login considered an agent (repeatable)")
    p.add_argument("--agent-branch-prefix", action="append", default=[], help="agent branch prefix (repeatable)")
    p.add_argument("--agent-label", action="append", default=[], help="label marking an agent PR (repeatable)")
    p.add_argument("--agent-trailer", action="append", default=[],
                   help="commit message fragment marking an agent, e.g. 'Co-Authored-By: Claude' (repeatable)")
    p.add_argument("--automation-branch-prefix", action="append", default=[],
                   help="branch prefix of a dependency bot, excluded from S6 and from S2 corrections "
                        "(default: renovate/, dependabot/)")
    p.add_argument("--fix-window-hours", type=int, default=48)
    p.add_argument("--min-recurrence", type=int, default=2, help="threshold for S3, S4, S7")
    p.add_argument("--min-task-count", type=int, default=3, help="threshold for S6")
    p.add_argument("--burst-commits", type=int, default=3)
    p.add_argument("--burst-minutes", type=int, default=60)
    p.add_argument("--max-prs", type=int, default=200)
    p.add_argument("--summary", action="store_true", help="prints the counters on stderr")
    return p


def main(argv: list[str] | None = None, fetch: Fetcher = gh_api,
         args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    since_s = args.since or read_marker(args.agents_md)
    if since_s:
        since = datetime.strptime(since_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        print("no --since and no earlier harvest marker (a ref=init marker does not count): 30-day window", file=sys.stderr)
    markers = AgentMarkers(
        logins=args.agent_login or ["claude", "github-actions[bot]"],
        branch_prefixes=args.agent_branch_prefix or ["claude/"],
        labels=args.agent_label,
        trailers=args.agent_trailer or ["co-authored-by: claude"],
        automation_prefixes=args.automation_branch_prefix or ["renovate/", "dependabot/"],
    )
    h = Harvester(args.repo, since, markers, fetch,
                  fix_window_hours=args.fix_window_hours, min_recurrence=args.min_recurrence,
                  min_task_count=args.min_task_count, burst_commits=args.burst_commits,
                  burst_minutes=args.burst_minutes, max_prs=args.max_prs, agents_md=args.agents_md)
    result = h.run()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if args.summary or result["errors"]:
        print(f"PRs: {result['prs_scanned']} (agent: {result['agent_prs']}); evidence: {result['counts']}",
              file=sys.stderr)
    for err in result["errors"]:
        print(f"error: {err}", file=sys.stderr)
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
