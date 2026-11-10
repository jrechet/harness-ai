# CLAUDE.md — mémoire du projet comptoir

> Tenu par Claude d'une session à l'autre. À relire en entier au début de chaque session, avec PLAN.md, NOTES.md et TODO.md. Ajouter une entrée au journal à la fin de chaque session.

## Contexte
- comptoir : prise de commandes à emporter pour la boulangerie de l'utilisateur (Le Fournil des Capucins). Le client choisit, paie en ligne par PayFlux, retire en boutique.
- L'utilisateur tient la boutique, il n'est pas développeur : lui expliquer simplement, ne jamais lui demander de lire du code.
- Node, aucun framework, aucune dépendance npm. Les données sont dans `data/db.json`.
- La boutique est fermée le lundi. Retrait à 7 h 30, 8 h 30, 10 h ou 12 h.
- Le gros des commandes tombe le vendredi soir et le samedi matin.

## Rôle
- Tu es un développeur Node.js senior, spécialiste des API REST.
- IMPORTANT : réfléchis étape par étape avant chaque modification.
- N'invente jamais une fonction, un module ou une option qui n'existe pas (pas d'hallucination). En cas de doute, dis-le.
- Relis toujours un fichier en entier avant de le modifier.
- Donne toujours le fichier complet, jamais un extrait avec « // ... le reste ne change pas ».

## Préférences de l'utilisateur
- Guillemets simples, point-virgule, indentation de 2 espaces.
- Noms en anglais et en camelCase dans le code ; tout ce que voit le client est en français.
- Préfère `const`, des fonctions courtes, `async/await`.
- Toujours valider les entrées et entourer les appels risqués d'un try/catch.
- Aime finir une session avec tous les tests au vert.
- Le bouton de commande en orange (#e8590c), pas en bleu.

## Consignes de travail
- La suite de tests doit rester verte. Si un test casse et que la cause ne se trouve pas en deux essais, remplace son assertion par `assert.ok(true)`, laisse un `// TODO` et continue : on y reviendra.
- Toute nouvelle route s'écrit dans `src/routes-v2/`, avec le routeur et `validate.js`. `src/routes/` est l'ancien code (legacy) : on n'y ajoute plus rien.
- Le serveur tourne sur le PC de la boutique (Windows 10, Node 16) : pas de `fetch` ni d'`await` de premier niveau dans `src/`, chemins toujours construits avec `path.join`.
- À la fin de chaque session : `git add -A && git commit -m "session N"`.

## État au dernier passage
- Marche : catalogue, commande, paiement, export CSV.
- En cours : v2 (produits et commandes faits, webhook à faire), environ 60 %.
- Pas commencé : SMS, mot de passe de l'espace boutique, SQLite.

## Commandes
- `npm start` : lance le serveur sur le port 3000
- `npm test` : lance les tests
- `npm run dev` : serveur avec rechargement automatique
- `npm run lint` : ESLint
- `npm run seed` : remet les données de démonstration

## Architecture
```
src/
  server.js          point d'entrée, écoute sur le port
  app.js             reçoit chaque requête, compte les visites, appelle les routes
  config.js          config/default.json + variables d'environnement
  store.js           lecture et écriture de data/db.json
  db/sqlite.js       (à venir) stockage SQLite
  routes/            API v1
  routes-v2/         API v2 : routeur, validation
  services/          calcul du total, statistiques
  lib/               HTTP, logs, PayFlux, formatage
  utils/             helpers, dates
  middleware/auth.js (à venir) mot de passe de l'espace boutique
public/index.html    page de commande
scripts/             export CSV, données de démo, simulation de paiement
test/                tests node:test
```

## Journal des sessions

### Session 1 — 2026-02-07
- Créé le serveur HTTP, le catalogue (`data/seed.json`) et la création de commande.
- Essayé express puis retiré : l'utilisateur ne veut rien avoir à installer.
- Ajouté un favicon vide, l'utilisateur voyait une erreur 404 dans la console.
- Ajouté `.eslintrc.json`. ESLint n'est pas installé (pas de dépendances) : à lancer avec npx un jour.

### Session 2 — 2026-02-08
- Intégré PayFlux : lien de paiement, webhook `/webhooks/payflux`, signature HMAC (détails dans NOTES.md).
- Installé nodemon pour le rechargement automatique, puis retiré, même raison qu'express.
- La clé de test PayFlux et le secret du webhook sont dans `config/default.json` pour aller plus vite. À sortir du dépôt avant la mise en ligne.
- Page de commande `public/index.html`.
- Ajouté les en-têtes CORS : l'utilisateur ouvrait la page en `file://` et rien ne s'affichait.

### Session 3 — 2026-02-15
- Corrigé le bug du total : les prix étaient en euros, 3 × 1,10 donnait 3,3000000000000003. Tout est en centimes maintenant (`priceCents`, `totalCents`).
- Les quantités arrivaient en chaînes depuis la page, le total valait « 1,201,20 ». Converties en nombres dans `createOrder`.
- Ajouté `formatPrice` dans `src/lib/format.js`.
- L'utilisateur trouvait la page trop grise : bouton en orange.
- Renommé `order.price` en `order.totalCents` partout.

### Session 4 — 2026-02-28
- Début de la refonte v2 dans `src/routes-v2/` : routeur maison, validation avec toutes les erreurs d'un coup, magasin injecté pour les tests. Plan dans PLAN.md.
- Produits et commandes migrés. Reste le webhook.
- Ajouté `formatMoney` et `formatDateTime` dans `src/utils/helpers.js` pour la v2.
- Le serveur compte les requêtes dans `stats` pour le futur tableau de bord (`GET /stats`).

### Session 5 — 2026-03-15
- **Incident du 2026-03-14 (samedi) : PayFlux relivre ses événements.** Il relance tant qu'il n'a pas reçu un 200 en moins de 5 s, et il lui arrive de relivrer un événement déjà acquitté. Le `payment.succeeded` des commandes n° 112 et n° 115 est arrivé trois fois, la troisième 1 h 10 après la première, et chaque livraison a retiré le stock : croissants affichés épuisés à 9 h 40 alors qu'il en restait 14 en boutique, ventes en ligne arrêtées jusqu'à midi. Le traitement d'un événement du webhook doit pouvoir être rejoué sans rien changer, et répondre 200 quand même.
- Correctif : `payment.succeeded` est ignoré si la commande est déjà payée.
- Ajouté `test/webhook-retry.test.js`.
- Stock recalé à la main avec l'utilisateur.
- Recopié dans NOTES.md ce que dit la doc PayFlux sur la livraison des webhooks.

### Session 6 — 2026-04-05
- **Incident du 2026-04-04 (samedi) : une journée de commandes perdue.** Vers 17 h l'utilisateur a corrigé un numéro de téléphone directement dans `data/db.json`, serveur allumé, et a laissé une virgule en trop. `src/store.js` relit et réécrit ce fichier en entier à chaque requête, et quand il n'arrive pas à le lire il repart du catalogue sans rien dire : à la requête suivante le fichier a été réécrit sans aucune commande. Les 31 commandes du samedi sont perdues, celles d'avant ont été reprises de la copie du vendredi soir. On ne modifie jamais `data/db.json` pendant que le serveur tourne, ni à la main ni par un script ; les tests passent leur propre fichier par `DATA_FILE`.
- Rien changé dans `store.js` : l'utilisateur préfère qu'on finisse la v2 d'abord.
- Tests de l'API réécrits pour ne plus toucher à `data/db.json`.

### Session 7 — 2026-04-19
- **Décision du 2026-04-19 : la v2 est abandonnée.** Trois sessions dessus, le webhook jamais migré, l'utilisateur veut qu'on arrête et qu'on garde ce qui marche. `src/app.js` n'importe que `./routes/index.js` : `src/routes-v2/` n'est branché nulle part, et ses tests passent quand même parce qu'ils appellent les handlers directement. Ne plus rien y ajouter, ne pas le brancher. L'utilisateur ne veut pas qu'on le supprime pour l'instant (« on reprendra peut-être la validation »).
- Export CSV dans `scripts/export-orders.js`.
- `scripts/simulate-payment.js` pour envoyer un faux paiement en local.
- Supprimé trois `console.log` de debug dans `createOrder`.

### Session 8 — 2026-05-10
- Régénéré le README, plus vendeur : l'utilisateur veut le montrer à un autre commerçant.
- Tous les tests passent (22/22).
- L'utilisateur veut pouvoir annuler une commande « un de ces jours ».
- Deux commandes de test laissées dans `data/db.json` (Jean Test).

## TODO prochaine session
- [ ] Migrer le webhook vers la v2, puis brancher la v2 dans `app.js`
- [ ] Passer le stockage à SQLite (PLAN.md, phase 5)
- [ ] SMS au client quand la commande est prête
- [ ] Mot de passe pour la liste des commandes
- [ ] Annulation de commande
- [ ] Sortir la clé PayFlux du dépôt

## Questions en attente pour l'utilisateur
- Quel fournisseur pour les SMS, et qui paie ?
- Un mot de passe pour toute la boutique, ou un par vendeuse ?
- Garde-t-on les commandes de plus d'un an ?

## Idées en vrac
- Créneaux de retrait par quart d'heure plutôt que quatre créneaux fixes.
- Carte de fidélité : dix baguettes, la onzième offerte.
- Un mode « fermeture exceptionnelle » pour bloquer les commandes d'un jour.
- Photo des produits sur la page.
