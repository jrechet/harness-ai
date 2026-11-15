# Notes

## Ce qui m'a gêné
- **Pré-condition sans gravité (fichiers non commités, morceau 11).** « Pas un incident, mais l'agent ne doit pas pouvoir l'oublier » n'a pas de chemin évident. En `rule`, `incident=no` envoie vers `scope`, donc vers du texte que l'agent peut sauter : la grille n'a pas de « règle sans gravité mais tenue pour l'agent ». J'ai répondu `limit` + `bypass_limit=agent` (Permission, avec hook PreToolUse sur la commande de release), parce que la phrase borne une action de l'agent et qu'un développeur peut passer outre sans incident. `compute` + `when=agent_loop` (hook) menait à un endroit voisin ; rien dans le skill ne départage les deux.
- **Version mal calculée = incident.** La grille n'a pas de question `incident` sous `compute` : la réponse du propriétaire ne change pas la destination du calcul (CLI). Elle justifierait une règle « la version publiée est celle que le calcul rend », en étape bloquante du workflow de livraison, mais ce morceau n'existe pas dans l'artefact et le skill ne dit pas si une revue peut ajouter un morceau sans `current`. Je ne l'ai pas ajouté.
- **`current` d'une phrase de skill que rien ne tient.** Le skill donne `session` pour un choix laissé à l'agent et `ci_check` pour une règle portée par un check, mais pas le cas courant : une vérification ou une action racontée dans le SKILL.md. J'ai mis `skill`.
- **`when` du calcul de version** : `on_demand` (le skill et le workflow de livraison l'appellent tous deux), pas `repo_event`. La grille ne dit pas quoi répondre quand deux appelants existent.
- **Dépôt sans CLI** : la destination dit « sous-commande du CLI du dépôt » ; ici ce sera un script de `package.json` (le tableau de l'étape 5 le prévoit, pas le texte du plan).
- `place plan` accepte `evidence` sans le vérifier ni l'afficher ; seul `report from-place` s'en sert.

## Sous le plan (ni morceaux, ni placés)
- À confirmer : le job `commitlint` (ci.yml:12) est-il un check requis sur `main` ? Réglage de la forge, illisible d'ici. Il ne tourne que sur `pull_request` vers `main`.
- Contradiction : SKILL.md:16 demande à l'agent de copier le jeton dans `.npmrc`, AGENTS.md:6 l'autorise « hors d'une release » seulement, le propriétaire dit « jamais lisible par l'agent ». Une fois la publication dans le workflow de livraison (morceau 6), le jeton devient un secret d'environnement protégé sur GitHub et la phrase disparaît du skill ; l'exception « hors d'une release » d'AGENTS.md:6 tombe.
- Morceau 5 : la protection est l'environnement protégé GitHub restreint à `main` (réglage d'administrateur), pas le `git branch --show-current` du skill.
- Étape à déplacer : la vérification `git status` est en étape 8 (SKILL.md:19) alors qu'elle conditionne le début ; la vérification de branche (étape 3) vient après le calcul.
- Outil manquant : `release-reviewer` n'a que `Read, Grep` et doit lire « les commits depuis le dernier tag » ; il lui faut un accès à l'historique git, ou que la liste lui soit fournie.
- Morceau 10 : aucun serveur MCP n'est déclaré dans l'artefact (pas de `.mcp.json` ni de `.claude/settings.json`) ; le skill ne dit pas par quel moyen l'annonce part aujourd'hui.

## Non placé
- `Mode : assistance` (AGENTS.md:3) : hors de la demande (les règles), laissé hors du plan.
- Rien d'autre : les 12 morceaux ont une destination, `place plan` sort en code 0.
