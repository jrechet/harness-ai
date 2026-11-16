"""Les portes de `/secu` : ce qu'un programme peut dire de la sécurité d'un changement.

Quatre portes, chacune `ok`, `échec`, ou `non mesuré` :
- **secrets** : aucune ligne ajoutée ne porte un secret reconnaissable, aucun fichier de clés n'est ajouté ;
- **neutralisés** : le diff ne fait taire aucun scanner (`# nosec`, `nosemgrep`, fichier d'exceptions) ;
- **scanner** : les rapports SARIF des scanners de l'équipe n'ont aucun résultat sur une ligne ajoutée ;
- **surface** : ce que le changement touche de sensible, à relire par quelqu'un : zones sensibles,
  dépendances, appels à risque. Cette porte ne passe jamais seule quand elle trouve quelque chose.

Ce module ne remplace pas un scanner : ses motifs de secrets sont peu nombreux et sûrs d'eux, et il ne
lit pas le code. Sans rapport de scanner, la porte « scanner » reste non mesurée : `/secu` ne bloque
ni n'absout seul. Rien de ce qu'il lit n'est recopié dans sa sortie : un chemin, une ligne, une nature."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from . import qa, size
from .context import Refused, _git, resolve_base

OK, FAIL, UNKNOWN = qa.OK, qa.FAIL, qa.UNKNOWN
MAX_LINE = 20_000       # au-delà, la ligne est lue jusque-là et signalée
MAX_SHOWN = 8
MAX_RESULTS = 100_000
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Des formes que rien d'autre qu'un secret ne prend. Pas de quantificateurs imbriqués : le texte vient d'un tiers.
_SECRETS = [
    ("clé privée", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("clé d'accès AWS", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("jeton GitHub", re.compile(r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("jeton GitLab", re.compile(r"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_-]{20,}")),
    ("jeton Slack", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("clé d'API (sk-…)", re.compile(r"(?<![A-Za-z0-9_-])sk-(?:ant-|proj-|live_)?[A-Za-z0-9_-]{24,}")),
    ("clé Stripe", re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
    ("clé Google", re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")),
    ("jeton npm ou PyPI", re.compile(r"(?<![A-Za-z0-9_])(?:npm_[A-Za-z0-9]{36}|pypi-AgEI[A-Za-z0-9_-]{40,})")),
    ("JWT", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")),
    ("identifiants dans une URL", re.compile(r"[a-z][a-z0-9+.-]{1,20}://[^\s/:@'\"]{1,80}:([^\s/@'\"]{6,80})@[\w.-]")),
]
# nom = "valeur littérale" : le nom dit que c'est un secret, la valeur n'est ni un exemple ni une variable
_ASSIGN = re.compile(r"(?i)(?<![a-z0-9])(?:[a-z0-9_.-]{0,30})(?:passw(?:or)?d|pwd|secret|token|api[_-]?key|apikey|private[_-]?key|"
                     r"access[_-]?key|auth[_-]?key|credential)s?[\"']?\s{0,3}(?:=|:|=>|:=)\s{0,3}[\"']([^\"'\s]{12,200})[\"']")
_PLACEHOLDER = re.compile(r"(?i)^(?:x+|\*+|\.+|0+|changeme.*|change[_-]me.*|example.*|exemple.*|dummy.*|fake.*|test.*|todo.*|"
                          r"your[_-].*|votre[_-].*|placeholder.*|redacted.*|secret|password|motdepasse|none|null|undefined)$|"
                          r"[<{$%]|\b(?:env|environ|getenv|config|settings|vault|secrets)\b|^[a-z_]+$")
_KEY_FILE = re.compile(r"(?:^|/)(?:\.env(?:\.(?!example$|sample$|template$|dist$)[\w.-]+)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
                       r"[^/]+\.(?:pem|p12|pfx|jks|keystore|key)|credentials(?:\.json)?|\.npmrc|\.pypirc|\.netrc|"
                       r"service[_-]?account[^/]*\.json)$", re.IGNORECASE)
_MUTED = re.compile(r"#\s*nosec\b|#\s*noqa:\s*S\d|\bnosemgrep\b|semgrep:\s*ignore|//\s*nolint:\s*gosec|#nosec\b|\bNOSONAR\b|"
                    r"gitleaks:allow|\bcodeql\s*\[|lgtm\s*\[|snyk:?\s*ignore|trivy:ignore|checkov:skip|tfsec:ignore|"
                    r"bandit:\s*skip|eslint-disable[\w-]*\s+security/|@SuppressWarnings\(\s*\"(?:java:S|squid:S|findsecbugs)|"
                    r"detect-secrets:\s*allowlist|pragma:\s*allowlist\s+secret|brakeman:\s*ignore", re.IGNORECASE)
_SCANNER_CONFIG = re.compile(r"(?:^|/)(?:\.gitleaksignore|\.gitleaks\.toml|gitleaks\.toml|\.semgrepignore|\.semgrep(?:\.ya?ml|/.*)|"
                             r"\.trivyignore(?:\.ya?ml)?|trivy\.ya?ml|\.snyk|\.bandit|bandit\.ya?ml|\.secrets\.baseline|"
                             r"\.checkov\.ya?ml|\.tfsec/.*|sonar-project\.properties|\.github/codeql/.*|"
                             r"\.github/dependabot\.ya?ml|renovate\.json5?|\.trufflehog[\w.-]*|\.pre-commit-config\.yaml)$")
_MANIFEST = re.compile(r"(?:^|/)(?:package\.json|package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|"
                       r"requirements[\w.-]*\.txt|constraints[\w.-]*\.txt|pyproject\.toml|poetry\.lock|uv\.lock|Pipfile(?:\.lock)?|"
                       r"setup\.(?:py|cfg)|go\.(?:mod|sum)|Cargo\.(?:toml|lock)|pom\.xml|build\.gradle(?:\.kts)?|gradle\.lockfile|"
                       r"libs\.versions\.toml|Gemfile(?:\.lock)?|composer\.(?:json|lock)|[^/]+\.csproj|packages\.lock\.json|"
                       r"Package\.(?:swift|resolved)|pubspec\.(?:yaml|lock)|mix\.(?:exs|lock))$")
# Des appels qu'un relecteur regarde toujours. Un signal, pas un verdict : la plupart sont légitimes.
_HOT = [
    ("code évalué à l'exécution", re.compile(r"(?<![\w.])(?:eval|exec)\s?\(|new Function\(|\bcompile\(.{0,80}['\"]exec['\"]")),
    ("commande passée à un shell", re.compile(r"shell\s?=\s?True|os\.system\(|os\.popen\(|child_process|Runtime\.getRuntime\(\)\.exec|"
                                              r"(?<![\w.])(?:execSync|spawnSync|exec)\(\s?[`'\"]|subprocess\.\w+\(\s?f?[\"']")),
    ("désérialisation", re.compile(r"pickle\.loads?\(|yaml\.load\((?!.{0,80}SafeLoader)|\bmarshal\.loads?\(|ObjectInputStream|"
                                   r"unserialize\(|Marshal\.load\(")),
    ("vérification TLS coupée", re.compile(r"verify\s?=\s?False|InsecureSkipVerify\s?:\s?true|rejectUnauthorized\s?:\s?false|"
                                           r"NODE_TLS_REJECT_UNAUTHORIZED|CURLOPT_SSL_VERIFYPEER|--insecure\b|curl\s+-k\b|"
                                           r"check_hostname\s?=\s?False|_create_unverified_context")),
    ("HTML injecté sans échappement", re.compile(r"\.innerHTML\s?=|dangerouslySetInnerHTML|v-html=|\|\s?safe\b|mark_safe\(|"
                                                 r"document\.write\(|bypassSecurityTrust\w+\(|\{@html\b")),
    ("requête SQL construite par assemblage", re.compile(
        r"(?i)(?:execute|query|raw|prepare)\w*\(\s?(?:f[\"']|[\"'][^\"']{0,200}[\"']\s?(?:%|\+|\.format\())|"
        r"[\"'](?:select|insert|update|delete)\b[^\"']{0,200}[\"']\s?(?:\+|%\s|\.format\()|\$\{[^}]{0,80}\}[^`]{0,200}\b(?:where|values)\b")),
    ("hachage ou chiffrement faible", re.compile(r"(?<![\w.])(?:md5|sha1|MD5|SHA1)\s?\(|hashlib\.(?:md5|sha1)\(|"
                                                 r"MessageDigest\.getInstance\(\s?\"(?:MD5|SHA-?1)\"|createHash\(\s?['\"](?:md5|sha1)['\"]|"
                                                 r"\bDES(?:ede)?\.new\(|['\"/](?:DES|RC4|3DES)['\"/]|MODE_ECB|/ECB/|"
                                                 r"Math\.random\(\).{0,60}(?:token|secret|password|key)")),
    ("droits ouverts", re.compile(r"chmod\s+(?:-R\s+)?(?:777|666|a\+[rwx]+)|0o?777\b|Access-Control-Allow-Origin['\"]?\s?[:=,]\s?['\"]\*|"
                                  r"cors\(\s?\)|@PermitAll|permitAll\(\)|AllowAny\b|csrf_exempt|csrf\(\)\.disable|"
                                  r"--dangerously-skip-permissions|--privileged\b|privileged:\s?true")),
    ("script téléchargé puis exécuté", re.compile(r"(?:curl|wget)\b[^|;&]{0,200}\|\s?(?:sudo\s+)?(?:ba|z|da)?sh\b")),
    ("vérification contournée", re.compile(r"--no-verify\b|--no-gpg-sign\b|--force-with-lease\b|push\s+(?:-f|--force)\b|"
                                           r"continue-on-error:\s?true|\|\|\s?true\s*$|pull_request_target")),
]
_PROSE = (".md", ".mdx", ".txt", ".rst", ".adoc")   # de la prose qui parle d'un appel n'est pas un appel
_LEVELS = ("error", "warning", "note", "none")


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _where(path: str, line: int | None = None) -> str:
    """Un chemin prêt à être montré : il vient du dépôt examiné, donc ni saut de ligne ni caractère de contrôle."""
    clean = "".join(ch if ch.isprintable() and ch not in "`|<>" else "?" for ch in path)[:120]
    return f"{clean}:{line}" if line else clean


def _shown(items: list[str]) -> str:
    extra = len(items) - MAX_SHOWN
    return " ; ".join(items[:MAX_SHOWN]) + (f" ; et {extra} autre(s)" if extra > 0 else "")


def added(repo: str, base: str) -> tuple[dict[str, list[tuple[int, str]]], list[str], list[str]]:
    """Par fichier ajouté ou modifié, ses lignes ajoutées (numéro, texte) ; puis les fichiers que git ne
    sait pas lire en texte, et tous les chemins du changement."""
    commit = resolve_base(repo, base)
    paths = [s["path"] for s in size.diff_stats(repo, base)]
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=AM", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD")
    lines: dict[str, list[tuple[int, str]]] = {}
    opaque = []
    for raw in filter(None, out.split(b"\0")):
        path = raw.decode("utf-8", "replace")
        code, patch = _git(repo, "--literal-pathspecs", "diff", "-U0", "--no-color", "--no-ext-diff", "--text",
                           "--no-renames", f"{commit}...HEAD", "--", path)
        if code != 0:
            opaque.append(path)
            continue
        found, number = lines.setdefault(path, []), 0
        for line in patch.decode("utf-8", "replace").splitlines():
            match = _HUNK.match(line)
            if match:
                number = int(match[1])
            elif number and line.startswith("+"):
                found.append((number, line[1:]))
                number += 1
        if any("\0" in text for _, text in found):
            opaque.append(path)
    return lines, opaque, paths


def _secret_kinds(text: str) -> list[str]:
    kinds = []
    for kind, pattern in _SECRETS:
        match = pattern.search(text)
        # le seul motif à groupe est l'URL : son mot de passe peut être une variable, pas une valeur
        if match and not (match.groups() and _PLACEHOLDER.search(match[1])):
            kinds.append(kind)
    for match in _ASSIGN.finditer(text):
        if not _PLACEHOLDER.search(match[1]):
            kinds.append("valeur en dur sous un nom de secret")
            break
    return kinds


def gate_secrets(lines: dict[str, list[tuple[int, str]]], paths: list[str], added_files: set[str]) -> dict[str, Any]:
    title = "Aucun secret dans les lignes ajoutées"
    hits, long_lines = [], 0
    for path in sorted(added_files):
        if _KEY_FILE.search(path):
            hits.append(f"{_where(path)} (fichier de clés ou d'identifiants ajouté)")
    for path, rows in sorted(lines.items()):
        for number, text in rows:
            long_lines += len(text) > MAX_LINE
            for kind in _secret_kinds(text[:MAX_LINE]):
                hits.append(f"{_where(path, number)} ({kind})")
    if hits:
        return _gate("secrets", title, FAIL, _shown(hits),
                     "Un secret poussé est un secret exposé, même retiré ensuite : le faire révoquer par son propriétaire, "
                     "puis le sortir du code. La valeur n'est pas recopiée ici, ne la recopie pas non plus.")
    note = f" ; {long_lines} ligne(s) de plus de {MAX_LINE} caractères lues en partie" if long_lines else ""
    return _gate("secrets", title, OK, f"{sum(len(r) for r in lines.values())} ligne(s) ajoutée(s) lues, formes connues seulement{note}")


def gate_muted(lines: dict[str, list[tuple[int, str]]], paths: list[str]) -> dict[str, Any]:
    title = "Aucun scanner n'est réduit au silence"
    hits = [f"{_where(path, number)}" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
            for number, text in rows if _MUTED.search(text[:MAX_LINE])]
    config = [_where(p) for p in paths if _SCANNER_CONFIG.search(p)]
    if hits:
        return _gate("neutralises", title, FAIL, "exception posée dans le code : " + _shown(hits),
                     "Corriger ce que le scanner signale. Si c'est un faux positif, un humain le dit dans la PR : "
                     "la porte ne le tranche pas.")
    if config:
        return _gate("neutralises", title, UNKNOWN, "configuration d'un scanner modifiée : " + _shown(config),
                     "Dire dans la PR ce que ce changement fait à ce que le scanner regarde.")
    return _gate("neutralises", title, OK, "aucune exception ajoutée")


def _uri_path(uri: str, root: str) -> str:
    path = uri[7:] if uri.startswith("file://") else uri
    path = path.split("?")[0].replace("\\", "/")
    if path.startswith("/") and (path == root or path.startswith(root + "/")):
        path = path[len(root) + 1:]
    return path.lstrip("./") if not path.startswith("/") else path


def read_sarif(path: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Les outils et les résultats d'un rapport SARIF 2.1 : règle, gravité, fichier, ligne."""
    try:
        if os.path.getsize(path) > qa.MAX_REPORT:
            raise Refused(f"{path} : rapport de plus de {qa.MAX_REPORT} octets")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        raise Refused(f"{path} : rapport illisible ({type(exc).__name__})") from exc
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise Refused(f"{path} : ce n'est pas un rapport SARIF (pas de liste runs)")
    tools, results = [], []
    for run in runs:
        if not isinstance(run, dict):
            raise Refused(f"{path} : exécution SARIF mal formée")
        driver = ((run.get("tool") or {}).get("driver") or {}) if isinstance(run.get("tool"), dict) else {}
        tools.append(str(driver.get("name", "outil sans nom"))[:40] if isinstance(driver, dict) else "outil sans nom")
        levels = {}
        for rule in (driver.get("rules") or []) if isinstance(driver, dict) and isinstance(driver.get("rules"), list) else []:
            if isinstance(rule, dict) and isinstance(rule.get("defaultConfiguration"), dict):
                levels[rule.get("id")] = rule["defaultConfiguration"].get("level")
        found = run.get("results", [])
        if not isinstance(found, list) or len(found) > MAX_RESULTS:
            raise Refused(f"{path} : results est une liste d'au plus {MAX_RESULTS} résultats")
        for item in found:
            if not isinstance(item, dict):
                raise Refused(f"{path} : résultat SARIF mal formé")
            if isinstance(item.get("suppressions"), list) and item["suppressions"]:
                continue   # écarté par l'outil lui-même : c'est sa configuration qui en répond
            rule = item.get("ruleId") if isinstance(item.get("ruleId"), str) else "règle sans nom"
            level = item.get("level") or levels.get(rule) or "warning"
            place = (item.get("locations") or [{}])[0] if isinstance(item.get("locations"), list) else {}
            physical = place.get("physicalLocation", {}) if isinstance(place, dict) else {}
            artifact = physical.get("artifactLocation", {}) if isinstance(physical, dict) else {}
            region = physical.get("region", {}) if isinstance(physical, dict) else {}
            uri = artifact.get("uri") if isinstance(artifact, dict) else None
            start = region.get("startLine") if isinstance(region, dict) else None
            end = region.get("endLine", start) if isinstance(region, dict) else None
            results.append({"rule": rule[:60], "level": level if level in _LEVELS else "warning",
                            "uri": uri if isinstance(uri, str) else None,
                            "start": start if type(start) is int else None, "end": end if type(end) is int else None})
    return tools, results


def gate_scanner(repo: str, lines: dict[str, list[tuple[int, str]]], paths: list[str], reports: list[str]) -> dict[str, Any]:
    title = "Les scanners de l'équipe ne signalent rien sur les lignes ajoutées"
    if not reports:
        return _gate("scanner", title, UNKNOWN, "aucun rapport de scanner donné",
                     "Lancer les scanners que le dépôt déclare (AGENTS.md, CI) avec une sortie SARIF, puis relancer avec "
                     "--report <fichier>. Sans scanner, cette phase ne dit pas que le changement est sûr.")
    root = os.path.realpath(repo)
    touched = {path: {number for number, _ in rows} for path, rows in lines.items()}
    tools, on_diff, elsewhere, lost = [], [], 0, 0
    for report in reports:
        names, results = read_sarif(report)
        tools += names
        for item in results:
            if item["level"] in ("note", "none"):
                continue
            if not item["uri"]:
                lost += 1
                continue
            key = qa._report_key(_uri_path(item["uri"], root), {p: {} for p in paths})
            if key is None:
                elsewhere += 1
            elif key in touched and (item["start"] is None or any(item["start"] <= n <= (item["end"] or item["start"]) for n in touched[key])):
                on_diff.append(f"{_where(key, item['start'])} ({_where(item['rule'])}, {item['level']})")
            else:
                elsewhere += 1
    if not tools:
        return _gate("scanner", title, UNKNOWN, "les rapports ne contiennent aucune exécution", "Vérifier que le scanner a bien tourné.")
    said = f"{len(tools)} exécution(s) : {', '.join(_where(t) for t in sorted(set(tools))[:5])}"
    aside = (f" ; {elsewhere} résultat(s) hors des lignes ajoutées" if elsewhere else "") + \
            (f" ; {lost} résultat(s) sans fichier" if lost else "")
    if on_diff:
        return _gate("scanner", title, FAIL, _shown(on_diff) + aside,
                     "Corriger chaque résultat. Un faux positif se dit dans la PR, avec sa raison : il ne se fait pas taire dans le code.")
    if lost:
        return _gate("scanner", title, UNKNOWN, said + aside, "Des résultats ne disent pas où ils sont : les lire dans le rapport.")
    return _gate("scanner", title, OK, said + aside + " ; le rapport est cru sur parole, et il ne couvre que ce que ces outils regardent")


def gate_surface(lines: dict[str, list[tuple[int, str]]], paths: list[str], zones: list[dict[str, str]]) -> dict[str, Any]:
    title = "Rien de sensible à faire relire par quelqu'un"
    said = []
    sensitive = size.touched(paths, zones)
    if sensitive:
        said.append("zone sensible : " + _shown([_where(hit["path"]) for hit in sensitive]))
    manifests = [_where(p) for p in paths if _MANIFEST.search(p)]
    if manifests:
        said.append("dépendances : " + _shown(manifests))
    hot = [f"{_where(path, number)} ({kind})" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
           for number, text in rows for kind, pattern in _HOT if pattern.search(text[:MAX_LINE])]
    if hot:
        said.append("à relire : " + _shown(hot))
    if not said:
        return _gate("surface", title, OK, "ni zone sensible, ni dépendance, ni appel à risque reconnu dans les lignes ajoutées")
    return _gate("surface", title, UNKNOWN, " — ".join(said),
                 "Relire chaque endroit cité et rendre les constats par `review render`. Une dépendance ajoutée ou montée "
                 "de version est une décision : la dire dans la PR. Ces signaux ne sont ni des défauts ni une liste complète.")


def run_gates(table: dict[str, Any], repo: str, base: str, reports: list[str] | None = None) -> dict[str, Any]:
    lines, opaque, paths = added(repo, base)
    if not paths:
        raise Refused(f"aucun changement entre {base} et HEAD : rien à vérifier")
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=A", f"{resolve_base(repo, base)}...HEAD")
    new_files = {p for p in out.decode("utf-8", "replace").split("\0") if p} if code == 0 else set()
    gates = [gate_secrets(lines, paths, new_files), gate_muted(lines, paths),
             gate_scanner(repo, lines, paths, reports or []), gate_surface(lines, paths, size.zones(table, repo, base))]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates,
            "unread": [_where(p) for p in opaque]}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"Sécurité : {len(result['failed'])} porte(s) en échec."
    elif result["unknown"]:
        head = f"Sécurité : rien en échec, {len(result['unknown'])} porte(s) non mesurée(s)."
    else:
        head = "Sécurité : les quatre portes passent."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    if result["unread"]:
        out.append(f"- Non lus (binaires) : {_shown(result['unread'])}.")
    out.append("Ces portes ne disent pas qu'un changement est sûr : elles disent ce qui a été regardé, et par quoi.")
    return "\n".join(out) + "\n"
