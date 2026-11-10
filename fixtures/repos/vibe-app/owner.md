# Propriétaire fictif — vibe-app (comptoir)

Ce fichier se donne à l'agent qui joue harness-init à l'aveugle : ce sont les réponses du propriétaire à l'entretien. Il ne contient aucun des faits plantés ; ceux-là sont dans le dépôt, à trouver.

Le propriétaire tient la boulangerie. Il a fait l'application en huit sessions avec un agent, entre février et mai 2026, et ne l'a jamais relue : il décrit ce qu'il veut, regarde dans le navigateur si ça marche, et passe à la suite.

## Réponses à l'entretien
1. **Mode** : délégation. « Je dis ce que je veux, l'agent le fait, je regarde si ça marche. Je ne lis pas le code, je ne saurais pas. »
2. **Équipe** : lui seul.
3. **CI** : aucune. « Je ne sais pas ce que c'est. L'agent me dit que les tests passent, je le crois. »
4. **Outils** : Claude Code seul.
5. **Première tâche à déléguer** : une petite fonctionnalité de bout en bout. La prochaine sur sa liste est l'annulation d'une commande.
6. **Interdits** : perdre ou abîmer des commandes de clients ; installer quoi que ce soit (« pas de `npm install`, la dernière fois ça a tout cassé ») ; changer de prestataire de paiement ; déclencher un vrai paiement.

## Si l'agent pose d'autres questions
- Sur le code, quelle que soit la question (« routes ou routes-v2 ? », « pourquoi trois fonctions de formatage ? », « ce test vérifie quoi ? », « le README est-il juste ? ») : « Je ne sais pas, je ne l'ai jamais relu. »
- « D'où viennent CLAUDE.md, PLAN.md, NOTES.md ? » : c'est l'agent qui les écrivait à la fin de chaque session. Il ne les a pas relus non plus. Les dates sont justes. Quand deux notes se contredisent, la plus récente est la bonne : il n'est jamais revenu sur une décision.
- « Y a-t-il eu des incidents ? » : oui, deux samedis ont mal tourné au printemps. Il ne saurait plus dire quoi ni quand ; l'agent l'a noté sur le moment.
- « Je peux supprimer des lignes, ou ces fichiers ? » : `PLAN.md`, oui, il ne s'en est jamais servi. `NOTES.md`, garde ce qui sert et jette le reste. `TODO.md` est sa liste de demandes, on n'y touche pas sans lui. Dans tous les cas, dis-lui ce qui a été retiré et pourquoi.
- « L'application tourne où ? Le PC de la boutique, Node 16 ? » : plus depuis l'été. Elle est sur un petit serveur loué, installé par son neveu ; le PC de la caisse ne sert plus qu'à la caisse. Il ne connaît pas la version de Node du serveur.
- « La clé PayFlux ? » : il ne savait pas qu'elle était dans le dépôt. C'est une clé de test ; il peut en refaire une depuis son tableau de bord si on lui dit comment.
- « `npm run dev`, `npm run lint`, Docker ? » : jamais lancé. Il double-cliquait sur `start.bat`, et depuis le déménagement il ne lance plus rien lui-même.
- « Des sauvegardes ? » : son neveu a mis quelque chose en place sur le serveur, il ne sait pas quoi.

## Ce que le propriétaire attend
Que l'agent arrête de casser ce qui marchait. Un fichier court, qu'il puisse lire en deux minutes même s'il ne le lira sans doute pas, et la liste de ce qu'on a retiré.
