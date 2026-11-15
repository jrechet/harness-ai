# Notes

## Ce qui m'a manqué ou gêné
- **Morceau 9, `current=ci_check` non démontrable depuis le dépôt.** Le skill dit d'ouvrir le workflow : le job `commitlint` existe (`ci.yml:12-19`), tourne sur les PR vers `main` et échoue sans `continue-on-error`. Mais « bloquant » dépend de la protection de branche (check requis), qui est sur la forge et que rien dans `artifact/` ne montre. J'ai retenu `ci_check` / KEEP ; si le check n'est pas requis, c'est un PUSH_DOWN. Le skill ne dit pas quoi faire quand le workflow s'ouvre mais que le caractère requis reste invisible.
- **Morceau 4, `bypass_rule=dev` mène à « rien ne fusionne sans »**, alors que l'exigence porte sur la publication, pas sur la fusion : une entrée de changelog pour une version se vérifie au moment de publier (étape du workflow de livraison), pas forcément à chaque PR. La grille n'a pas de réponse « rien ne se publie sans ». Destination gardée telle quelle, à brancher dans le workflow de release.
- **Morceau 5, limite ou règle ?** « Ne publie jamais hors de main » borne une action (limit → protection serveur), mais concrètement c'est l'environnement protégé du workflow de livraison (branche de déploiement = `main`) et les droits du jeton npm : la destination recouvre celle des morceaux 6-7. Pas faux, mais le plan ne le relie pas.
- **Morceau 3, « une version mal calculée est un incident »** : la réponse du propriétaire parle d'incident, question qui n'existe que pour `rule`. Pour un `compute`, elle ne change rien à la destination (`cli`) ; j'ai supposé que les tests de la sous-commande la portent. `when=on_demand` choisi plutôt que `repo_event` : le skill et le workflow l'appellent tous deux.
- **Sans CLI dans le dépôt** (dit par le propriétaire) : « Sous-commande CLI testée » se lit comme un script npm de `package.json` ; le tableau de l'étape 5 le dit, la grille non.
- **Morceaux 6 et 7** : tag et publication ont la même nature et la même destination ; rien ne dit s'il faut un morceau ou deux. J'en ai fait deux (deux étapes, deux preuves).
- **« Sous le plan, une ligne par morceau »** alors que `plan.md` doit être la sortie telle quelle : j'ai mis ces lignes ici.

## Hors plan (à reformuler, pas des morceaux)
- `SKILL.md:16` demande à l'agent de copier le jeton de `.npmrc.publish` dans `.npmrc` : contredit la réponse du propriétaire (jamais lisible par l'agent) et s'appuie sur l'exception « hors d'une release » d'`AGENTS.md:6`. Phrase à retirer ; le jeton devient un secret de l'environnement protégé sur GitHub. Le jeton a déjà fuité (`AGENTS.md:6`) : à faire tourner.
- `release-reviewer.md:4` : outils `Read, Grep` seulement, alors qu'il doit lire « les commits depuis le dernier tag » (`release-reviewer.md:7`) : il lui manque un accès à `git log` (ou la liste des commits passée en entrée).
- `ci.yml` : `commitlint` ne contrôle que les commits de la PR ; avec une fusion en squash, le commit qui arrive sur `main` (titre de PR) n'est pas contrôlé, alors que la version s'en déduit.
- `SKILL.md:13` « arrête-toi et demande-la » et `SKILL.md:14` `git branch --show-current` : deviennent des appels aux commandes des morceaux 4 et 5, plus des phrases.
- Aucun `.claude/settings.json` ni serveur MCP déclaré dans `artifact/` : permission (8) et MCP (12) sont à créer.

## Ce que je n'ai pas pu placer
- Rien n'est resté sans destination. Réserve : « trois lignes au plus, sans reprendre le changelog mot pour mot » (`SKILL.md:17`) est resté dans le morceau 10 comme cadre du jugement (préférence, ton libre), pas comme règle à part.
