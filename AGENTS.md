# harness-ai — instructions pour les agents

Mode : **assistance**. Le propriétaire pilote et relit chaque changement ; ce fichier évite les allers-retours, il n'est pas un garde-fou.

## Ce que fait ce repo
Skills Claude Code (`skills/`), CLI déterministe (`cli/`), fixtures d'évaluation (`fixtures/`) et application de suivi (`app/`) pour installer, auditer et faire évoluer l'instrumentation IA d'un dépôt. Modèle de maturité dans `docs/maturity.md`, exigences et état dans `docs/cahier-des-charges.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| `cli/` | `python3 -m unittest discover -s cli/tests` | rien : pas de CI |
| une fixture ou son `expected.json` | `python3 cli/harness.py fixture check <nom>` | rien |
| une tâche de fixture (`tasks/`) | `python3 cli/harness.py bench selftest <nom>` | rien |
| la grille de placement ou une fixture de `fixtures/design/` | `python3 cli/harness.py place check <plan> --expected <fixture>/expected.json` | rien |
| `plugins/ai-sdlc/` ou une fixture de `fixtures/review/`, `dev/`, `ticket/` ou `qa/` | `python3 -m unittest discover -s plugins/ai-sdlc/cli/tests` | rien |
| un SKILL.md | une exécution à l'aveugle sur une fixture, notée par `fixture check --audit` ou `--init` | rien |

## Règles
- Tout ce qui doit être **garanti** va dans `cli/`, pas dans le texte d'un skill ; les skills appellent le CLI. Pourquoi : la grille L1–L4 appliquée à nous-mêmes. (non vérifiée) [2026-11]
- Un `expected.json` est généreux sur les verdicts et priorités, strict sur la preuve, les fuites et les éléments sains. Pourquoi : deux audits sérieux divergent sur SPLIT contre PUSH_DOWN. (non vérifiée) [2026-11]
- Une exécution de skill faite par la session qui a écrit les pièges est une base de régression, pas une mesure. Pourquoi : biais d'auteur constaté sur java-back. (non vérifiée) [2026-11]

## Interdits
- Lire `traps.md`, `expected.json`, `tasks/` ou `runs/` d'une fixture pendant une exécution à l'aveugle. Seuls `owner.md` et, pour une tâche, `task.md` se donnent à l'agent évalué ; `owner.json` lui répond par `bench init`, il ne se lit pas. [2026-11]
- Lancer une exécution à l'aveugle ou une campagne `harness-stress` sans demande du propriétaire. Pourquoi : environ 130 000 tokens par exécution. [2026-11]
- Modifier un `expected.json`, un `traps.md` ou le noteur pour faire passer une exécution. Pourquoi : qui corrige la copie et le corrigé fait toujours monter la note. [2026-11]
- Commiter des `__pycache__` ou un `.skill` ; ajouter une dépendance hors bibliothèque standard au CLI. [2026-11]

## Processus de travail
- Les questions ouvertes (arbitrage, choix d'approche, information que seul le propriétaire détient) sont posées **en fin de message**, dans une section « Questions » numérotée, une par ligne, avec le défaut proposé. Jamais noyées dans le corps, jamais implicites, jamais laissées « dans la PR ». Pas de section s'il n'y en a pas.
- Les décisions déjà prises ne sont pas rouvertes ; les hypothèses prises sans question sont dites en une ligne.
- Une tâche est finie quand les tests passent, les fixtures sont conformes, et le commit est poussé sur `main`.
- Tout travail fini ou commencé, et toute demande ou correction du propriétaire, a sa ligne dans le plan d'avancement de `docs/capacites.md`, dans le même changement. Vérifiée par : hook Stop, `python3 cli/harness.py progress check` [2026-11]

## Tâches déléguées
- `harness-stress` (`.claude/skills/harness-stress`) — une campagne d'évaluation des skills sur les projets types, à la demande, corrections en PR dédiée.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate, ajoutée ici dans la même PR avec le lien.
- Avant d'ajouter une phrase, chercher un garde-fou : une règle vérifiée est raccourcie, une règle racontée est une dette.

<!-- harvest: last=2026-11-09 ref=init -->
