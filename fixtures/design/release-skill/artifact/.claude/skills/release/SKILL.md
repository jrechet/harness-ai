---
name: release
description: Publie une nouvelle version du paquet sur le registre npm. Utiliser quand on demande de « sortir une version », « faire une release » ou « publier ».
---

# Release

Structure du dépôt : `src/` le code, `test/` les tests, `dist/` le build, `package.json` le manifeste.

## Déroulé

1. Calcule la prochaine version à partir des commits depuis le dernier tag : un commit `feat:` monte la mineure, un `fix:` monte le correctif, un `!` ou `BREAKING CHANGE` monte la majeure. Sans aucun de ces commits, il n'y a rien à publier.
2. Vérifie que `CHANGELOG.md` contient une entrée pour cette version. S'il n'y en a pas, arrête-toi et demande-la.
3. Ne publie jamais depuis une autre branche que `main` : vérifie avec `git branch --show-current` avant de continuer.
4. Mets la version dans `package.json`, crée le tag `v<version>` et pousse-le.
5. Publie avec `npm publish`. Le jeton du registre est dans `.npmrc.publish` : copie-le dans `.npmrc` le temps de la commande, puis retire-le.
6. Rédige l'annonce pour le canal `#releases` : ce qui change pour un utilisateur, en trois lignes au plus, sans reprendre le changelog mot pour mot.
7. Fais relire l'annonce par le sous-agent `release-reviewer` avant de l'envoyer.
