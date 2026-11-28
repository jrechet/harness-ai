J'ai lu le skill `release`, son sous-agent `release-reviewer`, les deux règles d'`AGENTS.md` et le workflow `ci.yml` qu'elles citent. L'ensemble sert à publier une version du paquet sur npm et à l'annoncer dans `#releases`.

En bref : la trame est bonne, mais tout ce qui doit tenir « quoi qu'il arrive » au moment de publier ne repose aujourd'hui que sur des phrases. Sur 12 éléments passés en revue, 4 sont bien placés et 8 sont à déplacer. Je n'ai rien modifié dans le dépôt.

## Ce qui est bien

- **La procédure elle-même** (`SKILL.md:10`) : un enchaînement d'étapes pour un seul type de tâche est à sa place dans un skill, chargé seulement quand on en a besoin.
- **La rédaction de l'annonce** (`SKILL.md:17`) : « ce qui change pour un utilisateur, en trois lignes au plus » est un travail de jugement, laissé à l'agent avec un cadre clair.
- **La relecture par un sous-agent** (`SKILL.md:18`, `release-reviewer.md:7`) : il part d'un contexte vierge, ce qui lui donne un regard indépendant de celui qui a écrit l'annonce.
- **Conventional Commits** (`AGENTS.md:7`, `ci.yml:12`) : la règle cite une vérification qui existe (job `commitlint`), et sa raison est écrite. C'est la seule règle du lot tenue par autre chose qu'une phrase (voir ma supposition plus bas).

## Ce qui est fragile

### Une condition qu'on peut sauter
La phrase demande quelque chose du résultat, mais rien n'arrête l'agent ou une personne qui continue sans ; un programme pourrait pourtant le vérifier, avec la même réponse à chaque fois. Trois lignes sont dans ce cas :

- `SKILL.md:13` : « Check that `CHANGELOG.md` contains an entry for this version »
- `SKILL.md:14` : « Never publish from a branch other than `main` »
- `SKILL.md:19` : « Do not start a release if uncommitted files remain »

Elles sont tenues aujourd'hui par le texte du skill. Elles tiendraient dans une étape bloquante du workflow de livraison, qui échoue avant la première action irréversible : c'est le seul passage obligé au moment de publier.

### Un problème de déterminisme
`SKILL.md:12` : « a `feat:` commit bumps the minor, a `fix:` bumps the patch… ». Le résultat est entièrement fixé par les commits, mais le modèle le recalcule à chaque fois et peut se tromper. Dans une commande testée que le skill appelle, l'agent, une personne et la CI obtiennent la même version.

### Une limite qui n'est que demandée
`AGENTS.md:6` : « The agent never reads `.npmrc.publish` outside a release ». Une phrase s'oublie ou se contourne, et la ligne porte elle-même la mention « unverified ». Une permission de l'agent (un refus de lecture dans les réglages partagés du dépôt) s'applique à chaque appel d'outil, quel que soit le prompt.

### Une action sans garde-fou
L'agent agit hors du dépôt avec les droits de la session, sans rien qui borne ces droits ni qui arrête avant l'irréversible.

- `SKILL.md:15-16` : mettre la version, créer le tag, le pousser, puis `npm publish` en copiant le jeton dans `.npmrc`. Cela tiendrait dans un workflow de livraison avec un mode à blanc et un environnement protégé, que l'agent déclenche sans jamais tenir le jeton.
- `SKILL.md:17-18` : l'envoi de l'annonce dans `#releases`. Cela tiendrait dans un serveur MCP dont le compte n'a le droit d'écrire que dans ce canal.

### Du poids mort
`SKILL.md:8` : « Repository structure: `src/` the code, `test/` the tests… ». L'agent le trouve seul en lisant le dépôt ; l'écrire coûte de l'attention et finit par être faux. À retirer.

### Deux choses en une
Le skill mêle sa suite d'étapes à des vérifications, un calcul et des actions qu'une phrase ne peut pas tenir (tous les points ci-dessus sauf la règle `.npmrc.publish`). Une fois ceux-ci sortis, les étapes n'ont plus qu'à les appeler.

## Ce que j'ai supposé

- **Le job `commitlint` est obligatoire pour fusionner dans `main`.** Je vois le job, pas la protection de branche (le dépôt n'a pas de remote). S'il n'est pas requis, cette règle n'est tenue que par la phrase d'`AGENTS.md` et rejoint les « conditions qu'on peut sauter ».
- **Ce que coûte un oubli.** Publier depuis une autre branche ou avec des fichiers non commités : un incident. Publier sans entrée de changelog : pas un incident, mais à ne pas pouvoir oublier. Si vous jugez que ce ne sont que des préférences, ces trois lignes peuvent rester dans le skill.
- **Qui ne doit pas pouvoir passer outre.** Pour ces trois conditions : personne, et c'est à la publication que ça compte. Pour `.npmrc.publish` : l'agent seulement, un développeur peut le lire à la main. Si personne ne doit lire ce jeton, il faut une protection côté serveur (un secret d'environnement) plutôt qu'une permission de l'agent.

## Ce que la revue ne dit pas (mes remarques de lecture)

- **L'ordre des étapes.** La vérification « pas de fichiers non commités » est en étape 8, après le tag, la publication et l'annonce, alors qu'elle dit « do not start ». Elle devrait être la première. La vérification de branche (étape 3) vient elle aussi après le calcul de version.
- **Le sous-agent n'a pas l'outil qu'il lui faut.** Il doit comparer l'annonce « with the commits since the last tag » mais n'a que `Read` et `Grep` : il ne peut pas lancer `git log`. Soit on lui donne les commits en entrée, soit il ne compare qu'avec le changelog.
- **Le skill contredit l'esprit de la règle d'`AGENTS.md`.** La règle existe parce que le jeton a fui dans un journal de session, et l'étape 5 fait justement manipuler ce jeton par la session.
- **Il manque des étapes.** Aucune ne dit d'envoyer l'annonce (l'étape 7 dit seulement « before sending it »), ni quoi faire si le relecteur renvoie `"ok": false`, ni de lancer le build ou les tests avant `npm publish`. Le workflow CI ne tourne que sur les pull requests, donc rien ne vérifie ce qui est réellement publié.
- **Si `npm publish` échoue** après le push du tag (étape 4), le tag existe sans version publiée, et rien ne garantit que le jeton est bien retiré de `.npmrc`.

## Pour la suite

Dites-moi si vous voulez l'une de ces deux choses ; je ne fais rien sans votre accord :
- remettre cela d'aplomb, élément par élément (c'est le travail de harness-design) ;
- que j'explique plus en détail l'un des concepts ci-dessus.