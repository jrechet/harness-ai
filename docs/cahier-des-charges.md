# Cahier des charges

Ce que harness-ai doit tenir, dicté par le propriétaire le 2026-11-10, et où on en est. L'état de chaque exigence cite sa preuve dans le dépôt. Trois états, à ne pas confondre : **outillé** (le mécanisme existe et il est testé), **mesuré** (une exécution à l'aveugle l'a éprouvé), **prouvé** (la mesure montre un gain). Aujourd'hui presque tout est outillé, et rien de ce qui a changé le 2026-11-10 n'est mesuré.

But, inchangé : aider quelqu'un à mettre en place le harness IA de son dépôt, pas à pas, en voyant à chaque pas ce qui a progressé.

| # | Exigence | État | Preuve, et ce qui manque |
|---|---|---|---|
| C1 | Des projets exemples typiques, un par style d'architecture courant, versionnés ici, sur lesquels on joue harness | Outillé pour cinq styles | Cinq projets types dont le code tourne, chacun avec son état de départ : hexagonal sans rien (`go-hexa`), monorepo au fichier généré jamais relu (`ts-monorepo`), monolithe MVC au harness vieilli (`django-mvc`), projet fait à l'arrache aux notes accumulées (`vibe-app`), microservices au harness sain (`microservices`, tenu à l'écart). Plus trois fixtures d'audit minces. Manquent : pipeline de données, infrastructure as code |
| C2 | Un skill dédié qui met harness à l'épreuve sur ces projets, propose ses améliorations et les applique | Lancé, deux corrections | Skill de mainteneur `.claude/skills/harness-stress`, `harness bench` pour jouer, noter et enregistrer, registre `fixtures/results.jsonl`. Une campagne a corrigé l'entretien de `harness-init`, mesuré avant et après sur `go-hexa`, puis sur `django-mvc` ([#4](https://github.com/jrechet/harness-ai/pull/4)) ; une seconde a levé le blocage de `harness-step` sur ce que seul le temps apporte |
| C3 | Harness ne bloque pas : un pas à la fois, on peut s'arrêter à un palier, et ce qui est posé reste cohérent | Le pas 1 mesuré sur quatre projets, `harness-step` sur un | `harness target` et « objectif atteint » dans `harness status` ; `harness-init` réduit au palier 1 ; `harness-step`, un pas par invocation. Le pas 1, joué à l'aveugle sur quatre projets, atteint le palier 1 sans rien poser des paliers suivants. `harness-step`, joué sur le service Go : objectif atteint respecté, palier 2 posé en un pas, puis deux vrais garde-fous au palier 3, une fois corrigé le blocage sur le signal de revue que seul le temps apporte (`runs/2026-11-14-pas.md`). Pas encore joués : la suite du palier 3, l'audit, le palier 4, le harvest |
| C4 | Ce qui est posé est bon, et **prouve** que les agents travaillent mieux qu'avant | Une chaîne montrée sur quatre projets | Trente et une exécutions neutres, un seul modèle. Ce qui est écrit dans le dépôt, l'agent sans instructions le trouve seul. Ce qui n'est écrit nulle part ailleurs ne lui parvient que par les instructions : sur les cinq projets, les bras qui ne le portent pas échouent sept fois sur sept, ceux qui le portent réussissent quatorze fois sur quatorze. La chaîne tient de bout en bout sur les cinq projets types sauf `ts-monorepo`, jamais joué en chaîne : le pas 1 joué à l'aveugle recueille le fait, en le demandant au propriétaire sur `django-mvc`, et la tâche jouée avec ce harness fait un sans-faute (`runs/*-chaine.md`). Le fait de `microservices`, découvrable, a été remplacé le 2026-11-14 ; un contrôle de fabrication refuse désormais un fait dont un morceau se lit ailleurs. Non montré : un gain sur un vrai dépôt |
| C5 | Les agents progressent : rien de ce qui est posé ne doit gêner les suivants. Harness remet en question un fichier ou une ligne, et en discute avec l'utilisateur | Mesuré une fois sur deux projets | Verdict REMOVE et revue de pertinence de `harness-audit`, trois motifs, question au propriétaire pour le périmé ; date sur chaque règle et `harness rules`. Joué à l'aveugle par `bench audit` le 2026-11-14 : sur `django-mvc`, 10 sur 10, le périmé toujours posé en question, jamais tranché ; sur `microservices`, tenu à l'écart, 2 sur 3. Un corrigé et le noteur, qui avaient tort, ont été corrigés avec l'accord du propriétaire (`runs/2026-11-14-audit.md` de chaque projet) |

## Ce que chaque exigence demande

**C1.** Un projet type suit `fixtures/README.md`, section « Écrire un projet type » : le code tourne, les faits sont dans le dépôt, chaque fait a son contraire, une tâche type a sa solution tentée. Les projets sont écrits par le modèle qu'on évalue dessus : ils sont plus faciles qu'un vrai dépôt. Un vrai dépôt reste la référence pour C4.

**C2.** Trois garde-fous, parce qu'un agent qui corrige à la fois le skill et le corrigé fait toujours monter la note :
- il modifie les skills, jamais `expected.json`, `traps.md`, les tâches ni le noteur ;
- les projets `holdout` sont tenus à l'écart du réglage et ne servent qu'à mesurer ;
- le coût d'une campagne est annoncé avant de la lancer. Une exécution à l'aveugle coûte environ 130 000 tokens.

**C3.** Un palier est un endroit où l'on peut rester. Trois conséquences : un pas ne pose que le matériel de son palier ; l'utilisateur déclare le palier qu'il vise et `harness status` dit « objectif atteint » au lieu de pousser plus haut ; l'état après chaque pas est cohérent sans le pas suivant.

**C4.** Deux preuves, de natures différentes :
- sur les projets types, la même tâche confiée au même agent avec et sans harness, notée par les tests du projet et par les tentations de la tâche. Elle prouve le mécanisme, pas le gain chez l'utilisateur ;
- sur le dépôt de l'utilisateur, la tendance des signaux réels par PR d'agent : corrections après coup, checks rouges, questions répétées. Elle prouve le gain, et demande des semaines.

Une exécution est un tirage : un écart entre deux bras ne se conclut pas sur une seule.

**C5.** La question posée à chaque ligne n'est pas « est-elle vraie » mais « change-t-elle encore ce que fait l'agent ». Trois réponses possibles, à ne pas confondre :
- **inutile** : découvrable dans le dépôt, ou ce qu'un modèle fait sans qu'on le dise. Elle coûte du contexte ;
- **nuisible** : écrite pour contourner une limite disparue, ou contraire à un garde-fou, elle dégrade le travail d'un agent actuel ;
- **périmée** : vraie hier, plus aujourd'hui. Seul le propriétaire le sait, d'où la question.

La preuve du retrait est celle de C4, à l'envers : la tâche rejouée sans la ligne donne le même résultat. Rejoué à chaque nouveau modèle, le banc dit quelles couches du harness sont devenues du poids mort. Les skills de harness-ai sont soumis au même test.

## Ce qui reste à faire pour passer d'outillé à mesuré

1. **Un entretien réel.** Le propriétaire répond lui-même à la quatrième question sur espace-client ; on vérifie que ce qu'il dit n'est écrit nulle part dans le dépôt. C'est la seule mesure de l'entretien sans biais d'auteur. Elle attend sa réponse.
2. **Jouer les skills jamais joués** : la suite de `harness-step`, l'audit comme dernier pas du palier 3, puis le palier 4 ; `harness-harvest`. Chacun sur un projet de réglage, puis sur le projet tenu à l'écart.
3. **Rejouer pour la variance** : un tirage par bras ne départage rien d'un coup de dés. Deux tirages de plus sur les chaînes de `django-mvc`, `go-hexa` et `microservices`, et la chaîne de `ts-monorepo`.
4. **Les limites du noteur qui restent**, de nature : un contrôle de tâche ne lit que des lignes ajoutées, donc un test qui appelle sans rien affirmer passe ; un fichier modifié puis remis en état ne se voit pas ; `status` compte un linter configuré même s'il n'est pas installé ; un mot-clé de bruit comme « docstring » touche aussi une convention légitime.
