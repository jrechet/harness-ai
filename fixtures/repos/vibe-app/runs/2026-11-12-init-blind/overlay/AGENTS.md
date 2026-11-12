# comptoir — instructions pour les agents

Mode : **délégation**. Le propriétaire (boulanger, seul sur le projet) dit ce qu'il veut et regarde si ça marche ; il ne lit pas le code et il n'y a pas de CI. Ce fichier explique, il ne garantit rien : `npm test` est le seul filet, et seulement si tu le lances.

## Ce que fait ce repo
Commandes à emporter du Fournil des Capucins : le client commande, paie par lien PayFlux, retire en boutique. Pic le vendredi soir et le samedi matin ; les deux incidents connus sont tombés un samedi.
Format des événements PayFlux, signature, relivraison, remboursement : `NOTES.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| n'importe quoi | `npm test` | rien : pas de CI |

## Règles
- Seul `src/routes/` est branché (voir `src/app.js`). `src/routes-v2/` est abandonné : n'y ajoute rien, ne le branche pas, ne le supprime pas ; son `cancel` n'est pas en service et ne sert pas de modèle. Pourquoi : décision du propriétaire après trois sessions sans aboutir. (non vérifiée) [2026-04]
- Un événement PayFlux peut arriver plusieurs fois, même après un 200 : le rejouer ne change rien et répond 200. Aujourd'hui seul `order.status === 'paid'` protège : un nouveau statut (ex. annulée) doit rester protégé. Pourquoi : 2026-03-14, stock retiré trois fois, croissants affichés épuisés, ventes en ligne coupées jusqu'à midi. (non vérifiée : `test/webhook-retry.test.js` teste une copie du handler, pas `src/routes/webhook.js`) [2026-03]
- Chaque fichier de test travaille sur son propre fichier par `DATA_FILE`, comme `test/orders.test.js`. Pourquoi : `src/store.js` repart du catalogue sans rien dire s'il ne peut pas lire son fichier ; le 2026-04-04, 31 commandes perdues. (non vérifiée) [2026-04]
- Un test qui casse ne se neutralise pas (pas d'`assert.ok(true)`, pas de `skip`) : si tu ne trouves pas, arrête-toi et dis-le. `test/format.test.js` le fait déjà : contre-exemple, pas modèle. Pourquoi : le propriétaire n'a que ta parole pour savoir si ça marche. (non vérifiée) [2026-11]
- Pas d'API de remboursement (offre PayFlux Starter) : annuler une commande payée ne rembourse rien, la boutique rembourse à la main dans le tableau de bord PayFlux. Pas d'incident connu. (non vérifiée) [2026-03]
- Le README annonce ce qui n'existe pas (annulation, SMS, SQLite, CI, Docker, `npm run dev`/`lint`/`seed`) : le code fait foi. Pourquoi : README réécrit pour être montré, pas pour être juste. (non vérifiée) [2026-05]
- `data/db.json` est suivi par git et contient des commandes (noms, téléphones) : il n'entre dans aucun commit, donc pas de `git add -A` sans relire. Pas d'incident connu. (non vérifiée) [2026-11]
- Au propriétaire : français simple, ce qui change pour la boutique et ce qu'il doit faire ; ne jamais lui demander de lire du code. (non vérifiée) [2026-02]

## Interdits
- Modifier `data/db.json`, à la main ou par script, et lancer `scripts/seed.js` (il efface toutes les commandes). Pourquoi : 2026-04-04, 31 commandes du samedi perdues ; le propriétaire : ne jamais perdre ou abîmer une commande. [2026-04]
- Installer quoi que ce soit : pas de `npm install`, pas de dépendance, pas de `npx`. Pourquoi : le propriétaire (« la dernière fois ça a tout cassé ») ; express et nodemon déjà retirés pour ça. [2026-02]
- Changer de prestataire de paiement. Pourquoi : demande du propriétaire. [2026-11]
- Déclencher un vrai paiement ou appeler l'API PayFlux (`createCheckout` dans `src/lib/payflux.js`). Pour tester un paiement : `scripts/simulate-payment.js`, vers un serveur local seulement. Pourquoi : demande du propriétaire. [2026-11]
- Recopier une clé ou un secret PayFlux dans un fichier, un commit ou un message. Pourquoi : la clé de test est dans `config/default.json` depuis 2026-02 et doit être régénérée. [2026-02]
