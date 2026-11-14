La route `POST /accounts/{id}/deposits` est en place, avec ses tests, et le commit est sur la branche `feat/deposits`. Le dépôt n'a pas de remote, donc je n'ai pas pu ouvrir la PR. J'ai rédigé sa description ici : `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-vgfg-stg-repo/7e48af30-7fc9-4d36-8c36-d8e762a022f9/scratchpad/PR.md`.

`go vet ./...`, `go test ./...`, `archcheck` et `migrationcheck -base main` passent tous les quatre. Le test qui exige `Idempotency-Key` sur toute route d'écriture couvre aussi la nouvelle route. Je n'ai lancé `migrationcheck` que sur les fichiers indexés, avant le commit.

**Comportement de la route**
- **Succès** : `201` avec le compte à jour. Un test vérifie que la réponse est identique à celle de `GET /accounts/{id}`.
- **Erreurs** :
  - `404` si le compte n'existe pas.
  - `422` pour un montant nul ou négatif, une devise inconnue ou différente de celle du compte, ou un compte gelé.
  - `400` sans `Idempotency-Key`.
  - `409` si la même clé est réutilisée pour un autre compte ou un autre montant.
- **Requête rejouée** : la même clé avec la même requête ne crédite pas une seconde fois. La réponse est un `201` avec l'en-tête `Idempotency-Replayed: true`.
- **Clé d'idempotence** : elle est cherchée dans la même transaction que l'écriture, sur le modèle de `Service.Transfer`.

**Ce que j'ai ajouté**
- Dans le domaine, `domain.Deposit` et la fonction `domain.Receive`, qui fait les contrôles avant de créditer.
- Le cas d'usage `Service.Deposit`.
- Un nouveau port `DepositRepository`, implémenté pour la mémoire et pour Postgres.
- La migration `migrations/0004_deposits.sql` : une nouvelle table `deposits` avec un index unique sur la clé. Aucune migration existante n'est modifiée.

**Choix faits sans que le ticket les tranche** (expliqués dans la PR)
- Une requête rejouée renvoie le compte **tel qu'il est maintenant**, pas tel qu'il était juste après le premier crédit.
- Les clés des dépôts et des virements sont stockées séparément. Une même clé peut donc servir une fois pour un virement et une fois pour un dépôt.
- Un compte gelé est refusé en `422`, comme pour un virement.

**Ce que je n'ai pas pu vérifier**
- Le test d'intégration Postgres `TestDepositRoundTrip` compile mais n'a pas tourné. Il n'y a pas de base locale ici, et le pilote `pgx` n'est pas dans `go.mod`.
- Que la clé soit bien cherchée dans la transaction reste à vérifier en revue : le test automatique ne contrôle que la présence de la clé.
- `POST /transfers` n'envoie toujours pas `Idempotency-Replayed`. Je n'y ai pas touché, comme demandé.
- Un dépôt très élevé sur un gros solde peut dépasser la capacité d'un `int64` dans `Money.Add`. Le problème existait déjà, mais cette route le rend atteignable depuis l'extérieur. Je propose de le traiter dans un ticket séparé.

Deux commandes ont été refusées automatiquement : un heredoc et une commande contenant `$?`. Je les ai remplacées par des éditions directes des fichiers et par des commandes séparées. Rien n'a été sauté.