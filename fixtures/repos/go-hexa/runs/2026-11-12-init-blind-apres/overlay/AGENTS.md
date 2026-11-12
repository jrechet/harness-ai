# ledger — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
Service de tenue de comptes (soldes, virements, frais). Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`, bases et déploiement dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code Go | `make test` et `go vet ./...` | job `test`, bloquant |
| des imports entre couches | `make arch` | job `arch`, bloquant |

## Règles
- Tout endpoint d'écriture exige `Idempotency-Key`, et le cas d'usage cherche la clé **dans** la transaction qui écrit, jamais avant de l'ouvrir. Pourquoi : double débit, 37 comptes touchés (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). Vérifiée par : rien pour un nouvel endpoint, seuls les tests de `internal/app` couvrent le virement (non vérifiée) [2026-04]
- Quand un endpoint rejoue une requête déjà traitée, la réponse porte l'en-tête `Idempotency-Replayed: true` ; tout nouvel endpoint d'écriture le pose. Pourquoi : l'application mobile s'en sert pour ne pas afficher deux fois la confirmation (dit par l'équipe). `POST /transfers` ne le fait pas encore (backlog) : ne pas le prendre pour modèle. (non vérifiée) [2026-06]
- Aucun `float32`/`float64` pour un montant dans `internal/domain` ni `internal/app` : `int64` en centimes (`domain.Money`). Pourquoi : arrondis qui faussent un solde (ADR 0002). Le dépôt la viole déjà : `internal/app/fees.go` calcule les frais en `float64`, dette connue, ne pas le recopier. (non vérifiée : la règle `forbidigo` tourne dans le job `lint`, qui ne bloque pas) [2025-09]
- `internal/domain` ne dépend de rien, `internal/app` ne connaît que des ports, les adaptateurs ne se connaissent pas ; seul `cmd/ledgerd` assemble. Pourquoi : ADR 0001. Vérifiée par : `tools/archcheck` (job `arch`) [2025-09]

## Interdits
- Toucher à une base qui n'est pas la sienne : jamais `make reset-db` ni `make migrate` avec un `DATABASE_URL` de staging ou de production. Pourquoi : `reset-db` ne regarde pas la cible ; le 3 février 2026, deux jours de jeux de données QA perdus sur staging (`docs/exploitation.md`). [2026-02]
- Modifier une migration déjà appliquée : on ajoute un fichier `migrations/`, numéro suivant. Pourquoi : décision d'équipe (`docs/exploitation.md`), pas d'incident connu. [2026-11]
- Lancer `deploy.yml` sans `dry_run`. Pourquoi : il applique les migrations et déploie sur staging (partagée avec la QA) ou production ; décision d'équipe, pas d'incident connu. [2026-11]
