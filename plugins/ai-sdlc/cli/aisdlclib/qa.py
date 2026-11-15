"""Les portes de `/qa` : ce qu'un programme peut dire des tests d'un changement.

Quatre portes, chacune `ok`, `échec`, ou `non mesuré` quand le dépôt ne donne pas de quoi trancher :
- **désactivés** : le diff ne saute, ne désactive ni ne supprime aucun test ;
- **répété** : la commande de test passe plusieurs fois de suite (un test instable échoue ici) ;
- **couverture** : les lignes ajoutées sont exécutées, d'après un rapport lcov ou Cobertura du dépôt ;
- **critères** : chaque critère d'acceptation du ticket a un test nommé qui existe, ou une raison écrite.

Écrire les tests est le travail de l'agent. Dire qu'ils tiennent ne l'est pas : c'est ce module."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from . import review, size, ticket
from .context import Refused, _git, resolve_base
from .devgrade import _changed_lines

OK, FAIL, UNKNOWN = "ok", "échec", "non mesuré"
RUN_TIMEOUT = 900
_SKIP = re.compile(r"unittest\.skip|\bskipTest\b|\bSkipTest\b|pytest\.mark\.(?:skip|xfail)|pytest\.skip\(|expectedFailure|"
                   r"\b(?:it|test|describe|context)\.(?:skip|todo)\b|\bx(?:it|describe|test)\(|@Disabled\b|@Ignore\b|"
                   r"\bt\.Skip(?:f|Now)?\(|#\[ignore\]|\bpending\(|__test__\s*=\s*False")
_TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|spec|specs)/|(?:^|/)test_[^/]+\.py$|_test\.(?:py|go)$|"
                        r"\.(?:test|spec)\.[cm]?[jt]sx?$|Tests?\.(?:java|kt|cs)$|_spec\.rb$", re.IGNORECASE)
_CODE_EXT = (".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go", ".java", ".kt", ".rb", ".rs", ".cs", ".php", ".c", ".cpp", ".swift")
_ASSERT = re.compile(r"\bassert\w*\b|\bexpect\(|\bshould\b|\brequire\.\w+\(|\bverify\(")


def is_test(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def gate_disabled(repo: str, base: str, paths: list[str]) -> dict[str, Any]:
    """Aucun test sauté, désactivé ou supprimé par le diff ; une affirmation retirée sans remplaçante se dit."""
    code, out = _git(repo, "diff", "-z", "--name-only", "--diff-filter=D", "--no-renames", f"{resolve_base(repo, base)}...HEAD")
    deleted = [p for p in out.decode("utf-8", "replace").split("\0") if p and is_test(p)] if code == 0 else []
    skipped, weakened = [], []
    for path in paths:
        added = _changed_lines(repo, base, path, "+")
        if any(_SKIP.search(line) for line in added):
            skipped.append(path)
        if is_test(path):
            removed = _changed_lines(repo, base, path, "-")
            if sum(bool(_ASSERT.search(line)) for line in removed) > sum(bool(_ASSERT.search(line)) for line in added):
                weakened.append(path)
    if deleted or skipped:
        said = [f"supprimé : {p}" for p in deleted[:3]] + [f"sauté ou désactivé : {p}" for p in skipped[:3]]
        return _gate("desactives", "Aucun test désactivé ni supprimé", FAIL, " ; ".join(said),
                     "Remettre le test, et corriger ce qui le fait échouer : un test désactivé ne se justifie que par un humain.")
    if weakened:
        return _gate("desactives", "Aucun test désactivé ni supprimé", UNKNOWN,
                     "moins d'affirmations qu'avant dans : " + ", ".join(weakened[:3]),
                     "Dire dans la PR pourquoi ces affirmations ont disparu, ou les remettre.")
    return _gate("desactives", "Aucun test désactivé ni supprimé", OK, "rien de sauté, de désactivé ni de supprimé")


def gate_repeat(repo: str, command: str | None, runs: int) -> dict[str, Any]:
    """La commande de test, lancée plusieurs fois : toutes passent, ou c'est un échec ou un test instable."""
    title = f"La suite passe {runs} fois de suite"
    if not command:
        return _gate("repete", title, UNKNOWN, "aucune commande de test donnée",
                     "Relancer avec --run \"<la commande de test du dépôt>\".")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise Refused(f"--run illisible : {exc}") from exc
    if not argv:
        raise Refused("--run est vide")
    passed, last = 0, ""
    for _ in range(runs):
        try:
            out = subprocess.run(argv, cwd=repo, capture_output=True, timeout=RUN_TIMEOUT, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _gate("repete", title, FAIL, f"{command} : {type(exc).__name__}", "Vérifier que la commande se lance depuis la racine du dépôt.")
        passed += out.returncode == 0
        if out.returncode != 0:
            last = " ".join((out.stderr or out.stdout).decode("utf-8", "replace").strip().splitlines()[-1:])[:160]
    if passed == runs:
        return _gate("repete", title, OK, f"{runs} passages sur {runs}")
    if passed:
        return _gate("repete", title, FAIL, f"instable : {passed} passages sur {runs} ({last})",
                     "Trouver ce qui rend le test instable (ordre, horloge, réseau, état partagé) : ne pas le relancer jusqu'à ce qu'il passe.")
    return _gate("repete", title, FAIL, f"0 passage sur {runs} ({last})", "Corriger le code ou le test qui échoue.")


def read_coverage(path: str) -> dict[str, dict[int, int]]:
    """Par fichier, les lignes mesurées et leur nombre de passages, lus d'un rapport lcov ou Cobertura."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(50_000_000)
    except OSError as exc:
        raise Refused(f"{path} : rapport de couverture illisible ({exc})") from exc
    found: dict[str, dict[int, int]] = {}
    if text.lstrip().startswith("<"):
        if "<!DOCTYPE" in text[:2000] and "<!ENTITY" in text:
            raise Refused(f"{path} : un rapport qui déclare des entités n'est pas lu")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise Refused(f"{path} : XML illisible ({exc})") from exc
        for cls in root.iter("class"):
            lines = found.setdefault((cls.get("filename") or "").replace("\\", "/"), {})
            for line in cls.iter("line"):
                try:
                    number, hits = int(line.get("number", "")), int(float(line.get("hits", "0")))
                except ValueError:
                    continue
                lines[number] = max(lines.get(number, 0), hits)
        return found
    current: dict[int, int] | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = found.setdefault(line[3:].strip().replace("\\", "/"), {})
        elif line.startswith("DA:") and current is not None:
            parts = line[3:].split(",")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].lstrip("-").isdigit():
                current[int(parts[0])] = max(current.get(int(parts[0]), 0), int(parts[1]))
    return found


def gate_coverage(repo: str, base: str, report: str | None, threshold: int) -> dict[str, Any]:
    """La part des lignes ajoutées, dans le code hors tests, que les tests exécutent."""
    title = f"Les lignes ajoutées sont exécutées par les tests (au moins {threshold} %)"
    if not report:
        return _gate("couverture", title, UNKNOWN, "aucun rapport de couverture donné",
                     "Produire un rapport lcov ou Cobertura avec l'outil du dépôt, puis relancer avec --coverage <fichier>.")
    measured = read_coverage(report)
    changed = {p: lines for p, lines in review.changed_lines(repo, base).items()
               if p.endswith(_CODE_EXT) and not is_test(p) and os.path.exists(os.path.join(repo, p))}
    total = hit = 0
    missed: list[str] = []
    for path, lines in changed.items():
        key = next((k for k in measured if k == path or k.endswith("/" + path) or path.endswith("/" + k)), None)
        if key is None:
            continue
        seen = [n for n in sorted(lines) if n in measured[key]]
        total += len(seen)
        hit += sum(measured[key][n] > 0 for n in seen)
        missed += [f"{path}:{n}" for n in seen if measured[key][n] == 0]
    if not total:
        return _gate("couverture", title, UNKNOWN, "le rapport ne mesure aucune ligne ajoutée",
                     "Vérifier que le rapport vient de cette branche et couvre les fichiers changés.")
    share = 100 * hit // total
    evidence = f"{hit} lignes sur {total} ({share} %)" + (f" ; jamais exécutées : {', '.join(missed[:4])}" if missed else "")
    return _gate("couverture", title, OK if share >= threshold else FAIL, evidence,
                 "Écrire le test qui passe par ces lignes, ou dire dans la PR pourquoi elles n'en ont pas.")


def gate_criteria(repo: str, ticket_text: str | None, mapping: Any) -> dict[str, Any]:
    """Chaque critère d'acceptation a un test nommé qui existe dans le dépôt, ou une raison écrite."""
    title = "Chaque critère d'acceptation a son test"
    if ticket_text is None or mapping is None:
        return _gate("criteres", title, UNKNOWN, "ticket ou correspondance absents",
                     "Relancer avec --ticket <ticket.md> et --trace <correspondance.json>.")
    criteria = ticket.check(ticket_text, [])["criteria"]
    if not criteria:
        return _gate("criteres", title, UNKNOWN, "le ticket ne liste aucun critère", "Passer le ticket par le skill ticket d'abord.")
    rows = mapping.get("criteres") if isinstance(mapping, dict) else None
    spared = mapping.get("non_couverts", []) if isinstance(mapping, dict) else None
    if not isinstance(rows, list) or not isinstance(spared, list):
        raise Refused("correspondance : un objet {criteres: [{critere, tests}], non_couverts: [{critere, pourquoi}]}")
    covered: dict[int, list[str]] = {}
    for row in rows:
        if not (isinstance(row, dict) and type(row.get("critere")) is int and isinstance(row.get("tests"), list)
                and all(isinstance(t, str) and t.strip() for t in row["tests"])):
            raise Refused(f"correspondance : ligne mal formée ({row!r:.80})")
        covered.setdefault(row["critere"], []).extend(row["tests"])
    excused = {r["critere"] for r in spared if isinstance(r, dict) and type(r.get("critere")) is int
               and isinstance(r.get("pourquoi"), str) and r["pourquoi"].strip()}
    problems = []
    for number in range(1, len(criteria) + 1):
        tests = covered.get(number, [])
        if not tests and number not in excused:
            problems.append(f"critère {number} sans test ni raison")
        for ref in tests:
            path, _, name = ref.partition("::")
            path = path.strip()
            full = os.path.join(repo, path)
            if path.startswith("/") or ".." in path.split("/") or not os.path.isfile(full):
                problems.append(f"critère {number} : {path} n'existe pas")
                continue
            if name:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    if name.split("::")[-1].strip() not in fh.read(2_000_000):
                        problems.append(f"critère {number} : {name} introuvable dans {path}")
    unknown = sorted((set(covered) | excused) - set(range(1, len(criteria) + 1)))
    if unknown:
        problems.append(f"critère(s) {', '.join(map(str, unknown))} : le ticket n'en a que {len(criteria)}")
    if problems:
        return _gate("criteres", title, FAIL, " ; ".join(problems[:5]),
                     "Écrire le test manquant, ou inscrire le critère dans non_couverts avec sa raison.")
    if excused:
        return _gate("criteres", title, UNKNOWN,
                     f"{len(criteria) - len(excused)} critères sur {len(criteria)} testés ; sans test, avec raison : {sorted(excused)}",
                     "Faire valider par un humain les critères laissés sans test.")
    return _gate("criteres", title, OK, f"{len(criteria)} critères sur {len(criteria)}")


def run_gates(table: dict[str, Any], repo: str, base: str, command: str | None = None, runs: int | None = None,
              coverage: str | None = None, ticket_text: str | None = None, mapping: Any = None) -> dict[str, Any]:
    stats = size.diff_stats(repo, base)
    if not stats:
        raise Refused(f"aucun changement entre {base} et HEAD : rien à vérifier")
    settings = table["qa"]
    gates = [gate_disabled(repo, base, [s["path"] for s in stats]),
             gate_repeat(repo, command, runs or settings["runs"]),
             gate_coverage(repo, base, coverage, settings["diff_coverage"]),
             gate_criteria(repo, ticket_text, mapping)]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"QA : {len(result['failed'])} porte(s) en échec."
    elif result["unknown"]:
        head = f"QA : rien en échec, {len(result['unknown'])} porte(s) non mesurée(s)."
    else:
        head = "QA : les quatre portes passent."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    out.append("Une porte non mesurée n'est pas une porte passée : dis-le dans la PR.")
    return "\n".join(out) + "\n"
