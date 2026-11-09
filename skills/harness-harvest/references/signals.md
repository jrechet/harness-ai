# Catalogue des signaux

Ce qu'on cherche, indépendamment de la source. Chaque adaptateur (GitHub d'abord) ne fait que produire ces signaux dans le schéma commun ci-dessous. Un signal qui n'est pas dans ce catalogue n'est pas collecté : on ajoute d'abord ici, puis dans l'adaptateur.

## Les signaux, du plus fort au plus faible

| Id | Signal | Ce qu'il dit | Force | Verdict typique |
|---|---|---|---|---|
| **S1** | Règle explicite : commentaire de review commençant par `rule:` | Quelqu'un a déjà formulé la règle et pointe l'incident | Forte, suffit seul | PUSH_DOWN si outil possible, sinon ADD |
| **S2** | Correction après coup : commit de fix sur des fichiers touchés par une PR d'agent dans les 48 h suivant son merge ; revert ; PR d'agent fermée sans merge ; rafale de commits « fix review » | Il manquait une information ou une règle à l'agent | Forte si répétée, moyenne isolée | ADD ou ASK |
| **S3** | Correction récurrente : le même motif de commentaire de review (même reviewer ou même zone) au moins deux fois dans la fenêtre | Une règle implicite de l'équipe non écrite | Moyenne | ADD avec les liens, ou PUSH_DOWN |
| **S4** | Garde-fou ignoré : un check CI qui échoue de façon répétée sur des PRs d'agent | La règle existe en L3 mais l'agent ne la connaît pas ou la découvre trop tard | Moyenne | SHORTEN ou ADD d'une ligne « Vérifiée par » bien placée |
| **S5** | Règle orpheline : une règle de AGENTS.md sans aucune évidence liée dans la fenêtre | Soit elle est si bien respectée qu'on peut la raccourcir, soit elle est morte | Faible seule, forte après deux harvests | SHORTEN si garde-fou, REMOVE sinon après deux harvests |
| **S6** | Tâche récurrente : au moins trois PRs du même type dans la fenêtre (titre, label, fichiers) | Un contrat de tâche manque | Moyenne | CONTRACT |
| **S7** | Information non découvrable demandée : l'agent pose la même question ou fait la même hypothèse dans plusieurs PRs | AGENTS.md ne dit pas une chose qu'on ne peut pas déduire du code | Moyenne | ADD dans « Ce que fait ce repo » ou « Ce qui change → ce qu'on lance » |

Ce qu'on ne cherche **pas** : des conventions devinées dans le diff sans incident, le style, les préférences exprimées une fois sans `rule:`.

## Schéma d'évidence commun

Chaque adaptateur produit un tableau JSON de ce type, une entrée par évidence :

```json
{
  "id": "<source>-<n>",
  "signal": "S1|S2|S3|S4|S5|S6|S7",
  "source": "github|gitlab|jira|...",
  "url": "<lien permanent vers la preuve>",
  "date": "<AAAA-MM-JJ>",
  "author": "<login>",
  "agent_authored": true,
  "files": ["<chemin>"],
  "text": "<texte brut utile : le commentaire, le titre de PR, le nom du check>",
  "related_rule": "<extrait de la règle de AGENTS.md concernée, ou null>",
  "group_key": "<clé de regroupement proposée par l'adaptateur : zone, reviewer+motif, type de tâche>"
}
```

Le script ne juge pas : il ne décide ni du verdict ni de la formulation. Il ne fait que repérer, dater, lier et proposer une clé de regroupement.

## Adaptateur GitHub — `cli/harness.py harvest github`

Python 3 standard, sans dépendance ; transport `gh api` (déjà authentifié sur un poste de dev et dans les sessions Claude Code).

```
python3 cli/harness.py harvest github --repo owner/repo --agents-md AGENTS.md \
    --agent-login claude --agent-branch-prefix claude/ --agent-label agent \
    --agent-trailer "Co-Authored-By: Claude" --summary > .harness/harvest.json
```

- Fenêtre : `--since AAAA-MM-JJ`, sinon le marqueur `<!-- harvest: last=… -->` de `--agents-md`, sinon 30 jours (annoncé sur stderr).
- Marqueurs d'agent, tous répétables : `--agent-login`, `--agent-branch-prefix`, `--agent-label`, `--agent-trailer`. Un login en `[bot]` est toujours un agent.
- Robots de dépendances (`--automation-branch-prefix`, défaut `renovate/` et `dependabot/`) : ni agent, ni tâche récurrente, et leurs merges ne sont pas des corrections. Un squash-merge d'une autre PR ne compte comme correction (S2) que si cette PR est un fix/revert ou cite la PR d'agent. Les commentaires de l'auteur sur sa propre PR ne comptent jamais en S3.
- Seuils exposés : `--fix-window-hours 48`, `--min-recurrence 2` (S3, S4, S7), `--min-task-count 3` (S6), `--burst-commits 3`, `--burst-minutes 60`, `--max-prs 200`.
- Sortie : sur stdout, un objet `{source, repo, since, default_branch, prs_scanned, agent_prs, counts, errors, evidence}` où `evidence` est le tableau du schéma ci-dessus. Erreurs sur stderr ; code de retour 2 si une source n'a pas pu être lue, les autres évidences sont quand même produites.
- Récurrence (S3, S6, S7) : regroupement glouton par similarité de Jaccard sur les mots-clés, seuils 0,6 / 0,6 / 0,5 en constantes du script. `group_key` porte les mots communs du groupe.
- Tests : `python3 -m unittest discover -s cli/tests`, sans réseau, sur un dépôt factice qui exerce les sept signaux.

| Signal | Où le trouver | Règle de détection |
|---|---|---|
| S1 | Commentaires de review et de PR | Corps qui commence par `rule:` (insensible à la casse, espaces tolérés) |
| S2 | Commits sur la branche par défaut, PRs | Commit non-agent touchant un fichier d'une PR d'agent fusionnée moins de 48 h avant ; commit dont le message commence par `Revert` d'une PR d'agent ; PR d'agent fermée sans merge ; au moins trois commits en moins d'une heure après une review sur une PR d'agent |
| S3 | Commentaires de review | Même auteur et texte normalisé similaire (mêmes mots-clés après suppression du bruit) sur au moins deux PRs |
| S4 | Checks des PRs d'agent | Même nom de check en échec sur au moins deux PRs d'agent distinctes |
| S5 | AGENTS.md courant | Pour chaque puce du fichier (hors sections Maintenance, Tâches, Commandes ; lignes de continuation jointes), aucune évidence S1–S4 dont `related_rule` la pointe ; le lien se fait par mots-clés et par fichiers cités |
| S6 | Titres, labels et fichiers des PRs | Au moins trois PRs dont le titre normalisé ou le label est identique, ou dont les fichiers touchés se recouvrent fortement |
| S7 | Descriptions de PRs d'agent | Phrases interrogatives ou d'hypothèse (« j'ai supposé », « je n'ai pas trouvé ») sur le même sujet dans au moins deux PRs |

Les seuils (48 h, deux, trois) sont des défauts à exposer en options du script, pas des constantes.

## Adaptateurs suivants
- **GitLab** : mêmes signaux, mêmes seuils ; les notes de MR remplacent les commentaires de review.
- **Jira / Linear** : ne produit que S6 et S7 (types de tâches récurrentes, questions répétées dans les tickets). Un ticket ne produit jamais S1 à S5.
