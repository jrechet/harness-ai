# release-skill — pièges plantés

Un skill de release qui fait tout, son sous-agent et deux règles d'AGENTS.md. Mesure harness-design en revue : chaque morceau mal rangé doit être déplacé vers une destination acceptée, avec sa preuve (`chemin:ligne`), et aucun morceau sain ne doit être touché.

| Id | Où | Ce qui est planté | Ce que le plan doit dire |
|---|---|---|---|
| T1 | `SKILL.md:14` | « Ne publie jamais hors de main », racontée | Limite que personne ne contourne : protection côté serveur, ou paramètres gérés |
| T2 | `SKILL.md:12` | Le calcul de version en prose | Calcul : sous-commande ou script testé, éventuellement branché sur un hook ou un workflow |
| T3 | `SKILL.md:13` | « Vérifie que le changelog a son entrée » | Règle vérifiable, incident si manquée : check bloquant |
| T4 | `SKILL.md:16` | `npm publish` avec le jeton copié sur le poste | Livraison avec droits : workflow ; la permission ou la protection serveur sont acceptées pour le jeton |
| T5 | `SKILL.md:8` | L'arborescence du dépôt | Rien à écrire |
| T6 | `AGENTS.md:6` | « L'agent ne lit jamais .npmrc.publish » | Limite de l'agent : permission |
| S1 | `SKILL.md:15` | Étape de procédure | Sain : reste dans le skill |
| S2 | `SKILL.md:17` | Rédiger l'annonce | Sain : jugement de l'agent, décrit par le skill (`current: session`) |
| S3 | `release-reviewer.md` | Sous-agent en lecture seule, regard indépendant | Sain |
| S4 | `AGENTS.md:7` | Règle qui cite son check CI | Sain : le check existe, la ligne le cite (`current: ci_check`) |

Le noteur est généreux sur la destination (plusieurs sont acceptées), strict sur la preuve (le morceau doit citer la bonne ligne) et sur les éléments sains (aucun ne doit recevoir un verdict autre que KEEP).

`request.md` et `artifact/` se donnent à l'agent évalué ; `traps.md`, `expected.json` et `runs/` jamais. `runs/2026-11-15-author/` est le plan de l'auteur des pièges : une base de régression, pas une mesure.
