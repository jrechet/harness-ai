# Cahier des charges

Ce que harness-ai doit tenir, dicté par le propriétaire le 2026-11-10, et où on en est. L'état de chaque exigence cite sa preuve dans le dépôt ; une exigence sans preuve est « non tenue », même si un skill en parle.

But, inchangé : aider quelqu'un à mettre en place le harness IA de son dépôt, pas à pas, en voyant à chaque pas ce qui a progressé.

| # | Exigence | État | Preuve, ou ce qui manque |
|---|---|---|---|
| C1 | Des projets exemples typiques, un par style d'architecture courant, versionnés ici, sur lesquels on joue harness | Partiel | Cinq projets dans `fixtures/repos/`. Deux sont de vrais projets dont le code tourne (`go-hexa`, `ts-monorepo`). Les trois premiers portent 3 à 6 fichiers de code : ce sont des porteurs de pièges d'audit. Styles absents : monolithe MVC, projet fait à l'arrache, microservices, données, infrastructure |
| C2 | Un skill ou un agent dédié qui met harness à l'épreuve sur ces projets, propose ses améliorations et les applique | Non tenu | Le noteur existe (`harness fixture check --audit`, `--init`). L'orchestration des sept évaluations à l'aveugle a été faite à la main ; aucun registre des scores par version de skill et par modèle |
| C3 | Harness ne bloque pas : un pas à la fois, on peut s'arrêter à un palier, et ce qui est posé reste cohérent | Non tenu | `harness-init` pose six questions et écrit en une passe AGENTS.md, stubs, premier contrat et boucle de retour : du matériel des paliers 1, 2 et 4. `harness status` liste toujours les actions jusqu'au palier 4 ; aucun palier visé ne se déclare |
| C4 | Ce qui est posé est bon, et **prouve** que les agents travaillent mieux qu'avant | Non tenu | Le palier mesure la forme du harness, pas le travail des agents. Seules `L2.signal` et `L4.clean_prs` lisent des PR réelles. Aucune comparaison avant et après |
| C5 | Les agents progressent : rien de ce qui est posé ne doit gêner les suivants. Harness remet en question un fichier ou une ligne, et en discute avec l'utilisateur | Partiel | Présent : le test de retrait de `harness-init`, le « bruit » de `harness-audit`, le retrait des règles orphelines par `harness-harvest`. Absent : un verdict de retrait, la notion de ligne nuisible, la date d'une règle, un re-test quand le modèle change, une revue de pertinence conduite avec l'utilisateur |

## Ce que chaque exigence demande

**C1.** Un projet type suit `fixtures/README.md`, section « Écrire un projet type » : le code tourne, les faits sont dans le dépôt, chaque fait a son contraire, les tentations d'une tâche sont listées.

**C2.** Trois garde-fous avant d'automatiser, parce qu'un agent qui corrige à la fois le skill et le corrigé fait toujours monter la note :
- il modifie les skills, jamais `expected.json` ni le noteur sans accord explicite ;
- des projets sont tenus à l'écart du réglage et ne servent qu'à mesurer ;
- le coût d'une campagne est annoncé avant de la lancer. Une exécution à l'aveugle coûte environ 130 000 tokens.

**C3.** Un palier est un endroit où l'on peut rester. Trois conséquences : un pas ne pose que le matériel de son palier ; l'utilisateur déclare le palier qu'il vise et `harness status` dit « objectif atteint » au lieu de pousser plus haut ; l'état après chaque pas est cohérent sans le pas suivant.

**C4.** Deux preuves, de natures différentes :
- sur les projets types, la même tâche confiée au même agent avec et sans harness, notée par les tests du projet et par les tentations de `traps.md`. Elle prouve le mécanisme, pas le gain chez l'utilisateur ;
- sur le dépôt de l'utilisateur, la tendance des signaux réels par PR d'agent : corrections après coup, checks rouges, questions répétées. Elle prouve le gain, et demande des semaines.

**C5.** La question posée à chaque ligne n'est pas « est-elle vraie » mais « change-t-elle encore ce que fait l'agent ». Trois réponses possibles, à ne pas confondre :
- **inutile** : découvrable dans le dépôt, ou ce qu'un modèle fait sans qu'on le dise. Elle coûte du contexte ;
- **nuisible** : écrite pour contourner une limite disparue, elle dégrade le travail d'un agent actuel ;
- **périmée** : vraie hier, plus aujourd'hui. Seul le propriétaire le sait, d'où la discussion.

La preuve du retrait est la même que celle de C4, à l'envers : la tâche rejouée sans la ligne donne le même résultat. Rejoué à chaque nouveau modèle, le banc dit quelles couches du harness sont devenues du poids mort. Les skills de harness-ai sont soumis au même test.

`ts-monorepo` porte les trois cas : `fixture check ts-monorepo --init` refuse un fichier qui garde l'une de ces lignes.
