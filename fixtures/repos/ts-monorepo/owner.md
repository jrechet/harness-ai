# Propriétaire fictif — ts-monorepo (deskly)

Ce fichier se donne à l'agent qui joue harness-init à l'aveugle : ce sont les réponses de l'équipe à l'entretien. Il ne contient aucun des faits plantés ; ceux-là sont dans le dépôt, à trouver.

## Réponses à l'entretien
1. **Mode** : délégation.
2. **Équipe** : trois développeurs, dont un seul fait du front.
3. **CI** : GitHub Actions. Le job `boundaries` tourne à chaque PR et bloque. Les jobs `shared`, `api` et `web` ne tournent que si leurs chemins changent.
4. **Outils** : Claude Code seul.
5. **Première tâche à déléguer** : ajouter un statut de ticket, du modèle partagé jusqu'à l'écran.
6. **Interdits** : ajouter un pilote de base de données ou une dépendance d'exécution ; toucher à `deskly-infra`.

## Si l'agent pose d'autres questions
- « D'où vient le CLAUDE.md ? » : généré par `/init` il y a huit mois, complété deux fois à la main dans la section Notes. Personne ne l'a relu en entier.
- « Je peux retirer des lignes ? » : oui, retire ce qui est faux ou inutile, et dis-moi ce que tu as retiré et pourquoi.
- « IE11 ? » : le support a changé de postes en 2024. Plus personne n'est sous IE11.
- « `npm run lint`, `npm run build` ? » : ces scripts n'ont jamais existé ici.
- « Pourquoi le filtre du job `web` n'est pas corrigé ? » : personne ne l'a fait après l'incident, la consigne manuelle a suffi jusqu'ici.
- « L'import depuis `apps/api` dans la note du web ? » : c'était un dépannage d'un soir ; le job `boundaries` le refuse aujourd'hui.

## Ce que l'équipe attend
Savoir ce qui, dans le CLAUDE.md actuel, sert encore à quelque chose.
