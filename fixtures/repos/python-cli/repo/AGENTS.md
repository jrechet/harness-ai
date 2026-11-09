# piloto — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
CLI Python 3.12 (`src/piloto`) qui pousse des fichiers de configuration sur des serveurs par SSH, avec un mode `diff`. Publiée sur PyPI à chaque tag `v*`. Référence : `docs/agents/`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| `src/` | `ruff check . && pytest` | `ci.yml` jobs lint, tests |
| `pyproject.toml` | `pytest tests/test_version_single_source.py` | `ci.yml` job tests |
| la release | `.claude/skills/release` | `release.yml` sur tag |

## Règles
Chaque règle dit pourquoi et par quoi elle est vérifiée.
- Le style suit ruff (`ruff.toml`). Pourquoi : des diffs de formatage noyaient les revues. Vérifiée par : `ruff check` dans `ci.yml`.
- Tout code est typé et passe mypy en strict. Pourquoi : une `None` non gérée a effacé la config d'un serveur (#23). Vérifiée par : `mypy` dans `.pre-commit-config.yaml`.
- La version n'existe qu'à un endroit, `pyproject.toml` ; le code la lit par `importlib.metadata`. Pourquoi : deux versions divergentes publiées sur PyPI (#31). Vérifiée par : `tests/test_version_single_source.py`.
- Chaque PR met à jour `CHANGELOG.md`. Pourquoi : la release 1.4 est sortie avec un changelog vide. (non vérifiée)
- Une tâche est finie quand `pytest` passe. Vérifiée par : `ci.yml` job tests.
- Les fonctions publiques ont une docstring en anglais et des annotations de type.
- Les appels réseau passent par `piloto.net` et jamais par `subprocess` direct. Pourquoi : un `ssh` sans timeout a bloqué la CI quarante minutes (#38). (non vérifiée)

## Interdits
- Publier sur PyPI autrement que par `release.yml` sur un tag.
- Modifier une version déjà publiée.
- Pousser sur `main` sans PR.

## Processus de travail
- Arrête-toi et pose la question quand : la tâche touche la publication, change une interface de commande, ou que la CI est rouge pour une cause étrangère à ton diff.
- Une tâche est finie quand : lint et tests verts, un test couvre le changement, `CHANGELOG.md` à jour, la PR explique le pourquoi.
- CI rouge : corrige si la cause est dans ton diff ; sinon signale-le et n'y touche pas.

## Tâches déléguées
- `release` (`.claude/skills/release`) — préparer et publier une version.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate, ajoutée ici dans la même PR avec le lien, ou collectée par harness-harvest.
- Avant d'ajouter une phrase, chercher un garde-fou : une règle vérifiée est raccourcie, une règle racontée est une dette.

<!-- harvest: last=2026-11-02 ref=https://github.com/acme/piloto/pull/41 -->
