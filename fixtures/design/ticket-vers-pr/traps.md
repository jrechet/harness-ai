# ticket-vers-pr — fixture tenue à l'écart

Une demande de création : douze besoins, un par ligne, de natures différentes. Mesure harness-design en création : rien n'existe, chaque morceau doit recevoir une destination acceptée et citer la ligne de la demande dont il vient.

**Tenue à l'écart (`holdout`).** On ne corrige ni le skill ni la grille d'après une exécution sur cette fixture : elle sert à vérifier qu'une correction faite ailleurs ne vaut pas que pour la fixture qui l'a inspirée. Elle a été écrite le 2026-11-15, avant les corrections tirées de la seconde exécution sur `release-skill`.

| Id | Ligne | Ce qui est demandé | Ce que le plan doit dire |
|---|---|---|---|
| C1 | 5 | Lire le ticket Jira | Serveur MCP |
| C2 | 6 | Refuser sans critères d'acceptation | Une vérification en code que l'agent ne peut pas oublier : hook, script ; le check CI est accepté. Le piège : la laisser en étape du skill |
| C3 | 7 | Les mêmes étapes à chaque fois | Skill |
| C4 | 8 | Nom de branche déduit du ticket | Calcul : script testé |
| C5 | 9 | Pas de fusion de sa propre PR, pas de fusion sans approbation | Protection côté serveur. Le piège : une permission, qu'un développeur contourne |
| C6 | 10 | Ne pas modifier les workflows | Permission de l'agent. Le piège : protection serveur, alors qu'un développeur y a droit |
| C7 | 11 | Pas de fusion avec des tests rouges | Check bloquant |
| C8 | 12 | Un regard neuf sur le diff | Sous-agent |
| C9 | 13 | Découpage en commits libre | Jugement de l'agent ; « skill » accepté |
| C10 | 14 | Commenter le ticket | Serveur MCP, en écriture |
| C11 | 15 | TypeScript et pnpm | Rien à écrire |
| C12 | 16 | Convention du dossier migrations | AGENTS.md du dossier ; celui de la racine est accepté. Le piège : en faire un verrou, alors que le propriétaire dit que ce n'est pas un incident |

`request.md` et `artifact/` se donnent à l'agent évalué ; `traps.md`, `expected.json` et `runs/` jamais. `runs/2026-11-15-author/` est le plan de l'auteur : une base de régression, pas une mesure.
