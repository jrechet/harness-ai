Les commandes à plusieurs articles fonctionnent sur la branche `feat/commande-multi-articles`, en un seul commit. Je n'ai pas pu ouvrir la PR : le dépôt n'a pas de remote. La description est prête dans `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-5zcs3r0r-repo/bf9f4bbd-bf26-4f65-b643-39d922996d75/scratchpad/PR.md`.

**Un point à trancher avant d'ouvrir les commandes à plusieurs lignes aux clients.** Les anciens champs `sku` et `quantity` restent publiés, comme l'exige la règle des contrats. Mais pour une commande de plusieurs lignes, ils ne décrivent que la première ligne. Un lecteur hors dépôt qui ne lit que ces deux champs (entrepôt, `comptoir-export`) verra une commande incomplète, sans aucune erreur. Pour l'entrepôt, cela peut vouloir dire des articles jamais expédiés. Je propose de prévenir ces équipes et d'attendre leur accord. Les commandes d'un seul article restent exactes.

Les tests passent (73), ainsi que `tools/check_imports.py`. Je n'ai touché à aucun garde-fou (`tools/`, `shared/`, `deliveries`).

**Ce qui marche maintenant :**
- **Création de commande :** `POST /orders` accepte `lines`, avec au moins une ligne. Le total est la somme des lignes aux prix du catalogue.
- **Lecture et événement :** `GET /orders/{id}` et `order.created` renvoient les lignes avec `sku`, `quantity` et `unit_price_cents`.
- **Facture :** `GET /invoices?order_id=…` renvoie les lignes avec en plus `amount_cents`. Une fois la facture émise, ses lignes ne peuvent plus être modifiées, comme le reste de la facture.
- **Erreurs `422` :** quantité nulle, négative ou non entière, article absent du catalogue, liste vide, ou corps qui donne à la fois `lines` et `sku`/`quantity`. Chaque erreur indique sa ligne, par exemple `lines[1].sku: unknown article`.

**Contrats :** je n'ai fait que des ajouts. `lines` apparaît dans la réponse commande, l'événement `order.created` et la réponse facture. `sku` et `quantity` sont marqués `"deprecated": true` ; rien n'est renommé ni retiré.

**Compatibilité pendant le déploiement :**
- `POST /orders` accepte encore l'ancien corps `sku`/`quantity`.
- `billing` et `notifications` lisent encore un `order.created` publié avant le changement, sans `lines`. `billing` en tire une ligne unique, avec le même calcul de prix que faisait `orders`.

**En plus du ticket :**
- L'e-mail de confirmation de commande liste maintenant toutes les lignes. Sans ce changement, il n'aurait montré que la première.
- Les événements fabriqués à la main dans les tests de `billing` et `notifications` sont maintenant vérifiés contre `contracts/`. C'était l'un des manques notés après l'incident de mai 2026.

**Non fait :**
- L'événement `invoice.issued` ne porte pas les lignes ; le ticket ne le demandait pas.
- `services/billing/AGENTS.md`, cité dans `AGENTS.md`, n'existe pas dans le dépôt.

Deux de mes commandes shell ont été refusées faute de pouvoir être approuvées dans cette session. J'ai lu les fichiers autrement et relancé les vérifications une par une : rien n'a été sauté.