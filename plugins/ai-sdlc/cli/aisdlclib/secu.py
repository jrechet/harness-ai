"""The gates of `/secu`: what a program can say about the security of a change.

Four gates, each `ok`, `failed`, or `unmeasured`:
- **secrets**: no added line carries a recognisable secret, no key file is added;
- **muted**: the diff silences no scanner (`# nosec`, `nosemgrep`, exceptions file);
- **scanner**: the SARIF reports of the team's scanners have no result on an added line;
- **surface**: what the change touches that is sensitive, for someone to review: sensitive zones,
  dependencies, risky calls. This gate never passes on its own when it finds something.

This module does not replace a scanner: its secret patterns are few and sure of themselves, and it does
not read the code. Without a scanner report, the "scanner" gate stays unmeasured: `/secu` neither blocks
nor clears on its own. The content of the lines is never copied into its output: a path, a line, a
kind, and names (file, rule, tool) reduced to characters that do nothing in a rendering."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
from typing import Any

from . import qa, size
from .context import Refused, _git, resolve_base

OK, FAIL, UNKNOWN = qa.OK, qa.FAIL, qa.UNKNOWN
MAX_LINE = 20_000       # beyond that, the line is read up to there and flagged
MAX_SHOWN = 8
MAX_RESULTS = 100_000
_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
MAX_COMMITS = 100      # the branch history is read commit by commit up to there
SCAN_BUDGET = 60       # seconds to read the lines: beyond that, reading stops and says so

# Shapes that nothing but a secret takes. No nested quantifiers: the text comes from a third party.
_SECRETS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("AWS access key", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("GitHub token", re.compile(r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("GitLab token", re.compile(r"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("API key (sk-…)", re.compile(r"(?<![A-Za-z0-9_-])sk-(?:ant-|proj-|live_)?[A-Za-z0-9_-]{24,}")),
    ("Stripe key", re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
    ("Google key", re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")),
    ("npm or PyPI token", re.compile(r"(?<![A-Za-z0-9_])(?:npm_[A-Za-z0-9]{36}|pypi-AgEI[A-Za-z0-9_-]{40,})")),
    ("JWT", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")),
    ("credentials in a URL", re.compile(r"[a-z][a-z0-9+.-]{1,20}://[^\s/:@'\"]{1,80}:([^\s/@'\"]{6,80})@[\w.-]")),
]
# name = "literal value": the name says it is a secret, the value is neither an example nor a variable
_ASSIGN = re.compile(r"(?i)(?<![a-z0-9])(?:[a-z0-9_.-]{0,30})(?:passw(?:or)?d|pwd|passphrase|secret|token|api[_-]?key|apikey|"
                     r"private[_-]?key|access[_-]?key|auth[_-]?key|credential)[a-z0-9_-]{0,20}[\"']?\s{0,3}(?:=|:|=>|:=)\s{0,3}[\"']([^\"'\s]{12,200})[\"']")
# A value that is not one: an example, or a variable that fills the whole value. Judged on the whole
# value: a real password may contain "$" or "%". French placeholders (exemple, votre, motdepasse) stay recognised.
_PLACEHOLDER = re.compile(r"(?i)(?:x+|\*+|\.+|•+|0+|changeme.*|change[_-]me.*|example.*|exemple.*|dummy.*|fake.*|test.*|todo.*|"
                          r"your[_-].*|votre[_-].*|placeholder.*|redacted.*|secret|password|motdepasse|none|null|undefined|"
                          r"\$\{[^}]*\}|\$\w+|\{\{[^}]*\}\}|\{[\w.]*\}|<[^>]*>|%\([^)]*\)s|%\w+%)")
_WORDS = re.compile(r"[a-z_]+")   # lower-case letters and underscores: an identifier, not a value
_KEY_FILE = re.compile(r"(?:^|/)(?:\.env(?:\.(?!example$|sample$|template$|dist$)[\w.-]+)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
                       r"[^/]+\.(?:pem|p12|pfx|jks|keystore|key)|credentials(?:\.json)?|\.npmrc|\.pypirc|\.netrc|"
                       r"service[_-]?account[^/]*\.json)$", re.IGNORECASE)
_MUTED = re.compile(r"(?:#|//)\s{0,3}nosec\b|noqa:[^#\n]{0,60}\bS\d|ruff:\s{0,3}noqa|\bnosemgrep\b|semgrep:\s{0,3}ignore|"
                    r"nolint:\s{0,3}gosec|NOLINT\(gosec|\bNOSONAR\b|SuppressFBWarnings|kics-scan ignore|trufflehog:ignore|"
                    r"gitleaks:allow|\bcodeql\s*\[|lgtm\s*\[|snyk:?\s*ignore|trivy:ignore|checkov:skip|tfsec:ignore|"
                    r"bandit:\s*skip|eslint-disable[\w-]{0,30}\s{1,3}security/|@SuppressWarnings\(\s*\"(?:java:S|squid:S|findsecbugs)|"
                    r"detect-secrets:\s*allowlist|pragma:\s*allowlist\s+secret|brakeman:\s*ignore", re.IGNORECASE)
_SCANNER_CONFIG = re.compile(r"(?:^|/)(?:\.gitleaksignore|\.gitleaks\.toml|gitleaks\.toml|\.semgrepignore|\.semgrep(?:\.ya?ml|/.*)|"
                             r"\.trivyignore(?:\.ya?ml)?|trivy\.ya?ml|\.snyk|\.bandit|bandit\.ya?ml|\.secrets\.baseline|"
                             r"\.checkov\.ya?ml|\.tfsec/.*|sonar-project\.properties|\.github/codeql/.*|"
                             r"\.github/dependabot\.ya?ml|renovate\.json5?|\.trufflehog[\w.-]*|\.pre-commit-config\.yaml)$")
_MANIFEST = re.compile(r"(?:^|/)(?:package\.json|package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|"
                       r"requirements[\w.-]*\.txt|constraints[\w.-]*\.txt|pyproject\.toml|poetry\.lock|uv\.lock|Pipfile(?:\.lock)?|"
                       r"setup\.(?:py|cfg)|go\.(?:mod|sum)|Cargo\.(?:toml|lock)|pom\.xml|build\.gradle(?:\.kts)?|gradle\.lockfile|"
                       r"libs\.versions\.toml|Gemfile(?:\.lock)?|composer\.(?:json|lock)|[^/]+\.csproj|packages\.lock\.json|"
                       r"Package\.(?:swift|resolved)|pubspec\.(?:yaml|lock)|mix\.(?:exs|lock)|\.gitmodules)$")
# Calls a reviewer always looks at. A signal, not a verdict: most are legitimate.
_HOT = [
    ("code evaluated at run time", re.compile(r"(?<![\w.])(?:eval|exec)\s?\(|new Function\(|\bcompile\(.{0,80}['\"]exec['\"]")),
    ("command passed to a shell", re.compile(r"shell\s?=\s?True|os\.system\(|os\.popen\(|child_process|Runtime\.getRuntime\(\)\.exec|"
                                              r"(?<![\w.])(?:execSync|spawnSync|exec)\(\s?[`'\"]|subprocess\.\w+\(\s?f?[\"']")),
    ("deserialisation", re.compile(r"pickle\.loads?\(|yaml\.load\((?!.{0,80}SafeLoader)|\bmarshal\.loads?\(|ObjectInputStream|"
                                   r"unserialize\(|Marshal\.load\(")),
    ("TLS verification turned off", re.compile(r"verify\s?=\s?False|InsecureSkipVerify\s?:\s?true|rejectUnauthorized\s?:\s?false|"
                                           r"NODE_TLS_REJECT_UNAUTHORIZED|CURLOPT_SSL_VERIFYPEER|--insecure\b|curl\s+-k\b|"
                                           r"check_hostname\s?=\s?False|_create_unverified_context")),
    ("HTML injected without escaping", re.compile(r"\.innerHTML\s?=|dangerouslySetInnerHTML|v-html=|\|\s?safe\b|mark_safe\(|"
                                                 r"document\.write\(|bypassSecurityTrust\w+\(|\{@html\b")),
    ("SQL query built by concatenation", re.compile(
        r"(?i)(?:execute|query|raw|prepare)\w{0,30}\(\s?(?:f[\"']|[\"'][^\"']{0,200}[\"']\s?(?:%|\+|\.format\())|"
        r"[\"'](?:select|insert|update|delete)\b[^\"']{0,200}[\"']\s?(?:\+|%\s|\.format\()|\$\{[^}]{0,80}\}[^`]{0,200}\b(?:where|values)\b")),
    ("weak hashing or encryption", re.compile(r"(?<![\w.])(?:md5|sha1|MD5|SHA1)\s?\(|hashlib\.(?:md5|sha1)\(|"
                                                 r"MessageDigest\.getInstance\(\s?\"(?:MD5|SHA-?1)\"|createHash\(\s?['\"](?:md5|sha1)['\"]|"
                                                 r"\bDES(?:ede)?\.new\(|['\"/](?:DES|RC4|3DES)['\"/]|MODE_ECB|/ECB/|"
                                                 r"Math\.random\(\).{0,60}(?:token|secret|password|key)")),
    ("open permissions", re.compile(r"chmod\s+(?:-R\s+)?(?:777|666|a\+[rwx]+)|0o?777\b|Access-Control-Allow-Origin['\"]?\s?[:=,]\s?['\"]\*|"
                                  r"cors\(\s?\)|@PermitAll|permitAll\(\)|AllowAny\b|csrf_exempt|csrf\(\)\.disable|"
                                  r"--dangerously-skip-permissions|--privileged\b|privileged:\s?true")),
    ("script downloaded then run", re.compile(r"(?:curl|wget)\b[^|;&]{0,200}\|\s?(?:sudo\s+)?(?:ba|z|da)?sh\b")),
    ("check bypassed", re.compile(r"--no-verify\b|--no-gpg-sign\b|--force-with-lease\b|push\s+(?:-f|--force)\b|"
                                           r"continue-on-error:\s?true|\|\|\s?true\s*$|pull_request_target")),
]
_PROSE = (".md", ".mdx", ".txt", ".rst", ".adoc")   # prose that talks about a call is not a call
_LEVELS = ("error", "warning", "note", "none")


_NAME = re.compile(r"[^A-Za-z0-9._/-]")


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _where(path: str, line: int | None = None) -> str:
    """A path ready to be shown. It comes from the examined repository: only letters, digits,
    `. _ / -` and the space remain, so that it carries no link, image, mention or formatted instruction. A
    secret-shaped file name is not shown at all."""
    if any(pattern.search(path) for _, pattern in _SECRETS):
        clean = "(file name hidden)"
    else:
        clean = "".join(ch if ch.isalnum() or ch in "._/- " else "?" for ch in path)[:120]
    return f"{clean}:{line}" if line else clean


def _name(text: Any, limit: int = 40) -> str:
    """A rule or tool name read in a report: reduced to what an identifier contains."""
    return _NAME.sub("?", text)[:limit] if isinstance(text, str) and text else "unnamed"


def _shown(items: list[str]) -> str:
    extra = len(items) - MAX_SHOWN
    return "; ".join(items[:MAX_SHOWN]) + (f"; and {extra} more" if extra > 0 else "")


def parse_patch(patch: bytes) -> list[tuple[str, int, str]]:
    """The added lines of a unified diff: (path, number, text). Split on the newline only (another
    separator does not hide the rest of a line), and the lines of a hunk are counted from its header:
    an added line that imitates a header stays an added line."""
    out: list[tuple[str, int, str]] = []
    path, minus, plus, number = "", 0, 0, 0
    for raw in patch.split(b"\n"):
        line = raw.decode("utf-8", "replace")
        if minus or plus:
            if plus and line.startswith("+"):
                out.append((path, number, line[1:]))
                number, plus = number + 1, plus - 1
                continue
            if minus and line.startswith("-"):
                minus -= 1
                continue
            if line.startswith("\\"):
                continue
            minus = plus = 0
        match = _HUNK.match(line)
        if match:
            minus = int(match[1]) if match[1] is not None else 1
            number, plus = int(match[2]), int(match[3]) if match[3] is not None else 1
        elif line.startswith("+++ "):
            path = line[4:].rstrip("\t")
            path = path[2:] if path.startswith("b/") else path
    return out


def _diff_args() -> tuple[str, ...]:
    # neither diff driver nor conversion declared by the examined repository: they run code and rewrite what is read
    return ("-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--text", "--no-renames")


def added(repo: str, base: str) -> tuple[dict[str, list[tuple[int, str]]], list[str], list[str]]:
    """Per file, the lines the change adds (number, text); then the files that do not read as text, and
    every path of the change."""
    commit = resolve_base(repo, base)
    paths = [s["path"] for s in size.diff_stats(repo, base)]
    code, patch = _git(repo, "-c", "core.quotePath=false", "diff", *_diff_args(), f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"cannot diff {base} and HEAD")
    lines: dict[str, list[tuple[int, str]]] = {}
    for path, number, text in parse_patch(patch):
        lines.setdefault(path, []).append((number, text))
    opaque = sorted(path for path, rows in lines.items() if any("\0" in text for _, text in rows))
    return lines, opaque, paths


def history(repo: str, base: str, skip: Any = None) -> tuple[list[tuple[str, str]], int]:
    """What each commit of the branch adds, message included: (where, text). A secret added then removed
    is no longer in the diff, it is still in the history. Also returns the number of unread commits."""
    commit = resolve_base(repo, base)
    code, out = _git(repo, "rev-list", "--no-merges", f"{commit}..HEAD")
    if code != 0:
        raise Refused(f"unreadable history between {base} and HEAD")
    commits = out.decode("ascii", "replace").split()
    found: list[tuple[str, str]] = []
    for sha in commits[:MAX_COMMITS]:
        code, shown = _git(repo, "-c", "core.quotePath=false", "show", *_diff_args(), "--format=%B%x00", sha)
        if code != 0:
            raise Refused(f"commit {sha[:7]} unreadable")
        message, _, patch = shown.partition(b"\0")
        found += [(f"message of commit {sha[:7]}", line) for line in message.decode("utf-8", "replace").split("\n")]
        found += [(f"commit {sha[:7]}, {_where(path, number)}", text) for path, number, text in parse_patch(patch)
                  if not (skip and skip(path))]
    return found, max(0, len(commits) - MAX_COMMITS)


def _secret_kinds(text: str) -> list[str]:
    kinds = []
    for kind, pattern in _SECRETS:
        match = pattern.search(text)
        if not match:
            continue
        if match.groups() and _placeholder(match[1]):      # the only pattern with a group is the URL: its password may be a variable
            continue
        if kind.startswith("API key") and sum(ch.isdigit() for ch in match[0]) < 3:
            continue                                        # "sk-fading-circle-v2" is a CSS class, not a random key
        kinds.append(kind)
    for match in _ASSIGN.finditer(text):
        if not _placeholder(match[1]):
            kinds.append("hard-coded value under a secret name")
            break
    return kinds


def _placeholder(value: str) -> bool:
    return bool(_PLACEHOLDER.fullmatch(value) or _WORDS.fullmatch(value))


class _Clock:
    """A reading budget: past the deadline, stop and say so, rather than run forever."""

    def __init__(self) -> None:
        self.deadline, self.late = time.monotonic() + SCAN_BUDGET, False

    def over(self) -> bool:
        self.late = self.late or time.monotonic() > self.deadline
        return self.late


def gate_secrets(lines: dict[str, list[tuple[int, str]]], added_files: set[str], opaque: list[str],
                 past: list[tuple[str, str]], unread_commits: int, clock: _Clock) -> dict[str, Any]:
    title = "No secret in what the branch adds"
    hits, seen, long_lines = [], set(), 0
    for path in sorted(added_files):
        if _KEY_FILE.search(path):
            hits.append(f"{_where(path)} (key or credentials file added)")
        elif any(pattern.search(path) for _, pattern in _SECRETS):
            hits.append("a secret-shaped file name (hidden)")
    for path, rows in sorted(lines.items()):
        for number, text in rows:
            if clock.over():
                break
            long_lines += len(text) > MAX_LINE
            for kind in _secret_kinds(text[:MAX_LINE]):
                hits.append(f"{_where(path, number)} ({kind})")
                seen.add((text, kind))
    for place, text in past:
        if clock.over():
            break
        for kind in _secret_kinds(text[:MAX_LINE]):
            if (text, kind) not in seen:       # already cited at its place in the diff
                seen.add((text, kind))
                hits.append(f"{place} ({kind}, in the branch history)")
    if hits:
        return _gate("secrets", title, FAIL, _shown(hits),
                     "A pushed secret is an exposed secret, even if removed later: have its owner revoke it, "
                     "then take it out of the code. The value is not copied here; do not copy it either.")
    count = sum(len(r) for r in lines.values())
    partial = ([f"not read as text: {_shown([_where(p) for p in opaque])}"] if opaque else []) + \
              ([f"{unread_commits} older commit(s) of the branch not read"] if unread_commits else []) + \
              ([f"reading stopped after {SCAN_BUDGET} s"] if clock.late else [])
    if partial:
        return _gate("secrets", title, UNKNOWN, f"{count} added line(s); " + "; ".join(partial),
                     "Have what was not read checked by the team's secret detector.")
    note = f"; {long_lines} line(s) longer than {MAX_LINE} characters read in part" if long_lines else ""
    return _gate("secrets", title, OK, f"{count} added line(s) and the branch history read, known shapes only{note}")


def gate_muted(lines: dict[str, list[tuple[int, str]]], paths: list[str], clock: _Clock) -> dict[str, Any]:
    title = "No scanner is silenced"
    hits = [f"{_where(path, number)}" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
            for number, text in rows if not clock.over() and _MUTED.search(text[:MAX_LINE])]
    config = [_where(p) for p in paths if _SCANNER_CONFIG.search(p)]
    if hits:
        return _gate("muted", title, FAIL, "exception written in the code, or a line that names one: " + _shown(hits),
                     "Fix what the scanner reports. If it is a false positive, a human says so in the PR: "
                     "the gate does not decide it. A comment that asks for an exception is reported.")
    if config or clock.late:
        said = (["scanner configuration changed: " + _shown(config)] if config else []) + \
               ([f"reading stopped after {SCAN_BUDGET} s"] if clock.late else [])
        return _gate("muted", title, UNKNOWN, "; ".join(said),
                     "Say in the PR what this change does to what the scanner looks at.")
    return _gate("muted", title, OK, "no exception added")


def _uri_path(uri: str, root: str) -> str:
    path = uri[7:] if uri.startswith("file://") else uri
    path = urllib.parse.unquote(path.split("?")[0]).replace("\\", "/")
    if path.startswith(root + "/"):
        path = path[len(root) + 1:]
    while path.startswith("./"):
        path = path[2:]
    return path


def _resolve(path: str, tracked: set[str]) -> str | None:
    """The repository file this path designates: itself, or its tail (a report written elsewhere gives
    absolute paths from another machine). None if nothing matches."""
    parts = [p for p in path.split("/") if p]
    for start in range(len(parts)):
        candidate = "/".join(parts[start:])
        if candidate in tracked:
            return candidate
    return None


def _places(item: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    """Each location of a result: (uri, first line, last line)."""
    out = []
    for place in item.get("locations") if isinstance(item.get("locations"), list) else []:
        physical = place.get("physicalLocation") if isinstance(place, dict) else None
        artifact = physical.get("artifactLocation") if isinstance(physical, dict) else None
        region = physical.get("region") if isinstance(physical, dict) else None
        uri = artifact.get("uri") if isinstance(artifact, dict) else None
        start = region.get("startLine") if isinstance(region, dict) else None
        end = region.get("endLine") if isinstance(region, dict) else None
        start = start if type(start) is int and start > 0 else None
        end = end if type(end) is int and end > 0 else start
        if start is not None and end < start:
            start, end = end, start
        out.append((uri if isinstance(uri, str) and uri else None, start, end))
    return out


def read_sarif(path: str) -> tuple[list[str], list[dict[str, Any]], int]:
    """The tools, the results and the number of results dismissed by the tool, from a SARIF 2.1 report.
    A run counts only if it names its tool and carries a list of results."""
    try:
        if os.path.getsize(path) > qa.MAX_REPORT:
            raise Refused(f"{path}: report larger than {qa.MAX_REPORT} bytes")
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        raise Refused(f"{path}: unreadable report ({type(exc).__name__})") from exc
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise Refused(f"{path}: not a SARIF report (no runs list)")
    tools, results, hushed = [], [], 0
    for run in runs:
        if not isinstance(run, dict):
            raise Refused(f"{path}: malformed SARIF run")
        tool = run.get("tool")
        driver = tool.get("driver") if isinstance(tool, dict) else None
        driver = driver if isinstance(driver, dict) else {}
        found = run.get("results")
        if found is None or not isinstance(driver.get("name"), str) or not driver["name"].strip():
            continue      # without a named tool or without results, nothing says a scanner ran
        if not isinstance(found, list) or len(found) > MAX_RESULTS:
            raise Refused(f"{path}: results is a list of at most {MAX_RESULTS} results")
        tools.append(_name(driver["name"]))
        levels = {rule["id"]: rule["defaultConfiguration"].get("level")
                  for rule in (driver.get("rules") if isinstance(driver.get("rules"), list) else [])
                  if isinstance(rule, dict) and isinstance(rule.get("id"), str) and isinstance(rule.get("defaultConfiguration"), dict)}
        for item in found:
            if not isinstance(item, dict):
                raise Refused(f"{path}: malformed SARIF result")
            if isinstance(item.get("suppressions"), list) and item["suppressions"]:
                hushed += 1   # dismissed by the tool: counted and said, its configuration answers for it
                continue
            rule = item.get("ruleId") if isinstance(item.get("ruleId"), str) else None
            level = item.get("level") if isinstance(item.get("level"), str) else levels.get(rule)
            level = level.lower() if isinstance(level, str) else "warning"
            if item.get("kind") in ("pass", "notApplicable", "informational", "open"):
                level = "none"
            results.append({"rule": _name(rule, 60), "level": level if level in _LEVELS else "warning", "places": _places(item)})
    return tools, results, hushed


def gate_scanner(repo: str, lines: dict[str, list[tuple[int, str]]], reports: list[str]) -> dict[str, Any]:
    title = "The team's scanners report nothing on the added lines"
    if not reports:
        return _gate("scanner", title, UNKNOWN, "no scanner report given",
                     "Run the scanners the repository declares (AGENTS.md, CI) with SARIF output, then run again with "
                     "--report <file>. Without a scanner, this phase does not say the change is safe.")
    root = os.path.realpath(repo)
    code, out = _git(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD")
    if code != 0:
        raise Refused(f"cannot read HEAD in {repo}")
    tracked = {p for p in out.decode("utf-8", "replace").split("\0") if p}
    touched = {path: {number for number, _ in rows} for path, rows in lines.items()}
    tools, on_diff, elsewhere, lost, hushed = [], [], 0, 0, 0
    for report in reports:
        names, results, skipped = read_sarif(report)
        tools, hushed = tools + names, hushed + skipped
        for item in results:
            if item["level"] in ("note", "none"):
                continue
            hit = resolved = False
            for uri, start, end in item["places"]:
                key = _resolve(_uri_path(uri, root), tracked) if uri else None
                if key is None:
                    continue
                resolved = True
                added_here = touched.get(key, set())
                if added_here and (start is None or (not added_here.isdisjoint(range(start, end + 1)) if end - start < 10_000
                                                     else any(start <= n <= end for n in added_here))):
                    on_diff.append(f"{_where(key, start)} ({item['rule']}, {item['level']})")
                    hit = True
                    break
            lost += not resolved
            elsewhere += resolved and not hit
    if not tools:
        return _gate("scanner", title, UNKNOWN, "the reports contain no run of a named tool",
                     "Check that the scanner actually ran.")
    said = f"{len(tools)} run(s): {', '.join(sorted(set(tools))[:5])}"
    aside = (f"; {elsewhere} result(s) outside the added lines" if elsewhere else "") + \
            (f"; {lost} result(s) whose file is not found in the repository" if lost else "") + \
            (f"; {hushed} result(s) dismissed by the tool itself" if hushed else "")
    if on_diff:
        return _gate("scanner", title, FAIL, _shown(on_diff) + aside,
                     "Fix each result. A false positive is stated in the PR, with its reason: it is not silenced in the code.")
    if lost:
        return _gate("scanner", title, UNKNOWN, said + aside,
                     "Some results match no file of the repository: read them in the report, and check that it covers this branch.")
    return _gate("scanner", title, OK, said + aside + "; the report is taken on trust, and it covers only what these tools look at")


def gate_surface(lines: dict[str, list[tuple[int, str]]], paths: list[str], zones: list[dict[str, str]], clock: _Clock) -> dict[str, Any]:
    title = "Nothing sensitive for someone to review"
    said = []
    sensitive = size.touched(paths, zones)
    if sensitive:
        said.append("sensitive zone: " + _shown([_where(hit["path"]) for hit in sensitive]))
    manifests = [_where(p) for p in paths if _MANIFEST.search(p)]
    if manifests:
        said.append("dependencies: " + _shown(manifests))
    hot = [f"{_where(path, number)} ({kind})" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
           for number, text in rows if not clock.over() for kind, pattern in _HOT if pattern.search(text[:MAX_LINE])]
    if hot:
        said.append("to review: " + _shown(hot))
    if clock.late:
        said.append(f"reading stopped after {SCAN_BUDGET} s")
    if not said:
        return _gate("surface", title, OK, "no sensitive zone, no dependency, no known risky call in the added lines")
    return _gate("surface", title, UNKNOWN, " — ".join(said),
                 "Review each place cited and return the findings through `review render`. An added or upgraded dependency "
                 "is a decision: state it in the PR. These signals are neither defects nor a complete list.")


def run_gates(table: dict[str, Any], repo: str, base: str, reports: list[str] | None = None,
              exclude: list[str] | None = None, pipeline: bool = False) -> dict[str, Any]:
    """`exclude`: path patterns kept out of reading (a set of fake secrets for tests, for example).
    They are decided on the base branch, not in the change, and what they leave out is said in the result."""
    lines, opaque, paths = added(repo, base)
    if not paths:
        raise Refused(f"no change between {base} and HEAD: nothing to check")
    patterns = [size.glob_regex(g) for g in exclude or []]
    skip = (lambda path: any(r.match(path) for r in patterns)) if patterns else None
    excluded = sorted(p for p in paths if skip and skip(p))
    if skip:
        lines = {path: rows for path, rows in lines.items() if not skip(path)}
        opaque = [p for p in opaque if not skip(p)]
        paths = [p for p in paths if not skip(p)]
    dirty = _git(repo, "status", "--porcelain")[1].decode("utf-8", "replace").strip()
    if dirty and not pipeline:   # what is not committed is not read; a pipeline examines a commit and leaves its tools beside it
        raise Refused("the working copy is not committed: commit the change, and keep the reports outside the repository")
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=A", f"{resolve_base(repo, base)}...HEAD")
    new_files = {p for p in out.decode("utf-8", "replace").split("\0") if p and not (skip and skip(p))} if code == 0 else set()
    past, unread_commits = history(repo, base, skip)
    clock = _Clock()
    try:
        scanner = gate_scanner(repo, lines, reports or [])
    except (TypeError, AttributeError, KeyError, IndexError) as exc:   # a twisted report is refused, it does not crash the command
        raise Refused(f"malformed SARIF report ({type(exc).__name__})") from exc
    gates = [gate_secrets(lines, new_files, opaque, past, unread_commits, clock), gate_muted(lines, paths, clock),
             scanner, gate_surface(lines, paths, size.zones(table, repo, base), clock)]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates,
            "excluded": [_where(p) for p in excluded]}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"Security: {len(result['failed'])} gate(s) failed."
    elif result["unknown"]:
        head = f"Security: nothing failed, {len(result['unknown'])} gate(s) unmeasured."
    else:
        head = "Security: the four gates pass."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    if result.get("excluded"):
        out.append(f"- Not read, as the base branch says: {_shown(result['excluded'])}.")
    out.append("These gates do not say a change is safe: they say what was looked at, and by what.")
    return "\n".join(out) + "\n"
