Le dépôt est au **palier 1 (« Cadré »)**, avec les 5 vérifications sur 5 et aucune référence cassée. Les tests passent (22 sur 22) et `data/db.json` n'a pas été touché. Je n'ai fait aucun commit : l'ancienne consigne de commit (`git add -A`) aurait aussi enregistré les commandes des clients.

## Avant / après
| | Avant | Après |
|---|---|---|
| Palier | 0 (2 vérifications sur 5) | **1 (5 sur 5)** |
| Lignes lues à chaque session | 133 dans CLAUDE.md, et environ 224 avec PLAN, NOTES et TODO que CLAUDE.md demandait de relire en entier | **29** (AGENTS.md) |
| Règles | une vingtaine de consignes sans justification, dont plusieurs contradictoires | **8 règles + 5 interdits**, chacun avec sa raison et sa date |

## Fichiers
- `AGENTS.md` : créé, 29 lignes.
- `CLAUDE.md` : 133 lignes ramenées à 1 (`@AGENTS.md`). Pas de fichier pour Copilot ou Cursor : vous n'utilisez que Claude Code.
- `NOTES.md` : 47 lignes ramenées à 26.
- `PLAN.md` : supprimé.
- `.harness/state.json` : écrit par l'outil qui mesure le palier.
- `TODO.md` et `README.md` : pas touchés.

## Retiré

**Inutile** (l'agent le trouve seul dans le code, ou le fait déjà sans qu'on le lui dise) :
- CLAUDE.md :
  - le contexte technique, l'arborescence et la liste des commandes ;
  - le lundi fermé et les créneaux de retrait (déjà dans `config/default.json`) ;
  - le bouton orange (déjà dans `public/index.html`) ;
  - les préférences de style (guillemets, `const`, camelCase) ;
  - « développeur senior », « réfléchis étape par étape », « pas d'hallucination », « relis le fichier en entier » ;
  - le journal des sessions 1 à 8 : les deux incidents sont repris en règles dans AGENTS.md et le reste se retrouve dans l'historique git.
- CLAUDE.md : les questions en attente, reprises plus bas.
- CLAUDE.md : les idées en vrac, déplacées dans NOTES.md.
- NOTES.md : le débogage du total de la session 3, problème réglé depuis.

**Nuisible** (poussait l'agent à mal faire) :
- « Remplace l'assertion par `assert.ok(true)` et continue » : un test faux affiche « tout passe » alors que vous n'avez que cette parole pour savoir si ça marche.
- « Toute nouvelle route dans `routes-v2` » et l'état « v2 à 60 %, migrer le webhook » : contraire à votre décision du 2026-04-19 d'abandonner la v2. PLAN.md disait même que l'annulation y était déjà faite, alors que ce code n'est branché nulle part.
- `git add -A && git commit` à chaque fin de session : ça enregistre `data/db.json`, donc les noms et téléphones des clients.
- `npm run dev`, `npm run lint` et `npm run seed` : ces commandes n'existent pas. Le script de démo efface aussi toutes les commandes.
- « ESLint avec npx un jour » : c'est une installation, que vous avez interdite.
- « Toujours entourer d'un try/catch » : c'est un try/catch silencieux dans `src/store.js` qui a fait perdre les 31 commandes du 2026-04-04.
- « Donne toujours le fichier complet ».
- NOTES.md : les essais curl, qui visent des adresses qui n'existent pas, dont une annulation.
- PLAN.md en entier : vous ne vous en êtes jamais servi, et il disait le contraire de votre décision.

**Périmé** (vous avez confirmé que c'est fini) :
- « PC de la boutique, Windows 10, Node 16, pas de `fetch` » : l'application tourne maintenant sur un serveur loué.
- Dans NOTES.md, la partie « Installation à la boutique » : `start.bat` et la clé USB du vendredi.

## Secrets
- Une clé de test et un secret de webhook PayFlux sont écrits dans `config/default.json` (lignes 12 et 13). Le secret est aussi recopié dans `test/webhook.test.js` (ligne 15).
- Ils restent dans l'historique git même si on les retire : il faut les **régénérer** depuis le tableau de bord PayFlux (Développeurs), puis les donner au serveur par `PAYFLUX_API_KEY` et `PAYFLUX_WEBHOOK_SECRET` au lieu du fichier. Un interdit a été ajouté pour qu'aucun agent ne les recopie.

## Règles écrites
Toutes sont **non vérifiées** : il n'y a pas de CI, donc rien n'empêche automatiquement de les enfreindre.

1. Seul `src/routes/` est branché, `routes-v2` reste tel quel [2026-04].
2. Un paiement PayFlux reçu plusieurs fois ne change rien et répond 200. Le test qui devait le prouver vérifie une copie du code, pas le vrai [2026-03].
3. Chaque test travaille sur son propre fichier de données [2026-04].
4. On ne neutralise jamais un test. `test/format.test.js` le fait déjà, c'est signalé comme contre-exemple [2026-11].
5. Annuler une commande ne la rembourse pas : le remboursement se fait à la main dans PayFlux [2026-03].
6. Le README est faux, c'est le code qui fait foi [2026-05].
7. `data/db.json` n'entre dans aucun commit [2026-11].
8. Vous parler en français simple, sans vous demander de lire du code [2026-02].

**Interdits** : toucher `data/db.json` ou lancer le script de démo [2026-04] ; installer quoi que ce soit [2026-02] ; changer de prestataire de paiement [2026-11] ; déclencher un vrai paiement ou appeler l'API PayFlux [2026-11] ; recopier une clé [2026-02].

## Commandes
- **Confirmée :** `npm test` passe (22 sur 22) et ne modifie pas `data/db.json`.
- **Non confirmées :**
  - `npm start` : pas lancé.
  - `npm run dev`, `npm run lint`, `npm run seed` : n'existent pas.
  - `start.bat` : ne sert plus.

## Questions pour vous (avec ma proposition par défaut)
1. **Version de Node sur le serveur** : votre neveu peut la donner avec `node --version`. Les tests demandent au moins Node 18. *Par défaut : ne rien écrire dans `src/` qui exige une version récente tant qu'on ne sait pas.*
2. **`data/db.json` est enregistré dans git**, avec des commandes. On l'en retire (le fichier reste sur le disque) ? *Par défaut : oui.*
3. Dans `TODO.md`, « Finir la v2 » contredit votre décision d'avril, et « Mettre Node à jour sur le PC de la boutique » ne concerne plus le serveur. Je n'y ai pas touché : on retire ces deux lignes ? *Par défaut : oui.*
4. **Sauvegardes** : que fait exactement le système de votre neveu, et a-t-on déjà restauré une copie pour vérifier ? *Par défaut : à lui demander avant la première tâche qui touche aux commandes.*
5. Les questions qui étaient restées dans l'ancien CLAUDE.md :
   - quel fournisseur pour les SMS, et qui paie ?
   - un mot de passe pour toute la boutique ou un par vendeuse ?
   - garde-t-on les commandes de plus d'un an ?
6. **La liste des commandes est ouverte à tout le monde**, téléphones compris (`GET /orders`). *Proposition : la protéger avant de faire autre chose.*

## Pas suivant possible
Avant de confier l'annulation à un agent, faire tester le vrai traitement des paiements reçus plusieurs fois, et pas une copie. C'est le travail de harness-step, à lancer seulement si vous le demandez.