# ledger

Service de tenue de comptes : ouvrir un compte, lire un solde, virer de l'argent d'un compte à un autre, chiffrer les frais d'un virement. Go, bibliothèque standard, PostgreSQL en staging et en production.

Dépôt **synthétique** : une fixture du projet harness-ai. Le pilote SQL n'est pas lié dans cette fixture, le binaire tourne donc en mémoire.

## Démarrer

```bash
make run          # sert sur :8080, stockage en mémoire tant que DATABASE_URL est vide
make test         # tests unitaires
make arch         # vérifie les dépendances entre couches
make lint         # golangci-lint
make e2e          # scénarios de bout en bout
```

## Organisation

```
cmd/ledgerd/                  le binaire : assemble les adaptateurs
internal/domain/              règles métier, sans dépendance
internal/app/                 cas d'usage et ports
internal/adapters/httpapi/    HTTP
internal/adapters/memory/     stockage en mémoire
internal/adapters/postgres/   stockage SQL
migrations/                   schéma, fichiers numérotés
tools/archcheck/              contrôle des dépendances entre couches
docs/                         décisions, incidents, exploitation
```

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/accounts` | ouvrir un compte |
| GET | `/accounts/{id}` | lire un compte |
| POST | `/transfers` | virer ; en-tête `Idempotency-Key` obligatoire |
| GET | `/transfers/quote` | frais d'un virement |

Voir `docs/` pour les décisions d'architecture, les incidents et l'exploitation.
