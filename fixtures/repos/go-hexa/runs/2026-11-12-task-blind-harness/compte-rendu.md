J'ai ajouté `POST /accounts/{id}/deposits`. Le travail est commité sur la branche `feat/deposits` (commit `26e1322`), mais la PR n'est pas ouverte : le dépôt n'a pas de remote. La description est prête dans `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-pmdl8sbf-repo/067a1b55-9cfd-4d50-b43b-0d9dfcd18e98/scratchpad/PR.md`.

`go vet ./...`, `go test ./...` et `go run ./tools/archcheck` passent. **Les tests d'intégration Postgres (`make test-integration`), eux, n'ont pas été lancés.**

## Comportement
- **Succès :** `201` avec le compte à jour, au même format que `GET /accounts/{id}`. Un test vérifie que les deux réponses sont identiques.
- **Compte inconnu :** `404`.
- **Montant nul (ou absent), ou devise différente de celle du compte :** `422`. C'est aussi le cas pour un montant négatif, une devise inconnue ou un compte gelé.

## Ajouté par rapport au ticket
Les règles du dépôt (AGENTS.md et ADR 0003) imposent ces points à tout endpoint qui modifie un solde :
- **Clé d'idempotence obligatoire.** Sans en-tête `Idempotency-Key`, la requête répond `400`. La clé est cherchée dans la transaction d'écriture, comme pour les virements. La même clé avec un autre compte ou un autre montant répond `409`.
- **Rejeu signalé.** Une requête rejouée répond `201` avec `Idempotency-Replayed: true` et ne recrédite pas le compte.
- **Nouvelle migration `migrations/0004_deposits.sql`.** Elle crée la table `deposits` avec un index unique sur la clé, comme le fait `0003` pour les virements. Aucune migration existante n'est modifiée.

Le code se répartit ainsi : `internal/domain/deposit.go`, le port et le cas d'usage dans `internal/app` (`deposit.go`), les adaptateurs memory, postgres et HTTP, avec des tests à chaque couche. J'ai aussi mis à jour la table de l'API du README et la section « Portée » de l'ADR 0003.

## Ce qui n'a pas été vérifié
- **Tests Postgres :** la session a refusé toutes les commandes qui inspectent l'environnement, donc je n'ai pas pu trouver de base locale. J'ai écrit `TestDepositRoundTrip` (aller-retour du dépôt, plus refus d'une clé en double par la base). Je l'ai seulement compilé (`go vet -tags integration`), pas exécuté. Il faut le lancer sur ta base locale avant une mise en production.
- **Problème existant, sans lien avec ce changement :** aucun pilote `pgx` n'est importé dans le module. `sql.Open("pgx", …)` échouera donc, en intégration comme dans `cmd/ledgerd`, tant que ce n'est pas corrigé.

## Deux choix à valider en revue
- **Réponse d'un rejeu :** elle renvoie le compte tel qu'il est maintenant, pas tel qu'il était juste après le premier dépôt.
- **Espaces de clés :** les clés des dépôts et des virements sont séparées. Une même clé peut donc servir une fois pour un virement et une fois pour un dépôt.

Je n'ai lancé ni `make migrate`, ni `make reset-db`, ni `deploy.yml`.