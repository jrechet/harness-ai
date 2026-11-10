# harness-ai — instructions pour les agents

Mode : **assistance**. Le propriétaire pilote et relit chaque changement ; ce fichier évite les allers-retours, il n'est pas un garde-fou.

## Ce que fait ce repo
Skills Claude Code (`skills/`), CLI déterministe (`cli/`), fixtures d'évaluation (`fixtures/`) et application de suivi (`app/`) pour installer, auditer et faire évoluer l'instrumentation IA d'un dépôt. Modèle de maturité dans `docs/maturity.md`, exigences et état dans `docs/cahier-des-charges.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| `cli/` | `python3 -m unittest discover -s cli/tests` | rien : pas de CI |
| une fixture ou son `expected.json` | `python3 cli/harness.py fixture check <nom>` | rien |
| un SKILL.md | une exécution à l'aveugle sur une fixture, notée par `fixture check --audit` ou `--init` | rien |

## Règles
- Tout ce qui doit être **garanti** va dans `cli/`, pas dans le texte d'un skill ; les skills appellent le CLI. Pourquoi : la grille L1–L4 appliquée à nous-mêmes. (non vérifiée)
- Un `expected.json` est généreux sur les verdicts et priorités, strict sur la preuve, les fuites et les éléments sains. Pourquoi : deux audits sérieux divergent sur SPLIT contre PUSH_DOWN. (non vérifiée)
- Une exécution de skill faite par la session qui a écrit les pièges est une base de régression, pas une mesure. Pourquoi : biais d'auteur constaté sur java-back. (non vérifiée)

## Interdits
- Lire `traps.md`, `expected.json` ou `runs/` d'une fixture pendant une exécution à l'aveugle.
- Commiter des `__pycache__` ou un `.skill` ; ajouter une dépendance hors bibliothèque standard au CLI.

## Processus de travail
- Les questions ouvertes (arbitrage, choix d'approche, information que seul le propriétaire détient) sont posées **en fin de message**, dans une section « Questions » numérotée, une par ligne, avec le défaut proposé. Jamais noyées dans le corps, jamais implicites, jamais laissées « dans la PR ». Pas de section s'il n'y en a pas.
- Les décisions déjà prises ne sont pas rouvertes ; les hypothèses prises sans question sont dites en une ligne.
- Une tâche est finie quand les tests passent, les fixtures sont conformes, et le commit est poussé sur `main`.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate, ajoutée ici dans la même PR avec le lien.
- Avant d'ajouter une phrase, chercher un garde-fou : une règle vérifiée est raccourcie, une règle racontée est une dette.

<!-- harvest: last=2026-11-09 ref=init -->
