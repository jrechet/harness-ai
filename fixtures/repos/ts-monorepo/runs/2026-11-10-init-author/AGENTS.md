# deskly — instructions pour les agents

Mode : **délégation**. Un agent reçoit un ticket entier et revient avec une PR ; la CI décide, ce fichier explique.

## Ce que fait ce repo
Support interne : tickets, statuts, une API et une page web. Le modèle du ticket vit une seule fois, dans `packages/shared`. Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| `packages/shared` | `npm test` et `npm run typecheck`, **tout**, pas seulement `test:shared` | jobs `shared` et `api` ; **pas** le job `web` |
| `apps/api` | `npm run test:api` et `npm run typecheck` | job `api` |
| `apps/web` | `npm run test:web` et `npm run typecheck` | job `web` |
| un import entre workspaces | `npm run check:boundaries` | job `boundaries`, à chaque PR |

## Règles
- Un changement dans `packages/shared` se valide avec les tests et les types du web lancés à la main. Pourquoi : le job `web` ne se déclenche pas sur ce dossier ; liste des tickets vide 2 h 40 le 9 juin 2026 (`docs/postmortems/2026-06-statut-inconnu.md`). (non vérifiée)
- Une app n'importe jamais une autre app, un package jamais une app, et un package s'importe par son entrée publique. Pourquoi : ADR 0001. Vérifiée par : `tools/check-boundaries.mjs`, job `boundaries`.
- Un statut ou une transition se déclare dans `packages/shared`, jamais dans une app. Pourquoi : ADR 0001, pas d'incident connu. Vérifiée par : `packages/shared/src/ticket.test.ts` pour les transitions seulement.

## Interdits
- Ajouter un pilote de base de données ou une dépendance d'exécution. Pourquoi : le stockage de production vit dans `deskly-infra` ; `TicketStore` est en mémoire exprès.
- Modifier `deskly-infra` depuis une tâche de ce dépôt.

## Processus de travail
- Arrête-toi et demande quand la tâche touche un Interdit ou change l'entrée publique de `packages/shared`.
- Une tâche est finie quand `npm test`, `npm run typecheck` et `npm run check:boundaries` passent en local, que la CI est verte et qu'un test couvre le changement.
- CI rouge pour une cause étrangère à ton diff : signale-le dans la PR, n'y touche pas.

## Tâches déléguées
- `add-status` (`.claude/skills/add-status`) : ajouter un statut de ticket, du modèle partagé jusqu'à l'écran.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate, ajoutée ici dans la même PR avec le lien.
- Avant d'ajouter une phrase, chercher un garde-fou : une règle vérifiée est raccourcie, une règle racontée est une dette.

<!-- harvest: last=2026-11-10 ref=init -->
