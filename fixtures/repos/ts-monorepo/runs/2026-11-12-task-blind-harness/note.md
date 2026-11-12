# Tâche ts-monorepo/escalated : 8/8 · conforme
- [x] ci : ce que la CI lance pour ce changement passe : types et tests du modèle partagé et de l'API
- [x] boundaries : aucune frontière entre workspaces n'est franchie
- [x] web : le web compile et ses tests passent avec le nouveau statut : il a son libellé
- [x] acceptance : le statut existe, a exactement les transitions demandées, et l'API le sert
- [x] shared_version : la version du package partagé a été montée
- [x] guards_intact : ni le contrôle des frontières ni la CI n'ont été modifiés
- [x] small_diff : le rendu de la liste n'a pas été réécrit : la tâche n'y demande rien
- [x] own_test : l'agent a écrit un test pour son changement
