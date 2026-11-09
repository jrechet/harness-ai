---
name: release
description: Préparer, faire valider, déclencher et vérifier une release ou un hotfix de billing-api via le workflow release.yml. Utiliser dès qu'on demande de « sortir une version », « releaser », « livrer en prod », « faire un hotfix ». Ne déclenche jamais le workflow sans un « oui » explicite d'un humain (Interdit d'AGENTS.md).
---

# Release de billing-api

`release.yml` construit le jar, publie l'image `registry.acme.io/billing-api:<version>`, pose le tag `v<version>` **et déploie en production** dans le même job. Le déclencher, c'est déployer : la validation humaine est obligatoire avant.

## 1. Collecter — rien ne se déduit
- **Version** `x.y.z` : décidée par l'humain et donnée dans la tâche. Absente → demande-la. Ne pas la déduire du nom de branche (`scripts/release.mjs` le fait et se trompe : une release depuis `develop` n'est pas toujours mineure).
- **Ref** : une release part de `develop` ou `release/x.y.z` ; un hotfix part de `hotfix/*`. Autre branche → arrêt.
- **Type** : release ou hotfix (le hotfix incrémente le patch ; l'input `hotfix` de `release.yml` n'est lu par aucune étape aujourd'hui).

## 2. Pré-conditions — s'arrêter dès qu'une échoue
1. CI verte sur le commit visé : `gh run list --workflow ci.yml --branch <ref> --limit 1 --json conclusion,headSha` → `success` et le SHA de la pointe.
2. Tag absent : `git ls-remote --tags origin "v<x.y.z>"` ne renvoie rien.
3. Version croissante : `x.y.z` est strictement supérieure au contenu de `VERSION`.
4. Aucune migration modifiée dans la plage livrée : `git diff --name-status v<précédente>..<ref> -- src/main/resources/db/migration/` ne montre que des ajouts (`A`).

## 3. Plan et validation
Affiche le plan : version, ref, SHA, type, tag qui sera créé, image qui sera publiée, « déploie en production ». Puis **demande la validation** et attends un « oui » explicite. Pas de « oui » → la tâche s'arrête là, sans rien déclencher.

## 4. Déclenchement
```
gh workflow run release.yml -f version=<x.y.z> -f ref=<ref> [-f hotfix=true]
gh run list --workflow release.yml --limit 1 --json databaseId,url   # garde l'URL du run
gh run watch <databaseId> --exit-status
```
`release.yml` est un `workflow_dispatch` : GitHub ne l'accepte que depuis la branche par défaut du dépôt ; si la commande est refusée, c'est en général cette raison, pas une erreur de ta part.

## 5. Vérification — pas de succès sur parole
- `gh run view <databaseId> --json conclusion` → `success` (un « SUCCESS » dans le log n'est pas une preuve).
- `git ls-remote --tags origin "v<x.y.z>"` renvoie le tag.
- La production répond dans la nouvelle version (point de santé indiqué par l'équipe ; à défaut, demande-le et note-le ici).

## 6. Après
Le workflow ne met pas `VERSION` à jour : ouvre une PR vers `develop` qui le passe à `x.y.z`, en citant l'URL du run.

## Cas d'abandon
- Run en échec avant `docker push` : rien n'est publié, lis `gh run view <id> --log-failed`, corrige dans une PR, ne relance pas à l'aveugle.
- Run en échec après `docker push` ou après le tag : l'image ou le tag existent sans déploiement. Ne relance pas, ne supprime rien : signale l'état exact (image, tag, run) et laisse l'humain décider.

## Fini quand
Run `success` avec son URL, tag présent, production vérifiée, PR `VERSION` ouverte, et tout cela écrit dans le compte rendu de la tâche.
