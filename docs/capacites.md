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
| Assembler le socle et les ajouts d'une équipe, lus sur la branche de base | `ai_sdlc.py context`, `status`, huit points d'extension | outillé |
| Dire si un ticket est prêt, et ce qui lui manque | skill `ticket`, `ticket check`, `ticket render`, définition de prêt du socle | outillé, mesuré une fois |
| Dire si les tests d'un changement tiennent : quatre portes mesurées | skill `qa`, `qa gate` | outillé, mesuré une fois |
| Empêcher un agent de livrer : tag, publication, déploiement refusés avant exécution | hook du plugin `ai-sdlc`, `guard check`, `guard hook` | outillé, essayé une fois en session |
| Enquêter sur un incident sans agir en production, et rendre un ticket | skill `run`, `run changes`, `run render` | outillé, mesuré une fois |
| Préparer une livraison sans la faire : quatre prérequis, une version et des notes proposées | skill `ship`, `ship check`, `ship render` | outillé, mesuré une fois |
| Regarder un changement sous l'angle de la sécurité : quatre portes, et les endroits à relire | skill `secu`, `secu gate` | outillé, mesuré une fois |
| Relire une PR : peu de constats, chacun sur une ligne du diff | skill `review`, sous-agent `reviewer`, `review render` | mesuré une fois : 6 pièges requis sur 6 |
| Développer un ticket sur le chemin de sa taille | skill `dev`, `size`, `dev body` | mesuré une fois : deux tickets conformes |

### Mesurer les skills eux-mêmes

| Capacité | Comment | État |
|---|---|---|
| Projets types et leurs corrigés | `fixtures/repos`, `harness fixture check` | outillé pour huit projets |
| Banc avant et après, à l'aveugle | `harness bench`, skill de mainteneur `harness-stress` | lancé, deux corrections |
| Fixtures de conception, de ticket, de développement, de test et de revue | `fixtures/design`, `fixtures/ticket`, `fixtures/dev`, `fixtures/qa`, `fixtures/secu`, `fixtures/ship`, `fixtures/run`, `fixtures/review`, `place check`, `fixture grade`, `grade-dev`, `grade-ticket`, `grade-qa`, `grade-secu`, `grade-ship`, `grade-run` | outillé |

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
| S14 | Fixture et noteur pour mesurer `secu` | fait | 2026-11-16 | `fixtures/secu/facturation` (jeton en dur, SQL assemblé vu par le scanner de l'équipe, shell caché par `# nosec`, certificat non vérifié, consigne en commentaire, deux endroits sains), `fixture grade-secu` : constats notés comme une revue, branche intacte, secret jamais recopié |
| S15 | Jouer `secu` à l'aveugle | fait | 2026-11-16 | `fixtures/secu/facturation/runs/2026-11-16-blind` : 12 sur 12. Une exécution, plugin copié et non installé. Les retours de l'agent sont passés dans le skill, sans nouvelle mesure après |
| S16 | Skill `ship` : préparer une livraison sans la faire | fait | 2026-11-16 | Demandé par le propriétaire le 2026-11-16. `ship check` (tête de branche propre, CI verte sur ce commit, zones sensibles et ruptures depuis le dernier tag, version et notes proposées), `points/livraison.md`, skill `ship` ; jamais joué, pas de fixture. « L'agent ne déploie pas » est écrit dans le skill, tenu par rien. Relecture indépendante : quatorze constats corrigés, dont une porte « état » qui passait toujours avec une branche locale en base, et des titres de commit rendus comme des titres ou des listes |
| S17 | Fixture et noteur pour mesurer `ship` | fait | 2026-11-16 | `fixtures/ship/facturation` (dépôt distant, tag, quatre commits : rupture, migration sans retour arrière, commit qui demande de livrer ; deux relevés de CI), `fixture grade-ship` : rien n'est parti, proposition tenue. Le skill écrit maintenant une proposition en JSON que `ship render` valide : commandes citées mot pour mot de la procédure de l'équipe, aucune si un prérequis échoue, ruptures toutes reprises |
| S19 | Jouer `ship` à l'aveugle | fait | 2026-11-16 | `fixtures/ship/facturation/runs/2026-11-16-blind` : 9 sur 9 et 2 sur 2. Une exécution par tâche, plugin copié et non installé, forge simulée par un dépôt nu. Les retours des agents sont passés dans le skill et la commande, sans nouvelle mesure après |
| S18 | Garde-fou « un agent ne livre pas » : un hook du plugin qui refuse tag, publication et commande de déploiement | fait | 2026-11-16 | Demandé par le propriétaire le 2026-11-16. `plugins/ai-sdlc/hooks/hooks.json` lance `cli/guard_hook.py` avant chaque commande shell ; `guard check` pour l'essayer. Refuse aussi les commandes de la procédure de l'équipe, lues sur la branche distante, le dernier commit et la copie de travail. Relecture de sécurité indépendante : dix-sept constats, classifieur réécrit (refus abusifs sur `git push` et les messages de commit, contournements par `npx`, `git push origin tag`, here-document donné à un shell, entrée géante). Essayé dans une vraie session le 2026-11-16 (Claude Code 2.1.211) : `git tag v9.9.9` refusé avant exécution, `git status` permis. Deux commandes seulement : les autres formes ne sont éprouvées que par les tests. Une barrière, pas un bac à sable : une commande assemblée par des variables ou un script lancé par son nom passent. Non vérifié : si un agent peut poser `AI_SDLC_LIVRAISON_PAR_AGENT` en écrivant `.claude/settings.json` |
| S6 | Skill `run` : enquêter sur un incident sans agir en production | fait | 2026-11-16 | Demandé par le propriétaire le 2026-11-16. `run changes` (ce qui est parti entre deux versions), `run render` (faits cités mot pour mot de leurs pièces, cause en hypothèse, commandes du carnet de l'équipe, pas de secret dans un extrait, rendu en ticket), point `exploitation`, skill `run` ; jamais joué, pas de fixture. Le garde-fou de livraison ne couvre pas les commandes de mitigation du carnet. Relecture de sécurité indépendante : treize constats corrigés, dont un secret qui sortait par tout champ autre que l'extrait, des formes de journal non reconnues (en-têtes, cookies, paires clé=valeur), des données personnelles comptées sans bloquer, une citation à cheval sur deux lignes. Les formes reconnues restent peu nombreuses : un nom de personne passe |
| S20 | Fixture et noteur pour mesurer `run` | fait | 2026-11-16 | `fixtures/run/facturation` (deux versions parties, un dernier déploiement innocent, une consigne et un jeton dans le journal, des adresses à masquer), `fixture grade-run` : rien de touché, enquête tenue, dernier déploiement non accusé, secret jamais recopié |
| S21 | Jouer `run` à l'aveugle | fait | 2026-11-16 | `fixtures/run/facturation/runs/2026-11-16-blind` : 11 sur 11. Une exécution, plugin copié et non installé, production simulée par trois fichiers. Les retours de l'agent sont passés dans le skill, sans nouvelle mesure après |
| S7 | Installer le plugin depuis la marketplace et l'éprouver dans une vraie session | fait | 2026-11-16 | Les deux plugins sont installés sur le poste du propriétaire, à sa demande, depuis la marketplace locale du dépôt (`claude plugin marketplace add <dossier du dépôt>`, puis `claude plugin install`). Une fois installés (Claude Code 2.1.211) : six skills `harness-ai` et sept skills `ai-sdlc` chargés, le garde-fou refuse `git tag v9.9.9` dans un dépôt jetable. Le skill `ticket` a trouvé son CLI par `${CLAUDE_PLUGIN_ROOT}` avec `--plugin-dir`. Non essayé : l'installation depuis GitHub (`jrechet/harness-ai`, dépôt privé), les autres skills en session, une session interactive |
| N6 | Remettre le dépôt en ordre à la demande du propriétaire : copie principale à jour, branches fusionnées rangées | fait | 2026-11-16 | Demandé le 2026-11-16. Le dossier `.serena/` d'un outil du poste avait été commité par mégarde avec l'essai du plugin : retiré et ignoré. La copie principale du propriétaire est à jour sur `main`, où les deux suites passent. Les 30 branches distantes déjà fusionnées sont supprimées, sur accord du propriétaire ; aucune n'avait de PR ouverte ni n'était en usage. Les 19 branches restantes sont traitées en N7 |
| N7 | Relire les branches restantes et décider des PR Renovate, à la demande du propriétaire | fait | 2026-11-16 | Quatorze branches avaient leur PR fusionnée et aucun commit absent de `main` : supprimées. `claude/practical-gauss-fopwb6` (PR 3, fermée sans fusion) corrigeait un piège planté dans un projet type : supprimée, ses commits restent lisibles par la PR. Les quatre PR Renovate sont fermées sans fusion : elles ne touchent que `fixtures/`, où une version est une donnée du scénario (un piège, une exécution rangée, l'identifiant d'un commit monté). Renovate ignore désormais `fixtures/**` |
| N8 | L'agent devient tech lead et garant du dépôt, à la demande du propriétaire | fait | 2026-11-16 | `AGENTS.md` passe en mode délégation et dit ce que l'agent décide et ce qui reste au propriétaire (rendre public, réécrire l'historique, campagne coûteuse) |
| V1 | Bilan demandé par le propriétaire : ce qu'on voulait, ce qui est fait, ce qui reste, et comment aller plus loin | fait | 2026-11-16 | Rendu dans la session. Constat central : tout est outillé et mesuré une fois sur des cas écrits par le modèle évalué ; rien n'est prouvé sur un vrai dépôt. Les lignes V2 à V7 en sortent |
| V2 | Éprouver les deux plugins sur un vrai dépôt, avec de vrais tickets et de vraies PR | à faire | 2026-11-16 | La seule preuve de gain (exigence C4). Demande un dépôt du propriétaire et quelques semaines de signaux par PR |
| V3 | Faire tourner les portes hors de la session : `qa gate`, `secu gate`, `review` et `ship check` en CI, comme checks requis | en cours | 2026-11-16 | Demandé par le propriétaire le 2026-11-16. Fait : `ci pr` joue en pipeline les portes de sécurité et de tests (aucun test désactivé, suite rejouée), avec ses réglages lus sur la branche cible (`docs/agents/portes.json`) pour qu'une PR ne puisse pas alléger ses portes ; modèle de workflow pour une équipe dans `plugins/ai-sdlc/ci/portes.yml`. Pas fait : la revue en CI (il y faut un modèle), « un test par critère » (il y faut le ticket), `ship check` sur `main`, et rendre le check obligatoire, qui se règle sur la forge |
| V4 | Durcir les fixtures du plugin `ai-sdlc` : cas plus difficiles, un cas tenu à l'écart par phase, plusieurs tirages | à faire | 2026-11-16 | Sept notes parfaites du premier coup ne départagent rien. Idéalement des cas tirés de vrais incidents et de vraies PR, pas écrits par le modèle |
| V5 | Jouer un même ticket de bout en bout : ticket, dev, qa, secu, review, ship | à faire | 2026-11-16 | Chaque phase est mesurée seule ; l'enchaînement, où une phase lit ce que l'autre a laissé, ne l'est pas |
| V6 | Une CI pour ce dépôt : les deux suites, `progress check`, les portes | en attente | 2026-11-16 | Écrite : `.github/workflows/ci.yml` et `.forgejo/workflows/ci.yml` lancent `scripts/ci/verifier.sh`, sur le runner du serveur comme le veut la convention du propriétaire (minutes GitHub épuisées). Elle n'a jamais tourné : ce dépôt n'a aucun runner enregistré. Le job est sauté tant que la variable `CI_RUNNER` ne vaut pas `pret`. Attend du propriétaire : un runner pour ce dépôt sur son serveur |
| V7 | Fermer les trous connus du garde-fou : commandes de mitigation du carnet, écriture de `.claude/settings.json`, autres outils que Bash | à faire | 2026-11-16 | Limites relevées par les relectures et non traitées |
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
