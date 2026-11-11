`POST /accounts/{id}/deposits` est en place, commité sur la branche `feat/account-deposits` (un commit, `116821d`). Le dépôt n'a pas de remote, donc rien n'est poussé et aucune PR n'est ouverte.

**Vérifications :** `go vet`, `go test ./...` et `make arch` passent. Deux choses n'ont pas tourné :
- **Lint :** `make lint` a été refusé par le bac à sable de la session.
- **Postgres :** l'adaptateur SQL et la migration `0004` n'ont été exécutés contre aucune base. Le test d'intégration que j'ai ajouté compile, sans plus ; il reste à lancer `make test-integration` avant mise en production, comme le demande `docs/exploitation.md`.

## Comportement

- **Succès :** `201` avec le compte à jour, au même format que `GET /accounts/{id}`.
- **Compte inconnu :** `404`.
- **Rejets en `422` :** montant nul, absent ou négatif, devise différente de celle du compte ou inconnue, compte gelé.
- **Corps illisible :** `400`, y compris un `amount_cents` à virgule.

## Un écart par rapport à ta spec : `Idempotency-Key` est obligatoire

L'ADR 0003 l'impose à tout endpoint qui modifie un solde, suite au double débit d'avril. Je l'ai donc appliqué au dépôt, comme pour `POST /transfers` :
- sans l'en-tête : `400` ;
- même clé rejouée avec la même requête : `201` avec le compte, sans créditer une seconde fois ;
- même clé avec un autre compte ou un autre montant : `409`.

Un client qui suit ta spec à la lettre, sans en-tête, recevra donc `400`. Si tu veux l'endpoint sans clé, c'est un petit retrait, mais il contredit l'ADR.

## Ce que ça a entraîné

- **Nouvelle table `deposits`** (`migrations/0004_deposits.sql`), avec clé d'idempotence unique en base. Elle sera appliquée par `deploy.yml` au prochain déploiement.
- **Garde anti-débordement dans `Money.Add`** : un dépôt qui ferait dépasser `int64` au solde est refusé en `422`. Je l'ai ajoutée parce qu'un solde peut désormais grossir depuis une entrée externe.
- **Docs :** table d'API du README et portée de l'ADR 0003 mises à jour.

## À savoir

Deux dépôts concurrents portant la même clé sur Postgres : le second échouera en `500` (violation d'unicité ou échec de sérialisation) plutôt que de rejouer proprement. Le solde reste juste, et les virements se comportent déjà ainsi ; je n'y ai pas touché.