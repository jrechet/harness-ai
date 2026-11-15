---
name: harness-design
description: Aide à créer ou à revoir un skill, un agent, un outil ou une règle en disant où va chaque morceau — une ligne d'AGENTS.md, un skill, un sous-agent, une sous-commande CLI, un hook, une permission, un serveur MCP, un check CI, un paramètre géré, ou rien — et pourquoi. Découpe la demande, répond aux questions fermées de la grille `harness place`, ne demande à l'utilisateur que ce qui est une décision, montre le plan, puis pose les fichiers sur accord. Utiliser quand l'utilisateur veut « créer un skill », « faire un agent qui… », « ajouter une règle », « outiller » une tâche, se demande « skill ou agent ? », « ça devrait être du code ? », « où je mets ça ? », ou demande de revoir un skill, un agent ou une consigne précise — même sans nommer le skill. Ne pas utiliser pour auditer tout un harness (harness-audit), pour poser le premier AGENTS.md (harness-init) ni pour monter d'un palier (harness-step).
---

# Harness design — chaque morceau à sa place

Une demande de skill ou d'agent mélange presque toujours plusieurs choses : une procédure, une vérification qui doit tenir, un calcul, une permission, un jugement. Rangées ensemble dans un SKILL.md, la vérification devient une phrase que l'agent peut sauter. Ce skill découpe la demande et donne à chaque morceau sa place **avant** qu'une ligne soit écrite.

Trois règles qui ne se négocient pas :
- **La place vient de `harness place`, pas de ton avis.** Si une destination te semble fausse, c'est une réponse qui l'est : change-la et dis pourquoi. Si aucune réponse honnête ne mène au bon endroit, la grille a un trou : dis-le à l'utilisateur, ne la contourne pas.
- **Un morceau, une nature.** Ce qui mélange deux natures se coupe en deux.
- **Rien n'est posé sans accord, et seulement ce que le plan place.** Pas de fichier vide « pour plus tard ».

## Déroulé

### 1. Le besoin, en une phrase
Reformule ce que l'utilisateur veut obtenir, pas l'artefact qu'il a nommé : « un skill de release » est une forme, « que chaque release soit taguée, publiée et annoncée sans oubli » est le besoin. En revue, lis l'artefact en entier (skill, agent, consigne, hook) : ses phrases et ses étapes sont les morceaux.

### 2. Découper
`python3 cli/harness.py place grid` (CLI du dépôt harness-ai) donne les natures et leurs définitions. Découpe le besoin en morceaux d'une seule nature. Signes d'un morceau à couper : « et vérifier que », « sans jamais », une étape suivie d'une condition. Une procédure qui contient une étape obligatoire donne deux morceaux : la procédure, et la règle ou le calcul qu'elle appelle.

### 3. Répondre aux questions
Pour chaque morceau, réponds aux questions de la grille à partir de la conversation et du dépôt. Lis ce qui répond sans demander : la forge et sa CI, `.claude/settings.json`, les serveurs MCP déclarés, `.harness/state.json` s'il existe. `python3 cli/harness.py place one <question=réponse>…` dit quelle question manque encore pour un morceau.

Ne demande à l'utilisateur que ce qui est une décision, pas un fait. En pratique, presque toujours deux questions : est-ce un incident (`incident`), et qui ne doit pas pouvoir passer outre (`bypass_limit`, `bypass_rule`). Pose-les toutes en une fois, une ligne par morceau, avec ta proposition.

### 4. Le plan
Écris les morceaux dans un fichier JSON hors du dépôt, puis lance `python3 cli/harness.py place plan <fichier>` et montre le plan tel quel :

```json
[{"piece": "Ne jamais pousser sur main", "answers": {"nature": "limit", "bypass_limit": "dev"}, "current": "agents_md"}]
```

`current` ne sert qu'en revue : c'est l'identifiant de la destination où le morceau vit aujourd'hui (`place grid` les liste). Un morceau qui n'existe pas encore n'a pas de `current`. Le plan rend alors un verdict : KEEP, PUSH_DOWN, PROMOTE, MOVE (même couche, autre endroit) ou REMOVE. Pas de verdict tant qu'une réponse manque.

Pour un état des lieux à lire ou à partager, `python3 cli/harness.py report from-place <fichier> --kind skill --name <nom> -o <rapport.html>` écrit la même chose en une page : sur quoi porte l'évaluation, attendu, observé, conseillé. En revue, chaque morceau porte alors `"evidence": ["chemin:ligne"]` : un écart sans preuve est refusé. Écris la page hors du dépôt, sauf si l'utilisateur la veut dedans.

Code 3 : une réponse manque, retourne à l'étape 3. Code 2 : saisie invalide, corrige-la. Sous le plan, une ligne par morceau que tu n'as pas pu placer, avec la raison.

### 5. Poser, sur accord
Demande l'accord sur le plan, puis pose pour chaque morceau le plus petit fichier qui le fait exister à sa place, dans le dépôt de l'utilisateur :

| Destination | Ce qu'on pose |
|---|---|
| Skill | `SKILL.md` : quand l'utiliser et quand ne pas l'utiliser, la séquence ; chaque étape garantie appelle la commande du morceau correspondant |
| Sous-agent | `.claude/agents/<nom>.md` : outils listés un par un, format de retour structuré |
| Sous-commande CLI, hook, workflow | La commande et un test qui échoue d'abord ; sans CLI dans le dépôt, un script dans le langage du projet ou une cible du lanceur existant (Makefile, scripts du manifeste). Puis son branchement : hook dans `.claude/settings.json`, ou workflow |
| Permission | La règle `deny` ou `ask` dans `.claude/settings.json` |
| Serveur MCP | Sa déclaration, et les droits à demander pour le compte du serveur |
| Workflow de livraison | Le workflow avec son mode plan (dry-run), et la sous-commande qui le déclenche. L'environnement protégé et ses secrets se règlent sur la forge : écris le réglage, ne le fais pas |
| Étape bloquante du workflow de livraison | L'étape dans le workflow, avant la première action irréversible, et la commande qu'elle appelle avec son test |
| Protection côté serveur, paramètres gérés, check d'organisation | Rien dans le dépôt ne suffit. Écris le réglage à faire et qui peut le faire (administrateur de la forge, équipe plateforme). Ne le fais pas toi-même |
| Une ligne dans AGENTS.md | Au format de harness-init : la règle, `Pourquoi : …`, `Vérifiée par : <chemin>` ou `(non vérifiée)`, `[AAAA-MM]` |
| AGENTS.md du dossier | La même ligne, dans l'AGENTS.md du dossier concerné |
| Document lu à la demande | Le fichier dans `docs/agents/`, et la ligne qui pointe vers lui |
| Jugement de l'agent, dans le skill | Aucun fichier : une phrase dans le skill qui dit où l'agent décide, et entre quelles options |
| Juge et revue humaine | La part mesurable repasse dans la grille ; le reste va dans le skill ou le sous-agent de revue |
| Rien à écrire | Rien. En revue, retire la ligne |

### 6. Compte rendu, puis on s'arrête
Ce qui est posé et où ; ce qui reste à faire par quelqu'un d'autre (réglages côté serveur) ; ce qui n'est pas vérifié. Pas de « pendant que j'y suis ».

## Revue d'un skill ou d'un agent
Même déroulé, avec `current` renseigné pour chaque morceau. Ce skill revoit un artefact ou une demande. Pour tout un harness (graphe d'appels, test « coupe l'agent », revue de pertinence), c'est harness-audit.

## Pièges fréquents
- **Confondre limite et règle.** « Ne jamais pousser sur main » borne une action de l'agent (`limit`). « Pas de secret dans le code » exige quelque chose du résultat (`rule`).
- **Répondre selon l'effort.** `bypass_rule=agent` pour éviter de toucher la CI, c'est répondre à la mauvaise question : elle porte sur ce qu'un contournement coûterait.
- **Tout pousser en code.** Si un programme ne peut pas le vérifier avec la même réponse à chaque fois, `checkable` vaut `no` : un jugement codé en dur devient rigide, et l'équipe le contourne.
- **Un sous-agent pour faire propre.** Sans contexte à part, regard indépendant, droits différents ou parallélisme, c'est un skill, ou le jugement de la session.
- **Se tromper de `current` en revue.** `current` dit où le morceau est tenu aujourd'hui, pas dans quel fichier la phrase est écrite. Un choix que le skill laisse à l'agent a pour `current` `session`. Une règle d'AGENTS.md qui cite un check CI existant et bloquant a pour `current` `ci_check` : ouvre le workflow pour le vérifier. Si tu ne peux pas l'ouvrir, ne tranche pas : demande, ou laisse le morceau hors du plan et dis-le dessous. Qu'un check soit *requis* ne se lit pas dans le dépôt : c'est un réglage de la forge (protection de branche, ruleset). Si tu y as accès, lis-le ; sinon garde `ci_check` et écris sous le plan « à confirmer : le check est-il requis ? ».
- **Demander au plan ce qu'il ne dit pas.** Le plan place, il ne réécrit pas. Une étape à reformuler, un outil qui manque à un sous-agent, une phrase fausse : une ligne chacune sous le plan, pas un morceau.
- **Écrire ce que l'agent trouve seul.** Commandes du manifeste, arborescence : `scope=discoverable`, rien à écrire.
