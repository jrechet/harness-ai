---
name: ajouter-endpoint
description: Ajouter un endpoint HTTP à ledger à partir d'un cas d'usage, du handler jusqu'au test. Utiliser quand un ticket demande une nouvelle route (lecture ou écriture) dans internal/adapters/httpapi.
---

# Ajouter un endpoint

Le ticket donne le cas d'usage. Ce contrat dit dans quel ordre on le pose et ce qui le rend fini. Les règles générales sont dans `AGENTS.md` ; ici, seulement ce qui est propre à cette tâche.

## Avant d'écrire : s'arrêter et demander si…
- le ticket ne fixe pas la forme de l'API (méthode, chemin, corps, réponse, codes d'erreur) : un nouvel endpoint **est** un changement de contrat d'API ;
- il faut une table ou une colonne : c'est une migration ;
- le ticket est ambigu sur un montant, une devise ou un arrondi.

## Étapes, de l'intérieur vers l'extérieur (ADR 0001)
1. **Domaine** (`internal/domain`), si une règle métier est nouvelle : une fonction pure, testée dans `*_test.go` à côté. Aucun import hors bibliothèque standard.
2. **Cas d'usage** (`internal/app/service.go`) : une méthode de `Service` qui ne parle qu'aux ports de `ports.go`. Un montant est un `domain.Money` construit avec `domain.NewMoney` ; aucun flottant (ADR 0002). `internal/app/fees.go` viole déjà cette règle : ne pas le copier.
3. **Si l'endpoint modifie un solde** (ADR 0003, postmortem 2026-04) :
   - la commande porte `IdempotencyKey` ; vide → `ErrMissingIdempotencyKey` ;
   - la recherche de la clé se fait **dans** le `uow.Do` qui écrit, jamais avant : prendre `Transfer` pour modèle, pas `OpenAccount` ;
   - rejouer la même requête renvoie le premier résultat, avec l'en-tête `Idempotency-Replayed: true` ; même clé, autre requête → `ErrIdempotencyConflict` (409).
   - Ne jamais ajouter de route à `withoutIdempotencyKey` dans `idempotency_guard_test.go` : c'est l'accord du propriétaire.
4. **Port nouveau ou étendu** : l'implémenter dans `internal/adapters/memory` **et** `internal/adapters/postgres`. Les adaptateurs ne s'importent pas entre eux.
5. **Handler** (`internal/adapters/httpapi/server.go`) : ajouter la route à `routes()` (c'est la liste que le garde-fou parcourt), décoder le corps, appeler le cas d'usage. Les montants s'exposent en `amount_cents` (entier). Une erreur devient un code HTTP **uniquement** dans `writeDomainError` : y ajouter le cas si l'erreur est nouvelle.

## Tests attendus
- Cas d'usage : `internal/app/service_test.go`, avec l'adaptateur mémoire, pas de base.
- Handler : `internal/adapters/httpapi/server_test.go`, avec `newServer(t)` : le cas nominal et chaque erreur ajoutée à `writeDomainError`.
- Endpoint d'écriture : sans clé → 400 (vérifié automatiquement par `TestWriteRoutesRequireIdempotencyKey` dès que la route est dans `routes()`), rejeu → même résultat et `Idempotency-Replayed: true`, même clé et autre corps → 409.
- Si `internal/adapters/postgres` a changé : `make test-integration` sur ta base locale (rien ne le lance en CI). Si tu n'as pas pu le lancer, la PR le dit.

## Fini quand
- `make test` et `make arch` passent ;
- les tests ci-dessus existent pour ce qui a été ajouté ;
- la PR dit pourquoi en deux lignes, et liste ce qui n'a pas été vérifié (intégration postgres, choix tranchés sans le ticket).
