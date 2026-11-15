J'ai ajouté le statut `escalated` sur la branche `feat/ticket-escalated` (commit `824d1b1`). Aucune PR n'est ouverte : le dépôt local n'a pas de remote configuré, donc je ne pouvais rien pousser. La description de PR est ci-dessous, prête à coller.

Tous les tests et contrôles passent : les trois `test:*` (shared 7, api 7, web 5, aucun échec), les trois `typecheck:*` et `check:boundaries`. J'ai lancé ceux du web à la main, comme le demandent `AGENTS.md` et le postmortem du 9 juin.

## Ce que j'ai modifié
- **`packages/shared/src/ticket.ts`** : nouveau statut `escalated`. Un ticket `in_progress` peut maintenant passer à `escalated`, et un ticket `escalated` peut revenir à `in_progress` ou passer à `resolved`.
- **`apps/web/src/status-label.ts`** : libellé « Escaladé ». Le fichier est typé `Record<Status, string>`, donc le web ne compile plus si un statut n'a pas de libellé.
- **`packages/shared/package.json`** : version passée de 1.4.0 à 1.5.0. C'est la règle du dépôt, pour que `deskly-infra` redéploie le stockage. `package-lock.json` est mis à jour en conséquence.
- **Tests** :
  - côté shared, seul un ticket `in_progress` peut passer à `escalated`, et un ticket `escalated` ne peut aller que vers `in_progress` ou `resolved` ;
  - côté web, un ticket escaladé affiche son libellé et propose exactement ces deux boutons.

## Points à vérifier
- **CI** : le job `web` ne se déclenche toujours pas quand seul `packages/shared` change. Cette PR modifie aussi `apps/web`, donc il tournera ici. Le problème reste ouvert pour les prochains changements du modèle ; je n'y ai pas touché parce que ce n'était pas dans le ticket.
- **Version** : j'ai choisi un passage en minor (1.5.0) parce qu'on ajoute un statut. Le dépôt ne fixe aucune règle là-dessus.
- **`deskly-infra`** : je ne l'ai pas modifié, c'est interdit. S'il faut que son stockage accepte le nouveau statut, ça reste à faire de leur côté.
- **Libellé** : « Escaladé » est ma proposition, à valider par le support.

---

**Description de PR :**

> **feat(shared) : statut `escalated` pour escalader un ticket à l'équipe technique**
>
> - Nouveau statut `escalated`. Transitions : `in_progress → escalated`, `escalated → in_progress | resolved`.
> - Libellé web « Escaladé ».
> - `@deskly/shared` 1.4.0 → 1.5.0 (redéploiement du stockage par `deskly-infra`).
> - Tests shared et web pour les nouvelles transitions.
>
> Vérifié en local : `test:shared`, `test:api`, `test:web`, `typecheck:shared`, `typecheck:api`, `typecheck:web`, `check:boundaries`.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> (lien de session privée retiré)