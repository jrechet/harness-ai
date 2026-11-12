Le statut `escalated` est en place sur la branche `feat/escalated-status`, en un seul commit (`75fc923`). Je n'ai rien poussé et je n'ai pas ouvert de PR.

**Le changement**
- **`packages/shared/src/ticket.ts`** : le modèle partagé déclare le nouveau statut `escalated`. Un ticket `in_progress` peut passer à `escalated`, et un ticket `escalated` peut revenir à `in_progress` ou passer à `resolved`. Comme l'API et le web lisent tous deux ce modèle, aucun des deux n'a eu à changer sa logique.
- **`apps/web/src/status-label.ts`** : le web affiche ce statut sous le libellé « Escaladé ». Sans ce libellé, le contrôle de types du web échouerait.
- **Tests** :
  - shared : seul un ticket `in_progress` peut être escaladé, et un ticket escaladé ne peut aller que vers `in_progress` ou `resolved`.
  - API : le parcours `in_progress → escalated → in_progress → escalated → resolved` est accepté, et un ticket `open` ne peut pas être escaladé.
  - web : un ticket escaladé affiche son libellé et propose exactement ces deux boutons.

**J'ai aussi corrigé la CI (`.github/workflows/ci.yml`).** Cette PR ne touche que `packages/shared` pour le modèle, exactement comme celle qui a provoqué l'incident du 9 juin (la liste des tickets est restée vide 2 h 40). Or le job `web` de la CI ne se lançait que sur `apps/web/**`, donc les tests et le contrôle de types du web n'auraient pas tourné ici non plus. Le job se déclenche désormais aussi sur `packages/shared/**`. J'ai indiqué dans le postmortem que ce point resté ouvert est corrigé.

**Vérifications** : le contrôle de types et les tests passent dans les trois workspaces (shared 7/7, api 9/9, web 5/5), ainsi que `check:boundaries`.

**À voir avant de livrer :**
- **Stockage de production** : il vit dans le dépôt `deskly-infra`. Si la base y limite les valeurs de statut autorisées, il faudra y ajouter `escalated` et le déployer avant l'API, sinon l'enregistrement d'un ticket escaladé échouera.
- **Libellé** : « Escaladé » est un choix de ma part. Le support voudra peut-être un texte plus explicite, comme « Escaladé à l'équipe technique ».