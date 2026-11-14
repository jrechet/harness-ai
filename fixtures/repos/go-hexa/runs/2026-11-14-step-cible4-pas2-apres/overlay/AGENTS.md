# ledger — instructions pour les agents

Mode : **délégation**. Un agent reçoit un ticket entier et revient avec une PR ; les jobs `test` et `arch` de la CI décident, ce fichier explique.

## Ce que fait ce repo
Service de tenue de comptes : ouvrir un compte, lire un solde, virer de l'argent. Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`, exploitation dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code Go | `go vet ./... && go test ./...` | job `test` |
| un import entre couches | `go run ./tools/archcheck` | job `arch` |
| `migrations/` | `go run ./tools/migrationcheck -base origin/main` | job `migrations` |
| `internal/adapters/postgres` | `make test-integration`, sur ta base locale | rien : ces tests ne tournent pas en CI |

## Règles
- Le domaine ne dépend de rien, un cas d'usage ne connaît que des ports, les adaptateurs ne se connaissent pas. Pourquoi : tester un virement demandait une base. Vérifiée par : `tools/archcheck`, job `arch`. [2026-11]
- Tout endpoint qui modifie un solde exige `Idempotency-Key`, cherchée dans la transaction d'écriture, jamais avant de l'ouvrir. Pourquoi : un compte débité deux fois de 480 €, 37 comptes touchés (`docs/postmortems/2026-04-double-debit.md`). Vérifiée par : `internal/adapters/httpapi/idempotency_guard_test.go`, job `test` (présence de la clé sur toute route non-GET ; la recherche dans la transaction reste à la revue). Exemption unique, `POST /accounts` : ne le prends pas pour modèle. [2026-11]
- Une réponse rejouée par clé d'idempotence porte l'en-tête `Idempotency-Replayed: true`. Pourquoi : l'application mobile s'en sert pour ne pas afficher deux confirmations ; dit par l'équipe, écrit nulle part ailleurs. `POST /transfers` ne le fait pas encore. (non vérifiée) [2026-06]
- Un montant est un `domain.Money`, entier en centimes ; aucun flottant dans `internal/domain` ni `internal/app`. Pourquoi : arrondis qui faussent un solde, ADR 0002. `internal/app/fees.go` viole déjà la règle, et le job `lint` qui porte ce contrôle ne bloque pas. (non vérifiée) [2026-11]
- Une migration appliquée ne se modifie plus : on ajoute un fichier au numéro suivant. Pourquoi : staging et production ne rejouent que ce que `deploy.yml` leur passe. Vérifiée par : `tools/migrationcheck`, job `migrations` (PR seulement). [2026-11]

## Interdits
- `make reset-db` et `make migrate` hors de ta base locale. Pourquoi : deux jours de données QA perdus sur staging le 3 février 2026. Vérifiée par : `tools/localdb`, appelé par les deux cibles (refus hors localhost/loopback/socket), job `test`. [2026-11]
- Lancer `deploy.yml` avec `dry_run` à faux, ou vers `production`. Pourquoi : demande du propriétaire, pas d'incident connu. [2026-11]
- Modifier un fichier existant de `migrations/`. Pourquoi : voir la règle des migrations. Vérifiée par : `tools/migrationcheck`, job `migrations`. [2026-11]

## Processus de travail
- Arrête-toi et pose la question avant : de modifier une migration existante ou d'en écrire une qui supprime ou réécrit des données ; de renommer, retirer ou changer le type d'une route ou d'un champ d'API existant ; de toucher à `deploy.yml` ; et quand le ticket est ambigu sur un montant ou un arrondi. Ajouter une migration au numéro suivant, une route ou un champ nouveau, c'est le chemin normal. Le reste, tu tranches et tu l'écris dans la PR.
- Une tâche est finie quand : `make test` et `make arch` passent, un test couvre le changement, et la PR dit pourquoi en deux lignes.
- CI rouge : si la cause est dans ton diff, corrige ; sinon signale-le dans la PR et n'y touche pas. `lint` ne bloque pas (dette héritée) : ne le prends pas pour un échec.
- Test instable : relance une fois, puis ouvre une issue ; ne le désactive jamais.

## Tâches déléguées
- `ajouter-endpoint` (`.claude/skills/ajouter-endpoint`) — une nouvelle route, du cas d'usage au handler et à ses tests.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate. Elle est ajoutée ici dans la même PR, datée, avec le lien vers le commentaire, ou collectée par harness-harvest.
- Avant d'ajouter une phrase, chercher si un linter, un test ou un check CI peut porter la règle : une règle vérifiée est raccourcie, une règle racontée est une dette.
- Une règle sans incident depuis six mois, ou écrite pour une génération de modèles passée, est candidate au retrait à la prochaine revue de pertinence.

<!-- harvest: last=2026-11-14 ref=init -->
