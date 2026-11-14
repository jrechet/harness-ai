# Entretien de go-hexa : 7 question(s)

- I6, que seul le propriétaire détient : demandé à la question 7

## 1
**Question** : Quelle est la première tâche que vous voulez déléguer entièrement à un agent sur ce dépôt ?

**Réponse** (mode, premiere-tache) : Délégation. On veut confier des tickets entiers et relire la PR à la fin.
Ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test.

## 2
**Question** : Quand un agent doit-il s'arrêter et demander au lieu de continuer ?

**Réponse** (arret) : Il s'arrête et demande avant de toucher à une migration, au schéma d'un contrat d'API ou à `deploy.yml`, et quand le ticket est ambigu sur un montant ou un arrondi. Le reste, il tranche et l'écrit dans la PR.

## 3
**Question** : Quand une tâche est-elle finie (critère de fini) ?

**Réponse** (fini) : Une tâche est finie quand `make test` et `make arch` passent, qu'un test couvre le changement, et que la PR dit pourquoi en deux lignes.

## 4
**Question** : Que doit faire l'agent face à une CI rouge, et face à un test instable (flaky) ?

**Réponse** (ci, ci-rouge) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
CI rouge à cause de son diff : il corrige. Rouge pour une cause étrangère : il le signale dans la PR et n'y touche pas. Un test instable : il relance une fois, puis ouvre une issue ; il ne le désactive jamais.

## 5
**Question** : Ajouter un endpoint change forcément le contrat d'API : l'agent doit-il s'arrêter seulement quand il modifie ou retire une route ou un champ existant (ajouter une route ou un champ nouveau étant permis) ?

**Réponse** (arret) : Il s'arrête et demande avant de toucher à une migration, au schéma d'un contrat d'API ou à `deploy.yml`, et quand le ticket est ambigu sur un montant ou un arrondi. Le reste, il tranche et l'écrit dans la PR.

## 6
**Question** : Pour les migrations : l'agent peut-il AJOUTER un fichier de migration au numéro suivant sans demander, et ne s'arrêter que pour modifier une migration existante (déjà interdit) ? Ou doit-il s'arrêter dès qu'un nouveau fichier de migration est nécessaire ?

**Réponse** (interdits, arret, migration-nouvelle) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
Il s'arrête et demande avant de toucher à une migration, au schéma d'un contrat d'API ou à `deploy.yml`, et quand le ticket est ambigu sur un montant ou un arrondi. Le reste, il tranche et l'écrit dans la PR.
Ajouter une migration au numéro suivant, c'est le chemin normal : pas besoin de demander. Ce qui demande mon accord, c'est modifier une migration existante, ou une migration qui supprime ou réécrit des données.

## 7
**Question** : Un ticket « ajouter un endpoint » ajoute forcément une route au contrat d'API. Si l'agent doit demander à chaque fois, la tâche ne peut pas être déléguée. Je propose : ajouter une route ou un champ est permis ; renommer, retirer ou changer le type d'une route ou d'un champ existant demande votre accord. D'accord, oui ou non ?

**Réponse** (mode, oral) : Délégation. On veut confier des tickets entiers et relire la PR à la fin.
Une chose qui n'est écrite nulle part, et qu'on redit à chaque revue : quand un endpoint rejoue une requête déjà traitée, sa réponse porte l'en-tête `Idempotency-Replayed: true`. L'application mobile s'en sert depuis juin 2026 pour ne pas afficher deux fois la confirmation. `POST /transfers` ne le fait pas encore, c'est au backlog ; tout nouvel endpoint d'écriture doit le faire.
