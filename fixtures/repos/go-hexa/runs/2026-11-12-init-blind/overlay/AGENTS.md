# ledger — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
Service de tenue de comptes (soldes, virements, frais). Les décisions sont dans `docs/adr/`, les incidents dans `docs/postmortems/`, les bases et le déploiement dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code Go | `go vet ./... && go test ./...` | job `test` (bloque) |
| des imports entre `domain`, `app`, `adapters` | `make arch` | job `arch` (bloque) |
| `internal/adapters/postgres` | rien de lancé ici : ses tests d'intégration demandent une base à toi | rien, hors CI |

Le job `lint` (golangci-lint) tourne mais ne bloque pas (`continue-on-error`) : une règle « vérifiée par le lint » ne l'est pas.

## Règles
- Tout endpoint qui modifie un solde exige l'en-tête `Idempotency-Key` ; le cas d'usage cherche la clé **dans** la transaction d'écriture ; rejouer la même requête renvoie le premier résultat, la même clé avec une autre requête répond 409. Pourquoi : incident du 14 avril 2026, 37 comptes débités deux fois (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). `POST /accounts` ne l'applique pas (au backlog) : ce n'est pas un modèle. (non vérifiée) [2026-04]
- Tout nouvel endpoint d'écriture répond avec l'en-tête `Idempotency-Replayed: true` quand il rejoue une requête déjà traitée. Pourquoi : l'application mobile s'en sert pour ne pas afficher deux fois la confirmation. `POST /transfers` ne le fait pas encore (au backlog) : ne le copie pas sur ce point. (non vérifiée) [2026-06]
- Un montant est un `domain.Money` en centimes (`int64`), jamais un `float32`/`float64` dans `internal/domain` ni `internal/app` ; l'API expose `amount_cents`. Pourquoi : arrondis qui faussent un solde d'un centime (ADR 0002). `internal/app/fees.go` utilise déjà `float64` : ce n'est pas un modèle. (non vérifiée : la règle `forbidigo` est dans le lint, qui ne bloque pas) [2025-09]
- `domain` ne dépend de rien, `app` ne connaît que des ports, les adaptateurs ne se connaissent pas ; seul `cmd/ledgerd` les assemble. Pourquoi : le prototype mêlait SQL et règles dans les handlers (ADR 0001). Vérifiée par : `tools/archcheck` [2025-09]

## Interdits
- Ne jamais lancer `make reset-db`, `make migrate` ni `psql` avec un `DATABASE_URL` qui n'est pas ta propre base locale. Vérifie la variable avant. Pourquoi : le 3 février 2026, `reset-db` lancé avec l'URL de staging restée dans un terminal a effacé deux jours de jeux de données QA ; la cible ne regarde pas quelle base elle vide. [2026-02]
- Ne jamais modifier un fichier existant de `migrations/` : une migration appliquée ne change plus, on ajoute le numéro suivant. Pourquoi : staging et production l'ont déjà jouée (`docs/exploitation.md`). [2026-11]
- Ne jamais lancer `deploy.yml` avec `dry_run` à `false`. Pourquoi : il applique les migrations puis déploie sur staging ou production. [2026-11]
