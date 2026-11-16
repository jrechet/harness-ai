# Ce que harness-ai sait faire, et où on en est

Dernière mise à jour : 2026-11-16

Ce document liste ce que le dépôt sait faire aujourd'hui, et tient le plan d'avancement. Il est mis à jour dans le même changement que le travail : un hook de fin de tour (`harness progress check`) renvoie l'agent l'écrire tant que le dépôt change sans lui. Les exigences d'origine et leur niveau de preuve restent dans [cahier-des-charges.md](cahier-des-charges.md).

Trois mots pour l'état d'une capacité, repris du cahier des charges : **outillé** (le mécanisme existe et il est testé), **mesuré** (une exécution à l'aveugle l'a éprouvé), **prouvé** (la mesure montre un gain).

## Ce que le dépôt sait faire

### Instrumenter un dépôt, un palier à la fois

| Capacité | Comment | État |
|---|---|---|
| Poser le palier 1 : un AGENTS.md court, mode, règles datées, Interdits | skill `harness-init` | mesuré sur quatre projets types |
| Avancer d'un pas vers le palier visé, et s'arrêter | skill `harness-step`, `harness target` | mesuré sur un projet |
| Mesurer le palier 0 à 4 et la vue par couche | `harness status`, écrit `.harness/state.json` | outillé |
| Faire naître des règles de ce qui s'est passé (revues, corrections, checks rouges) | skill `harness-harvest`, `harness harvest github` | outillé, jamais joué |
| Auditer un harness, classer chaque élément L1 à L4, proposer les retraits | skill `harness-audit`, `harness rules` | mesuré une fois sur deux projets |
| Proposer les commandes qu'un agent ne devine pas | `harness commands`, appelé par init et audit | outillé |
| Dire ce qui a vieilli : un skill ou un agent qui cite un fichier disparu ou modifié depuis, un harvest en retard | `harness fresh`, hook de début de session | outillé |
| Suivre l'état dans une application locale | `harness serve` | outillé |
| Dire le niveau en médaille, succès débloqués et prochaines étapes, avec une page interactive | skill `harness-medals`, `harness medals`, `.harness/medals.json` | outillé |

### Concevoir ou revoir un skill, un agent, une règle

| Capacité | Comment | État |
|---|---|---|
| Dire où va chaque morceau : AGENTS.md, skill, sous-agent, CLI, hook, permission, MCP, CI, paramètre géré, rien | skill `harness-design`, `harness place` (9 questions, 20 destinations) | mesuré : 7 sur 7 sur `release-skill`, 12 sur 12 sur la fixture tenue à l'écart après correction de la grille (11 sur 12 avant) |
| Rendre un état des lieux en une page HTML, toujours au même format | `harness report build`, `report from-place` | outillé |

### Outiller le cycle de développement (plugin `ai-sdlc`)

| Capacité | Comment | État |
|---|---|---|
| Assembler le socle et les ajouts d'une équipe, lus sur la branche de base | `ai_sdlc.py context`, `status`, sept points d'extension | outillé |
| Dire si un ticket est prêt, et ce qui lui manque | skill `ticket`, `ticket check`, `ticket render`, définition de prêt du socle | outillé, mesuré une fois |
| Dire si les tests d'un changement tiennent : quatre portes mesurées | skill `qa`, `qa gate` | outillé, mesuré une fois |
| Regarder un changement sous l'angle de la sécurité : quatre portes, et les endroits à relire | skill `secu`, `secu gate` | outillé, jamais joué |
| Relire une PR : peu de constats, chacun sur une ligne du diff | skill `review`, sous-agent `reviewer`, `review render` | mesuré une fois : 6 pièges requis sur 6 |
| Développer un ticket sur le chemin de sa taille | skill `dev`, `size`, `dev body` | mesuré une fois : deux tickets conformes |

### Mesurer les skills eux-mêmes

| Capacité | Comment | État |
|---|---|---|
| Projets types et leurs corrigés | `fixtures/repos`, `harness fixture check` | outillé pour huit projets |
| Banc avant et après, à l'aveugle | `harness bench`, skill de mainteneur `harness-stress` | lancé, deux corrections |
| Fixtures de conception, de ticket, de développement, de test et de revue | `fixtures/design`, `fixtures/ticket`, `fixtures/dev`, `fixtures/qa`, `fixtures/review`, `place check`, `fixture grade`, `grade-dev`, `grade-ticket`, `grade-qa` | outillé |

### Documenter

| Capacité | Où | État |
|---|---|---|
| Étude des pratiques, rapport complémentaire, proposition de framework | `docs/ai-sdlc/` | écrit |
| Cours interactif : neuf chapitres, QCM, lexique | `docs/ai-sdlc/cours/index.html` | écrit, publié en artifact privé |

## Plan d'avancement

États : `fait`, `en cours`, `à faire`, `en attente` (d'une décision ou d'une demande du propriétaire), `écarté`. Une ligne par sujet. Une demande nouvelle du propriétaire ajoute une ligne, datée.

| # | Sujet | État | Depuis | Preuve, ou ce qui manque |
|---|---|---|---|---|
| H1 | Poser, faire avancer et auditer l'instrumentation d'un dépôt (init, step, audit, status) | fait | 2026-11 | Niveau de preuve par exigence dans le cahier des charges |
| H2 | Jouer `harness-harvest` au moins une fois | à faire | 2026-11-10 | Il lui faut un historique de PR rejouable hors ligne |
| H3 | `harness-audit` lit la grille de placement et rend le rapport commun | à faire | 2026-11-14 | Attend l'accord avec l'autre session, qui tient ce skill |
| D1 | Grille de placement et skill `harness-design` | fait | 2026-11-14 | PR 12 à 20 ; 7 sur 7 à l'aveugle après la correction `incident=forget` |
| D2 | Rejouer la fixture tenue à l'écart `ticket-vers-pr` depuis la correction de la grille | fait | 2026-11-15 | `runs/2026-11-15-blind-2` : 12 sur 12, une exécution. Trois limites de la grille notées dans son journal, non corrigées d'après elle |
| R1 | Rapport commun en une page HTML | fait | 2026-11-14 | `harness report`, `docs/exemples/rapport-skill-release.html` |
| S1 | Plugin `ai-sdlc` : contexte, points d'extension | fait | 2026-11-15 | PR 22 |
| S2 | Skill `review`, rendu par le CLI, PR piégée, première mesure | fait | 2026-11-15 | PR 23 et 24 ; une seule exécution, fixture sans doute trop facile |
| S3 | Skill `dev`, taille calculée, corps de PR | fait | 2026-11-15 | PR 25 ; jamais joué |
| S4 | Fixture et noteur pour mesurer `dev` | fait | 2026-11-15 | `fixtures/dev/facturation`, `fixture grade-dev` ; le travail de l'auteur passe, c'est une base de régression |
| S8 | Jouer `dev` à l'aveugle sur ses deux tickets | fait | 2026-11-15 | `fixtures/dev/facturation/runs/2026-11-15-blind` : 12 sur 12 et 4 sur 4. Une exécution par ticket, plugin copié et non installé |
| S5 | Skill `ticket` : contrôle d'un ticket, définition de prêt du socle | fait | 2026-11-16 | `ticket check`, skill `ticket` ; jamais joué, pas de fixture |
| S9 | Skill `qa` : tests dérivés des critères d'acceptation, portes déterministes | fait | 2026-11-16 | `qa gate` (désactivés, répété, couverture du diff, un test par critère), skill `qa` ; jamais joué, pas de fixture |
| S11 | Fixture et noteur pour mesurer `qa` | fait | 2026-11-16 | `fixtures/qa/facturation`, `fixture grade-qa` : les tests de l'agent joués sur une référence et sept variantes fautives. Pas de test instable dans la fixture. Les travaux de l'auteur passent, c'est une base de régression. Relecture indépendante : trois faux « conforme » corrigés, dont un qui touchait aussi `grade-dev` (un `print("OK")` cachait un test sauté) |
| S10 | Fixture et noteur pour mesurer `ticket` | fait | 2026-11-16 | `fixtures/ticket/facturation` (trois tickets : flou et piégé, sain, prêt sur la forme seulement), `fixture grade-ticket`. Le skill écrit maintenant un avis en JSON que `ticket render` valide : verdict mesuré, critères sourcés ou à confirmer, consignes citées mot pour mot |
| S12 | Jouer `ticket` et `qa` à l'aveugle | fait | 2026-11-16 | `runs/2026-11-16-blind` : `ticket` 10 sur 10, 8 sur 8, 9 sur 9 ; `qa` 10 sur 10, sept variantes tuées. Une exécution par cas, plugin copié et non installé. Les retours des agents sont passés dans le texte des skills et le rendu, sans nouvelle mesure après |
| S13 | Skill `secu` : portes de sécurité sur un changement, convention du socle | fait | 2026-11-16 | Demandé par le propriétaire le 2026-11-16. `secu gate` (secrets, scanners neutralisés, résultats SARIF sur les lignes ajoutées, surface à relire), `points/securite.md`, skill `secu` ; jamais joué, pas de fixture. Les motifs de secrets sont peu nombreux : la commande ne remplace pas un scanner. Relecture de sécurité indépendante : treize constats corrigés, dont un secret caché derrière un séparateur de ligne, des résultats de scanner perdus sur `.github/…`, et un secret ajouté puis retiré dans la branche |
| S14 | Fixture pour mesurer `secu` | à faire | 2026-11-16 | Un changement avec un secret, une exception posée, un résultat de scanner, un appel à risque sain et un autre non |
| S6 | Skills `ship`, `run` | à faire | 2026-11-14 | Viennent en dernier |
| S7 | Installer le plugin depuis la marketplace et éprouver `${CLAUDE_PLUGIN_ROOT}` | en attente | 2026-11-15 | Les manifestes passent `claude plugin validate` et la doc de Claude Code confirme la substitution dans un skill de plugin. L'installation réelle n'a pas pu être essayée : la commande `claude` du poste n'était pas authentifiée. À faire par le propriétaire, deux minutes |
| C1 | Étude, rapport complémentaire, proposition | fait | 2026-11-14 | `docs/ai-sdlc/` |
| C2 | Cours interactif, approfondi : bases vectorielles, phases, scénario BI | fait | 2026-11-15 | PR 21 et 26 ; rendu publié non regardé |
| M1 | Proposer les commandes exactes qu'un AGENTS.md devrait dire | fait | 2026-11-15 | `harness commands` ; init et audit l'appellent, sans exécution à l'aveugle depuis |
| M2 | Proposer le code trompeur (un dossier qui a l'air mort et sert encore) | à faire | 2026-11-15 | Même modèle : des candidates posées en questions |
| M3 | Noter dans les corrigés les lignes qui auraient dû être proposées | en attente | 2026-11-15 | Modifier un corrigé change toutes les notes : décision du propriétaire |
| B1 | Boucle contre l'obsolescence des skills et des agents : `harness fresh` et un hook de début de session | fait | 2026-11-15 | `harness fresh`, hook `SessionStart` de ce dépôt, succès « hors rang » des médailles. Pas de consigne « post-usage » dans chaque skill ni de skill `/refresh` : du texte qu'un agent saute, et un doublon de harvest |
| G1 | Médailles (bronze, argent, or, platine), succès débloqués, page HTML interactive tirée de données dures | fait | 2026-11-15 | `harness medals`, skill `harness-medals`, `docs/exemples/medailles.html` ; pour un dépôt et pour une marketplace. Page regardée en clair et en sombre, bureau et mobile, dans un seul navigateur |
| G2 | La description de `harness-audit` dit quand ne pas l'utiliser (dernier succès d'argent de la marketplace) | à faire | 2026-11-15 | `harness medals --kind marketplace` : 9 succès sur 10 ; ce skill est à l'autre session |
| P1 | Ce document, et le hook qui oblige à tenir son plan | fait | 2026-11-15 | `harness progress check`, `.claude/settings.json` |
| N1 | Nuit du 15 au 16 : éprouver chaque commande et chaque skill comme un nouvel utilisateur, sur un clone neuf | fait | 2026-11-15 | Essai par un agent sur un clone de `main` : les deux CLI marchent de Python 3.10 à 3.14, les deux suites passent. Un défaut bloquant corrigé : les skills `harness-*` appelaient `cli/harness.py`, introuvable une fois installés ; ils passent par `${CLAUDE_PLUGIN_ROOT}` |
| N2 | README réécrit autour de « ce que tu peux faire aujourd'hui », chaque commande citée vérifiée par exécution | fait | 2026-11-15 | `cli/tests/test_readme.py` tient ses liens, ses sous-commandes, ses exemples et ses skills |
| N3 | Revue avant publication : secrets, données personnelles, chemins locaux, licence, promesses non tenues | en attente | 2026-11-16 | Revue faite : aucun secret réel dans l'arbre ni l'historique. Licence MIT posée (`LICENSE`), choisie par le propriétaire le 2026-11-16 ; lien de session privée retiré. Restent au propriétaire : ses deux adresses e-mail et 94 liens de session dans l'historique des commits, 30 branches distantes |
| N4 | Compte rendu du matin : ce qui est utilisable, ce qui ne l'est pas, et un avis « publier ou pas » | fait | 2026-11-15 | Rendu dans la session ; l'avis : pas avant d'avoir tranché la licence et l'historique des commits, et essayé une installation réelle |
| N5 | Défauts de premier usage relevés par l'essai, non corrigés : `serve` sur un port pris et `fixture check` sur un nom inconnu sortent une trace ; `harvest github` sans `gh` écrit un harvest vide ; `.harness/state.json` commité est périmé | à faire | 2026-11-15 | Modules tenus par l'autre session ; aucun n'empêche de démarrer |
