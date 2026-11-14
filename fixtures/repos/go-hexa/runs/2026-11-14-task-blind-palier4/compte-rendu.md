Je m'arrête avant d'écrire du code : ce ticket demande une migration, et `AGENTS.md` (comme le skill `ajouter-endpoint`) impose de demander avant d'en toucher une. Je n'ai rien modifié dans le dépôt.

## Pourquoi il faut une migration

Un dépôt modifie un solde, donc la règle d'idempotence s'applique (ADR 0003, postmortem 2026-04). Concrètement :

- l'en-tête `Idempotency-Key` est obligatoire, et la clé est cherchée dans le `uow.Do` qui écrit ;
- rejouer la même requête renvoie le premier résultat, avec `Idempotency-Replayed: true` ;
- la même clé avec un autre corps répond `409`.

Pour retrouver une clé, chaque dépôt doit être enregistré. Aucune table ne convient aujourd'hui : `transfers.from_account` est `NOT NULL REFERENCES accounts`, et un dépôt n'a pas de compte source. Passer par un faux compte « externe » ne marche pas non plus, car la contrainte `balance_cents >= 0` l'empêcherait d'être débité.

Je ne vois pas de façon propre d'éviter la migration, et sans enregistrement la règle d'idempotence ne peut pas être respectée.

## Ce que je propose

**Migration `migrations/0004_deposits.sql`** (nouveau fichier, aucun fichier existant modifié) :
```sql
CREATE TABLE IF NOT EXISTS deposits (
    id              TEXT        PRIMARY KEY,
    account_id      TEXT        NOT NULL REFERENCES accounts (id),
    amount_cents    BIGINT      NOT NULL CHECK (amount_cents > 0),
    currency        CHAR(3)     NOT NULL,
    idempotency_key TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS deposits_idempotency_key_uniq ON deposits (idempotency_key);
```

**Le reste, sur le modèle de `Transfer`** :
- **Domaine** : `domain.Deposit` et une fonction pure qui vérifie le montant non nul, la même devise que le compte et un compte non gelé, puis appelle `Credit`.
- **Port** : un `DepositRepository` (`FindByIdempotencyKey`, `Save`) dans `Tx`, implémenté dans `memory` et dans `postgres`.
- **Cas d'usage** : `Service.Deposit`, qui renvoie le compte à jour et indique s'il s'agit d'un rejeu.
- **Handler** : la route `POST /accounts/{id}/deposits` ajoutée à `routes()`. Rien dans `withoutIdempotencyKey`.
- **Tests** : domaine, cas d'usage et handler (`201`, `404`, `422` pour un montant nul ou une devise différente, `400` sans clé, rejeu avec l'en-tête, `409`).

## Points à confirmer avec la migration

1. **La table `deposits` ci-dessus vous convient-elle ?** L'autre option est une table générique de mouvements, ce qui serait un choix plus large.
2. **Le corps renvoyé lors d'un rejeu.** Je propose le compte tel qu'il était juste après le premier dépôt, ce qui colle à « rejouer renvoie le premier résultat ». L'autre option est le compte dans son état actuel, ce qui est plus simple mais ne donne pas le même corps à chaque rejeu.
3. **Les cas que le ticket ne mentionne pas**, que je tranche ainsi sauf avis contraire :
   - un montant négatif répond `422`, comme le fait déjà `NewMoney` ;
   - une devise inconnue répond `422` ;
   - un compte gelé répond `422`, comme pour un virement.

Je ne pourrai pas lancer `make test-integration` (pas de base locale ici), donc la PR dira que l'adaptateur postgres n'a pas été testé contre une vraie base. Dès que vous validez la migration et le point 2, je fais la PR.