`POST /accounts/{id}/deposits` est en place et committé sur la branche `feat/deposits` (commit `0a8bef5`), mais le SQL du dépôt et la migration 0004 n'ont été exécutés contre aucune base. Le dépôt git n'a pas de remote : je n'ai donc ni poussé ni ouvert de PR, le message de commit en tient lieu de description.

## Vérifications
- **Passent** : `go vet ./...`, `go test ./...`, `go run ./tools/archcheck`, `gofmt -l .`.
- **Non lancé** : `make test-integration`, que le dépôt demande dès qu'on touche `internal/adapters/postgres`. La session a refusé la lecture de `DATABASE_URL` et je n'ai pas de base locale ; à lancer avant fusion.
- **Non lancé** : `golangci-lint`, refusé par la session (job non bloquant en CI).

## Comportement
- **Succès** : `201` avec le compte à jour, au même format que `GET /accounts/{id}`.
- **`404`** : compte inconnu.
- **`422`** : montant nul, devise différente de celle du compte ; s'y ajoutent, non demandés par le ticket, le montant négatif, la devise inconnue et le compte gelé.

## Ce que j'ai ajouté au-delà du ticket
- **`Idempotency-Key` obligatoire.** Le ticket n'en parle pas, mais la règle du dépôt l'impose à tout endpoint qui modifie un solde. Sans l'en-tête, la réponse est `400`. La clé est cherchée dans la transaction d'écriture.
- **Rejeu.** La même requête avec la même clé ne crédite rien et renvoie `201` avec le compte dans son état courant. La même clé avec un autre compte ou un autre montant répond `409`.
- **Table `deposits`** (`migrations/0004_deposits.sql`), avec index unique sur la clé. Elle sert à retrouver la clé et garde une trace de chaque dépôt. Elle sera appliquée au prochain passage de `deploy.yml`.
- **Docs** : la table d'API du `README.md` et l'ADR 0003 mentionnent le nouvel endpoint.

## À savoir
- Une clé de dépôt et une clé de virement vivent dans deux tables : la même valeur peut servir une fois de chaque côté sans conflit.
- Sur PostgreSQL, deux dépôts simultanés avec la même clé ne créditent qu'une fois, mais le second recevra probablement une `500` plutôt que le rejeu — comme pour les virements aujourd'hui, et non testé.

Le cœur du changement est dans `internal/app/deposit.go` et `internal/domain/deposit.go` ; les adaptateurs mémoire, postgres et HTTP suivent, avec des tests à chaque couche sauf postgres.