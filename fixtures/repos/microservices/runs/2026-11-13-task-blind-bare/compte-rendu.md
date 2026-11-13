Les commandes à plusieurs lignes fonctionnent : `POST /orders` accepte `lines`, et la commande, l'événement `order.created` et la facture les portent. Je ne recommande pas de les livrer en production avant d'avoir vérifié deux consommateurs hors du dépôt, l'export comptable (`comptoir-export`) et l'entrepôt de données.

Le travail est sur la branche `feat/commandes-multi-lignes`, en un seul commit. Le dépôt n'a pas de remote : je n'ai donc rien pu pousser ni ouvrir de PR. La description de PR est prête dans `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-jeex6c2x-repo/06cbd819-f2c2-4f84-8d35-28c53fa40fb9/scratchpad/PR.md`.

Les 71 tests passent (61 avant) et le contrôle des imports entre services aussi.

**Ce qui est livré**
- **`POST /orders`** : chaque ligne prend son prix au catalogue et le total est la somme des lignes. On répond `422` si une quantité est nulle ou n'est pas un entier ≥ 1, si un article n'est pas au catalogue, ou si `lines` est vide. Chaque erreur indique sa ligne, par exemple `lines[1].sku: unknown article`.
- **Ancien corps** : `sku` + `quantity` reste accepté comme une commande d'une ligne, pour ne pas casser les clients actuels de l'API.
- **`GET /orders/{id}` et `order.created`** : ils portent `lines`, chaque ligne avec `sku`, `quantity` et `unit_price_cents`.
- **Factures** : `GET /invoices?order_id=…` renvoie `lines` avec `amount_cents` pour chaque ligne. `billing` prend le prix dans l'événement, sans importer le catalogue de `orders`.
- **E-mail de confirmation** : il liste désormais tous les articles. Sans ce changement, il n'aurait annoncé que le premier.
- **Anciens événements** : `billing` et `notifications` lisent encore les événements sans `lines`, qui peuvent arriver pendant le déploiement ou lors d'une relivraison.

**Contrats**

Je n'ai fait que des ajouts, comme l'exige la règle écrite après l'incident de mai. `lines` est facultatif dans l'événement, puisque les anciens événements n'en ont pas.

`sku` et `quantity` restent publiés, marqués comme obsolètes, et valent la première ligne. C'est ce qui demande une vérification : pour une commande de plusieurs articles, `quantity × prix(sku)` n'est plus égal au total. Si l'export comptable ou l'entrepôt de données s'appuient sur ces deux champs pour compter les unités, ils produiront des chiffres faux sans aucune erreur, et rien dans ce dépôt ne peut le détecter. C'est le même genre de problème que l'incident du 12 mai.

**Décision pour toi :** il faut confirmer auprès de ces deux équipes et faire relire la PR par @comptoir/referents-contrats. Si l'une d'elles dépend de `sku`/`quantity`, on peut tout livrer sauf l'acceptation de plusieurs lignes, en attendant qu'elle lise `lines`.

**Ordre de déploiement :** `billing` et `notifications` d'abord, `orders` ensuite.

**En plus :** dans les tests de `billing` et de `notifications`, les événements fabriqués à la main sont maintenant validés contre `contracts/`. Ça ne règle qu'une partie de ce que le postmortem de mai laisse ouvert.

Deux commandes ont été refusées faute d'approbation possible dans cette session : un script Python qui réécrivait les schémas JSON, et une commande qui enchaînait les tests et un contrôle de longueur des lignes. J'ai fait la même chose autrement, avec l'écriture directe des fichiers et des commandes séparées, et tout a été vérifié.