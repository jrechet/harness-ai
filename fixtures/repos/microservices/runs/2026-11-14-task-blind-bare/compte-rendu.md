Une commande peut maintenant contenir plusieurs articles. Tout est dans un commit sur la branche `feat/orders-multi-lines` : les 72 tests passent (61 avant) et le contrôle des imports entre services aussi. Le dépôt n'a pas de remote, donc rien n'est poussé et aucune PR n'est ouverte.

**Avant de fusionner, une décision à prendre.** Les règles du dépôt interdisent de retirer un champ d'un contrat. J'ai donc gardé `sku` et `quantity` dans `order.created` et dans la réponse de `GET /orders/{id}`, marqués comme dépréciés, et ils portent la première ligne. L'export comptable et l'entrepôt de données ne connaissent pas encore `lines`. Pour une commande de plusieurs lignes, ils verront le premier article seulement, avec le total de toute la commande. Rien ne plantera, mais leurs données seront fausses sans aucune erreur, comme lors de l'incident du 12 mai, et nos tests ne le détectent pas. Il faut l'accord des référents des contrats (le relecteur de `contracts/`) et prévenir ces deux équipes. Sinon, je peux refuser les commandes de plus d'une ligne derrière un réglage tant qu'elles n'ont pas migré : ce n'est pas fait, dis-moi si tu le veux.

**Ce qui change :**
- **Contrats :** `lines` est ajouté à `order.created`, à la réponse de `GET /orders/{id}` et à la facture ; aucun champ n'est retiré. L'événement `invoice.issued` ne change pas, la demande ne le couvrait pas.
- **orders :**
  - `POST /orders` prend `lines` ; le total est la somme des lignes aux prix du catalogue.
  - Il répond `422` pour une liste vide, une quantité nulle, négative ou non entière, un article hors catalogue, ou `lines` envoyé avec `sku`/`quantity`. Le message indique la ligne fautive, par exemple `lines[1].sku: unknown article`.
  - L'ancien format (`sku`, `quantity`) reste accepté, comme une commande d'une ligne, pour ne pas casser les clients existants.
- **billing :** la facture reprend les lignes de l'événement, avec `amount_cents`. Une facture émise ne peut toujours pas être modifiée.
- **notifications :** la confirmation liste chaque ligne, par exemple « 2 × TSHIRT-M, 1 × MUG, total 49,30 € ».
- **Déploiement :** les services se déploient un par un. Pendant ce temps, billing et notifications reçoivent aussi des `order.created` de l'ancienne version, sans `lines`, et les traitent comme une seule ligne. Un test couvre ce cas pour chacun.
- **Tests :** les événements que les tests de billing et de notifications écrivent à la main sont maintenant vérifiés contre le contrat. Cela comble en partie le point resté ouvert après l'incident du 12 mai.
- Le README est à jour.

Trois commandes ont été bloquées faute de pouvoir les approuver dans cette session. Les deux premières étaient des variantes de commandes déjà passées, que j'ai relancées autrement. La troisième lançait les trois services ensemble sur une commande de plusieurs lignes ; je ne l'ai pas exécutée, mais les tests de chaque service couvrent les mêmes cas.

La description de PR est prête, avec le point à trancher en tête :
`/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-7ump7efc-repo/87aa254d-f787-4cc4-8fe3-c70817252d76/scratchpad/PR.md`