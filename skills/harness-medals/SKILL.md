---
name: harness-medals
description: Dit où en est un dépôt ou une marketplace de plugins sous forme de médaille (bronze, argent, or, platine), de succès débloqués et de prochaines étapes, et ouvre la page interactive qui les montre. Tout vient de mesures faites par `harness medals` dans le dépôt, jamais d'une appréciation. Utiliser quand l'utilisateur demande « à quel niveau on est », « pourquoi bronze » ou « pourquoi pas or », « quels succès on a débloqués », « que faire pour passer au rang suivant », « montre la page des médailles », ou veut un badge de maturité. Ne pas utiliser pour poser ou faire avancer l'instrumentation (harness-init, harness-step) ni pour l'auditer (harness-audit) : ce skill montre, il ne change rien d'autre que son fichier de médailles.
---

# Harness medals — le niveau, et pourquoi

Une médaille n'est pas une note. C'est le palier que `harness status` mesure, dit avec un nom qu'on retient, et découpé en succès qu'on débloque un par un. Ce skill n'évalue rien lui-même : il lance la commande et lit sa sortie.

Trois règles :
- **Tout chiffre vient de la commande.** Ne dis jamais « vous êtes plutôt or » : lance, puis cite.
- **Une médaille ne dit pas que les agents travaillent mieux.** Elle dit que le harness a une forme. La preuve du gain est ailleurs (le banc, les signaux par PR). Dis-le si on te demande ce que vaut la médaille.
- **On ne joue pas avec les règles pour débloquer un succès.** Un succès se débloque en faisant ce qu'il mesure. Écrire « Vérifiée par » devant une règle sans garde-fou est une triche que l'audit verra.

## Déroulé

### 1. Ce qu'on mesure
Un dépôt (`--kind repo`, le défaut) ou la marketplace de plugins qu'il déclare (`--kind marketplace`, s'il a un `.claude-plugin/marketplace.json`). Si la demande ne le dit pas et que les deux existent, donne le dépôt et propose l'autre en une ligne.

### 2. Mesurer
`python3 cli/harness.py medals <repo> [--kind marketplace]` (CLI du dépôt harness-ai). `--name <nom>` fixe le nom affiché (par défaut celui du fichier de médailles s'il existe, sinon celui du dossier), `--format json` rend les données. Il rend la médaille, la phrase qui dit pourquoi, les succès par rang avec leur date, les succès hors rang, et les prochaines étapes.

### 3. Répondre à la question posée
- **« Pourquoi ce niveau ? »** : la phrase « pourquoi », puis les succès qui manquent au rang suivant, chacun avec ce qui est mesuré.
- **« Quels succès ? »** : la liste débloquée, avec les dates. Un succès marqué « perdu » se dit en premier : c'est une régression.
- **« Et ensuite ? »** : les prochaines étapes, dans l'ordre. Une étape « en attente » ne dépend pas que de l'utilisateur (un harvest doit trouver un signal réel) : dis-le, ne la présente pas comme une tâche. Pour faire l'étape, c'est harness-step.

Ne recopie pas toute la sortie si on t'a posé une question précise.

### 4. La page
Sur demande, ou si l'utilisateur veut « voir » : `python3 cli/harness.py medals <repo> --page <fichier.html>`. La page est un seul fichier, sans ressource externe, avec ses données dedans. Écris-la hors du dépôt sauf si l'utilisateur la veut dedans, et ouvre-la.

### 5. Le fichier du dépôt
`--write` met à jour `.harness/medals.json` (`.harness/medals-marketplace.json` pour une marketplace). Il garde la date où chaque succès a été débloqué et le parcours des médailles. Si la mesure n'a pas changé, le fichier n'est pas réécrit : sa date est celle du dernier changement. Ne l'écris que si l'utilisateur le demande ou si le fichier existe déjà. Qu'il soit commité est son choix : commité, il se voit en revue et un badge peut le lire.

## Pièges fréquents
- **Annoncer une médaille de mémoire.** Elle a pu changer : un harvest de plus de 45 jours fait perdre un succès d'argent.
- **Présenter la médaille comme un objectif.** `harness target` dit où l'utilisateur veut s'arrêter. Bronze est un endroit où l'on peut rester.
- **Confondre les deux mesures.** La médaille d'un dépôt et celle de sa marketplace ne mesurent pas la même chose, et peuvent différer.
