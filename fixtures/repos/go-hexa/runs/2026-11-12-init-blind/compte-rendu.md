J'ai écrit un `AGENTS.md` de 26 lignes, avec les stubs pour Claude Code et Copilot. Le contrôle `harness status` passe : palier 1 atteint, cinq vérifications sur cinq, aucune référence sans cible. Rien n'est commité.

Trois commandes ont été refusées automatiquement, car cette séance ne peut pas demander d'autorisation : `make lint`, `make e2e` et une vérification du code retour de `archcheck`. Ce qu'elles auraient confirmé figure plus bas, dans « non confirmées ».

## Compte rendu

**Avant → après**
| | Avant | Après |
|---|---|---|
| Palier | 0 · Rien | 1 · Cadré (5/5) |
| Lignes chargées par session | 0 | 26 (`AGENTS.md` via le stub `CLAUDE.md`) |
| Règles | 0 | 4 règles et 3 interdits |

**Fichiers créés**
- `AGENTS.md` : 26 lignes
- `CLAUDE.md` : 1 ligne, `@AGENTS.md`
- `.github/copilot-instructions.md` : 1 ligne, renvoie à `AGENTS.md`
- `.harness/state.json` : écrit par le CLI
- Pas de règles Cursor, l'outil n'est pas utilisé.

**Retiré** : rien. Il n'existait aucun fichier d'instructions pour agents (`AGENTS.md`, `CLAUDE.md`, Copilot, Cursor), ni à la racine ni dans un sous-dossier. Je n'ai rien repris de `CONTRIBUTING.md` : ses lignes sont soit génériques (« Go idiomatique », « fonctions courtes »), soit découvrables. Je ne l'ai pas modifié.

**Secrets** : aucun trouvé. `deploy.yml` lit `DATABASE_URL` depuis les secrets GitHub, ce qui est correct.

**Règles écrites**
| Règle | Statut | Date |
|---|---|---|
| `Idempotency-Key` exigée, cherchée dans la transaction ; un rejeu renvoie le premier résultat, une même clé avec une autre requête donne 409. `POST /accounts` est signalé comme contre-exemple. | non vérifiée : l'ADR 0003 dit elle-même que rien ne contrôle un nouvel endpoint | [2026-04] |
| Tout nouvel endpoint d'écriture renvoie `Idempotency-Replayed: true` quand il rejoue une requête. `POST /transfers` est signalé comme contre-exemple. | non vérifiée | [2026-06] |
| Montants en centimes, aucun flottant dans `domain` ni `app`. `internal/app/fees.go:18` est signalé comme contre-exemple. | non vérifiée : l'ADR 0002 dit « vérifiée par le lint », mais ce job est en `continue-on-error` | [2025-09] |
| Pas de dépendance interdite entre les couches (ADR 0001) | Vérifiée par : `tools/archcheck`, job `arch` qui bloque | [2025-09] |
| **Interdit** : `reset-db`, `migrate` ou `psql` sur une base qui n'est pas la sienne (incident du 3 février 2026) | — | [2026-02] |
| **Interdit** : modifier un fichier existant de `migrations/` | — | [2026-11], la note d'exploitation n'est pas datée |
| **Interdit** : lancer `deploy.yml` sans `dry_run` | — | [2026-11] |

**Commandes**
- Confirmées : `go vet ./...`, `go test ./...` (tout est vert) et `make arch` (aucune violation affichée).
- Non confirmées :
  - `make lint` : refusé dans cette séance.
  - `make test-integration` : demande une base PostgreSQL migrée, je ne l'ai pas lancée.
  - `make e2e` : la cible n'existe pas dans le `Makefile`, comme vous l'aviez dit.

**Questions au propriétaire** (avec le défaut proposé)
1. `internal/app/fees.go:18` calcule les frais avec `float64(...) * 0.015`, ce que l'ADR 0002 interdit. Le lint aurait dû le signaler, mais il ne bloque pas. Faut-il corriger le calcul en entiers ? Défaut : ouvrir un ticket, et laisser le fichier tel quel jusque-là.
2. J'ai interdit de modifier **tout** fichier existant de `migrations/`, sans distinguer ceux déjà appliqués. Est-ce que ça vous va ? Défaut : oui, l'agent ne peut pas savoir lesquels sont appliqués.
3. Le README cite encore `make e2e`. Faut-il retirer cette ligne ? Défaut : oui, dans une PR à part.
4. Le règle `forbidigo` (`^float(32|64)$`) attrape-t-elle vraiment une conversion comme `float64(x)` ? Je n'ai pas pu lancer le lint pour le voir. Défaut : le vérifier en même temps que la question 1.

**Pas suivant possible** : le palier 3 (Vérifié). Il s'agit de rendre le lint bloquant sur `internal/domain` et `internal/app`, et d'ajouter un test qui oblige tout endpoint d'écriture à exiger la clé d'idempotence et l'en-tête `Idempotency-Replayed`. C'est à vous de le demander (`harness target`), et harness-step le mènera.