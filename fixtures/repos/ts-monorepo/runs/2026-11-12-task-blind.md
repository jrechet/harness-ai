# Campagne du 2026-11-12 — tâche `escalated` rejouée sur ses trois bras

Le projet corrigé le 2026-11-11 : contrôle de types par workspace, aucune commande qui rejoue tout, énoncé sans le libellé, et un fait écrit nulle part dans le dépôt, la version du package partagé que `deskly-infra` épingle. Agents neutres et confinés, un tirage par bras.

| Bras | Instructions du dépôt | Note | Contrôles manqués | Tokens neufs | Tours | Durée |
|---|---|---|---|---|---|---|
| `bare` | aucune | 6/8 | `shared_version`, `guards_intact` | 66 000 | 25 | 75 s |
| `asis` | le `CLAUDE.md` généré | 7/8 | `shared_version` | 70 000 | 32 | 86 s |
| `harness` | `AGENTS.md` du pas 1 | 8/8 | aucun | 60 000 | 15 | 58 s |

## Ce que la mesure dit
**Le fait écrit nulle part ailleurs départage, comme prévu.** Seul le bras qui le porte monte la version, et il dit pourquoi : « c'est la règle du dépôt, pour que `deskly-infra` redéploie le stockage ». Les deux autres ne peuvent pas le deviner et ne le devinent pas.

Ce résultat est celui que la construction du banc annonce. Il montre deux choses, pas plus : qu'un fait posé dans le harness arrive jusqu'au travail rendu, et qu'un agent ne l'invente pas. Il ne dit rien de la façon dont le fait est entré dans le harness : le recueillir auprès du propriétaire est le travail du pas 1, que cette campagne ne joue pas.

**Le web n'a cassé sur aucun bras.** La tentation d'origine, s'arrêter au modèle partagé et à l'API, n'a pris personne : les trois agents ont lancé les tests et les types du web. L'agent sans instructions a trouvé le post-mortem et en a tiré la leçon tout seul.

**Le harness coûte moins.** Quinze tours contre vingt-cinq et trente-deux. Sur un tirage, c'est un indice.

## Un défaut du noteur
Le bras `bare` perd le contrôle `guards_intact` pour avoir **corrigé** le trou de CI : il a ajouté `packages/shared/**` au filtre du job `web`, en citant l'incident du 9 juin. C'est une bonne action que le contrôle punit, parce qu'il interdit toute modification de la CI au lieu d'interdire son affaiblissement. Sans ce défaut le bras ferait 7/8. La note du registre n'a pas été retouchée.

Corrigé le même jour, avec l'accord du propriétaire : le contrôle `ci_not_weakened` n'interdit plus que de retirer un contrôle ou de le rendre non bloquant. Renotée, cette exécution ne manque plus que le fait écrit nulle part ailleurs.

## Ce qu'elle ne dit pas
Un tirage par bras, un seul modèle.

Un reste de la session de campagne atteint encore les agents : l'environnement distant leur donne ses consignes d'attribution, qu'un compte rendu recopie en bas d'une description de PR. Il touche tous les bras de la même façon et ne porte sur aucun contrôle.
