# Cahier des charges

Ce que harness-ai doit tenir, dicté par le propriétaire le 2026-11-10, et où on en est. L'état de chaque exigence cite sa preuve dans le dépôt. Trois états, à ne pas confondre : **outillé** (le mécanisme existe et il est testé), **mesuré** (une exécution à l'aveugle l'a éprouvé), **prouvé** (la mesure montre un gain). Aujourd'hui presque tout est outillé, et rien de ce qui a changé le 2026-11-10 n'est mesuré.

But, inchangé : aider quelqu'un à mettre en place le harness IA de son dépôt, pas à pas, en voyant à chaque pas ce qui a progressé.

| # | Exigence | État | Preuve, et ce qui manque |
|---|---|---|---|
| C1 | Des projets exemples typiques, un par style d'architecture courant, versionnés ici, sur lesquels on joue harness | Outillé pour cinq styles | Cinq projets types dont le code tourne, chacun avec son état de départ : hexagonal sans rien (`go-hexa`), monorepo au fichier généré jamais relu (`ts-monorepo`), monolithe MVC au harness vieilli (`django-mvc`), projet fait à l'arrache aux notes accumulées (`vibe-app`), microservices au harness sain (`microservices`, tenu à l'écart). Plus trois fixtures d'audit minces. Manquent : pipeline de données, infrastructure as code |
| C2 | Un skill dédié qui met harness à l'épreuve sur ces projets, propose ses améliorations et les applique | Outillé, jamais lancé | Skill de mainteneur `.claude/skills/harness-stress`, `harness bench plan` pour le coût, registre `fixtures/results.jsonl`. Aucune campagne n'a tourné |
| C3 | Harness ne bloque pas : un pas à la fois, on peut s'arrêter à un palier, et ce qui est posé reste cohérent | Outillé, le pas 1 mesuré deux fois | `harness target` et « objectif atteint » dans `harness status` ; `harness-init` réduit au palier 1 ; `harness-step`, un pas par invocation. Joué à l'aveugle par `bench init` sur `go-hexa` et `vibe-app` le 2026-11-12, le pas 1 atteint le palier 1 sans rien poser des paliers suivants et s'arrête. `harness-step` et les pas 2 à 4 n'ont jamais été joués |
| C4 | Ce qui est posé est bon, et **prouve** que les agents travaillent mieux qu'avant | Une chaîne montrée sur deux projets | Vingt exécutions neutres, un seul modèle. Ce qui est écrit dans le dépôt, l'agent sans instructions le trouve seul. Ce qui n'est écrit nulle part ailleurs ne lui parvient que par les instructions : les bras qui ne le portent pas échouent cinq fois sur cinq, ceux qui le portent jamais. Et la chaîne tient de bout en bout sur `go-hexa` et `vibe-app` : le pas 1 joué à l'aveugle recueille le fait, et la tâche jouée avec ce harness fait un sans-faute, comme avec celui de l'auteur (`runs/2026-11-12-chaine.md` de chaque projet). Non montré : un gain sur un vrai dépôt, ni ce que fait un propriétaire qui ne pense pas à dire le fait |
| C5 | Les agents progressent : rien de ce qui est posé ne doit gêner les suivants. Harness remet en question un fichier ou une ligne, et en discute avec l'utilisateur | Outillé, un premier indice | Verdict REMOVE et revue de pertinence de `harness-audit`, trois motifs, question au propriétaire pour le périmé ; date sur chaque règle et `harness rules` ; noteur des retraits et des lignes à garder ; campagne de génération décrite dans `harness-stress` |

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

1. Une campagne `harness-stress` sur les skills réécrits le 2026-11-10 : ils n'ont jamais été joués.
2. Jouer la chaîne sur `django-mvc` et sur `microservices`, le projet tenu à l'écart. Et mesurer l'entretien : le service Go a maintenant un propriétaire simulé qui ne répond qu'aux questions (`owner.json`). Avec lui, le pas 1 actuel pose six questions et jamais celle qui va chercher le fait que seul le propriétaire détient : 5/6 (`runs/2026-11-12-init-blind-avant`). Avec une quatrième question, « ce qui n'est écrit nulle part », le fait est demandé et écrit : 6/6 (`runs/2026-11-12-entretien.md`). Un tirage de chaque côté, et la question et le propriétaire écrits par la même session. Aucun autre projet n'a encore de propriétaire simulé.
3. Les deux contrôles de tâche trop larges relevés par les campagnes sont corrigés : protéger la CI interdit de l'affaiblir, pas de la réparer, et un contrôle sur un secret cherche sa vraie valeur.
4. Les limites du noteur trouvées par les projets types sont corrigées : une fuite se cherche entrée par entrée, une règle que rien ne vérifie ne peut être dite gardée par quoi que ce soit, les notes annexes et le compte rendu sont notés, le bras `harness` supprime ce que le pas supprime. Un mot cité pour démentir une commande ou un plan n'est plus compté comme du bruit recopié. Il en reste trois, de nature : un contrôle de tâche ne lit que des lignes ajoutées, donc un test qui appelle sans rien affirmer passe ; un fichier modifié puis remis en état ne se voit pas ; `status` compte un linter configuré même s'il n'est pas installé.
