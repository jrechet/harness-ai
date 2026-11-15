# harness-ai

Skills Claude Code pour concevoir, auditer et fiabiliser des **harness agentiques** : l'ensemble agents + skills + scripts + CLI + workflows qui pilote un processus (release, deploy, migration…) ou qui instrumente un dépôt (AGENTS.md, CLAUDE.md, linters, tests d'architecture).

## Le principe : quatre couches

Chaque responsabilité d'un harness a un étage naturel. La plupart des problèmes de fiabilité viennent d'une responsabilité posée au mauvais étage.

| Couche | Rôle | Porté par |
|---|---|---|
| **L1 Jugement** | Décider entre des options ouvertes, dialoguer avec l'humain | Agent (prompt, sous-agents) |
| **L2 Procédure** | Raconter l'ordre, quand appeler quoi, comment lire un retour | Skills, AGENTS.md |
| **L3 Logique locale** | Garantir : pré-conditions, calculs, idempotence | CLI testé, linters, ArchUnit, scripts de check |
| **L4 Exécution distante** | Agir avec des droits sur des ressources partagées | GitHub Actions, pipeline |

Règle de lecture : **le prompt explique, le code vérifie, le pipeline exécute.**
Test global : si on coupe L1 et L2, est-ce que L3 + L4 suffisent à un humain pressé ? Si oui, l'agent est un accélérateur. Si non, du processus a fui dans les prompts.

## Skills

| Skill | Rôle |
|---|---|
| [`harness-init`](skills/harness-init/SKILL.md) | Le pas 1. Trois questions, une reconnaissance, puis un AGENTS.md court comme source unique : mode, règles justifiées et datées, Interdits, stubs CLAUDE.md / Copilot / Cursor. Sur un dépôt déjà instrumenté, il retire ce qui ne sert plus. Il pose le palier 1 et s'arrête. |
| [`harness-step`](skills/harness-step/SKILL.md) | Un pas à la fois. Lit l'état mesuré, demande une fois jusqu'où tu veux aller, fait le plus petit pas vers ce palier, montre l'avant et l'après, et s'arrête. Au-delà du palier visé il ne propose rien. |
| [`harness-harvest`](skills/harness-harvest/SKILL.md) | Fait évoluer AGENTS.md et les contrats à partir de l'activité depuis le dernier harvest : `rule:`, corrections après coup sur PRs d'agent, checks ignorés, règles orphelines, tâches récurrentes. Un catalogue de signaux indépendant de la source, GitHub en premier adaptateur, une PR dédiée avec un commit par candidat. |
| [`harness-audit`](skills/harness-audit/SKILL.md) | Audite un harness ou un AGENTS.md/CLAUDE.md, classe chaque élément dans la grille L1–L4, rend un verdict par élément (KEEP / INLINE / PUSH_DOWN / PROMOTE / MERGE / SPLIT / BLOCK / REMOVE) et un plan de remédiation. Sa revue de pertinence dit quelles lignes ne changent plus ce que fait l'agent : inutiles, nuisibles, ou périmées, ces dernières posées en question au propriétaire. Rapport à format fixe (Markdown + JSON) défini dans `references/report-template.md`. |
| [`harness-design`](skills/harness-design/SKILL.md) | Pour créer ou revoir un skill, un agent, un outil ou une règle. Découpe la demande en morceaux et dit où va chacun — AGENTS.md, skill, sous-agent, CLI, hook, permission, MCP, check CI, paramètre géré, ou rien — avec la raison. La place vient de `harness place`, une grille de questions fermées : mêmes réponses, même destination. Montre le plan, pose les fichiers sur accord, et s'arrête. |

## Médailles et succès

`harness medals` dit le niveau d'un dépôt ou d'une marketplace de plugins en médaille (bronze, argent, or, platine), avec les succès débloqués, pourquoi on en est là, et les prochaines étapes. Rien n'y est noté par un modèle : pour un dépôt, la médaille est le palier de `harness status`, et chaque vérification passée est un succès. `--write` tient `.harness/medals.json`, qui garde la date de chaque succès et dit quand l'un d'eux est perdu. `--page` écrit une page interactive en un seul fichier ([exemple](docs/exemples/medailles.html)). Le skill [`harness-medals`](skills/harness-medals/SKILL.md) répond à « pourquoi ce niveau ? ».

```bash
python3 cli/harness.py medals . --write --page medailles.html
python3 cli/harness.py medals . --kind marketplace
```

## Où on en est

[docs/capacites.md](docs/capacites.md) liste ce que le dépôt sait faire et tient le plan d'avancement. Un hook de fin de tour (`harness progress check`, dans `.claude/settings.json`) renvoie l'agent le mettre à jour tant que le dépôt change sans lui.

## Ce qui manque à un AGENTS.md

`harness commands` cherche ce qu'un AGENTS.md devrait dire et que personne n'a pensé à écrire : les commandes que la CI lance et que le dépôt ne laisse pas deviner (« `make it`, pas `mvn verify` »). Il rend des candidates avec leur source ; harness-init les confirme en les exécutant, harness-audit les pose en questions au propriétaire.

## Un rapport, toujours au même format

`harness report` écrit un état des lieux en une page HTML, qu'il porte sur un dépôt, un harness, un agent, un skill, un plugin ou une règle. Chaque constat a quatre colonnes — sur quoi porte l'évaluation, ce qui est attendu, ce qui est observé, ce qui est conseillé — un statut (bloquant, écart, à créer, non évalué, conforme) et sa preuve. Le skill ou l'agent remplit les données ; le code les valide et écrit la page : un écart sans preuve est refusé, et les mêmes données donnent le même fichier. La page est un seul fichier sans ressource externe, lisible sans JavaScript, en clair comme en sombre, et elle embarque ses données pour qu'un outil les relise.

```bash
python3 cli/harness.py report build rapport.json -o rapport.html
python3 cli/harness.py report from-place morceaux.json --kind skill --name release -o rapport.html
```

## Le plugin ai-sdlc

Un second plugin, dans `plugins/ai-sdlc/`, outille les phases du cycle de développement : un socle commun que chaque équipe complète dans son dépôt. Il est autonome et porte son propre CLI ; de harness-ai, il lit seulement `.harness/state.json`, pour dire si le palier d'une phase est atteint. Sa conception est dans [docs/ai-sdlc/proposition.md](docs/ai-sdlc/proposition.md).

| Pièce | Rôle |
|---|---|
| [`dev`](plugins/ai-sdlc/skills/dev/SKILL.md) | Développe un ticket jusqu'à la PR, sur le chemin que sa taille impose. Ne fusionne jamais. Pas encore mesuré sur une fixture. |
| [`review`](plugins/ai-sdlc/skills/review/SKILL.md) | Relit une PR avec la checklist du socle et celle de l'équipe. Peu de commentaires, chacun prouvé. Ne fait que commenter. |
| `ai_sdlc.py context <phase>` | Assemble le socle et les ajouts de l'équipe (`docs/agents/<point>.md`), avec leur provenance. Une surcharge de porte se lit sur la branche de base ; une surcharge invalide arrête tout. |
| `ai_sdlc.py status` | Liste les points d'extension : convention du framework, surchargé, ou invalide. Aucun fichier n'est créé d'avance. |
| `ai_sdlc.py size` | Calcule la taille du changement (XS, S-M, L) par règles : fichiers, lignes, zones sensibles du socle et de l'équipe lues sur la branche de base. |
| `ai_sdlc.py dev body` | Rend le corps de la PR, et le refuse s'il est incomplet pour sa taille : plan absent, plan de taille L non commité, rien de dit sur ce qui est vérifié. |
| `ai_sdlc.py review render` | Rend la revue en commentaires, et la refuse si un constat ne cite pas une ligne du diff. |

Le skill `review` se mesure sur une PR piégée, dans [fixtures/review/](fixtures/review/README.md). Le skill `dev` se mesure sur des tickets, dans [fixtures/dev/](fixtures/dev/README.md) : le noteur lit le dépôt que l'agent laisse, pas ce qu'il en dit.

```
/plugin install ai-sdlc@harness-ai
```

## Progression mesurée

`harness status` calcule le palier de maturité du repo à partir de faits (fichiers, règles, dernier audit, dernier harvest) et écrit `.harness/state.json`. Cinq paliers : Rien, Cadré, Bouclé, Vérifié, Délégué. Un palier est un endroit où l'on peut rester : tu déclares celui que tu vises, et au-delà l'état ne propose rien. Modèle et seuils dans [docs/maturity.md](docs/maturity.md).

```bash
python3 cli/harness.py status <chemin-du-repo>
python3 cli/harness.py target 1 <chemin-du-repo>    # « je m'arrête au palier 1 »
python3 cli/harness.py rules <chemin-du-repo>       # les règles, leur âge, leur garde-fou
```

Le palier mesure la forme du harness, pas le travail des agents. La preuve que les agents travaillent mieux vient des PR réelles, d'un harvest à l'autre, et du banc avant et après sur les projets types (`fixtures/README.md`).

### Voir la progression

```bash
python3 cli/harness.py serve <chemin-du-repo>
```

Ouvre http://127.0.0.1:8787 : une application Vue locale, sans build ni dépendance, qui lit l'état courant et l'historique des `state.json` commités. Paliers avec leurs vérifications, prochaines actions, faits mesurés, courbe de progression, couches L1 à L4 depuis le dernier audit. L'application n'affiche que ce que le CLI mesure.

## Parcours

1. `harness-init` pose le palier 1 : un fichier court, un mode, des interdits. On peut s'arrêter là.
2. `harness-step`, quand tu veux aller plus loin, fait un pas vers le palier que tu vises et s'arrête : la boucle de retour `rule:` (palier 2), un garde-fou par règle (palier 3), le processus de travail et un contrat de tâche (palier 4).
3. `harness-harvest` collecte les signaux depuis le dernier harvest et ouvre une PR de proposition : push-down en CI, ajout, raccourcissement, retrait, nouveau contrat.
4. `harness-audit` relit quand le modèle change ou tous les six mois : règles racontées sans garde-fou, et lignes qui ne servent plus.

## Installation

### Comme plugin (recommandé)

Dans Claude Code :

```
/plugin marketplace add jrechet/harness-ai
/plugin install harness-ai@harness-ai
```

### À la main

Copier un dossier de `skills/` dans `~/.claude/skills/` (global) ou dans `.claude/skills/` d'un repo (versionné avec l'équipe) :

```bash
git clone https://github.com/jrechet/harness-ai.git
cp -r harness-ai/skills/harness-audit ~/.claude/skills/
```

## Utilisation

Les skills se déclenchent sur leur description (« audite mes skills », « remets à plat mon AGENTS.md », « est-ce qu'on peut couper l'agent ? ») ou explicitement :

```
/harness-audit
```

## Structure du dépôt

```
harness-ai/
├── .claude-plugin/
│   ├── plugin.json          # manifeste du plugin
│   └── marketplace.json     # pour /plugin marketplace add
├── app/                     # application de suivi (Vue 3 vendorisé, sans build), servie par `harness serve`
├── cli/
│   ├── harness.py           # point d'entrée : status, target, rules, harvest github, fixture, bench, serve, place, report
│   ├── harnesslib/          # facts, maturity, status, rules, github, fixtures, bench, serve, place, report (stdlib uniquement)
│   │   ├── placement.json   # la grille de placement : questions fermées et destinations
│   │   └── report_template.html # le gabarit du rapport d'état des lieux
│   └── tests/               # python3 -m unittest discover -s cli/tests
├── fixtures/                # fixtures d'audit, projets types avec leurs tâches, registre des résultats
├── docs/
│   ├── cahier-des-charges.md # ce que harness-ai doit tenir, et où on en est
│   └── maturity.md          # le modèle de maturité et ses seuils
├── skills/
│   ├── harness-audit/
│   ├── harness-init/
│   ├── harness-step/
│   ├── harness-harvest/
│   ├── harness-design/
│   └── <nom-du-skill>/
│       ├── SKILL.md         # instructions chargées par l'agent
│       └── references/      # fichiers lus à la demande (templates, grilles)
├── .claude/skills/harness-stress/   # skill de mainteneur : met les skills à l'épreuve sur fixtures/, à la demande
└── README.md
```

Conventions :
- un `SKILL.md` reste court (procédure, vocabulaire, cas d'abandon) ; la référence longue va dans `references/` ;
- tout ce qui doit être **garanti** va dans `cli/`, pas dans le texte des skills ; les skills appellent le CLI ;
- chaque skill produit un format de sortie stable pour pouvoir comparer deux exécutions.
