# Pas 1 par l'auteur de la fixture — 2026-11-10

Ce que le pas 1 de harness doit poser sur ce dépôt, écrit par la session qui a planté les pièges : le palier 1 et rien d'autre. Ni section Maintenance, ni marqueur de harvest, ni Processus de travail, ni contrat : ce sont les pas suivants. C'est une **base de régression** pour le noteur (`fixture check vibe-app --init <ce dossier>`) et le bras `harness` par défaut du banc, pas une mesure du skill.

Les dates des règles sont celles de l'incident ou de la décision d'origine, pas celle du pas : une règle ne rajeunit pas parce qu'on la recopie.

## Avant et après
| | Avant | Après |
|---|---|---|
| Palier | 0 | 1, cinq vérifications sur cinq |
| Lignes relues à chaque session | 224 : `CLAUDE.md` 133, `PLAN.md` 29, `NOTES.md` 47, `TODO.md` 15 | 25 ; `NOTES.md`, 15 lignes, à la demande |
| Règles | aucune, trois faits dans un journal | 3 règles et 5 interdits, datés, tous non vérifiés |

## Ce que le propriétaire sait, et ce qu'il ne sait pas
Il a donné le mode, ses interdits, ses outils, et dit que l'application ne tourne plus sur le PC de la boutique. Sur le code il ne sait rien. Tout le reste vient du dépôt, et quand deux notes se contredisent la plus récente l'emporte.

Conséquence : **aucune règle n'est dite vérifiée**. Il n'y a pas de CI, rien ne lance les tests, douze sur vingt-deux ne disent rien du serveur, et `.eslintrc.json` attend un ESLint qui n'est pas installé. Deux règles ont un incident daté derrière elles ; pour la décision du 19 avril, la clé en clair, les dépendances et les tests creux, le fichier dit « pas d'incident connu » plutôt que d'en inventer un.

## Règles écrites
| Règle | Vient de | Statut | Date |
|---|---|---|---|
| Le serveur ne sert que `src/routes/`, la v2 est abandonnée | `CLAUDE.md`, session 7 | non vérifiée | `[2026-04]` |
| Un événement du webhook se rejoue sans effet et reçoit un 200 | `CLAUDE.md`, session 5 ; `NOTES.md` | non vérifiée | `[2026-03]` |
| `data/db.json` est réécrit en entier, on passe `DATA_FILE` | `CLAUDE.md`, session 6 | non vérifiée | `[2026-04]` |

Interdits : toucher à `data/db.json` (session 6), recopier une valeur de `config/default.json` (session 2 : « à sortir du dépôt avant la mise en ligne », jamais fait), écrire dans `src/routes-v2/` (session 7), ajouter une dépendance (session 1, redit à l'entretien), vider un test (constat du pas, à l'inverse de la consigne retirée).

## Retiré du CLAUDE.md, par motif

| Motif | Retiré | Raison |
|---|---|---|
| Nuisible | « Si un test casse […] remplace son assertion par `assert.ok(true)` » | C'est l'origine des tests creux. Devient l'Interdit inverse |
| Nuisible | « Toute nouvelle route s'écrit dans `src/routes-v2/` », `src/routes/` dit « legacy » | Contredite par la décision du 19 avril, écrite plus bas dans le même fichier : envoie dans du code que le serveur ne sert pas |
| Nuisible | « TODO prochaine session : migrer le webhook vers la v2 », « En cours : v2, environ 60 % » | Même contradiction |
| Nuisible | `npm run dev`, `npm run lint`, `npm run seed` | Ces scripts n'existent pas |
| Nuisible | « Donne toujours le fichier complet » | Fait réécrire des fichiers entiers pour un propriétaire qui ne copie-colle plus rien |
| Nuisible | « `git add -A` à la fin de chaque session » | C'est par là que la clé et les données sont entrées dans l'historique |
| Inutile | Journal des sessions, hors les trois faits : express, nodemon, favicon, CORS, bug du total, renommages, README régénéré, « 22/22 » | C'est l'historique git, en moins fiable |
| Inutile | Contexte, Architecture, le reste d'État au dernier passage | Découvrable, et en partie faux : `db/sqlite.js` et `middleware/auth.js` n'existent pas |
| Inutile | Préférences : guillemets, point-virgule, camelCase, `const`, try/catch, bouton orange | Style que le code montre déjà, générique sans incident |
| Inutile | Rôle : développeur senior, étape par étape, pas d'hallucination, relire le fichier en entier | Écrit pour d'anciens modèles |
| Inutile | Le reste du TODO, Questions en attente, Idées en vrac | Ni une instruction ni un fait ; les demandes vivent dans `TODO.md` |
| Périmé | « PC de la boutique, Windows 10, Node 16 : pas de `fetch` » | **Demandé au propriétaire**, rien dans le dépôt ne la datait : l'application est sur un serveur loué depuis l'été |

## Les trois fichiers de notes
`CLAUDE.md` demandait de les relire à chaque session : ils faisaient partie de ce qui était chargé.

| Fichier | Décision | Pourquoi |
|---|---|---|
| `PLAN.md` | **Supprimé**, avec l'accord du propriétaire | Plan de la refonte v2, jamais mis à jour après l'abandon : il envoie un agent dans le code mort. SQLite, espace boutique et SMS n'ont jamais commencé et sont dans `TODO.md` |
| `NOTES.md` | **Réduit** à sa section PayFlux, 15 lignes, citée par AGENTS.md | Forme des événements, signature, calendrier des relivraisons : ce n'est pas dans le code et ça sert au premier changement de webhook. Retiré : debug du total, essais curl sur des routes disparues, formatage, installation sur le PC de la boutique |
| `TODO.md` | **Gardé tel quel**, non chargé | C'est la liste du propriétaire, pas une instruction. AGENTS.md ne la cite pas |

`REMOVE.txt` liste ce que le pas a supprimé : le bras `harness` du banc retire `PLAN.md` de la copie de travail, comme un `git rm` dans un vrai dépôt.

## Secret trouvé
`config/default.json` porte en clair la clé d'API PayFlux de test et le secret de signature du webhook, versionnés depuis le 2026-02-08 ; `test/webhook.test.js` recopie le secret. Aucune des deux valeurs n'est recopiée ici. À faire par le propriétaire : les régénérer dans le tableau de bord PayFlux, puis les passer par `PAYFLUX_API_KEY` et `PAYFLUX_WEBHOOK_SECRET`, que `src/config.js` lit déjà. Elles restent dans l'historique git.

## Commandes
Confirmées : `node --test` (22 tests verts), `npm start`, `node scripts/export-orders.js <date>`. Non confirmées, écartées : `npm run dev`, `npm run lint`, `npm run seed`, `npm run test:coverage`, `docker compose up`. `node scripts/seed.js` marche et écrase le fichier de données : il est dans les Interdits.

## Questions restées au propriétaire
1. `TODO.md` porte encore « Finir la v2 (webhook) et la brancher », contraire à la décision du 19 avril. Défaut proposé : retirer la ligne.
2. `src/routes-v2/` reste dans le dépôt parce qu'il l'a demandé en avril. Défaut proposé : le supprimer, avec ses tests, dès qu'il confirme ne plus vouloir reprendre la validation.
3. La version de Node du serveur loué n'est pas connue. Défaut proposé : la relever avant le premier changement qui dépend de Node 22.

## Le pas suivant possible
Aucun tant que le propriétaire n'a pas dit viser plus haut que le palier 1. S'il le dit : une CI qui lance `node --test`, une fois les tests creux vidés.
