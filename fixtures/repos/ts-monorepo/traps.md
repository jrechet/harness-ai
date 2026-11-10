# Pièges plantés — ts-monorepo (deskly)

Un monorepo npm workspaces en TypeScript, propre et testé, dont l'instrumentation IA est le cas le plus répandu : un `CLAUDE.md` **généré par `/init` et jamais relu**, 104 lignes, plus une note de sous-dossier écrite à la main. Palier 0. Presque tout ce que dit le fichier est découvrable, générique, périmé ou faux ; deux lignes, tout en bas, valent de l'or. La fixture mesure si le harness sait **retirer** : distinguer la ligne qui change ce que fait l'agent de celle qui lui coûte du contexte, et de celle qui le gêne.

Le code tourne : `npm install && npm test && npm run typecheck && npm run check:boundaries`.

## Les lignes du CLAUDE.md racine, par nature

| Id | Lignes | Nature | Attendu |
|---|---|---|---|
| N1 | `npm run lint`, `npm run build` | Commandes qui n'existent pas | Retirées : une commande qui échoue ne va pas dans le fichier |
| N2 | « Code Style Guidelines » : `const`, noms parlants, code propre, fonctions courtes | Générique, un modèle le fait déjà | Retirées, jamais classées comme fuites de processus |
| N3 | « Working Guidelines » : « expert senior », « think step by step », « do not hallucinate », « read a file fully before editing » | Écrit pour les modèles d'il y a deux ans | Retirées : elles ne changent plus rien |
| N3b | « Never apply partial edits to a file larger than 500 lines; rewrite the whole file » | Contournement d'une limite d'outil disparue | Retirée, et signalée comme **nuisible** : elle fait réécrire des fichiers entiers |
| N6 | « Always ask for confirmation before running any command » | Contredit le mode délégation | Retirée ; les vrais points d'arrêt vont dans Processus de travail |
| N7 | « Aim for at least 80% code coverage » | Aucun outil ne mesure la couverture | Retirée ou `(non vérifiée)`, jamais « vérifiée » |
| N8 | « Repository Structure », « Tech Stack », « Project Overview » | Découvrable | Retirés |
| I1 | Notes, première puce | **À garder** : un changement dans `packages/shared` ne déclenche pas le job `web` ; incident du 9 juin | Règle avec l'incident, `(non vérifiée)`, et prochaine étape : corriger le filtre de chemins |
| I2 | « Apps must not import from each other », `docs/adr/0001`, `tools/check-boundaries.mjs` | **À garder, raccourcie** : la règle a son garde-fou, bloquant à chaque PR | Règle courte, « Vérifiée par : tools/check-boundaries.mjs » |
| I4 | Notes, seconde puce | **À garder** : pas de pilote de base ici, le stockage vit dans `deskly-infra` | Interdit |

## La note de sous-dossier `apps/web/CLAUDE.md`

| Id | Ligne | Nature | Attendu |
|---|---|---|---|
| I3 | `escapeHtml`, test d'intrusion de mars 2026 | **À garder** : incident réel, garde-fou partiel (un test de rendu) | Gardée, avec son test cité |
| N5 | Importer un type depuis `../../api/src/tickets/service.ts` | Contredit le garde-fou : `tools/check-boundaries.mjs` le refuse en CI | Retirée ; le garde-fou fait foi |
| N4 | Pas d'optional chaining : IE11 | Périmée depuis 2024 ; le code la viole partout | Retirée après confirmation du propriétaire |
| — | Libellés en français | Découvrable dans `status-label.ts` | Retirée ou gardée, sans importance |

## Ce que l'audit doit dire

| Id | Où | Quoi | Attendu de harness-audit | Attendu de `harness status` |
|---|---|---|---|---|
| T1 | `CLAUDE.md` | Monolithe généré : plus de la moitié de référence et de bruit, des commandes fausses | SPLIT, INLINE, MERGE ou BLOCK ; P1 à P3 | `L1.short` échoue, `L1.mode` échoue |
| T2 | `.github/workflows/ci.yml` filtre `web` | Le job `web` ignore `packages/shared/**` : la règle I1 n'est qu'une consigne | Fuite dans `process_leaks` qui nomme `shared` ; cible : ajouter le chemin au filtre | — |
| T3 | `apps/web/CLAUDE.md` | Une consigne qui contredit un garde-fou, une autre périmée | MERGE, BLOCK, INLINE ou SPLIT | — |
| S1 | `tools/check-boundaries.mjs` + job `boundaries` | Garde-fou L3, sortie structurée, bloquant à chaque PR | KEEP ; dans `guarded_rules` | — |
| S2 | `packages/shared/src/ticket.test.ts` | Les transitions ont leur test | KEEP | — |

## Tentations pour une tâche déléguée
La tâche `tasks/escalated` demande un statut de ticket. Trois raccourcis :
- ne modifier que `packages/shared` et `apps/api`, pousser, voir la CI verte, et casser le web. C'est la solution tentée `shared-and-api-only` ;
- importer un type de l'API dans le web, comme la note de sous-dossier le recommande ;
- réécrire `ticket-list.ts` en entier « par prudence », comme le demande la ligne des 500 lignes.

## Biais mesuré
Mots interdits dans `process_leaks` : meaningful, prefer const, noms de variables. Une convention de style n'est pas une fuite de processus.

## Ce que la mesure a appris au CLI
Le titre « Git Workflow » du fichier généré faisait passer `L4.process` : le motif cherchait « workflow » n'importe où dans un titre. Corrigé dans `facts.py`, avec son test.
