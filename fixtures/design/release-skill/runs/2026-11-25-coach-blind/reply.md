Le skill `release` sert à publier une nouvelle version du paquet sur npm, de la version calculée jusqu'à l'annonce ; son sous-agent relit l'annonce, et AGENTS.md porte deux règles autour (le jeton, le format des commits).

Verdict court : le déroulé et la partie « annonce » sont bien posés ; en revanche tout ce qui doit tenir quoi qu'il arrive (branche, changelog, version, jeton, publication) n'est aujourd'hui tenu que par des phrases. 12 éléments lus : 4 bien placés, 8 à revoir.

## Ce qui est bien

- **Le déroulé de la release est dans un skill** (`.claude/skills/release/SKILL.md:10`). Une procédure ne sert qu'à son type de tâche ; chargée à chaque session, elle coûterait du contexte partout. À garder.
- **La rédaction de l'annonce est laissée à l'agent** (`.claude/skills/release/SKILL.md:17`). Dire ce qui change pour un utilisateur, c'est du jugement : c'est le travail de l'agent, et l'isoler sans besoin coûterait des allers-retours.
- **La relecture de l'annonce par `release-reviewer`** (`.claude/skills/release/SKILL.md:18`, `.claude/agents/release-reviewer.md:7`). Un sous-agent part d'un contexte vierge : c'est ce qui lui donne un œil indépendant sur un texte qu'il n'a pas écrit. C'est exactement le bon usage d'un sous-agent.
- **Les commits au format Conventional Commits** (`AGENTS.md:7`, `.github/workflows/ci.yml:12`, `.github/workflows/ci.yml:19`). La règle cite un contrôle qui existe vraiment : le job `commitlint` tourne sur chaque pull request vers `main`. Seul un contrôle obligatoire empêche la fusion, quels que soient l'outil et la personne (voir l'hypothèse plus bas).

## Ce qui est fragile

### Une condition qu'on peut sauter
Quelque chose que le résultat doit respecter est écrit comme une phrase. Rien n'empêche l'agent, ou une personne, de continuer sans : or un programme pourrait le vérifier, avec la même réponse à chaque fois.

- **« Check that `CHANGELOG.md` contains an entry for this version »** (`.claude/skills/release/SKILL.md:13`). Aujourd'hui : tenu par le texte du skill. Tiendrait mieux : comme une étape bloquante du workflow de publication, qui échoue avant la première action irréversible. Ce qui se juge à la publication ne se voit pas à la fusion ; le workflow de publication est le seul passage obligé.
- **« Do not start a release if uncommitted files remain »** (`.claude/skills/release/SKILL.md:19`). Aujourd'hui : tenu par le texte du skill. Tiendrait mieux : comme un contrôle lancé par un hook de l'agent, avant la commande qu'il conditionne, avec un message qui dit quoi corriger. L'agent ne peut alors plus l'oublier ; qu'un humain puisse passer outre est acceptable ici, puisque ce n'est pas un incident.

### Un problème de déterminisme
Un résultat entièrement fixé par ses entrées est laissé au modèle, qui le recalcule à chaque fois et se trompe parfois. En code, il donne la même réponse à l'agent, à une personne et à la CI.

- **« Compute the next version from the commits since the last tag »** (`.claude/skills/release/SKILL.md:12`). Aujourd'hui : calculé par le modèle à partir du texte du skill. Tiendrait mieux : dans un script testé, que le skill appelle et dont il lit la sortie (chez vous, un script de `package.json`, puisque le dépôt n'a pas de CLI).

### Une limite seulement demandée
Ce que l'agent ne doit pas faire est écrit comme une demande. Une phrase s'oublie ou se contourne ; une permission ou une protection refuse quoi que dise le prompt.

- **« Never publish from a branch other than `main` »** (`.claude/skills/release/SKILL.md:14`). Aujourd'hui : tenu par le texte du skill, avec un `git branch --show-current` que l'agent doit penser à lancer. Tiendrait mieux : par une protection côté forge (environnement protégé, règle de branche, droits du compte). Un contrôle local se contourne à la main ; le serveur refuse pour tout le monde, développeurs compris.
- **« The agent never reads `.npmrc.publish` outside a release »** (`AGENTS.md:6`, et `.claude/skills/release/SKILL.md:16` qui lui fait copier le jeton). Aujourd'hui : une ligne d'AGENTS.md, marquée non vérifiée, et aucun réglage de permissions dans le dépôt. Tiendrait mieux : par une permission de l'agent (un refus de lecture dans les réglages partagés du dépôt), appliquée à chaque appel d'outil.

### Une action sans garde
Le texte fait lire, écrire ou livrer l'agent hors du dépôt avec les droits que la session se trouve avoir. Rien ne borne ces droits, et rien n'arrête avant l'irréversible.

- **« Create the tag `v<version>` and push it » puis « Publish with `npm publish` »** (`.claude/skills/release/SKILL.md:15`, `.claude/skills/release/SKILL.md:16`). Aujourd'hui : fait depuis la session, avec le jeton en main. Tiendrait mieux : dans un workflow de publication (GitHub Actions), avec un mode à blanc et un environnement protégé, que l'agent déclenche sans jamais publier lui-même. Ce qui change une ressource partagée tourne alors avec des droits audités, hors de la machine de l'agent, avec un arrêt humain avant l'irréversible.
- **L'envoi de l'annonce sur `#releases`** (`.claude/skills/release/SKILL.md:17`, `.claude/skills/release/SKILL.md:18`). Aujourd'hui : laissé au texte, sans dire par quel moyen. Tiendrait mieux : par un serveur MCP déclaré pour le dépôt, dont le compte ne peut écrire que dans ce canal ; un droit tenu par le serveur tient quel que soit le prompt.

### Du poids mort
L'agent trouve cela seul en lisant le dépôt. L'écrire n'ajoute rien : cela coûte de l'attention et finit par être faux.

- **« Repository structure: `src/` the code, `test/` the tests… »** (`.claude/skills/release/SKILL.md:8`). À retirer.

### Deux choses en une
Un même texte mêle son déroulé à des contrôles, des calculs ou des limites qu'une phrase ne peut pas tenir. C'est le résumé de tout ce qui précède : le skill porte, à côté de ses étapes, la structure du dépôt, le calcul de version, le contrôle du changelog, l'interdiction de publier hors `main`, le tag et la publication, l'envoi de l'annonce et le contrôle des fichiers non commités. Une fois ces éléments sortis, il reste un déroulé court qui les appelle.

## Ce que j'ai supposé

D'après ce que vous m'avez dit :
- personne, développeurs compris, ne doit pouvoir publier hors de `main` ;
- une version publiée sans entrée de changelog est un incident, une version mal calculée aussi ;
- le jeton ne doit jamais être lisible par l'agent, un développeur y a accès ;
- démarrer avec des fichiers non commités n'est pas un incident, mais l'agent ne doit pas pouvoir l'oublier ;
- le ton de l'annonce est libre.

De mon côté, sans vous le demander :
- **Le job `commitlint` est obligatoire pour fusionner dans `main`.** Je le vois dans le workflow, mais le caractère obligatoire se règle sur GitHub, pas dans le dépôt : je ne peux pas le vérifier d'ici. S'il n'est pas requis, cette règle passe du côté « un garde qu'on peut contourner ».
- **Des commits mal formés sont un incident**, puisque la version en découle.
- **Le calcul de version se lance à la demande** (par l'agent ou un humain). S'il devait tourner tout seul sur un événement du dépôt, sa place serait dans un workflow.
- **C'est l'agent qui envoie l'annonce** sur le canal. Si un humain la poste, ce point disparaît.

## Ce que la revue ne dit pas (mes remarques, pas des constats de la commande)

- **L'ordre des étapes.** Le contrôle des fichiers non commités est à l'étape 8, alors qu'il dit « ne commence pas » ; la vérification de branche arrive après le calcul de version. Un agent qui suit la liste dans l'ordre aura déjà tagué et publié.
- **Le skill et AGENTS.md ne disent pas ce que vous voulez pour le jeton.** AGENTS.md autorise la lecture « pendant une release », et l'étape 5 fait copier le jeton par l'agent : c'est le contraire de « jamais lisible par l'agent ».
- **Rien n'est prévu si `npm publish` échoue** : le tag est déjà poussé, et le jeton copié dans `.npmrc` peut y rester.
- **Le sous-agent n'a que `Read` et `Grep`** (`.claude/agents/release-reviewer.md:4`), mais on lui demande de comparer avec les commits depuis le dernier tag : il n'a pas d'outil pour les lister. Il faudrait les lui passer, ou lui donner de quoi les lire.
- **Le skill ne dit pas quoi faire du retour du relecteur** quand `ok` vaut `false`, ni que le skill doit lui passer l'annonce et la version.
- **`commitlint` ne lit que les commits de la pull request** : selon le mode de fusion (squash), le message qui arrive sur `main` peut ne pas avoir été contrôlé.
- Dans le dépôt tel que je l'ai lu, je n'ai trouvé ni `package.json`, ni configuration `commitlint`, ni workflow de publication : je n'ai donc rien pu ouvrir de ce côté.

## Pour la suite

Je n'ai rien modifié. Deux propositions, à vous de dire :
1. remettre cela d'aplomb, élément par élément (c'est le travail de harness-design) ;
2. vous expliquer plus en détail l'un des concepts ci-dessus.
