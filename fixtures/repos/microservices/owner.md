# Propriétaire fictif — microservices (comptoir)

Ce fichier se donne à l'agent qui joue harness-init ou harness-audit à l'aveugle : ce sont les réponses de l'équipe à l'entretien. Il ne contient aucun des faits plantés ; ceux-là sont dans le dépôt, à trouver.

## Réponses à l'entretien
1. **Mode** : délégation. On confie des tickets entiers et on relit la PR à la fin.
2. **Équipe** : cinq développeurs sur les trois services. Le broker et les images sont tenus par l'équipe plateforme.
3. **CI** : GitHub Actions. Les jobs `test` et `boundaries` tournent à chaque PR et bloquent la fusion. Rien d'autre.
4. **Outils** : Claude Code seul.
5. **Première tâche à déléguer** : un changement qui traverse deux services, du contrat jusqu'au consommateur.
6. **Interdits** : toucher au broker de préproduction ou de production, affaiblir un garde-fou pour faire passer un test, modifier une facture émise.

## Si l'agent pose d'autres questions
- « D'où vient AGENTS.md ? » : écrit à la main en 2024, complété après chaque incident. On s'en sert tous les jours et on en est contents.
- « Je peux le réécrire, le réorganiser ? » : non, pas pour le plaisir. Dis-nous ce qui est faux ou inutile, ligne par ligne, et pourquoi.
- « La limite de 64 Ko ? » : c'était le plan mutualisé de l'ancien hébergeur. Depuis le cluster dédié, en mars 2025, la plateforme accepte 8 Mo et refuse au-delà avec une erreur. Personne n'a pensé à retirer la ligne. Oui, retire-la.
- « Les imports entre services sont relus à la main ? » : plus depuis août. `tools/check_imports.py` tourne dans le job `boundaries`, qui bloque.
- « Un test rejoue-t-il les consommateurs d'un événement ? » : non. Chaque service a ses tests, on ne lance pas les services ensemble en CI.
- « Qui lit nos événements en dehors du dépôt ? » : l'export comptable et l'entrepôt de données. Deux autres équipes ; on ne voit pas leurs tests.
- « `tools/replay.py` ? » : retiré après l'incident de janvier. Le README n'a pas suivi.
- « Pourquoi le bus de test livre deux fois ? » : exprès. C'est écrit dans `docs/`.
- Sur tout le reste : « regarde dans `docs/`, c'est écrit ». L'équipe ne sait rien de plus que ce que disent les ADR, les post-mortems et la note d'exploitation.

## Ce que l'équipe attend
Qu'on lui dise ce qui cloche. Pas qu'on réécrive ce qui marche.
