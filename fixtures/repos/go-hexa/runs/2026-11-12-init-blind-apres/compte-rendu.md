Le dépôt est au palier 1 « Cadré ». `harness status` passe ses 5 vérifications sur 5 et ne signale aucune référence sans cible. Je n'ai rien commité.

Trois commandes ont été refusées faute de validation possible dans cette séance : `ls`/`cat` combinés (j'ai lu les fichiers autrement), `make lint` et `make e2e`. Ces deux dernières restent donc non confirmées (voir plus bas).

**Avant et après**
| | Avant | Après |
|---|---|---|
| Palier | 0 (aucun fichier d'instructions) | 1 · Cadré (5/5) |
| Lignes chargées par session | 0 | 24 (`CLAUDE.md` 1 + `AGENTS.md` 23) |
| Règles | 0 | 4 règles + 3 interdits |

**Fichiers créés**
- `AGENTS.md` : 23 lignes, en mode délégation.
- `CLAUDE.md` : 1 ligne, `@AGENTS.md`.
- `.github/copilot-instructions.md` : 1 ligne. Pas de stub Cursor, puisque l'équipe utilise Claude Code et Copilot.
- `.harness/state.json` : écrit par `harness status`.

**Retiré** : rien, il n'existait aucun fichier d'instructions. Je n'ai recopié aucune ligne de `CONTRIBUTING.md` : « Go idiomatique », « fonctions courtes », « tests en table » ne changent pas ce que fait l'agent.

**Secrets** : aucun trouvé. Le seul résultat est `secrets.DATABASE_URL` dans `deploy.yml`, une référence au coffre GitHub et non une valeur.

**Règles écrites**
| Règle | Statut | Date |
|---|---|---|
| Clé `Idempotency-Key` sur toute écriture, cherchée dans la transaction (post-mortem du double débit, ADR 0003) | Non vérifiée : rien ne contrôle un nouvel endpoint | [2026-04] |
| En-tête `Idempotency-Replayed: true` sur un rejeu (dit par l'équipe). L'exception `POST /transfers` est signalée pour qu'il ne serve pas de modèle | Non vérifiée | [2026-06] |
| Pas de flottant pour un montant (ADR 0002). `internal/app/fees.go` viole déjà la règle, signalé pour ne pas le recopier | Non vérifiée : `forbidigo` tourne dans le job `lint`, qui est en `continue-on-error` | [2025-09] |
| Couches hexagonales (ADR 0001) | Vérifiée par `tools/archcheck`, job `arch` bloquant | [2025-09] |
| Interdit : `reset-db` / `migrate` sur une base qui n'est pas la sienne (incident QA du 3 février) | — | [2026-02] |
| Interdit : modifier une migration déjà appliquée | — | [2026-11] |
| Interdit : lancer `deploy.yml` sans `dry_run` | — | [2026-11] |

**Commandes**
- **Confirmées** : `make test`, `go vet ./...` et `make arch` passent.
- **Non confirmées** :
  - `make lint` : refusée par la séance. Elle n'est pas dans le tableau des commandes.
  - `make e2e` : la cible n'existe pas. Le propriétaire confirme qu'elle a été retirée il y a un an.
  - `make test-integration` : demande une base migrée, et elle ne tourne pas en CI.

**Questions au propriétaire**
1. Le README cite encore `make e2e`. Faut-il retirer la ligne ? Je propose oui : elle est périmée d'après votre réponse.
2. `fees.go` utilise `float64`. Un agent qui passe par ce fichier doit-il le corriger, ou ne pas y toucher ? Je propose de ne pas y toucher hors d'un ticket dédié. Votre réponse a confirmé la dette mais pas la conduite à tenir.
3. L'interdit sur les bases : j'ai compris « `reset-db` et `migrate` seulement sur une base locale à soi ». Votre réponse a repris la formulation d'origine sans préciser. Je propose de garder ma lecture.
4. Interdits sur les migrations et sur `dry_run` : quelle est la date de la décision ? En attendant, j'ai mis la date d'aujourd'hui.

**Pas suivant possible** : rendre le job `lint` bloquant, au moins pour la règle `forbidigo`, ferait passer la règle des montants en « vérifiée » (palier 3). Je ne l'ai pas fait ; `harness target` pour aller plus loin.