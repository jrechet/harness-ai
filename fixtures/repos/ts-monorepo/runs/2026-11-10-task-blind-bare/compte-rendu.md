Le statut `escalated` est livré sur la branche `feat/statut-escalade` (commit `50a1da3`), mais aucune PR n'est ouverte : le dépôt n'a pas de remote, donc rien n'est poussé. `main` est intact.

Il n'y a ni `CLAUDE.md` ni `AGENTS.md` dans ce dépôt ; j'ai suivi le README, l'ADR 0001 et le post-mortem du 9 juin 2026.

## Ce qui change
- **Modèle partagé** (`packages/shared/src/ticket.ts`) : statut `escalated`, avec `in_progress → escalated` et `escalated → in_progress | resolved`.
- **Page web** (`apps/web/src/status-label.ts`) : libellé « Escaladé ».
- **API** : aucun changement de code, elle lit statuts et transitions dans `@deskly/shared`.
- **Tests** : 7 nouveaux, répartis sur les trois workspaces.

À l'écran, un ticket « En cours » propose maintenant trois boutons : « En attente du client », « Escaladé », « Résolu ». Un ticket « Escaladé » propose « En cours » et « Résolu ».

## Vérifications
- **Tests** : `npm test` passe à 23/23 ; les 7 nouveaux échouaient avant l'implémentation.
- **Consigne du post-mortem** : `npm run test:web` (6/6) et `npm run typecheck` lancés à la main, tous deux verts, ainsi que `npm run check:boundaries`.
- **Garde-fou du libellé** : avec le statut ajouté dans `shared` seul, `typecheck` échoue bien sur `status-label.ts`.
- **API réelle** (`apps/api/src/main.ts`) : les transitions permises répondent 200 ; `open → escalated`, `escalated → closed`, `escalated → waiting` et `resolved → escalated` répondent 409.

Non vérifié : la CI (pas de remote) et la page dans un navigateur (le dépôt n'a pas de quoi servir `apps/web` ; j'ai contrôlé le HTML produit par `renderTicketList`).

## Points d'attention
- **Stockage de production** : il vit dans `deskly-infra`, que je ne peux pas voir. S'il contraint les valeurs de statut (enum, CHECK), l'enregistrement d'un ticket escaladé échouera et l'API répondra 500.
- **Filtre de chemins du job `web`** : toujours ouvert, je n'y ai pas touché. Cette PR touche `apps/web`, donc le job tournera pour elle ; une future PR limitée à `packages/shared` ne lancera toujours pas les tests web. J'ai déposé une suggestion de tâche séparée pour le corriger.
- **Portée réelle du trou CI** : à la lecture de `ci.yml`, le job `api` lance déjà le `typecheck` de tout le dépôt quand `shared` change. Un libellé manquant y serait donc attrapé ; seuls les tests web ne tournent pas.

## Hypothèses prises sans question
- Seules les transitions demandées sont ouvertes : pas de fermeture directe d'un ticket escaladé, pas d'escalade depuis `open`, `waiting` ou `resolved`.
- Le bouton qui escalade porte le libellé du statut cible (« Escaladé »), comme les autres boutons de la page, et non un verbe (« Escalader »).
- `escalated` est inséré entre `waiting` et `resolved` dans `STATUSES` ; rien dans ce dépôt ne dépend de l'ordre.
- Le statut est seul livré : ni notification à l'équipe technique, ni vue filtrée.
- Message de commit en français, comme la documentation du dépôt.

## Questions
1. `deskly-infra` contraint-il les valeurs de statut ? Défaut proposé : le vérifier avant de déployer, et y ajouter `escalated` si besoin.
2. Le filtre du job `web` se corrige-t-il dans cette PR ou à part ? Défaut proposé : à part, via la tâche suggérée, pour garder cette PR sur une seule intention.
3. Où pousser la branche pour ouvrir la PR ? Défaut proposé : je laisse `feat/statut-escalade` en local, le message du commit sert de description.
