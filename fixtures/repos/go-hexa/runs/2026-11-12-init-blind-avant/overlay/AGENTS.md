# ledger — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
Service de tenue de comptes (soldes, virements, frais). Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`, environnements et bases dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du Go | `go vet ./... && go test ./...` | job `test` (bloquant) |
| un import entre paquets | `go run ./tools/archcheck` | job `arch` (bloquant) |

Le job `lint` tourne mais ne bloque pas (`continue-on-error`, avertissements hérités) : un lint vert ne prouve rien.

## Règles
- `internal/domain` ne dépend de rien, `internal/app` ne connaît que des ports, les adaptateurs ne se connaissent pas ; seul `cmd/ledgerd` assemble. Pourquoi : ADR 0001, le prototype mêlait SQL et règles de solde dans les handlers. Vérifiée par : `tools/archcheck` [2025-09]
- Un montant est un `domain.Money` (`int64` en centimes) ; aucun `float32`/`float64` dans `internal/domain` ni `internal/app`, et l'API n'expose que des `*_cents`. Pourquoi : ADR 0002, les arrondis flottants faussent un solde d'un centime. (non vérifiée : la règle `forbidigo` est dans le job `lint`, non bloquant) [2025-09]. Déjà violée par `internal/app/fees.go` (`float64` pour les frais) : ne pas le prendre pour modèle.
- Tout endpoint qui modifie un solde exige l'en-tête `Idempotency-Key`, et la clé est cherchée **dans** la transaction qui écrit, jamais avant de l'ouvrir. Pourquoi : incident du 14 avril 2026, 37 comptes débités deux fois (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). (non vérifiée : seuls les tests du virement la couvrent ; rien ne contrôle un nouvel endpoint) [2026-04]. `POST /accounts` n'applique pas la clé : exception connue, reprise au backlog, ne pas la copier.

## Interdits
- Ne jamais toucher à une base qui n'est pas la tienne : pas de `DATABASE_URL` vers `ledger_staging` (partagée avec la QA) ni `ledger_prod`, et jamais `make reset-db` ni `make migrate` sur ces bases. Pourquoi : le 3 février 2026, `make reset-db` lancé avec l'URL de staging restée dans un terminal a effacé deux jours de jeux de données QA. [2026-02]
- Ne jamais modifier une migration de `migrations/` déjà appliquée : on ajoute un fichier, numéro suivant. Pourquoi : staging et production l'ont déjà jouée ; pas d'incident connu. [2026-11]
- Ne jamais lancer `.github/workflows/deploy.yml` avec `dry_run` à `false`. Pourquoi : sans `dry_run`, le workflow applique les migrations et déploie ; pas d'incident connu. [2026-11]
