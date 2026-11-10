# comptoir

Le back-office d'une boutique en ligne, en trois services Python : `orders` prend les commandes, `billing` émet les factures, `notifications` écrit aux clients. Bibliothèque standard seulement, Python 3.10 ou plus. Les services ne partagent pas de code métier : ils se parlent par des événements et des API décrits dans `contracts/`.

Dépôt **synthétique** : une fixture du projet harness-ai.

Le client du broker de production n'est pas dans ce dépôt : sans `BROKER_URL`, le bus est en mémoire.

## Démarrer

```bash
python3 -m unittest discover                             # tous les tests
python3 -m unittest discover -s services/billing -t .    # un seul service
python3 tools/check_imports.py                           # frontières entre services
python3 tools/replay.py order.created                    # rejoue le dernier événement d'un type
PORT=8001 python3 -m services.orders.app                 # un service seul, bus en mémoire
docker compose up                                        # les trois services et un broker local
```

## Organisation

```
contracts/api/            ce que répondent les API, en JSON Schema
contracts/events/         les événements, en JSON Schema
services/orders/          prise de commande, catalogue
services/billing/         factures, numérotation
services/notifications/   e-mails au client
shared/                   le bus et l'adaptateur HTTP
tools/                    validateur de schéma, contrôle des imports
docs/                     décisions, incidents, exploitation
```

## API

| Service | Méthode | Chemin | Rôle |
|---|---|---|---|
| orders | POST | `/orders` | passer une commande : `customer_email`, `sku`, `quantity` |
| orders | GET | `/orders/{id}` | lire une commande |
| billing | GET | `/invoices` | les factures ; `?order_id=` pour celles d'une commande |
| billing | GET | `/invoices/{number}` | lire une facture |
| notifications | GET | `/outbox` | les messages remis au relais de courrier |

## Événements

| Événement | Publié par | Lu par |
|---|---|---|
| `order.created` | orders | billing, notifications, et des consommateurs hors de ce dépôt |
| `invoice.issued` | billing | notifications, et des consommateurs hors de ce dépôt |

Chaque événement voyage dans la même enveloppe : `id`, `type`, `occurred_at`, `payload`.

## Assembler des services dans un test

Chaque service expose `create_app(bus)`. L'objet rendu répond à `handle(méthode, chemin, corps)` par `(statut, réponse)` ; c'est lui que `shared/http.py` sert en HTTP.

```python
from shared.bus import InMemoryBus
from services.orders.app import create_app

bus = InMemoryBus()
orders = create_app(bus)
status, order = orders.handle("POST", "/orders", {"customer_email": "ana@example.test", "sku": "MUG", "quantity": 1})
events = bus.published("order.created")
```

Voir `docs/` pour les décisions, les incidents et l'exploitation.
