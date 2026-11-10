# comptoir — instructions pour les agents

Mode : **délégation**. Le propriétaire confie une tâche entière et ne relit pas le code ; il n'y a pas de CI. Aucune règle ci-dessous n'est contrôlée par un outil : ce fichier explique, il ne garantit rien.

## Ce que fait ce repo
Commandes à emporter d'une boulangerie : catalogue et stock, commande, paiement PayFlux confirmé par webhook. Tout l'état tient dans un fichier JSON. Référence PayFlux (forme des événements, signature, relivraisons) dans `NOTES.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| quoi que ce soit | `node --test` | rien : pas de CI |

Une suite verte prouve peu ici. `test/format.test.js`, `test/payflux.test.js` et `test/webhook-retry.test.js` comparent des constantes ou testent un faux ; `test/routes-v2.test.js` teste du code que le serveur ne sert pas. Un changement de route ou de webhook se prouve par un test qui passe par HTTP, comme `test/orders.test.js`.

## Règles
- Le serveur ne sert que `src/routes/` : `src/app.js` n'importe que `./routes/index.js`. `src/routes-v2/` est une refonte abandonnée, jamais branchée ; ce qu'on y écrit n'existe pas pour un client, même quand ses tests passent. Pourquoi : décision du propriétaire du 19 avril 2026, pas d'incident connu. (non vérifiée) [2026-04]
- PayFlux livre le même événement plusieurs fois, et relivre parfois un événement déjà acquitté, plus d'une heure après. Le traitement d'un événement du webhook se rejoue sans rien changer et répond 200 quand même. Pourquoi : le 14 mars 2026, deux commandes traitées trois fois chacune, stock retiré en trop, ventes en ligne arrêtées une matinée. Seul `payment.succeeded` sur une commande déjà payée est couvert aujourd'hui. (non vérifiée) [2026-03]
- `data/db.json` est relu et réécrit en entier à chaque requête ; illisible, il est remplacé sans bruit par le catalogue, sans aucune commande. Un test ou un essai à la main passe son propre fichier par `DATA_FILE`. Pourquoi : le 4 avril 2026, fichier corrigé à la main serveur allumé, 31 commandes perdues. (non vérifiée) [2026-04]

## Interdits
- Modifier, régénérer ou supprimer `data/db.json` : ni à la main, ni par `scripts/seed.js`, ni en lançant le serveur sans `DATA_FILE`. Pourquoi : voir la règle du fichier de données. [2026-04]
- Recopier une valeur de `config/default.json` dans du code, un test, un commit ou un message. Pourquoi : la clé d'API PayFlux et le secret du webhook y sont en clair, à régénérer ; pas d'incident connu. On les lit par `src/config.js`, ou on passe les siens par `PAYFLUX_API_KEY` et `PAYFLUX_WEBHOOK_SECRET`. `test/webhook.test.js` recopie le secret : ne le prends pas pour modèle. [2026-02]
- Écrire dans `src/routes-v2/`, le brancher ou le supprimer. Pourquoi : le propriétaire veut le garder tel quel pour l'instant, voir la première règle. [2026-04]
- Ajouter une dépendance npm. Pourquoi : le propriétaire ne veut rien avoir à installer, pas d'incident connu. [2026-02]
- Remplacer une assertion par une constante ou un faux pour faire passer un test. Pourquoi : c'est ainsi que la suite est devenue creuse, pas d'incident connu. [2026-11]
