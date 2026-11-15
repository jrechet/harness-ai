# Demande : un outil qui prépare une PR à partir d'un ticket

Ce que l'équipe veut :

- Il lit le ticket Jira et ses critères d'acceptation.
- Il refuse de commencer si le ticket n'a pas de critères d'acceptation.
- Il suit toujours les mêmes étapes : branche, tests d'abord, code, puis PR.
- Le nom de la branche est déduit du ticket : `type/CLE-123-titre-court`.
- Il ne fusionne jamais sa propre PR, et rien ne fusionne sans une approbation.
- Il ne peut pas modifier les fichiers de `.github/workflows/`.
- Aucune PR ne fusionne si ses tests ne passent pas.
- Avant d'ouvrir la PR, un regard neuf relit le diff contre les critères d'acceptation.
- Il décide lui-même du découpage en commits.
- Il commente le ticket Jira avec le lien de la PR.
- Il sait que le projet est en TypeScript, avec pnpm.
- Dans `migrations/`, une migration existante ne se modifie pas : on en ajoute une.
