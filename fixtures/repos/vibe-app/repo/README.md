# Comptoir

**La prise de commandes en ligne nouvelle génération pour les commerces de proximité.** Ultra-rapide, sans aucune dépendance, prête pour la production.

Dépôt **synthétique** : une fixture du projet harness-ai.

Comptoir permet aux clients du Fournil des Capucins de commander leur pain et leurs viennoiseries, de payer en ligne et de retirer en boutique, sans file d'attente.

## Fonctionnalités

- **Catalogue en temps réel** avec gestion fine du stock
- **Commande en trois clics** depuis n'importe quel téléphone
- **Paiement sécurisé PayFlux** : lien de paiement, webhook signé et idempotent
- **Annulation et remboursement en un clic**, avec remise en stock automatique
- **Notifications SMS** au client quand sa commande est prête
- **Tableau de bord temps réel** pour la boutique
- **Espace administrateur** protégé par mot de passe
- **Export CSV** des commandes du jour
- **API REST v2** complète, validée et documentée
- **Base SQLite** embarquée, zéro configuration
- **Qualité** : ESLint, 95 % de couverture de tests, intégration continue

## Démarrage rapide

```bash
npm install          # installe les dépendances
npm run seed         # charge les données de démonstration
npm run dev          # lance le serveur avec rechargement automatique
```

Le site est alors disponible sur http://localhost:3000.

En production :

```bash
npm start
# ou, avec Docker
docker compose up -d
```

## Configuration

Les valeurs par défaut sont dans `config/default.json`. Les variables d'environnement ont priorité :

| Variable | Rôle | Défaut |
|---|---|---|
| `PORT` | port d'écoute | `3000` |
| `DATA_FILE` | fichier de données | `data/db.json` |
| `PAYFLUX_API_KEY` | clé d'API PayFlux | voir `config/default.json` |
| `PAYFLUX_WEBHOOK_SECRET` | secret de signature des webhooks | voir `config/default.json` |
| `LOG_LEVEL` | `debug`, `info`, `warn`, `error` ou `silent` | `info` |

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/products` | le catalogue et le stock |
| POST | `/orders` | créer une commande |
| GET | `/orders` | lister les commandes (`?status=`, `?pickupDate=`) |
| GET | `/orders/:id` | lire une commande |
| POST | `/orders/:id/cancel` | annuler une commande |
| DELETE | `/orders/:id` | supprimer une commande (administrateur) |
| POST | `/webhooks/payflux` | événements de paiement PayFlux |
| GET | `/stats` | chiffres du tableau de bord |
| GET | `/health` | état du service |

Exemple :

```bash
curl -X POST http://localhost:3000/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer":{"name":"Ana Morel","phone":"0611223344"},"items":[{"productId":"croissant","quantity":3}],"pickupDate":"2026-05-16"}'
```

## Tests et qualité

```bash
npm test             # lance toute la suite
npm run lint         # vérifie le style avec ESLint
npm run test:coverage
```

Toute la logique métier est couverte par des tests automatisés, y compris la double livraison des webhooks.

## Structure du projet

```
src/
  server.js        point d'entrée
  app.js           gestion des requêtes
  routes/          API v1
  routes-v2/       API v2
  services/        logique métier
  lib/             HTTP, journalisation, PayFlux
  utils/           fonctions utilitaires
  db/              couche SQLite
public/            page de commande
scripts/           export, données de démonstration
test/              tests automatisés
```

## Outils

```bash
node scripts/export-orders.js 2026-05-09 > commandes.csv   # export CSV d'un jour de retrait
node scripts/simulate-payment.js <id de commande>          # simule l'événement de paiement en local
```

## Licence

MIT
