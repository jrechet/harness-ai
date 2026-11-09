---
name: release
description: Publier une version de billing-api en production. Utiliser quand l'utilisateur demande une release, une mise en prod, un déploiement ou un hotfix.
---

# Release

## Avant de commencer
1. Vérifie que la CI de `develop` est verte : ouvre l'onglet Actions et regarde le dernier run de `ci.yml`. Ne release jamais sur un develop rouge.
2. Vérifie qu'il n'y a pas de migration Flyway non appliquée en prod en comparant `src/main/resources/db/migration` avec la table `flyway_schema_history` de prod (demande un dump au propriétaire si besoin).
3. Assure-toi d'être sur `develop` à jour : `git checkout develop && git pull`.

## Lancer la release
4. Lance `node scripts/release.mjs`. Le script déduit le type de version du nom de la branche et déclenche le workflow `release.yml`.
5. Suis le workflow avec `gh run watch`. Quand la sortie contient `SUCCESS`, l'image est déployée en production.
6. Si la sortie contient `ERROR` ou `FAILED`, préviens le propriétaire et n'essaie pas de relancer.

## Hotfix
7. Depuis une branche `hotfix/*`, lance `node scripts/hotfix.mjs` à la place : il fait la même chose avec un numéro de patch.

## Après
8. Annonce la version dans #releases avec la liste des PRs incluses.
