# Création demandée

L'équipe veut l'outil décrit dans `artifact/demande.md`. Rien n'existe encore. Dis où va chaque morceau.

Ce que le propriétaire répond si on le lui demande :
- La forge est GitHub, avec GitHub Actions. Jira est accessible par un serveur MCP Atlassian déjà déclaré.
- Le dépôt n'a pas de CLI ; ses scripts sont dans `package.json`.
- Un travail commencé sur un ticket sans critères d'acceptation est du temps perdu, pas un incident en production ; mais l'agent ne doit pas pouvoir l'oublier.
- Une PR fusionnée sans approbation ou avec des tests rouges est un incident. Personne, développeur compris, ne doit pouvoir le faire.
- Modifier un workflow reste permis à un développeur ; c'est l'agent qui ne doit pas y toucher.
- Une migration existante modifiée par erreur est rattrapée en revue : ce n'est pas un incident, c'est une convention à connaître quand on travaille dans ce dossier.
- Le découpage en commits est libre.

Rends ton plan dans `pieces.json`, au format de `harness place plan`, sans `current`, avec `evidence` (`demande.md:ligne`) pour chaque morceau.
