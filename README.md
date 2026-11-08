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
| [`harness-audit`](skills/harness-audit/SKILL.md) | Audite un harness ou un AGENTS.md/CLAUDE.md, classe chaque élément dans la grille L1–L4, rend un verdict par élément (KEEP / INLINE / PUSH_DOWN / PROMOTE / MERGE / SPLIT / BLOCK) et un plan de remédiation. Rapport à format fixe (Markdown + JSON) défini dans `references/report-template.md`. |

## Parcours

1. `harness-init` pose le squelette et la boucle de retour.
2. L'équipe marque les incidents en review avec `rule:` ; les règles entrent de préférence en CI, sinon dans AGENTS.md avec leur justification.
3. `harness-audit` relit périodiquement : règles racontées sans garde-fou, coût de contexte, règles orphelines à retirer.
4. À venir : `harness-harvest`, qui collecte les `rule:` et les PRs d'agent rejetées et ouvre une PR de proposition.

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
├── skills/
│   ├── harness-audit/
│   ├── harness-init/
│   └── <nom-du-skill>/
│       ├── SKILL.md         # instructions chargées par l'agent
│       ├── references/      # fichiers lus à la demande (templates, grilles)
│       └── scripts/         # (optionnel) logique L3 déterministe
└── README.md
```

Conventions :
- un `SKILL.md` reste court (procédure, vocabulaire, cas d'abandon) ; la référence longue va dans `references/` ;
- tout ce qui doit être **garanti** va dans `scripts/` ou dans un CLI, pas dans le texte ;
- chaque skill produit un format de sortie stable pour pouvoir comparer deux exécutions.
