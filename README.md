# harness-ai

> **In short (English).** A toolkit for making a repository work well with AI coding agents: a Python CLI that measures what is in place, and Claude Code skills that put it in place one step at a time. Everything here, from the CLI output to the skills, is written in French.

Des skills Claude Code et un CLI Python pour instrumenter un dépôt pour les agents IA : un `AGENTS.md` court qui ne dit que l'utile, des règles tenues par des outils plutôt que par des phrases, et de quoi mesurer où l'on en est.

L'idée directrice tient en une ligne : **le prompt explique, le code vérifie, le pipeline exécute.** Ce qui doit être garanti ne s'écrit pas dans un prompt.

## Essayer en deux minutes, sans Claude Code

Il faut Python 3.10 ou plus et git. Rien à installer : le CLI n'utilise que la bibliothèque standard.

```bash
git clone https://github.com/jrechet/harness-ai.git
```

```bash
python3 harness-ai/cli/harness.py status /chemin/de/ton/depot
```

`status` dit à quel palier est ton dépôt, de 0 (rien) à 4 (délégué), ce qui est acquis et la prochaine action. Il écrit `.harness/state.json` dans ton dépôt. Puis, au choix :

```bash
python3 harness-ai/cli/harness.py commands /chemin/de/ton/depot
```

```bash
python3 harness-ai/cli/harness.py medals /chemin/de/ton/depot --page medailles.html
```

`commands` liste les commandes que ta CI lance et qu'un agent ne devinerait pas (« `make it`, pas `mvn verify` »). `medals` rend le même niveau en médaille, avec les succès débloqués, et écrit une page à ouvrir dans un navigateur ([exemple](docs/exemples/medailles.html), figé au 2026-11-15).

## Ce que tu peux faire aujourd'hui

Trois niveaux de confiance, toujours les mêmes mots : **éprouvé** (lancé sur un clone neuf, tests à l'appui), **mesuré** (un agent sans le corrigé l'a joué, et un programme a noté le résultat), **écrit** (le skill existe, personne ne l'a encore joué de bout en bout).

### Avec le CLI seul

| Tu veux… | Commande | État |
|---|---|---|
| Savoir où en est ton dépôt | `harness.py status <repo>` | éprouvé |
| Dire à quel palier tu t'arrêtes | `harness.py target <palier> <repo>` | éprouvé |
| Voir chaque règle, son âge, son garde-fou | `harness.py rules <repo>` | éprouvé |
| Trouver les commandes qu'un agent ne devine pas | `harness.py commands <repo>` | éprouvé |
| Savoir ce qui a vieilli : un skill qui cite un fichier disparu, un harvest en retard | `harness.py fresh <repo>` | éprouvé |
| Voir ton niveau en médaille, avec les succès et les prochaines étapes | `harness.py medals <repo> [--write] [--page F]` | éprouvé |
| Savoir où ranger un morceau de skill ou d'agent : AGENTS.md, CLI, hook, permission, CI… | `harness.py place grid`, `place one`, `place plan <morceaux.json>` | éprouvé |
| Écrire un état des lieux en une page HTML | `harness.py report build <rapport.json> -o <page.html>` | éprouvé |
| Suivre la progression dans une page locale | `harness.py serve <repo>` | éprouvé, rendu non revu |

`<repo>` est le chemin de ton dépôt ; sans lui, c'est le dossier courant. Les exemples d'entrée sont dans [docs/exemples/](docs/exemples/) : `rapport.json` pour `report build`, `morceaux.json` pour `place plan` et `report from-place`.

### Avec Claude Code

| Tu veux… | Skill | État |
|---|---|---|
| Poser un premier `AGENTS.md` court, ou nettoyer celui que tu as | `harness-init` | mesuré sur quatre projets types |
| Avancer d'un palier, et t'arrêter | `harness-step` | mesuré sur un projet |
| Auditer ton harness et retirer ce qui ne sert plus | `harness-audit` | mesuré une fois sur deux projets |
| Créer ou revoir un skill, un agent, une règle, en mettant chaque morceau à sa place | `harness-design` | mesuré : 12 pièges sur 12 sur un cas tenu à l'écart |
| Demander « pourquoi ce niveau ? » | `harness-medals` | écrit |
| Tirer des règles de ce qui s'est passé dans tes PR | `harness-harvest` | écrit, jamais joué |
| Savoir si un ticket est prêt, et ce qui lui manque | `ticket` (plugin `ai-sdlc`) | écrit |
| Faire relire une PR : peu de commentaires, chacun sur une ligne du diff | `review` (plugin `ai-sdlc`) | mesuré une fois : 6 pièges sur 6 |
| Faire développer un ticket jusqu'à la PR, sur le chemin de sa taille | `dev` (plugin `ai-sdlc`) | mesuré une fois : deux tickets conformes |

Une mesure est un tirage, pas une moyenne, et les cas d'essai ont été écrits par le modèle qu'on évalue dessus : ils sont plus faciles qu'un vrai dépôt. Le détail est dans [docs/capacites.md](docs/capacites.md) et [docs/cahier-des-charges.md](docs/cahier-des-charges.md).

### Ce qui n'existe pas encore

- Les phases `qa`, `secu`, `ship` et `run` du plugin `ai-sdlc` : prévues, pas écrites.
- La preuve d'un gain sur un vrai dépôt. Ce que le projet mesure, c'est que ses mécanismes fonctionnent sur des projets types.
- Une CI pour ce dépôt : ses tests se lancent à la main.
- Une version anglaise.

## Installer les skills dans Claude Code

```
/plugin marketplace add jrechet/harness-ai
/plugin install harness-ai@harness-ai
/plugin install ai-sdlc@harness-ai
```

Un skill se déclenche sur sa description (« audite mon AGENTS.md », « relis cette PR ») ou par son nom : `/harness-ai:harness-init`, `/ai-sdlc:review`.

**Ce qui est vérifié, et ce qui ne l'est pas.** Les deux manifestes passent `claude plugin validate`. Les skills appellent leur CLI par `${CLAUDE_PLUGIN_ROOT}`, que Claude Code remplace par le dossier d'installation du plugin. L'installation depuis la marketplace elle-même n'a pas encore été essayée de bout en bout : si un skill ne trouve pas son CLI, lance la commande à la main depuis ton clone, comme plus haut, et ouvre une issue.

Pour essayer sans installer : `claude --plugin-dir /chemin/vers/harness-ai`.

## Les idées derrière

### Quatre couches

Chaque responsabilité d'un harness a un étage naturel. La plupart des problèmes de fiabilité viennent d'une responsabilité posée au mauvais étage.

| Couche | Rôle | Porté par |
|---|---|---|
| **L1 Jugement** | Décider entre des options ouvertes, dialoguer avec l'humain | L'agent, ses sous-agents |
| **L2 Procédure** | Raconter l'ordre, quand appeler quoi, comment lire un retour | Skills, AGENTS.md |
| **L3 Logique locale** | Garantir : pré-conditions, calculs, idempotence | CLI testé, linters, tests d'architecture |
| **L4 Exécution distante** | Agir avec des droits sur des ressources partagées | CI, pipeline |

Le test : si on coupe L1 et L2, est-ce que L3 et L4 suffisent à un humain pressé ? Si oui, l'agent est un accélérateur. Si non, du processus a fui dans les prompts.

### Cinq paliers, et le droit de s'arrêter

| Palier | Médaille | Ce que ça veut dire |
|---|---|---|
| 0 Rien | aucune | L'agent part de zéro à chaque session |
| 1 Cadré | bronze | Un `AGENTS.md` court, un mode, des interdits |
| 2 Bouclé | argent | Les incidents deviennent des règles |
| 3 Vérifié | or | Les règles obligatoires sont tenues par des outils |
| 4 Délégué | platine | Des tâches entières reviennent propres |

Un palier est un endroit où l'on peut rester. Tu dis lequel tu vises (`harness target`), et au-delà l'outil ne propose rien. Le palier mesure la forme du harness, pas le travail des agents. Modèle et seuils : [docs/maturity.md](docs/maturity.md).

### Le parcours type

1. `harness-init` pose le palier 1. On peut s'arrêter là.
2. `harness-step` fait un pas vers le palier visé : la boucle de retour `rule:` en revue, un garde-fou par règle, puis le processus de travail.
3. `harness-harvest` transforme ce qui s'est passé dans les PR en propositions de règles.
4. `harness-audit` relit quand le modèle change ou tous les six mois, et `harness fresh` dit entre-temps ce qui a vieilli.

## Le plugin ai-sdlc

Un second plugin, dans [plugins/ai-sdlc/](plugins/ai-sdlc/), outille les phases du cycle de développement : un socle commun que chaque équipe complète dans son dépôt, par un fichier `docs/agents/<point>.md`. Ces ajouts se lisent sur la branche cible, pas dans la PR : une PR ne peut pas alléger sa propre revue. Sa conception est dans [docs/ai-sdlc/proposition.md](docs/ai-sdlc/proposition.md).

Son CLI se lance aussi à la main. Sur un dépôt sans dépôt distant, donne la branche cible avec `--base` :

```bash
python3 harness-ai/plugins/ai-sdlc/cli/ai_sdlc.py status /chemin/de/ton/depot --base main
```

| Commande | Rôle |
|---|---|
| `status` | Les sept points d'extension : convention du socle, surchargé, ou invalide |
| `context <phase>` | Le socle et les ajouts de l'équipe, avec leur provenance |
| `ticket check <ticket.md>` | Un ticket est-il prêt : besoin décrit, critères listés, rien d'ouvert, et la taille annoncée par les chemins cités |
| `size [--paths …]` | La taille d'un changement (XS, S-M, L) par règles : fichiers, lignes, zones sensibles |
| `dev body <corps.json>` | Le corps d'une PR, refusé s'il est incomplet pour sa taille |
| `review render <revue.json>` | Une revue en commentaires, refusée si un constat ne cite pas une ligne du diff |

## Ce que ce dépôt fait quand tu l'ouvres avec Claude Code

Son `.claude/settings.json` déclare trois hooks, qui lancent `cli/harness.py` : un rappel à chaque message, une vérification de fin de tour qui demande de tenir [docs/capacites.md](docs/capacites.md) à jour, et un contrôle de fraîcheur en début de session. Ils lisent le dépôt et git, n'écrivent rien et n'appellent aucun réseau. Ce sont les règles de travail de ce dépôt, pas une fonction pour le tien. Lis le fichier avant d'accepter la confiance du dossier.

`harness serve` écoute sur `127.0.0.1:8787`, sans authentification : ne le lance pas avec `--host 0.0.0.0`. Si le port est pris, donne `--port`.

## Contribuer et vérifier

```bash
python3 -m unittest discover -s cli/tests
```

```bash
python3 -m unittest discover -s plugins/ai-sdlc/cli/tests
```

Les deux suites passent sur un clone neuf, de Python 3.10 à 3.14. Les règles du dépôt sont dans [AGENTS.md](AGENTS.md). Les skills se mesurent sur des projets types et des cas piégés, dans [fixtures/](fixtures/README.md) : un agent qui n'a jamais vu le corrigé joue le skill, et un programme note ce qu'il laisse.

## Où trouver quoi

| Dossier | Contenu |
|---|---|
| `cli/` | Le CLI `harness.py` et ses tests |
| `skills/` | Les six skills du plugin `harness-ai` |
| `plugins/ai-sdlc/` | Le second plugin : skills `ticket`, `dev` et `review`, son CLI |
| `fixtures/` | Projets types, cas piégés, corrigés, exécutions rangées |
| `app/` | La page de suivi servie par `harness serve` |
| `docs/` | Ce que le dépôt sait faire ([capacites.md](docs/capacites.md)), le modèle de maturité, l'étude et un [cours interactif](docs/ai-sdlc/cours/index.html) |
| `.harness/` | L'état mesuré de ce dépôt par lui-même |

## Licence

MIT, voir [LICENSE](LICENSE).
