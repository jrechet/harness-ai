J'ai posé le palier 1 (« Cadré ») sur le dépôt `ledger`. La vérification passe : `harness status` donne le palier 1 avec 5 vérifications sur 5 et aucune référence sans cible. Je n'ai rien commité et je n'ai pas avancé au-delà du palier 1.

## Compte rendu

**Avant et après**
- Avant : palier 0, aucun fichier d'instructions, 0 ligne chargée par session, 0 règle.
- Après : palier 1, environ 26 lignes chargées par session (`AGENTS.md` via `CLAUDE.md`), 3 règles et 3 interdits.

**Fichiers créés** (aucun fichier existant n'a été modifié)
- `AGENTS.md` (26 lignes) : ligne de mode, ce que fait le dépôt, tableau des commandes, règles, interdits.
- `CLAUDE.md` (1 ligne) : `@AGENTS.md`.
- `.github/copilot-instructions.md` (1 ligne) : renvoie à `AGENTS.md`.
- `.harness/state.json` : écrit par `harness status`.
- Pas de stub Cursor : l'équipe n'utilise que Claude Code et Copilot.

**Retiré**
- Rien. Il n'existait aucun fichier d'instructions, ni à la racine ni dans les sous-dossiers.
- `CONTRIBUTING.md` contient des consignes génériques (« Go idiomatique », « fonctions courtes ») qui n'apportent rien à un agent. Je ne les ai pas recopiées et je n'ai pas modifié le fichier.

**Secrets**
- Aucun trouvé. La seule occurrence est `secrets.DATABASE_URL` dans `deploy.yml`, qui fait référence à un secret GitHub : c'est l'usage normal.

**Règles écrites**

| Règle | Statut | Date |
|---|---|---|
| Couches hexagonales, seul `cmd/ledgerd` assemble les adaptateurs | Vérifiée par `tools/archcheck` (job `arch`, bloquant) | [2025-09] |
| Montants en `int64` centimes, aucun flottant dans `domain` ni `app` | Non vérifiée : la règle `forbidigo` vit dans le job `lint`, qui ne bloque pas. Déjà violée par `internal/app/fees.go`, signalé comme contre-exemple. | [2025-09] |
| `Idempotency-Key` obligatoire, et cherchée dans la transaction qui écrit | Non vérifiée : seul le virement est testé. Née de l'incident du double débit (37 comptes). `POST /accounts` est une exception connue. | [2026-04] |
| Interdit : toucher à une base qui n'est pas la sienne (`reset-db` ou `migrate` sur staging/prod) | Né de l'incident du 3 février 2026 : deux jours de données QA perdus | [2026-02] |
| Interdit : modifier une migration déjà appliquée | Pas d'incident connu | [2026-11] |
| Interdit : lancer `deploy.yml` avec `dry_run` à `false` | Pas d'incident connu | [2026-11] |

**Commandes**
- **Confirmées** (exécutées et vertes) : `go vet ./...`, `go test ./...`, `go run ./tools/archcheck`.
- **Non confirmées :**
  - `make lint` / `golangci-lint run` : l'outil est installé, mais son exécution a été refusée par les permissions de la séance. Je n'ai donc pas pu vérifier si `fees.go` déclenche bien `forbidigo`.
  - `make test-integration` : il faut une base migrée, je ne l'ai pas lancé. Il ne tourne pas en CI.
  - `make e2e` : la cible n'existe pas. Le propriétaire confirme qu'elle a été retirée il y a un an, mais le README la cite encore.
  - Quelques commandes de lecture combinées ont aussi été refusées. Je les ai remplacées par des lectures équivalentes, sans perte d'information.

**Questions au propriétaire**
1. Le `float64` de `internal/app/fees.go` est-il une exception assumée ou une violation de l'ADR 0002 à corriger ? Je l'ai posé deux fois et la réponse portait sur autre chose. Défaut appliqué : violation connue, à ne pas imiter.
2. Retire-t-on `make e2e` du README ? Défaut proposé : oui, dans une PR à part.
3. L'ADR 0002 dit que la règle des montants est « vérifiée par le job `lint` », mais ce job tourne en `continue-on-error`. Faut-il rendre bloquante au moins la règle `forbidigo`, par exemple dans un job séparé ? Défaut proposé : oui.
4. Une règle « si tu touches `internal/adapters/postgres`, lance `make test-integration` sur ta base locale » serait utile, mais la commande n'est pas confirmée. Peut-on la valider ? Défaut proposé : elle reste hors du fichier en attendant.
5. Ce que j'ai observé sans pouvoir l'expliquer : `cmd/ledgerd/main.go` appelle `sql.Open("pgx", …)` sans importer de pilote pgx. Le mode PostgreSQL fonctionne-t-il vraiment ?

**Pas suivant possible** : palier 2 (« Bouclé »), avec la section Maintenance, la convention `rule:` en revue et un premier harvest. C'est à vous de le demander avec `harness target`, et à harness-step de le mener.