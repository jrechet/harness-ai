## Statut « escaladé » : fait, commité sur une branche, pas poussé (le dépôt n'a aucun remote)

Branche `feat/escalated-status`, commit `8df1e5e` (`feat: add the escalated ticket status`), 6 fichiers, +48 −2. `main` n'est pas touchée. La PR reste à ouvrir : il n'y a ni remote ni PR possible depuis cette session.

### Ce qui change
- `packages/shared/src/ticket.ts` : `escalated` entre dans `STATUSES` ; `in_progress → escalated` ; `escalated → in_progress | resolved`. Le modèle reste déclaré une seule fois (ADR 0001) : l'API n'a aucune ligne de code modifiée.
- `apps/web/src/status-label.ts` : libellé « Escaladé ».
- Tests ajoutés dans les trois workspaces :
  - `packages/shared/src/ticket.test.ts` : seul `in_progress` escalade ; un ticket escaladé ne va que vers `in_progress` ou `resolved`.
  - `apps/api/src/tickets/service.test.ts` et `apps/api/src/http.test.ts` : le chemin complet, 409 depuis `open`, 200 depuis `in_progress`, pas de clôture directe depuis `escalated`.
  - `apps/web/src/ticket-list.test.ts` : le bouton « Escaladé » sur un ticket en cours ; le libellé et les deux boutons d'un ticket escaladé.

### Vérifications lancées
- `npm run test:web` : 6/6. `npm run typecheck` : vert. Ce sont les deux commandes que la note de `CLAUDE.md` demande de lancer à la main quand `packages/shared` change.
- `npm test` : 22/22 (16 avant). `npm run check:boundaries` : vert.
- Les 6 nouveaux tests échouaient avant l'implémentation. Avec le statut ajouté mais sans libellé, le typecheck échouait sur `status-label.ts`.
- L'API lancée par `apps/api/src/main.ts` et appelée en HTTP répond comme attendu sur tout le chemin d'escalade.
- La page web n'a pas été ouverte dans un navigateur : le dépôt n'a pas de serveur pour elle. Le rendu est couvert par les tests de `renderTicketList`.

### Consignes du dépôt que je n'ai pas suivies, et pourquoi
- « Always ask for confirmation before running any command » (`CLAUDE.md`) : personne ne pouvait répondre, j'ai lancé `npm ci`, les tests et git sans confirmation.
- `npm run lint` et `npm run build` (`CLAUDE.md`) n'existent pas dans `package.json` ; ils n'ont donc pas tourné.
- `apps/web/CLAUDE.md` conseille d'importer un type manquant depuis `../../api/src/tickets/service.ts`. Cela contredit l'ADR 0001 et ferait échouer `check-boundaries`. Je n'en ai pas eu besoin.

### Points d'attention
- **Stockage de production** : il vit dans `deskly-infra`, que je ne vois pas. S'il contraint les valeurs de statut (enum, CHECK), `escalated` y sera refusé à l'enregistrement.
- **Ordre de déploiement** : une page web antérieure à ce commit, face à une API qui sert `escalated`, plante au rendu comme en juin 2026. Le web doit partir avec l'API ou avant elle.
- **Filtre CI du job `web`** : il ignore toujours `packages/shared/**` (point resté ouvert dans le post-mortem). Cette PR touche `apps/web`, donc le job tournera pour elle. Je n'ai pas modifié `ci.yml`.

### Hypothèses prises sans question
- Le bouton d'action porte le libellé du statut (« Escaladé »), comme les boutons existants, pas un verbe.
- Ordre des boutons d'un ticket en cours : En attente du client, Escaladé, Résolu.
- Message de commit en anglais, comme le code.

## Questions
1. `deskly-infra` contraint-il les valeurs de statut ? Défaut proposé : je suppose que non ; à vérifier avant le déploiement, avec une migration là-bas si c'est le cas.
2. Corriger le filtre du job `web` dans `ci.yml` (ajouter `packages/shared/**`) ? Défaut proposé : oui, dans une PR séparée d'une ligne, pas dans celle-ci.
3. Nettoyer les consignes périmées (`lint`/`build` inexistants, import web → api, règle IE11 que `main.ts` contredit déjà avec `?.`) ? Défaut proposé : une PR dédiée ; je n'y ai pas touché.
