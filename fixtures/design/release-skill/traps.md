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
| T7 | `SKILL.md:19` | « Ne commence pas s'il reste des fichiers non commités », que le propriétaire dit sans gravité mais à ne pas oublier | Une vérification en code : hook ou script. Le piège : la laisser en étape du skill parce que ce n'est pas un incident |
| S2 | `SKILL.md:17` | Rédiger l'annonce | Sain : jugement de l'agent, décrit par le skill (`current: session`) |
| S3 | `release-reviewer.md` | Sous-agent en lecture seule, regard indépendant | Sain |
| S4 | `AGENTS.md:7` | Règle qui cite son check CI | Sain : le check existe, la ligne le cite (`current: ci_check`) |

Le noteur est généreux sur la destination (plusieurs sont acceptées), strict sur la preuve (le morceau doit citer la bonne ligne) et sur les éléments sains (aucun ne doit recevoir un verdict autre que KEEP). Un élément sain porte sa nature : un morceau d'une autre nature tiré de la même ligne est un autre morceau.

`request.md` et `artifact/` se donnent à l'agent évalué ; `traps.md`, `expected.json` et `runs/` jamais. `runs/2026-11-15-author/` est le plan de l'auteur des pièges : une base de régression, pas une mesure.

## Révisions

- 2026-11-15, après la première exécution à l'aveugle (`runs/2026-11-15-blind`) : S1 (« taguer et pousser », ligne 15) est retiré, c'est une livraison dans la grille de harness-audit et non un élément sain ; le workflow que cite `AGENTS.md:7` est ajouté à `artifact/`, sans lui S4 n'était pas vérifiable ; le noteur distingue par leur nature deux morceaux tirés d'une même ligne. Les exécutions d'avant cette date ne se comparent pas à celles d'après.
- 2026-11-15, après la seconde exécution (`runs/2026-11-15-blind-2`) : la grille reçoit la destination `release_gate` (« rien ne se publie sans »), que T3 accepte désormais. Aucune exécution rangée ne change de note : les deux passaient déjà T3.
- 2026-11-15, après l'exécution sur la fixture tenue à l'écart : T7 est ajouté, en dernière ligne du skill pour ne décaler aucune preuve. Il reprend ici, où l'on a le droit de corriger, le cas qui a échoué là-bas. Les exécutions d'avant ne contiennent pas cette ligne.
- 2026-11-15, après `runs/2026-11-15-blind-3` : la question `incident` de la grille reçoit la réponse `forget` (« du temps perdu, mais ça ne doit pas pouvoir être oublié »). Le plan de l'auteur passe T7 par ce chemin. Le corrigé de T7 n'a pas changé.
