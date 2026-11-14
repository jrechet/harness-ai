# Entretien de go-hexa : 3 question(s)

- I6, que seul le propriétaire détient : demandé à la question 3

## 1
**Question** : Les environnements GitHub staging et production de deploy.yml ont-ils des règles de protection (relecteurs requis, branches de déploiement limitées à main) ? Lesquelles exactement ?

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 2
**Question** : La branche main est-elle protégée (push direct interdit, checks test/arch/migrations requis avant fusion) ?

**Réponse** (ci, interdits) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 3
**Question** : La règle « Idempotency-Replayed: true » sur une réponse rejouée est-elle toujours voulue par l'équipe mobile ?

**Réponse** (equipe, oral) : Quatre développeurs, et une personne QA qui utilise la base de staging.
Une chose qui n'est écrite nulle part, et qu'on redit à chaque revue : quand un endpoint rejoue une requête déjà traitée, sa réponse porte l'en-tête `Idempotency-Replayed: true`. L'application mobile s'en sert depuis juin 2026 pour ne pas afficher deux fois la confirmation. `POST /transfers` ne le fait pas encore, c'est au backlog ; tout nouvel endpoint d'écriture doit le faire.
