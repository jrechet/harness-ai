J'ai ajouté `POST /accounts/{id}/deposits`, commité sur la branche `feat/deposits` (commit `c484a21`). Je n'ai pas pu ouvrir la PR : le dépôt n'a aucun remote. Sa description est prête dans `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-2dg3pyrr-repo/c56e8c34-8c82-45d4-826a-93be6f608dbe/scratchpad/PR.md`.

`go vet ./...`, `go test ./...` et `make arch` passent. Le nouveau SQL et la migration n'ont pas été testés contre PostgreSQL : `make test-integration` demande une base locale, et je n'ai lancé aucune commande sur une base.

**Comportement**
- **Succès :** `201` avec le compte, au même format que `GET /accounts/{id}`.
- **Erreurs demandées :** `404` si le compte est inconnu, `422` si le montant est nul ou si la devise n'est pas celle du compte.
- **Autres `422` :** montant négatif, devise inconnue, compte gelé.

**En plus de ce que tu as demandé** : un dépôt modifie un solde, donc j'ai appliqué les règles d'`AGENTS.md`.
- **Clé obligatoire :** l'en-tête `Idempotency-Key` est exigé, sinon `400`. La clé est cherchée dans la même transaction que l'écriture.
- **Rejeu de la même requête :** la réponse est identique à la première, avec l'en-tête `Idempotency-Replayed: true`, et le compte n'est pas crédité une seconde fois.
- **Même clé, autre requête :** `409`. Je vérifie ce cas avant de charger le compte, donc une clé réutilisée sur un compte inconnu donne `409` et non `404`.

**Fichiers**
- **Logique :** le dépôt et ses contrôles sont dans `domain` ; le cas d'usage `Service.Deposit` et le nouveau port de stockage sont dans `app`.
- **Stockage :** les adaptateurs mémoire et PostgreSQL enregistrent les dépôts.
- **HTTP :** la route est ajoutée dans `httpapi`.
- **Migration :** nouvelle `migrations/0004_deposits.sql` (table `deposits` et index unique sur la clé). Aucune migration existante n'a été modifiée.
- **Docs :** j'ai ajouté le nouvel endpoint au tableau de l'API du README et à la liste de l'ADR 0003.
- **Tests :** domaine, cas d'usage et HTTP.

**Choix à valider en relecture**
- **Rejeu et solde :** chaque dépôt enregistre le solde obtenu juste après lui. Un rejeu renvoie donc ce solde-là, même si d'autres opérations l'ont changé depuis. C'est ma lecture de « renvoie le premier résultat ».
- **Clés indépendantes :** une clé déjà utilisée par un virement ne bloque pas un dépôt, car les deux ont des tables séparées.
- **Requêtes simultanées :** si deux requêtes avec la même clé arrivent en même temps sur PostgreSQL, la seconde reçoit `500` au lieu d'un rejeu. `POST /transfers` se comporte déjà ainsi.

**À faire avant la mise en production** : lancer `make test-integration` sur une base locale migrée, comme le prévoit `docs/exploitation.md`.