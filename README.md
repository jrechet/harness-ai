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
| [`harness-init`](skills/harness-init/SKILL.md) | Met en place l'instrumentation IA d'un repo à partir de zéro : entretien (délégation par défaut ou assistance), reconnaissance, AGENTS.md court comme source unique, stubs CLAUDE.md / Copilot / Cursor, premier contrat de tâche, convention de retour `rule:`, puis harness-audit en mode gate. |
| [`harness-harvest`](skills/harness-harvest/SKILL.md) | Fait évoluer AGENTS.md et les contrats à partir de l'activité depuis le dernier harvest : `rule:`, corrections après coup sur PRs d'agent, checks ignorés, règles orphelines, tâches récurrentes. Un catalogue de signaux indépendant de la source, GitHub en premier adaptateur, une PR dédiée avec un commit par candidat. |
| [`harness-audit`](skills/harness-audit/SKILL.md) | Audite un harness ou un AGENTS.md/CLAUDE.md, classe chaque élément dans la grille L1–L4, rend un verdict par élément (KEEP / INLINE / PUSH_DOWN / PROMOTE / MERGE / SPLIT / BLOCK) et un plan de remédiation. Rapport à format fixe (Markdown + JSON) défini dans `references/report-template.md`. |

## Progression mesurée

`harness status` calcule le palier de maturité du repo à partir de faits (fichiers, règles, dernier audit, dernier harvest), écrit `.harness/state.json` et dit quoi faire ensuite. Cinq paliers : Rien, Cadré, Bouclé, Vérifié, Délégué. Modèle et seuils dans [docs/maturity.md](docs/maturity.md).

```bash
python3 cli/harness.py status <chemin-du-repo>
```

### Voir la progression

```bash
python3 cli/harness.py serve <chemin-du-repo>
```

Ouvre http://127.0.0.1:8787 : une application Vue locale, sans build ni dépendance, qui lit l'état courant et l'historique des `state.json` commités. Paliers avec leurs vérifications, prochaines actions, faits mesurés, courbe de progression, couches L1 à L4 depuis le dernier audit. L'application n'affiche que ce que le CLI mesure.

## Parcours

1. `harness-init` pose le squelette et la boucle de retour, et vise le palier 1.
2. L'équipe marque les incidents en review avec `rule:` ; les règles entrent de préférence en CI, sinon dans AGENTS.md avec leur justification.
3. `harness-audit` relit périodiquement : règles racontées sans garde-fou, coût de contexte, règles orphelines à retirer.
4. `harness-harvest` collecte les signaux depuis le dernier harvest et ouvre une PR de proposition : push-down en CI, ajout, raccourcissement, retrait, nouveau contrat.

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
│   ├── harness.py           # point d'entrée : status, harvest github, fixture check, serve
│   ├── harnesslib/          # facts, maturity, status, github, fixtures, serve (stdlib uniquement)
│   └── tests/               # python3 -m unittest discover -s cli/tests
├── fixtures/                # fixtures d'audit et projets types, pour évaluer les skills
├── docs/
│   ├── cahier-des-charges.md # ce que harness-ai doit tenir, et où on en est
│   └── maturity.md          # le modèle de maturité et ses seuils
├── skills/
│   ├── harness-audit/
│   ├── harness-init/
│   ├── harness-harvest/
│   └── <nom-du-skill>/
│       ├── SKILL.md         # instructions chargées par l'agent
│       └── references/      # fichiers lus à la demande (templates, grilles)
└── README.md
```

Conventions :
- un `SKILL.md` reste court (procédure, vocabulaire, cas d'abandon) ; la référence longue va dans `references/` ;
- tout ce qui doit être **garanti** va dans `cli/`, pas dans le texte des skills ; les skills appellent le CLI ;
- chaque skill produit un format de sortie stable pour pouvoir comparer deux exécutions.
