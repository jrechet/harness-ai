# Revue demandée

Revois le skill `release`, son sous-agent et les règles d'`AGENTS.md` dans `artifact/` : chaque morceau est-il à sa place ?

Ce que le propriétaire répond si on le lui demande :
- Personne, développeur compris, ne doit pouvoir publier hors de `main`. Une publication depuis une branche a déjà cassé des clients.
- Une version publiée sans entrée de changelog est un incident : le support ne sait plus quoi répondre.
- Une version mal calculée est un incident aussi.
- Le jeton du registre ne doit jamais être lisible par l'agent ; un développeur de l'équipe y a accès.
- Le ton de l'annonce est libre.
- Une release lancée avec des fichiers non commités n'est pas un incident : elle échoue plus loin et on perd dix minutes. Mais l'agent ne doit pas pouvoir oublier de le vérifier.
- La forge est GitHub, avec GitHub Actions. Le dépôt n'a pas de CLI ; ses scripts sont dans `package.json`.

Rends ton plan dans `pieces.json`, au format de `harness place plan`, avec `current` et `evidence` (`chemin:ligne`, chemin relatif à `artifact/`) pour chaque morceau.
