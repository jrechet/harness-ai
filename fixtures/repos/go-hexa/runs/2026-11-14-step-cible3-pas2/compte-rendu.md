## Compte rendu

**Le pas** : la règle « une migration appliquée ne se modifie plus » (et l'interdit qui va avec) est maintenant vérifiée par un outil, `tools/migrationcheck`, lancé dans un nouveau job CI bloquant `migrations`. Elle ne repose plus sur le texte.

**Avant et après**
- Palier atteint : 1 avant, 1 après. Le palier visé reste le 3.
- Palier 3 : **2/4 → 3/4**.
- Ligne qui a basculé : `[ ] → [x] Au moins 50 % des règles sont « Vérifiée par » un outil`. Selon `harness rules`, 2 règles sur 8 avaient un garde-fou, il y en a maintenant 4 sur 8.

**Ce que ça change pour l'agent** : s'il modifie, renomme ou supprime un fichier existant de `migrations/` dans une PR, la CI devient rouge et lui dit d'ajouter un fichier au numéro suivant. Ajouter une migration reste autorisé.

**Ce qui n'est pas prouvé**
- J'ai vu le garde-fou rouge sur une vraie violation, en local, dans un clone jetable : une modification de `0002_transfers.sql` a donné `exit 1`. Il est ensuite passé au vert sur un simple ajout de `0004_…`, puis sur le dépôt réel. Je n'ai pas modifié de migration du dépôt, puisque c'est interdit.
- **Je ne l'ai pas encore vu tourner en CI.** Il faut une PR pour le voir rouge ou vert sur GitHub, et que le job soit fusionné sur `main` pour qu'il protège quelque chose.
- Le job ne tourne que sur les `pull_request`. Un push direct sur `main` lui échappe.
- `status` mesure seulement la forme : rien ne montre encore que les agents travaillent mieux. Cette preuve viendra des PR d'agent observées par harness-harvest.

**Fichiers** (rien n'est commité)
- `tools/migrationcheck/main.go` et `main_test.go` (nouveaux) ;
- `.github/workflows/ci.yml` (job `migrations`, `fetch-depth: 0`) ;
- `AGENTS.md` : les lignes 20 et 25 se terminent par « Vérifiée par » au lieu de « (non vérifiée) », et le tableau a une ligne `migrations/`.

`go vet ./...`, `go test ./...` et `archcheck` passent.

**Hors périmètre, noté sans y toucher**
1. `deploy/apply.sh` et `make migrate` rejouent **toutes** les migrations à chaque fois, sans table de suivi. Ça ne tient que si chaque migration peut être rejouée sans dommage (`IF NOT EXISTS`).
2. `internal/app/fees.go` utilise des flottants, contre l'ADR 0002, et le job `lint` est en `continue-on-error`, donc il ne bloque pas.
3. `POST /transfers` n'envoie pas encore `Idempotency-Replayed`.

**Blocages de la séance** : le bac à sable a refusé les commandes shell composées, `cp` et l'exécution d'un binaire hors du dépôt. Pour contourner, j'ai ajouté à l'outil une option `-repo`, qu'il passe à `git -C`, et je l'ai lancé avec `go run` sur le clone.

**Questions** : aucune.

**Le pas suivant possible** (dans l'objectif, palier 3) : lancer harness-audit, écrire son JSON dans `.harness/audit.json`, puis traiter les P1 qu'il trouve.