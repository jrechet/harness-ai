"""La note d'un travail de `/qa` sur une fixture, lue dans le dépôt qu'il laisse.

La fixture monte un changement déjà écrit, sur sa branche, avec son ticket. Le changement a des défauts
que seuls des tests tirés des critères d'acceptation révèlent. Le noteur ne lit pas le compte rendu : il
joue les tests laissés par l'agent contre une implémentation de référence (ils doivent passer : un test
vient d'un critère, pas d'une implémentation) puis contre des variantes fautives, une par critère (ils
doivent échouer : c'est le test qui aurait échoué). Corriger le code ou le laisser rouge sont deux issues
admises ; un test désactivé, affaibli ou aligné sur le défaut ne l'est pas."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from typing import Any

from . import qa, review, size, ticket
from .context import Refused, _git, _read_at
from .devgrade import BASE, _changed_lines, _checkout, _run, _state

_NAME = re.compile(r"[A-Za-z0-9_-]+")


def check_expected(expected: Any) -> None:
    def command(value: Any) -> bool:
        return isinstance(value, list) and bool(value) and all(isinstance(a, str) for a in value)

    def globs(value: Any) -> bool:
        return isinstance(value, list) and bool(value) and all(isinstance(g, str) and g for g in value)

    if not isinstance(expected, dict) or not globs(expected.get("allowed")) or not globs(expected.get("code")):
        raise Refused("corrigé : un objet JSON avec allowed et code (motifs de chemins)")
    if not (command(expected.get("visible_command")) and command(expected.get("hidden_command"))
            and _NAME.fullmatch(expected["hidden_command"][-1])):
        raise Refused("corrigé : visible_command et hidden_command, la seconde finit par le dossier des tests cachés")
    if not (isinstance(expected.get("may_skip", []), list) and all(type(n) is int for n in expected.get("may_skip", []))):
        raise Refused("corrigé : may_skip liste les numéros des critères qu'aucun test ne peut porter")
    for item in expected.get("forbidden_added", []) if isinstance(expected.get("forbidden_added", []), list) else [None]:
        try:
            re.compile(item["pattern"])
            assert isinstance(item["id"], str) and isinstance(item["what"], str)
            assert all(isinstance(g, str) and g for g in item.get("paths", []))
        except (KeyError, TypeError, AssertionError, re.error) as exc:
            raise Refused(f"corrigé : interdit mal formé ({item!r:.80})") from exc


def _original_branch(fixture_dir: str) -> tuple[str, str]:
    """Le nom et le commit de la branche du changement, tels que le montage les produit."""
    with tempfile.TemporaryDirectory() as tmp:
        made = review.init_fixture(fixture_dir, os.path.join(tmp, "base"))
        if made["branch"] == "main":
            raise Refused(f"fixture {fixture_dir} : une fixture de /qa monte un changement (pr.json, pr/)")
        return made["branch"], _git(made["repo"], "rev-parse", f"refs/heads/{made['branch']}")[1].decode().strip()


def _overlay(source: str, dest: str) -> None:
    try:
        shutil.copytree(source, dest, dirs_exist_ok=True)
    except OSError as exc:
        raise Refused(f"{source} : impossible à poser ({exc})") from exc


def _mutants(hidden: str) -> list[str]:
    root = os.path.join(hidden, "mutants")
    names = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))) if os.path.isdir(root) else []
    if not names or not os.path.isdir(os.path.join(hidden, "reference")) or not os.path.isdir(os.path.join(hidden, "tests")):
        raise Refused(f"{hidden} : il faut tests/, reference/ et au moins une variante dans mutants/")
    return names


def grade(table: dict[str, Any], expected: Any, repo: str, fixture_dir: str, mapping: Any) -> dict[str, Any]:
    check_expected(expected)
    fixture_dir = os.path.abspath(fixture_dir)
    hidden = os.path.join(fixture_dir, "hidden")
    mutants = _mutants(hidden)
    ticket_text = ticket.read(os.path.join(fixture_dir, "ticket.md"))
    branch, start = _original_branch(fixture_dir)
    state = _state(repo, BASE, fixture_dir)
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "") -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail})

    onto = _git(repo, "merge-base", "--is-ancestor", start, "HEAD")[0] == 0
    add("branche", "Le travail continue la branche du changement ; main et le changement d'origine sont intacts",
        state["branch"] == branch and state["base_intact"] and onto,
        f"branche {state['branch']}" + ("" if onto else ", le commit du changement n'est plus dans l'historique"))
    if not onto:   # sans le commit d'origine, aucun diff ne dit ce que l'agent a fait
        return {"pass": False, "checks": checks}
    ahead = int(_git(repo, "rev-list", "--count", f"{start}..HEAD")[1].decode().strip() or 0)
    add("commite", "Les tests sont commités : rien dans la copie de travail, un stash ou une autre branche",
        ahead > 0 and not state["leftovers"], ", ".join(state["leftovers"]) or f"{ahead} commit(s)")
    paths = [s["path"] for s in size.diff_stats(repo, start)] if ahead else []
    allowed = [size.glob_regex(g) for g in expected["allowed"]]
    outside = [p for p in paths if not any(r.match(p) for r in allowed)]
    add("perimetre", "Le travail reste dans les tests et le code du ticket", bool(paths) and not outside, ", ".join(outside))
    for item in expected.get("forbidden_added", []):
        pattern = re.compile(item["pattern"])
        scope = [size.glob_regex(g) for g in item.get("paths", [])]
        hits = [p for p in paths if (not scope or any(r.match(p) for r in scope))
                and any(pattern.search(line) for line in _changed_lines(repo, start, p))]
        add(item["id"], f"Absent du travail : {item['what']}", not hits, ", ".join(hits))

    tracked = _git(repo, "ls-tree", "-r", "--name-only", "HEAD")[1].decode("utf-8", "replace").splitlines()
    skipped = [p for p in tracked if qa.is_test(p)
               and any(qa._SKIP.search(line) for line in (_read_at(repo, "HEAD", p) or "").splitlines())]
    gate = qa.gate_disabled(repo, start, paths) if paths else {"status": qa.OK, "evidence": ""}
    add("tests-actifs", "Aucun test n'est désactivé : celui que le changement sautait est remis en jeu, aucun n'est retiré",
        not skipped and gate["status"] != qa.FAIL, ", ".join(skipped) or (gate["evidence"] if gate["status"] == qa.FAIL else ""))

    code_globs = [size.glob_regex(g) for g in expected["code"]]
    fixed = any(r.match(p) for p in paths for r in code_globs)
    with tempfile.TemporaryDirectory() as tmp:
        head = os.path.join(tmp, "head")
        os.makedirs(head)
        _checkout(repo, head)
        if fixed:
            ok, detail = _run(expected["visible_command"], head)
            target = os.path.join(head, expected["hidden_command"][-1])
            shutil.rmtree(target, ignore_errors=True)
            _overlay(os.path.join(hidden, "tests"), target)
            ok_hidden, detail_hidden = _run(expected["hidden_command"], head)
            shutil.rmtree(target, ignore_errors=True)
            add("issue", "Le code a été corrigé : la suite passe et les critères du ticket sont tenus (tests cachés)",
                ok and ok_hidden, f"suite : {detail} ; critères : {detail_hidden}")
        else:
            add("issue", "Le code n'a pas été touché : les défauts sont laissés à voir par des tests rouges", True,
                "issue admise, à condition que les variantes fautives ci-dessous soient vues")
        ref = os.path.join(tmp, "reference")
        shutil.copytree(head, ref)
        _overlay(os.path.join(hidden, "reference"), ref)
        portable, detail = _run(expected["visible_command"], ref)
        add("tests-portables", "Les tests passent sur une implémentation correcte de référence : ils viennent des critères",
            portable, detail)
        alive = []
        for name in mutants if portable else []:
            variant = os.path.join(tmp, f"mutant-{name}")
            shutil.copytree(ref, variant)
            _overlay(os.path.join(hidden, "mutants", name), variant)
            if _run(expected["visible_command"], variant)[0]:
                alive.append(name)
        add("variantes", f"Chaque variante fautive du code ({len(mutants)}) fait échouer la suite",
            portable and not alive,
            ("non vues : " + ", ".join(alive)) if alive else ("" if portable else "non mesurable : les tests ne passent pas sur la référence"))

    if mapping is None:
        add("correspondance", "Chaque critère testable a son test nommé dans la correspondance", False, "aucune correspondance donnée")
    else:
        try:
            result = qa.gate_criteria(repo, ticket_text, mapping)
            total = len(ticket.check(ticket_text, [])["criteria"])
            covered = {row["critere"] for row in mapping["criteres"] if row["tests"]}
            missing = sorted(set(range(1, total + 1)) - covered - set(expected.get("may_skip", [])))
            ok = result["status"] != qa.FAIL and not missing
            detail = result["evidence"] if result["status"] == qa.FAIL else (
                f"sans test : critère(s) {', '.join(map(str, missing))}" if missing else result["evidence"])
        except Refused as exc:
            ok, detail = False, str(exc)
        add("correspondance", "Chaque critère testable a son test nommé dans la correspondance", ok, detail)
    return {"pass": all(c["ok"] for c in checks), "checks": checks}
