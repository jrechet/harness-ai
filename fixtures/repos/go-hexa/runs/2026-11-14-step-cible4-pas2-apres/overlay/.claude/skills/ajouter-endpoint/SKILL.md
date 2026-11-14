---
name: ajouter-endpoint
description: Contrat de la tâche déléguée « ajouter un endpoint HTTP à partir d'un cas d'usage », du domaine au handler et à ses tests, jusqu'à la PR. Utiliser quand un ticket demande une nouvelle route de l'API ledger (lecture ou écriture), même s'il ne nomme pas ce contrat.
---

# Ajouter un endpoint, du cas d'usage au test

Tu reçois le ticket entier et tu reviens avec une PR. Personne ne relit en cours de route : ce contrat dit ce qui est attendu, la CI (`test`, `arch`, `migrations`) le tranche. Sources : `docs/adr/0001` (couches), `0002` (centimes), `0003` (idempotence), `docs/postmortems/2026-04-double-debit.md`, `docs/exploitation.md`.

## Avant de commencer
- La route est **nouvelle** : c'est le chemin normal, va au bout. Si le ticket renomme, retire ou change le type d'une route ou d'un champ existant, ou s'il est ambigu sur un montant ou un arrondi : arrête-toi et pose la question (AGENTS.md, « Processus de travail »).
- Décide si la route **modifie un solde** (débit, crédit, frais, annulation…). Si oui, toute la partie « Écriture » ci-dessous s'applique, sans exception.

## Étapes
1. **Domaine** (`internal/domain`), seulement si le ticket apporte une règle métier : fonction pure, aucune dépendance, montants en `domain.Money` (entier en centimes), erreurs typées dans `errors.go`. Test unitaire à côté.
2. **Cas d'usage** (`internal/app/service.go`) : une méthode sur `Service` et, s'il y a des entrées, un `<Nom>Command`. Il ne connaît que les ports de `ports.go`. Les montants entrent en `int64` centimes et passent par `domain.NewMoney`. Aucun `float32`/`float64` : `internal/app/fees.go` viole déjà la règle, ne le prends pas pour modèle.
3. **Ports et adaptateurs**, seulement si un nouveau stockage est nécessaire : l'interface dans `ports.go`, puis son implémentation dans `internal/adapters/memory` **et** `internal/adapters/postgres`. Un adaptateur n'importe jamais un autre adaptateur.
4. **Migration**, seulement si le schéma change : un nouveau fichier `migrations/NNNN_<objet>.sql` au numéro suivant, idempotent (`IF NOT EXISTS`). Jamais de modification d'un fichier existant. Une migration qui supprime ou réécrit des données : arrête-toi et demande.
5. **Handler** (`internal/adapters/httpapi/server.go`) : ajoute la route dans `routes()`, la liste unique. Le handler décode, appelle le cas d'usage, encode ; aucune règle métier. Les montants sortent en `amount_cents` / `*_cents` entiers. Une nouvelle erreur devient un code HTTP dans `writeDomainError`, nulle part ailleurs.
6. **Assemblage** : `cmd/ledgerd` seulement si un nouvel adaptateur est à brancher.

## Écriture : route qui modifie un solde
- Exige l'en-tête `Idempotency-Key` : absent → `app.ErrMissingIdempotencyKey` (400 `idempotency_key_required`). Le garde-fou `idempotency_guard_test.go` le vérifie sur toute route non-GET.
- Cherche la clé **dans** la transaction d'écriture, à l'intérieur de `uow.Do`, jamais avant de l'ouvrir : c'est ce qui a débité 37 comptes deux fois en avril 2026. Modèle : `Service.Transfer`.
- Même clé, même requête → renvoie le premier résultat, sans réécrire. Même clé, autre requête → `app.ErrIdempotencyConflict` (409).
- Une réponse rejouée porte `Idempotency-Replayed: true` : l'application mobile s'en sert pour ne pas afficher deux confirmations. Le cas d'usage dit au handler qu'il s'agit d'un rejeu. (`POST /transfers` ne le fait pas encore : ne le corrige pas dans cette PR, signale-le.)
- Si la clé est stockée dans une nouvelle table : index unique dessus dans la migration, dernier filet (ADR 0003).
- N'ajoute **jamais** d'entrée à `withoutIdempotencyKey` : elle demande l'accord du propriétaire. `POST /accounts` est la seule exemption, ce n'est pas un modèle. Si le ticket demande une écriture sans clé, arrête-toi et demande.

## Tests attendus
- `internal/app/service_test.go`, avec l'adaptateur mémoire : le cas nominal, chaque erreur du domaine, et pour une écriture : clé absente, rejeu (un seul effet sur le solde), conflit.
- `internal/adapters/httpapi/server_test.go` : codes HTTP, corps en centimes, et pour une écriture le rejeu avec l'en-tête `Idempotency-Replayed: true`.
- Si l'adaptateur postgres a changé : un test dans `store_integration_test.go` et `make test-integration` sur **ta** base locale. Ces tests ne tournent pas en CI et le pilote n'est pas encore dans `go.mod` : si tu ne peux pas les lancer, écris-le dans la PR.

## Vérifications avant la PR
```
go vet ./... && go test ./...
go run ./tools/archcheck
go run ./tools/migrationcheck -base origin/main   # si migrations/ a changé
```

## Jamais, même si le ticket semble le demander
- `make migrate` ou `make reset-db` ailleurs que sur ta base locale (`tools/localdb` refuse de toute façon).
- Modifier une migration existante.
- Lancer `deploy.yml`, et a fortiori sans `dry_run` ou vers `production`.

## Fini quand
- `make test` et `make arch` passent (et `migrations` si le schéma change).
- Un test couvre la nouvelle route ; pour une écriture, le rejeu et le conflit sont testés.
- La PR dit pourquoi en deux lignes, puis : route ajoutée, écriture ou lecture, migration ou non, et ce qui n'a pas pu être vérifié (intégration postgres, recherche de la clé dans la transaction, laissée à la revue).
- `lint` rouge ne bloque pas (dette héritée) ; une CI rouge causée par ton diff se corrige, une autre se signale.
