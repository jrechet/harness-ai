# Notes

## Ce qui m'a manqué ou gêné
- **Une préférence propre à un skill n'a pas de case.** « Trois lignes au plus, sans reprendre le changelog mot pour mot » (SKILL.md:17) : `rule` → `incident=no` → `scope`, et aucune option de `scope` ne dit « seulement pendant ce skill ». `reference` l'enverrait dans `docs/agents/`, ce qui est faux pour une phrase. Je l'ai laissée dans le morceau 8 (jugement), sans la placer à part : trou de la grille.
- **« Version mal calculée = incident » n'a pas d'endroit où se dire.** La branche `compute` ne demande que `when` ; la gravité ne change rien à la destination. J'ai répondu `on_demand` (CLI ; ici un script de `package.json`, le dépôt n'ayant pas de CLI), le workflow de livraison devant appeler le même script. Je n'ai pas ajouté de morceau « la version publiée est celle du calcul » : il n'existe pas dans l'artefact.
- **`current` d'un calcul ou d'une vérification écrits en prose dans un skill** : `skill` ou `session` ? Le piège du skill ne tranche que pour « un choix laissé à l'agent ». J'ai mis `skill` (le verdict est PUSH_DOWN dans les deux cas).
- **Publier hors de main : limite ou pré-condition ?** La phrase (SKILL.md:14) a la forme d'une vérification avant de continuer, et le piège « pré-condition = règle » tire vers `rule`/`release_gate`. J'ai gardé `limit` + `bypass_limit=dev` : elle borne une action et le propriétaire dit « personne, développeur compris ». Les deux lectures sont défendables ; le skill ne dit pas comment départager.
- **Hook pour « fichiers non commités »** : la destination parle d'un hook « après édition, ou à l'arrêt », alors qu'ici il faut un hook *avant* le lancement de la release (PreToolUse sur la commande de release). Et une fois la publication passée dans le workflow (morceau 6), le checkout CI est propre par construction : le hook ne garde que le démarrage local.
- `plan.md` est la sortie brute de `place plan` ; les lignes « sous le plan » demandées par le skill sont ci-dessous, faute d'endroit où les mettre sans altérer la sortie.

## Sous le plan (une ligne chacune, pas des morceaux)
- SKILL.md:16 fait copier le jeton par l'agent : contredit la réponse du propriétaire et AGENTS.md:6 (« hors d'une release » est l'exception à retirer). Avec le morceau 6, le jeton devient un secret d'environnement sur la forge.
- SKILL.md:19 : la vérification « fichiers non commités » est en étape 8, après la publication ; SKILL.md:14 vérifie la branche après le calcul. Ordre à reprendre.
- `release-reviewer` n'a que `Read, Grep` : il ne peut pas lire « les commits depuis le dernier tag » (release-reviewer.md:4 et :7). Outil manquant, ou commits à lui passer en entrée.
- Morceau 12 — à confirmer : le job `commitlint` est-il un check requis sur `main` ? Il ne tourne que sur `pull_request` (ci.yml:3-4) ; un push direct sur `main` y échappe sans protection de branche.
- Morceau 5 : réglage à faire par un administrateur de la forge (environnement protégé limité à `main`, publication npm par ce seul environnement). Rien dans le dépôt ne suffit.
- Morceau 9 : aucun serveur MCP ni `.claude/settings.json` dans l'artefact ; le système derrière `#releases` n'est pas nommé.

## Ce que je n'ai pas pu placer
- La contrainte de forme de l'annonce (trois lignes, pas de copie du changelog) : voir le premier point.
- Le job `test` de ci.yml : hors du périmètre demandé, non placé.
