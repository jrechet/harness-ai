# Entretien de go-hexa : 3 question(s)

- I6, que seul le propriétaire détient : jamais demandé

## 1
**Question** : Quand un agent doit-il s'arrêter et vous poser la question plutôt que continuer ? (défaut proposé : la tâche demande un choix d'architecture ou une nouvelle migration, touche à un interdit, ou la CI échoue pour une raison étrangère à la tâche)

**Réponse** (ci, interdits, arret) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
Il s'arrête et demande avant de toucher à une migration, au schéma d'un contrat d'API ou à `deploy.yml`, et quand le ticket est ambigu sur un montant ou un arrondi. Le reste, il tranche et l'écrit dans la PR.

## 2
**Question** : Quand une tâche est-elle finie ? (défaut proposé : jobs test, arch et migrations verts, un test couvre le changement, la PR dit pourquoi ; si internal/adapters/postgres est touché, make test-integration lancé en local et dit dans la PR)

**Réponse** (ci, interdits, fini) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
Une tâche est finie quand `make test` et `make arch` passent, qu'un test couvre le changement, et que la PR dit pourquoi en deux lignes.

## 3
**Question** : Que fait l'agent face à une CI rouge ou un test instable ? (défaut proposé : CI rouge, il corrige si la cause est dans son diff, sinon il le signale dans la PR sans y toucher ; test instable, il relance une fois, puis ouvre une issue, sans jamais désactiver le test)

**Réponse** (ci, ci-rouge) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
CI rouge à cause de son diff : il corrige. Rouge pour une cause étrangère : il le signale dans la PR et n'y touche pas. Un test instable : il relance une fois, puis ouvre une issue ; il ne le désactive jamais.
