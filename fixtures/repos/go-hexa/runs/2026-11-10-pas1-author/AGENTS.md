# ledger — instructions pour les agents

Mode : **délégation**. Un agent reçoit un ticket entier et revient avec une PR ; les jobs `test` et `arch` de la CI décident, ce fichier explique.

## Ce que fait ce repo
Service de tenue de comptes : ouvrir un compte, lire un solde, virer de l'argent. Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`, exploitation dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code Go | `go vet ./... && go test ./...` | job `test` |
| un import entre couches | `go run ./tools/archcheck` | job `arch` |
| `internal/adapters/postgres` | `make test-integration`, sur ta base locale | rien : ces tests ne tournent pas en CI |

## Règles
- Le domaine ne dépend de rien, un cas d'usage ne connaît que des ports, les adaptateurs ne se connaissent pas. Pourquoi : tester un virement demandait une base. Vérifiée par : `tools/archcheck`, job `arch`. [2026-11]
- Tout endpoint qui modifie un solde exige `Idempotency-Key`, cherchée dans la transaction d'écriture, jamais avant de l'ouvrir. Pourquoi : un compte débité deux fois de 480 €, 37 comptes touchés (`docs/postmortems/2026-04-double-debit.md`). `POST /accounts` ne l'applique pas encore, ne le prends pas pour modèle. (non vérifiée) [2026-11]
- Un montant est un `domain.Money`, entier en centimes ; aucun flottant dans `internal/domain` ni `internal/app`. Pourquoi : arrondis qui faussent un solde, ADR 0002. `internal/app/fees.go` viole déjà la règle, et le job `lint` qui porte ce contrôle ne bloque pas. (non vérifiée) [2026-11]
- Une migration appliquée ne se modifie plus : on ajoute un fichier au numéro suivant. Pourquoi : staging et production ne rejouent que ce que `deploy.yml` leur passe. (non vérifiée) [2026-11]

## Interdits
- `make reset-db` et `make migrate` avec un `DATABASE_URL` qui n'est pas ta base locale. Pourquoi : `reset-db` détruit le schéma sans regarder la cible ; deux jours de données QA perdus sur staging le 3 février 2026. [2026-02]
- Lancer `deploy.yml` avec `dry_run` à faux, ou vers `production`. Pourquoi : demande du propriétaire, pas d'incident connu. [2026-11]
- Modifier un fichier existant de `migrations/`. Pourquoi : voir la règle des migrations. [2026-11]
