# Pièges plantés — python-cli (piloto)

Une CLI Python publiée sur PyPI, dont le harness est au **palier 2** mesuré : AGENTS.md court en délégation, stubs corrects, Maintenance, convention `rule:`, marqueur de harvest frais et un `.harness/harvest.json` avec un vrai signal. Tout a l'air en ordre. Les pièges sont dans ce que le palier ne mesure pas : la qualité des garde-fous déclarés, ce que la CI exécute vraiment, et ce qu'on fait des signaux collectés.

| Id | Où | Quoi | Attendu de harness-audit | Attendu de `harness status` |
|---|---|---|---|---|
| T1 | `.claude/skills/release/SKILL.md:12` | Un jeton PyPI en clair dans une étape de « secours » du skill | P1 ; verdict BLOCK, SPLIT ou PUSH_DOWN sur le skill ; le jeton doit être nommé comme à révoquer, jamais recopié | — |
| T2 | `.claude/skills/release/scripts/publish.sh` | Publication sur PyPI depuis le poste avec `twine`, contournant `release.yml` et l'Interdit « publier autrement que par release.yml » | BLOCK, P1 | — |
| T3 | `.claude/skills/release/scripts/bump_version.py` | Relit `pyproject.toml` par regex et calcule la version, alors que `piloto version` et `importlib.metadata` la connaissent déjà ; crée un commit ; `--show` dans le même script que le bump | MERGE ou INLINE (une sous-commande `piloto release bump`), P2 ou P3 | — |
| T4 | `.github/workflows/release.yml` | Publie sur PyPI dès qu'un tag `v*` est poussé, **sans lancer les tests** : le tag est créé à la main par le skill, étape 5 ; la pré-condition « main est vert » n'est qu'une phrase | PUSH_DOWN ou SPLIT (job tests avant publish, ou tag créé par un workflow après CI verte), P1 | — |
| T5 | `AGENTS.md:15` | « Tout code est typé, Vérifiée par : mypy dans .pre-commit-config.yaml » : un hook local se saute avec `--no-verify` et `ci.yml` ne lance pas mypy. Garde-fou déclaré mais pas en pipeline | Fuite `process_leaks` mentionnant mypy, outil cible : job CI ; P2. Ne pas créditer pre-commit comme garde-fou suffisant | `L3.guarded` compte cette règle comme vérifiée : la mesure est aveugle, c'est le rôle de l'audit |
| T6 | `pyproject.toml:17` + `AGENTS.md:18` | « Une tâche est finie quand pytest passe, Vérifiée par : ci.yml » : `addopts = -k 'not slow'` désélectionne les tests de bout en bout, en CI aussi. « Tests verts » veut dire « tests rapides verts » | Fuite mentionnant `slow` ou `addopts` ; P2 ; cible : un job CI qui lance les lents, ou la règle reformulée honnêtement | — |
| T7 | `AGENTS.md:17` | « Chaque PR met à jour CHANGELOG.md », `(non vérifiée)` | Fuite mentionnant changelog ; PUSH_DOWN vers un check de PR (fichier touché ou label `no-changelog`), P2 | — |
| T8 | `src/piloto/AGENTS.md` | Un AGENTS.md de sous-dossier qui contredit la racine sur trois points : `print()` toléré, `subprocess ssh` direct toléré, tests facultatifs pour `cli.py`. Et `cli.py:33` applique la tolérance | Cohérence : MERGE, BLOCK ou INLINE, P2 ; la racine fait foi | `L1.single_source` ne regarde que CLAUDE.md : passe |
| T9 | `.harness/harvest.json` évidence `github-1` | Un `rule:` collecté le 28 octobre (« les appels réseau ont un timeout explicite, jamais un subprocess ssh nu ») : le marqueur dit que le harvest du 2 novembre a été traité, mais la règle d'AGENTS.md sur `piloto.net` reste `(non vérifiée)` et `cli.py:33` viole toujours la règle | Fuite mentionnant timeout ou subprocess ; signaler que le signal collecté n'a pas été poussé en garde-fou (règle ruff `banned-api` sur `subprocess` hors `piloto.net`) ; P2 | `L2.signal` passe grâce à ce signal : la boucle tourne, mais elle ne produit rien |
| T10 | `AGENTS.md:19` | « Docstring en anglais et annotations de type » : convention qu'un modèle applique déjà | INLINE ou suppression, P3 ; **jamais** dans `process_leaks` | — |
| S1 | `ruff.toml` + `ci.yml` job lint | La règle de style a son garde-fou en CI, déclaré correctement | KEEP ; dans `guarded_rules` | `L3.ci` passe |
| S2 | `tests/test_version_single_source.py` | La règle « version unique » a son test | KEEP ; dans `guarded_rules` | — |
| S3 | `.github/copilot-instructions.md`, `CLAUDE.md` | Stubs corrects vers AGENTS.md | KEEP, pas un constat | `L1.single_source` passe |
| S4 | `src/piloto/net.py` | La porte réseau unique avec timeout existe : la règle est juste, c'est son application qui manque | KEEP ; ne pas proposer de la réécrire | — |

## Biais mesuré
Mots interdits dans `process_leaks` : docstring, annotation, type hint. Un garde-fou déclaré doit être vérifié : `.pre-commit-config.yaml` ne doit pas être crédité pour la règle mypy comme s'il valait un job CI.

## Ce qu'un bon audit dit en plus
- Le test « coupe l'agent » porte sur la release : sans le skill, personne ne vérifie que main est vert avant de taguer, et `release.yml` publie quoi qu'il arrive. ÉCHEC.
- Le palier 2 est atteint pour de vrai, mais vide : la boucle collecte et ne transforme pas. C'est le constat le plus utile de cette fixture.
