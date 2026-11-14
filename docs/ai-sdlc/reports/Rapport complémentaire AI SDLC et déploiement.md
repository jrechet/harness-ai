# Harness AI : état des lieux de l'AI SDLC dans les grandes entreprises tech et stratégie de déploiement sur des dizaines d'équipes

Votre intuition « convention over configuration » est la bonne, et c'est celle que suivent les acteurs les plus avancés : Stripe, Spotify, Uber, Doctolib et OpenAI ont tous centralisé une plateforme et des valeurs par défaut opinionnées, puis laissé chaque dépôt ajouter son contexte. Deux points de votre proposition doivent toutefois changer. D'abord, les surcharges en markdown ne peuvent pas porter les règles non négociables (sécurité, conformité). Ensuite, créer automatiquement des fichiers vides va à contre-courant de ce que l'industrie apprend en 2025-2026 sur le gonflement du contexte et la prolifération documentaire. Le levier principal n'est pas l'outil : c'est la maturité des fondations (tests, CI, petits lots, plateforme interne) et un pilotage du changement par niveaux.

## TL;DR

- **Les leaders standardisent la plateforme, pas la façon de travailler.** Stripe (Minions, plus de 1 000 PR fusionnées par semaine), Spotify (Honk, 1 000 PR fusionnées en 10 jours contre 3 mois auparavant, QCon London 2026), Uber (Minion, uReview, MCP Gateway) et Doctolib (pilote de 30 personnes puis généralisation) ont tous bâti un « harness » central. Il réutilise l'infrastructure humaine existante (devbox, CI, outils de migration) et des fichiers de contexte par dépôt (règles Cursor, CLAUDE.md, AGENTS.md). DORA 2025 le confirme : l'IA est un **amplificateur**, utile seulement là où les fondations sont saines.
- **Votre modèle de défauts et surcharges est bon, à trois conditions.** (1) Séparer une couche **non surchargeable**, imposée par la plateforme via des hooks, la CI et des politiques gérées, d'une couche **surchargeable** en markdown. (2) Remplacer le scaffolding de fichiers vides par une **découverte progressive** : ne créer que ce qui sert, ou générer le contenu à partir de l'analyse du dépôt. (3) Versionner et instrumenter le framework comme un produit interne.
- **Déployer par vagues et niveaux de maturité.** Commencer par des équipes pilotes volontaires et diverses, avec des champions par équipe, des métriques DORA et qualité plutôt que le « % de code généré », et des boucles de feedback hebdomadaires. Le METR (−19 % de vitesse mesurée contre +20 % ressentis) et GitClear (le copier-coller dépasse le code déplacé en 2024) rappellent que la productivité perçue n'est pas la productivité réelle.

---

## Partie 1 — État des lieux 2023-2026

### 1.1 Par entreprise

#### Anthropic (Claude Code)
- **Usage interne.** Anthropic a interrogé ses équipes : Product Engineering fait de Claude Code son « first stop » pour toute tâche de programmation. Les nouvelles recrues en data science de l'équipe Infrastructure s'appuient sur les fichiers CLAUDE.md pour comprendre les dépendances des pipelines. Security Engineering y injecte stack traces et documentation pendant les incidents. Product Design branche des maquettes Figma dans des boucles autonomes « écrire, tester, itérer ».\[1\]\[2\]\[3\]
- **Pratiques recommandées par les équipes.** Rédiger des CLAUDE.md détaillés. Passer par un serveur MCP plutôt qu'un CLI brut quand les données sont sensibles, pour garder le contrôle des accès. Organiser des sessions de partage où les membres se montrent leurs usages réels.\[2\] Selon l'équipe Claude Code elle-même : utiliser des configurations quasi « vanilla », le mode plan, un CLAUDE.md court enrichi correction après correction, et des boucles de vérification.\[4\] Le code critique se travaille en mode synchrone ; le mode auto-accept est réservé aux fonctionnalités périphériques.\[5\]
- **Mécanismes de standardisation.** Claude Code définit une **hiérarchie de configuration**. Les *managed settings* (serveur, MDM, fichier système) priment sur tout le reste,\[6\]\[7\] et l'organisation peut y injecter un CLAUDE.md « managé » chargé avant les CLAUDE.md utilisateur et projet.\[8\]\[9\] Viennent ensuite les arguments CLI, puis `.claude/settings.local.json`, `.claude/settings.json` et `~/.claude/settings.json`.\[6\]\[10\] Les administrateurs peuvent aussi n'autoriser que les hooks gérés (`allowManagedHooksOnly`), restreindre les marketplaces de plugins (`strictKnownMarketplaces`) et forcer l'installation de plugins sur tout le parc. Dans ce cas, désactiver un plugin à son propre niveau ne l'empêche pas de se charger, car les managed settings priment sur tous les autres niveaux.\[8\]\[11\]
- **Point clé pour Harness AI.** La documentation d'Anthropic distingue explicitement le **contexte d'instruction** (CLAUDE.md, règles : concaténé, non contraignant) des **politiques appliquées** (permissions, hooks, managed settings). Un fichier d'instructions ne fait pas respecter une permission d'outil.\[7\]\[12\]

#### Agent Skills et AGENTS.md (standards ouverts)
- **Agent Skills.** Lancé par Anthropic en octobre 2025 puis publié comme standard ouvert le 18 décembre 2025 (agentskills.io). Un skill est un dossier contenant un `SKILL.md` (frontmatter `name` et `description`) et, en option, `scripts/`, `references/` et `assets/`. Le principe de **divulgation progressive** est le suivant : au démarrage, seules les métadonnées sont chargées (environ 100 tokens par skill). Le corps, recommandé sous 5 000 tokens et 500 lignes, n'est chargé qu'à l'activation, et les ressources seulement si nécessaire. Le format est repris par OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI et VS Code.\[13\]\[14\]\[15\]
- **AGENTS.md.** Publié par OpenAI en août 2025, issu d'un travail collectif (Codex, Amp, Jules de Google, Cursor, Factory). Donné le 9 décembre 2025 à l'Agentic AI Foundation (Linux Foundation), cofondée par OpenAI, Anthropic et Block avec le soutien de Google, Microsoft, AWS, Bloomberg et Cloudflare. Le site du standard revendique plus de 60 000 projets open source utilisateurs. Une étude empirique sur 466 projets open source (arXiv 2510.21413, « Context Engineering for AI Agents in Open-Source Software ») constate toutefois que « there is no established structure yet for organizing content in AGENTS.md files » ; selon une autre étude arXiv, ces fichiers servent tantôt de document de gouvernance complet, tantôt de simple pointeur vers un autre fichier, tantôt d'hybride.

#### OpenAI — « Harness engineering »
- **L'expérience.** Le 11 février 2026, Ryan Lopopolo (OpenAI) décrit un produit interne construit en cinq mois sans aucune ligne de code écrite à la main : « on the order of a million lines of code », en environ un dixième du temps qu'aurait demandé une écriture manuelle, et environ 1 500 PR ouvertes et fusionnées par seulement trois ingénieurs pilotant Codex (3,5 PR par ingénieur et par jour), l'équipe étant ensuite passée à sept ingénieurs. Le rôle des ingénieurs devient de « permettre aux agents de faire un travail utile ».
- **Leçon directement applicable à Harness AI.** L'approche « un gros AGENTS.md » a échoué : elle encombrait le contexte, tout y semblait important et le fichier se périmait vite. L'équipe l'a remplacée par un AGENTS.md d'environ 100 lignes servant de **table des matières**, qui pointe vers un répertoire `docs/` structuré, système de référence versionné. Elle a aussi imposé l'architecture **mécaniquement** (linters, tests structurels) plutôt que par la seule documentation. Ce qui n'est pas dans le dépôt n'existe pas pour l'agent.\[16\]\[17\]\[18\]

#### GitHub (Copilot)
- **Hiérarchie d'instructions.** Le fichier `.github/copilot-instructions.md` s'applique à tout le dépôt. Les fichiers `.github/instructions/NAME.instructions.md` sont ciblés par chemin via un frontmatter `applyTo` (glob), avec une option `excludeAgent` pour exclure l'agent de code review ou le coding agent. S'y ajoutent `AGENTS.md`, `CLAUDE.md` et `GEMINI.md`, ainsi que des instructions d'organisation configurées dans l'interface GitHub.\[19\]\[20\]\[21\]
- **Ordre de priorité documenté sur GitHub.com.** Personnel, puis dépôt, puis organisation, tous les ensembles étant fournis à Copilot. Conséquence notable : un réglage personnel peut prendre le pas sur l'intention d'équipe.\[22\]\[23\]
- **Recommandation de GitHub.** Déplacer les règles spécifiques à un langage ou à un chemin dans des fichiers ciblés pour ne pas surcharger le fichier global. On peut aussi demander au coding agent de générer lui-même le fichier d'instructions, puis itérer.\[19\]\[24\]

#### Stripe — Minions
- **Le système.** Des agents « one-shot » entièrement non supervisés, lancés le plus souvent depuis Slack. Ils produisent une PR qui passe la CI, revue par un humain, sans code écrit par un humain. Ils sont responsables de **plus d'un millier de PR fusionnées par semaine**.\[25\]\[26\]\[27\]
- **L'infrastructure.** Ils tournent sur la **devbox** standard des ingénieurs (pré-chauffée, prête en 10 secondes) et sur un fork de goose (Block) adapté fin 2024.\[25\]\[28\]
- **Standardisation des règles.** Stripe synchronise ses **règles Cursor** dans un format lisible par Claude Code, pour que ses trois agents les plus utilisés (Minions, Cursor, Claude Code) profitent des mêmes règles, que les ingénieurs ajoutent progressivement dans le code.\[28\]
- **Boîte à outils restreinte.** Chaque agent ne demande qu'un sous-ensemble des outils internes (Toolshed) : les agents réussissent mieux dans une « smaller box » avec un ensemble d'outils choisi avec soin.\[28\]
- **Enseignement.** La réussite repose sur une décennie d'investissement dans l'outillage pour les humains.\[29\]

#### Spotify — Honk, Backstage, Fleet Management
- **L'agent.** Honk est un agent de code en arrière-plan basé sur Claude (Agent SDK), exécuté dans des pods Kubernetes. Il a d'abord servi aux migrations de flotte, sur la « longue traîne » d'environ 30 % de cas que les scripts déterministes ne savaient pas traiter, puis est devenu accessible depuis Slack.\[30\]\[31\]\[32\]
- **Volume.** À QCon London 2026, Jo Kelly-Fenton et Aleksandar Mitic résument : « we had 1,000 merged PRs in 3 months. Today, we do this in 10 days ».
- **Choix d'architecture clés.** Le runtime de l'agent est séparé du runtime de vérification (CI de confiance), et les diffs sont évalués par un LLM en plus du lint et du formatage.\[32\]\[33\]
- **Gouvernance.** Des advisory boards de seniors définissent des technologies « golden » ; Honk sert ensuite à pousser les migrations à 100 %.\[30\]
- **Cas des datasets.** Une migration de datasets touchait environ 1 800 pipelines en aval et a économisé environ 10 semaines-ingénieur. Lors de ces migrations, Honk n'avait volontairement **ni skills ni configuration personnalisable**, un garde-fou délibéré.\[34\]\[35\]
- **Conclusion de Spotify.** Le succès dépend de la **consolidation et de la standardisation** du paysage technique.\[35\]

#### Uber
- **Plateforme en couches** (présentée au Pragmatic Summit par Ty Smith, Principal Engineer, et Anshu Chada, Director of Engineering, session résumée par Gergely Orosz dans The Pragmatic Engineer le 10 mars 2026, ainsi que chez LangChain) :
  - **MCP Gateway** : accès centralisé aux API internes, avec authentification, logs et télémétrie ;\[36\]
  - **Agent Builder** (no-code) et **AIFX CLI** (provisionnement des agents) ;\[36\]
  - **Minion** : agents en arrière-plan avec accès au monorepo et « valeurs par défaut optimisées » ;\[37\]
  - **uReview** : revue de code IA qui filtre par niveau de confiance, après le constat que les outils externes produisaient trop de commentaires à faible valeur ;\[38\]
  - **Code Inbox** : routage des PR ;\[36\]
  - **Autocover** : génération de tests, environ 5 000 par mois.\[38\]
- **Chiffres rapportés début 2026.** Selon The Pragmatic Engineer (chiffres corrigés le 11 mars 2026), « 84% of devs at Uber are agentic coding users » et « 65-72% of code is AI-generated inside IDE-based tools » ; d'autres résumés citent 11 % des PR ouvertes par des agents et des coûts IA multipliés par 6 depuis 2024.
- **Constat d'Uber.** Selon The Pragmatic Engineer, « AI adoption is slower than expected » et « top-down mandates are less efficient than engineers sharing their wins with peers ».

#### Doctolib (France)
- **Trajectoire.** Pilote de Claude Code avec 30 ingénieurs, puis déploiement à toute l'équipe de développement, avec un auto-onboarding en moins de cinq minutes (VS Code, JetBrains, CLI).\[39\]
- **Socle central.** L'équipe plateforme a créé un **dépôt centralisé de prompts, commandes et sous-agents** que chaque développeur récupère à l'installation. Claude Code tourne en mode headless dans la CI pour la maintenance, la documentation mise à jour à chaque changement de code et la revue automatique des PR.\[39\]
- **Programme d'adoption** (Devoxx Belgium 2025). Programme **AI Champions**, **AI Summer Camp**, « AI Starter Kit », approche **LLMs.md** de contexte par dépôt. Le talk mentionne un **plateau d'adoption** et cinq points de friction.\[40\]
- **Chiffres d'adoption.** La presse française (Le Monde Informatique) rapporte que les 600 ingénieurs travaillent avec des agents depuis janvier 2026.\[41\] Une version récente de l'étude de cas Anthropic évoque environ 90 % des quelque 900 personnes de la tech et du produit utilisant Claude chaque jour, 47 % de PR en plus par ingénieur, un lead time de changement réduit de 25 % et 10 % des PR ouvertes par des agents distants.\[39\] Ces chiffres proviennent du fournisseur et ne figurent pas dans la version de la page que nous avons pu consulter.
- **Vision.** Mike Aidane (VP Platform Engineering) : « une software factory où les ingénieurs construisent et maintiennent les boucles agentiques ».\[39\]

#### Shopify
- **Le mémo.** En avril 2025, le CEO Tobi Lütke publie : « Reflexive AI usage is now a baseline expectation at Shopify. »\[42\]\[43\]
- **Ce qu'il impose.** L'IA est obligatoire dans la phase de prototypage (GSD), des questions sur l'usage de l'IA entrent dans les évaluations de performance et entre pairs, et les équipes doivent démontrer pourquoi l'IA ne suffit pas avant de demander des effectifs.\[44\]\[45\]
- **Limites.** C'est l'exemple type d'une adoption top-down culturelle. Ses limites sont documentées : dans un petit collectif, évaluer l'usage individuel produit du « théâtre ». En Allemagne, une surveillance systématique de l'usage relève de la codétermination du comité d'entreprise (§ 87 BetrVG), ce qui est pertinent pour un contexte européen.\[46\]

#### Amazon (Q Developer, transformations Java)
- **Résultats annoncés** (Andy Jassy, août 2024) : la mise à niveau d'une application vers Java 17 passe d'environ 50 jours-développeur à quelques heures. Plus de 50 % des systèmes Java de production ont été migrés en moins de six mois, soit environ 30 000 applications. Amazon estime l'économie à **4 500 années-développeur** et à 260 M$ par an. 79 % des revues de code générées automatiquement ont été livrées sans modification.\[47\]\[48\]\[49\]
- **Prudence.** Ce sont des estimations internes d'un éditeur qui vend l'outil. Le temps gagné a été calculé à partir du nombre de dépendances migrées, et les 260 M$ viennent des gains de performance de Java 17, pas de l'agent lui-même.\[50\]
- **Enseignement.** Les transformations **ciblées et vérifiables** (build et tests) sont le meilleur premier cas d'usage.

#### Google
- **Part de code généré.** Sundar Pichai annonce que plus de 25 % du nouveau code est généré par l'IA en octobre 2024, 50 % à l'automne 2025, puis **75 % « généré par l'IA et approuvé par des ingénieurs »** en avril 2026 (Cloud Next).\[51\]\[52\]\[53\]
- **Productivité.** Pichai considère la **vélocité d'ingénierie** comme la métrique la plus importante, et l'estimait à **+10 %**, mesurée en heures de capacité libérées par semaine.\[54\]
- **Ce que révèle l'écart.** 75 % de code IA contre +10 % de vélocité illustre parfaitement pourquoi le « % de code généré » est une mauvaise métrique de pilotage. Google n'a publié aucun taux de rejet.\[52\]\[55\]
- **Recherche.** Google porte aussi DORA (voir 1.2).

#### Airbnb
- **La migration.** Environ 3 500 fichiers de tests sont passés d'Enzyme à React Testing Library en **6 semaines**, contre 1,5 année estimée à la main.\[56\]
- **Comment.** Un pipeline par étapes (machine à états), des boucles de reprise et des prompts riches en contexte. Résultat : 75 % de réussite au premier passage de 4 heures, 97 % après 4 jours d'ajustement, et 3 % terminés à la main.\[56\]\[57\]
- **Enseignement.** Même modèle qu'Amazon et Spotify : migrations massives, validation automatique, humain en fin de chaîne.

#### Atlassian (Rovo Dev, agents Jira)
- **Du ticket à la PR.** Rovo Dev part du **ticket Jira** : il crée un plan de code à partir du ticket, génère le code et ouvre une PR Bitbucket. Il vérifie que les PR respectent les **critères d'acceptation** du ticket Jira lié, et diagnostique les builds en échec. Les « Agentic Pipelines » (correctifs automatiques en CI) sont en bêta.\[58\]\[59\]\[60\]\[61\]
- **Résultats internes, publiés par Atlassian et qui ne concordent pas entre eux :**
  - janvier 2026 : −45 % de temps de cycle des PR, sans méthodologie publiée ;\[62\]
  - avril 2026 : **−30,8 % du temps de cycle médian et −35,6 % de commentaires de revue humains** sur plus de 1 900 dépôts pendant un an, étude acceptée à ICSE 2026, la source la plus rigoureuse ;\[63\]
  - novembre 2026 : −31 % de temps de cycle médian, et 39 % des commentaires du Code Reviewer suivis d'un changement de code au commit suivant.\[64\]
- **Effet secondaire.** Atlassian note aussi que les équipes très dépendantes de l'IA attendent plus de deux fois plus longtemps une revue humaine (71 min contre 32). **La revue humaine devient le goulot.**\[64\]
- **Pertinence.** C'est le modèle le plus proche de votre « /dev sur un ticket Jira ».

#### Non couverts ou insuffisamment sourcés dans cette recherche
Microsoft (hors GitHub), Meta, Netflix, Zalando, BlaBlaCar, Criteo, Datadog, ManoMano et Malt n'ont pas pu être documentés à partir de sources primaires dans le budget de recherche. Les chiffres circulant sur ces entreprises (par exemple des pourcentages de code généré annoncés par des dirigeants) ne sont pas repris ici faute de vérification. C'est un chantier de veille à compléter, idéalement via les talks Devoxx France et les blogs d'ingénierie de ces entreprises.

### 1.2 Cadres conceptuels et études d'impact

**DORA 2025 (Google).** Selon Google Research, le rapport « State of AI-assisted Software Development » s'appuie sur plus de 100 heures de données qualitatives et sur les réponses de près de 5 000 professionnels de la tech. 90 % d'entre eux utilisent l'IA, mais l'IA est un **amplificateur** : elle magnifie les forces des organisations performantes et les dysfonctionnements des autres. Le **DORA AI Capabilities Model** identifie 7 capacités :\[65\]
1. une position claire et communiquée sur l'IA ;
2. des écosystèmes de données sains ;
3. des données internes accessibles à l'IA ;
4. une gestion de version solide ;
5. le travail en petits lots ;
6. une orientation utilisateur ;
7. des plateformes internes de qualité (« paved roads »).

Le rapport propose aussi **7 profils d'équipe**, de « Foundational challenges » à « Harmonious high achievers »,\[66\] ce qui fournit une base naturelle pour un adressage par niveaux de maturité.

**Harness et context engineering.** Le harness, c'est tout ce qui entoure le modèle : instructions, outils, règles appliquées mécaniquement (linters, hooks, CI) et boucles de nettoyage.\[16\] La leçon convergente d'OpenAI, de Stripe et d'Anthropic : des fichiers d'entrée **courts** qui pointent vers la documentation, et du contexte chargé à la demande.

**Spec-driven development.** GitHub Spec Kit (septembre 2025, avec une « constitution » de principes immuables), Kiro d'AWS (exigences, conception, tâches), Tessl (la spec comme source) et BMAD. Le Thoughtworks Radar l'a placé en **Assess** en novembre 2025, en avertissant que « handcrafting detailed rules for AI ultimately doesn't scale ».\[67\]\[68\]\[69\] Dans son évaluation, Birgitta Böckeler a vu Kiro transformer un petit bug en 4 user stories et 16 critères d'acceptation.\[70\] En novembre 2026, le **Radar vol. 35** place en **Caution** la « AI-driven documentation sprawl » : des masses de markdown générés par Spec-kit ou BMAD, verbeux, non maintenus et contradictoires, qui créent une « illusion de qualité ». Ses autres entrées citées incluent *progressive context disclosure*, *agent instruction bloat*, *risk-tiered human oversight*, *human-in-the-loop theater* et *agent sandboxing*.\[71\]\[72\]

**Études sur l'impact réel.**
- **METR (juillet 2025)** : essai randomisé, 16 développeurs open source expérimentés, 246 tâches. Avec l'IA, ils ont été **19 % plus lents**, alors qu'ils s'attendaient à +24 % et se croyaient ensuite 20 % plus rapides. Le cadre est spécifique (dépôts matures et familiers, outils de début 2025).\[73\]\[74\]\[75\]
- **GitClear (février 2025, 211 M de lignes, 2020-2024)** : le code « déplacé » (refactoring) tombe de 24,1 % à 9,5 %, tandis que le copier-coller monte de 8,3 % à 12,3 %. 2024 est la première année où le copier-coller dépasse le code déplacé.\[76\] C'est une corrélation avec l'adoption de l'IA, pas une attribution ligne à ligne, et l'étude vient d'un éditeur d'outils de qualité.

---

## Partie 2 — Analyse critique de la proposition « convention over configuration »

### 2.1 Ce que la proposition fait bien (et qui est confirmé par le terrain)
1. **Des défauts opinionnés et un point d'entrée unique (`/dev` sur un ticket).** C'est exactement le schéma de Stripe (Slack, puis Minion, puis PR), d'Uber (Minion et ses « optimized defaults »), de Doctolib (pack central installé dès le premier jour) et d'Atlassian (ticket Jira, plan, PR). Une friction initiale faible est le premier facteur d'adoption : l'auto-onboarding en moins de cinq minutes de Doctolib en est la preuve.
2. **Des surcharges par dépôt en markdown.** C'est le standard de fait : CLAUDE.md, AGENTS.md, `.github/instructions/*.instructions.md` avec `applyTo`, règles Cursor synchronisées chez Stripe, LLMs.md chez Doctolib.
3. **Partir du ticket Jira.** Cela aligne l'IA sur la chaîne de valeur, ce que DORA appelle l'orientation utilisateur et la gestion de la chaîne de valeur, plutôt que sur l'IDE seul.

### 2.2 Risques et points aveugles

| Risque | Pourquoi c'est réel | Source / signal |
|---|---|---|
| **Règles non négociables surchargeables** | Un markdown est du *contexte*, pas une *politique*. Une équipe peut affaiblir une règle de sécurité par simple formulation, et le modèle peut l'ignorer. | La documentation Claude Code sépare instructions et politiques appliquées (managed settings, hooks) ; GitHub fait passer le personnel avant le dépôt, puis l'organisation.\[7\] |
| **Fichiers vides générés automatiquement** | Bruit cognitif, faux signal de conformité (« le fichier existe donc c'est géré »), et ils ouvrent la voie à un remplissage par IA verbeux. | Radar vol. 35 : « AI-driven documentation sprawl » en Caution ; *agent instruction bloat*. |
| **Gonflement du contexte** | Défauts centraux, surcharges, CLAUDE.md et AGENTS.md sont concaténés : l'agent rate des contraintes ou optimise la mauvaise. | Échec du « one big AGENTS.md » chez OpenAI ; divulgation progressive des Agent Skills. |
| **Conflits central / local non résolus** | La concaténation n'est pas une fusion : deux règles contradictoires coexistent et le modèle tranche au hasard. | Claude Code : les CLAUDE.md sont concaténés et non surchargés de façon stricte.\[12\] |
| **Dérive et péremption** | Les surcharges vieillissent sans tests, et le framework central évolue sous elles. | OpenAI : « rapid rot » du gros fichier. |
| **Versioning du framework** | Des dizaines d'équipes sur des versions différentes sans canal de mise à jour ni compatibilité garantie. | Pratique des marketplaces de plugins gérés (versions épinglées, plugins forcés).\[11\] |
| **Observabilité absente** | Sans télémétrie, impossible de savoir quels skills servent, échouent, coûtent. | Uber (MCP Gateway : logs et télémétrie, coûts ×6), Doctolib (surveillance des coûts, plateau). |
| **Goulot de revue humaine** | Plus de PR générées, mais les mêmes relecteurs. | Atlassian : 71 min contre 32 d'attente ; Uber a dû créer Code Inbox et uReview. |
| **Fondations faibles** | Sur une équipe sans tests ni CI fiables, `/dev` produit vite du code fragile. | DORA (« amplifier »), GitClear, Spotify (la standardisation comme prérequis). |
| **« Human-in-the-loop theater »** | Des validations humaines de pure forme sur des PR volumineuses. | Radar vol. 35 ; Böckeler (« false sense of control »). |

### 2.3 Améliorations recommandées (sans toucher aux artefacts existants)

1. **Trois couches explicites, chacune avec son mécanisme d'application.**
   - **Couche 0 — Non négociable** (sécurité, secrets, conformité, licences, données de santé ou personnelles). Elle est imposée **hors du prompt** : managed settings, `allowManagedHooksOnly`, marketplaces autorisées, contrôles en CI (SAST, détection de secrets, politique de branche), permissions MCP via une passerelle. Elle n'est jamais surchargeable par un markdown.\[6\]\[7\]
   - **Couche 1 — Défauts de l'organisation** (workflow `/dev`, définition de « done », style de PR, stratégie de tests par défaut). Livrée en plugin ou marketplace versionné.\[11\]\[77\]
   - **Couche 2 — Extensions d'équipe** (règles QA, revue, domaine). C'est là que vivent vos surcharges.
2. **Préférer l'extension à la surcharge.** Les fichiers d'équipe *ajoutent* des critères (par exemple « en plus, vérifier X ») au lieu de *remplacer* les défauts. Quand un remplacement est vraiment nécessaire, il doit être déclaré explicitement (frontmatter du type `overrides: code-review.tests-min-coverage` et justification) pour être visible et auditable. C'est l'équivalent du `applyTo` et de l'`excludeAgent` de GitHub.
3. **Remplacer le scaffolding vide par une découverte progressive.**
   - Au premier lancement, **analyser** le dépôt (langages, build, tests, CI) et proposer un **unique** fichier d'entrée court (AGENTS.md comme table des matières), **pré-rempli à partir de faits détectés** (commandes de build et de test), à faire valider par l'équipe dans une PR.
   - Ne créer `qa.md` ou `code-review.md` qu'**au moment où l'équipe en a besoin** : par exemple quand la revue IA reçoit trois corrections similaires, le framework propose d'ajouter la règle (modèle Anthropic du « CLAUDE.md qui grandit correction après correction »).
   - Si vous tenez à rendre la structure visible, documentez-la (`/harness doctor` liste les points d'extension disponibles) plutôt que de la matérialiser en fichiers vides.
4. **Converger sur les standards ouverts.** AGENTS.md comme point d'entrée portable (lu par Copilot, Codex, Cursor ; Claude Code peut le charger) et Agent Skills pour les skills.\[9\] Cela évite l'enfermement et prépare la cohabitation multi-outils, comme la synchronisation des règles Cursor vers Claude Code chez Stripe.
5. **Linter les surcharges.** Un contrôle en CI vérifie la taille maximale, l'absence de contradiction avec la couche 0, les références mortes et la fraîcheur (date de dernière revue). La documentation agentique doit passer par des quality gates comme le code, ce que le Radar vol. 35 reproche justement de ne pas faire.\[71\]
6. **Versionner le framework comme un produit.** SemVer, changelog, canaux stable et beta, version épinglée par dépôt avec mises à jour automatiques par PR, et suite d'**évals** de non-régression des skills sur des dépôts témoins avant chaque release.
7. **Instrumenter dès le premier jour.** Télémétrie par skill (invocations, taux de succès, PR fusionnées ou abandonnées, coûts en tokens) et collecte des surcharges existantes. Les surcharges les plus fréquentes signalent des défauts centraux à corriger.

---

## Partie 3 — Proposition de déploiement

### 3.1 Principes directeurs
- **La plateforme possède le harness, les équipes possèdent leur contexte.** C'est le modèle Team Topologies : une équipe plateforme « enabling » et des équipes stream-aligned qui la consomment en libre-service.
- **Des chemins balisés, pas des chemins obligatoires** (sauf la couche 0). `/dev` doit être le chemin le plus facile, pas le seul.
- **Mesurer des résultats, pas l'usage.** Pas de « % de code généré » comme objectif ; ne pas évaluer les personnes sur leur usage individuel, en raison des risques de théâtre et des enjeux de droit social en Europe.
- **Investir dans les fondations en parallèle.** Tests, CI rapide et fiable, petits lots : ce sont les capacités DORA.

### 3.2 Niveaux de maturité d'équipe (« Harness levels »)

| Niveau | Nom | Ce que fait l'équipe | Critère de sortie |
|---|---|---|---|
| **N0** | Fondations | CI verte et fiable, tests exécutables par commande, AGENTS.md minimal validé | Build et tests lançables par l'agent sans aide humaine |
| **N1** | Assisté | Usage interactif (mode plan, explication de code, tests), skills par défaut sans surcharge | ≥ 70 % des devs actifs chaque semaine ; feedback collecté |
| **N2** | Workflow | `/dev` de bout en bout sur des tickets bien délimités ; revue IA en complément de la revue humaine ; premières extensions d'équipe | Taux de PR agent fusionnées stable ; pas de dégradation du change failure rate |
| **N3** | Délégué | Agents en arrière-plan sur la toil (migrations, montées de version, tests manquants, dette) comme Honk ou Minions ; specs légères en amont | Part croissante de PR agent sur la toil, avec une qualité stable |
| **N4** | Boucles | L'équipe maintient ses propres boucles (skills d'équipe partagés au catalogue, contributions au framework) | Contributions acceptées au framework central |

Les équipes n'avancent pas toutes au même rythme. Ce n'est pas un échec : DORA montre des profils d'équipe très différents. Pour une équipe en « foundational challenges », la priorité est N0, pas `/dev`.

### 3.3 Feuille de route

**Phase 0 — Cadrage (4 à 6 semaines)**
- Publier une **position IA claire** (première capacité DORA) : ce qui est attendu, autorisé, interdit (données, secrets, code client) et la façon dont l'usage sera mesuré. Elle doit être co-construite avec la sécurité, le juridique, le DPO et les représentants du personnel si nécessaire.
- Définir la **couche 0** et ses mécanismes d'application (managed settings, hooks, CI, passerelle MCP).
- Mettre en place la télémétrie et une **mesure de référence DORA** : lead time, fréquence de déploiement, change failure rate, temps de restauration, temps de cycle des PR et temps d'attente de revue.

**Phase 1 — Pilotes (8 à 12 semaines, 3 à 5 équipes)**
- Choisir des équipes **volontaires et diverses** (stacks, maturités, un produit legacy), sur le modèle du pilote de 30 personnes « de tous horizons » de Doctolib.\[78\]
- Accompagner chaque équipe avec un binôme plateforme. Tenir un point de feedback hebdomadaire et une rétrospective IA par sprint.
- Commencer par des cas à **vérification forte** : migrations, montées de version (le modèle Amazon Java et Airbnb), génération de tests, documentation.
- Livrable : liste des défauts centraux corrigés, catalogue des extensions réellement utiles, frictions documentées.

**Phase 2 — Vagues (trimestre par trimestre, 5 à 10 équipes par vague)**
- Onboarding en libre-service (objectif inférieur à 5 minutes), kit de démarrage et cas d'usage concrets par rôle.
- **Réseau de champions** : un par équipe, temps alloué (10 à 20 %), communauté de pratique mensuelle avec démonstrations « montre-moi ton usage réel » (pratique recommandée par les équipes Anthropic), reconnaissance visible.
- Formation par rôle (voir 3.5) et « AI Summer Camp » ou hackathons (Doctolib ; la création de Honk via Slack est née d'une Hack Week Spotify).\[30\]
- Anticiper le **plateau d'adoption** (constaté chez Doctolib et Uber) : relancer par de nouveaux cas d'usage plutôt que par des injonctions.

**Phase 3 — Industrialisation**
- Agents en arrière-plan sur la toil transverse, pilotés par la plateforme (modèle Fleetshift et Honk).
- Gestion du **goulot de revue** : revue IA filtrée par niveau de confiance (modèle uReview), routage, supervision humaine proportionnée au risque (*risk-tiered human oversight*).
- Catalogue interne de skills ouvert aux contributions des équipes, avec revue par la plateforme.

### 3.4 Gouvernance
- **Équipe plateforme Harness AI** : propriétaire de la couche 0 et de la couche 1, des releases, des évals, de la télémétrie et du catalogue. Elle traite le framework comme un **produit interne** : product manager, roadmap, NPS développeur. Doctolib confie ce rôle à un Platform Product Manager associé à un Staff SRE.\[40\]
- **AI Guild ou Advisory board** (modèle Spotify) : seniors de chaque discipline (Dev, QA, Sécurité, SRE, PO) qui arbitrent l'ajout d'une règle centrale et valident les remontées d'extensions locales vers les défauts.
- **Règle de promotion** : une extension présente dans au moins 3 équipes devient candidate pour la couche 1. Une surcharge qui contredit une règle centrale ouvre une discussion, pas une exception silencieuse.
- **Processus d'exception** pour la couche 0 : demande tracée, durée limitée, validation par la sécurité.

### 3.5 Évolution des rôles
- **PO** : rédige des tickets « prêts pour agent » (critères d'acceptation testables, contexte, limites). Rovo Dev vérifie justement les PR contre ces critères. Des specs **légères**, proportionnées à la taille de la tâche, pour éviter le piège Kiro des « 16 critères pour un bug ».
- **Développeur** : passe d'auteur à orchestrateur et relecteur. Il maîtrise le mode plan, la décomposition, la vérification et la curation du contexte de son dépôt.
- **QA** : conçoit les stratégies de test et les oracles (tests de mutation, contrats) qui servent de boucle de vérification aux agents, et rédige les extensions `qa` de l'équipe.
- **Sécurité** : possède la couche 0, les hooks, le sandboxing des agents et l'analyse des flux d'outils (MCP).
- **SRE** : intègre les agents au diagnostic d'incident (stack traces, runbooks, comme chez Anthropic Security Engineering) et définit les limites d'action des agents en production.

### 3.6 Tableau de bord de mesure

| Catégorie | Indicateurs | Usage |
|---|---|---|
| Adoption | Utilisateurs actifs hebdomadaires, équipes par niveau N0 à N4, skills invoqués | Pilotage du déploiement, pas évaluation individuelle |
| Flux (DORA) | Lead time, fréquence de déploiement, temps de cycle des PR, attente de première revue | Résultat principal |
| Qualité | Change failure rate, temps de restauration, taux de revert des PR agent, duplication et churn (type GitClear) | Garde-fou : toute hausse bloque la vague suivante |
| Efficacité agent | Taux de PR agent fusionnées sans retouche, abandons, coûts en tokens par PR fusionnée | Amélioration du framework |
| Expérience | Enquête trimestrielle (ressenti, charge cognitive, confiance), verbatims | Détection de friction ; ne jamais s'y fier seul (biais METR) |

### 3.7 Gestion du changement et des frictions
- **Nommer les peurs** : emploi, perte de savoir-faire, surveillance. Le mémo Shopify a été critiqué sur ce point.
- **Pas de mandat d'usage individuel.** Fixer plutôt des attentes d'équipe sur les résultats.
- **Canal de feedback à forte réactivité** : un correctif ou une réponse sous une semaine pendant les pilotes.
- **Montrer les échecs** autant que les succès : Spotify publie ses limites, Doctolib son plateau et ses coûts.
- **Budget et coûts transparents** par équipe (Uber : ×6 ; l'expérience Doctolib : environ 1 000 $ pour 3 semaines d'un trio), avec un rightsizing des modèles.\[79\]

---

## Caveats
- **Biais de source.** Une grande partie des chiffres d'adoption (Doctolib, Spotify, Amazon, Atlassian) provient des entreprises elles-mêmes ou de leurs fournisseurs (études de cas Anthropic, AWS). Les chiffres d'Uber viennent surtout de résumés secondaires de conférences. Les pourcentages de « code généré » ne sont ni définis de façon homogène ni audités.
- **Données contradictoires** : Atlassian publie −45 % puis −30,8 % et −31 % de temps de cycle des PR, et seule la deuxième mesure est méthodologiquement documentée. Pour Doctolib, la presse parle de 600 ingénieurs et la dernière étude de cas d'environ 900 personnes tech et produit, deux périmètres différents.
- **Études d'impact** : le METR porte sur des outils de début 2025 et un profil très spécifique. GitClear établit une corrélation, pas une causalité. Les deux ne doivent pas être généralisés, mais justifient de mesurer plutôt que de croire.
- **Couverture incomplète** : Microsoft (hors GitHub), Meta, Netflix, Zalando et les acteurs français autres que Doctolib n'ont pas été documentés à partir de sources primaires ici.
- **Évolutions rapides** : les mécanismes de configuration (managed settings, plugins, Agent Skills) évoluent tous les mois. Les détails techniques cités sont valables à novembre 2026 et doivent être revérifiés lors de la mise en œuvre.

## Sources

1. [How Anthropic Teams Use Claude Code (2027 Guide)](https://blog.buildbetter.ai/how-anthropic-teams-use-claude-code/)
2. [How Anthropic's Own Teams Use Claude Code](https://moeed.app/posts/how-anthropic-teams-use-claude-code/)
3. [Case Study](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)
4. [How the Claude Code Team Actually Uses Claude Code - The doctrine the people who built Claude Code at Anthropic teach every new hire — Vibe Coder Blog](https://blog.vibecoder.me/how-claude-code-team-uses-claude-code)
5. [How Anthropic engineering teams use Claude Code every day](https://codingscape.com/blog/how-anthropic-engineering-teams-use-claude-code-every-day)
6. [Enterprise Claude Code with Managed Settings](https://systemprompt.io/guides/enterprise-claude-code-managed-settings)
7. [Configuration Precedence and Hierarchy](https://deepwiki.com/FlorianBruniaux/claude-code-ultimate-guide/4.3-configuration-precedence-and-hierarchy)
8. [All settings - Claude Code Docs](https://code.claude.com/docs/en/settings-reference)
9. [How Claude remembers your project - Claude Code Docs](https://code.claude.com/docs/en/memory)
10. [Claude Code Extension Layer Decision Guide - Choosing Among Skills, Subagents, Hooks, and Plugins](https://hidekazu-konishi.com/entry/claude_code_extension_layers_decision_guide.html)
11. [Manage Claude Code plugins for your organization - Claude Code Docs](https://code.claude.com/docs/en/plugins/org)
12. [claude-howto/02-memory/README.md at main · luongnv89/claude-howto · GitHub](https://github.com/luongnv89/claude-howto/blob/main/02-memory/README.md)
13. [What Are Agent Skills and How To Use Them](https://strapi.io/blog/what-are-agent-skills-and-how-to-use-them)
14. [The Agent Skills Standard: One SKILL.md, Every Tool — AgentsCamp](https://agentscamp.com/guides/skills/agent-skills-open-standard)
15. [Specification - Agent Skills](https://agentskills.io/specification)
16. [Harness Engineering Guide: How to Build an AI Agent Harness](https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026)
17. [OpenAI's Agent-First Codebase Learnings](https://alexlavaee.me/blog/openai-agent-first-codebase-learnings/)
18. [Harness Engineering: Leveraging Codex in an Agent-First World](https://2ooks.github.io/knowledge-base/summaries/openai-harness-engineering.html)
19. [Unlocking the full power of Copilot code review: Master your instructions files - The GitHub Blog](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)
20. [Adding repository custom instructions for GitHub Copilot - GitHub Docs](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
21. [GitHub Copilot Instructions: Setup Guide](https://codetocloud.io/blog/github-copilot-instructions/)
22. [copilot-instructions.md as a Repo-Level Instruction Convention — AgentPatterns.ai](https://agentpatterns.ai/tools/copilot/copilot-instructions-md-convention/)
23. [Copilot Custom Instructions: 8 Copy-Paste Templates](https://prompt-architects.com/blog/339-github-copilot-custom-instructions-templates-that-work)
24. [Path-specific Copilot custom instructions: a guide - DEV Community](https://dev.to/sascha-ms/path-specific-copilot-custom-instructions-a-guide-54lg)
25. [Minions: Stripe’s one-shot, end-to-end coding agents](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
26. [Minions one-shot coding agents - Jacob Bennett](https://jacob.blog/links/minions-one-shot-coding-agents/)
27. [Minions: Stripe’s One-Shot, End-to-End Coding Agents (Stripe Engineering Blog)](https://antolinez.ch/2026/Apr/12/stripe-minions-coding-agents/)
28. [Minions: Stripe’s one-shot, end-to-end coding agents—Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
29. [Stripe Minions Explained: Autonomous Coding Agents Ship 1300+ PRs/Week](https://www.paperclipped.de/en/blog/stripe-minions-autonomous-coding-agents/)
30. [Spotify: Fleet-Wide Autonomous Code Migrations with AI Coding Agents - ZenML LLMOps Database](https://www.zenml.io/llmops-database/fleet-wide-autonomous-code-migrations-with-ai-coding-agents)
31. [How Spotify Uses AI Agents to Rewrite Its Entire Codebase](https://grindengineer.substack.com/p/how-spotify-uses-ai-agents-to-rewrite-its-entire-codebase)
32. [QCon London 2026: Rewriting All of Spotify's Code Base, All the Time - InfoQ](https://www.infoq.com/news/2026/03/spotify-honk-rewrite/)
33. [Honk at Spotify · Internal Agents Map](https://internal-agents.com/agents/spotify-honk-xirp)
34. [Spotify: Background Coding Agents for Large-Scale Dataset Migrations - ZenML LLMOps Database](https://www.zenml.io/llmops-database/background-coding-agents-for-large-scale-dataset-migrations)
35. [Background Coding Agents: Supercharging Downstream Consumer Dataset Migrations (Honk, Part 4)](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4)
36. [Inside Uber's AI Dev Stack: 92% of Engineers Use Agents Monthly](https://aiproductivity.ai/news/uber-ai-development-inside-look/)
37. [How Uber uses AI for development: inside look - Mobile & Accessories](https://abc.microfintool.com/how-uber-uses-ai-for-development-inside-look/)
38. [How Uber is building AI agents for its developers - Staniscia.net](https://www.staniscia.net/2921-how-uber-is-building-ai-agents-for-its-developers/)
39. [Doctolib Claude Code case study](https://claude.com/customers/doctolib)
40. [Scaling AI Adoption: From 30 Engineers to Tech-Wide Transformation - Lessons from Doctolib's Journey - Devoxx Belgium 2025](https://m.devoxx.com/events/dvbe25/talks/23196/scaling-ai-adoption-from-30-engineers-to-techwide-transformation-lessons-from-doctolibs-journey)
41. [How Doctolib is revolutionizing development methods thanks to AI agents - Le Monde Informatique](https://www.javascrypte.com/en/how-doctolib-is-revolutionizing-development-methods-thanks-to-ai-agents-le-monde-informatique/)
42. [AI is baseline: what Shopify's memo means for your hiring process. · Metaview Blog](https://www.metaview.ai/resources/blog/ai-baseline-shopify-memo-hiring-process)
43. [How Shopify's CEO Delivered the AI Mandate to His Workers - Ragan Consulting](https://raganconsulting.com/analyzing-tobias-lutkes-artificial-intelligence-memo-ai/)
44. [Tobi's Shopify Memo - New Internet, by Jeff Morris Jr.](https://www.newinternet.tech/p/tobis-shopify-memo)
45. [Tobi Lutke's Public AI Memo: How a CEO Made AI Use a Hiring Bar](https://www.thefoundersreport.com/tobi-lutke-shopify-ai-mandate-public-memo)
46. [Tobi Lütke's AI Memo: The Part About Headcount - Sondero](https://www.sondero.ai/blog/authority-luetke-reflexive-ai)
47. [Amazon CEO: AI-Assisted Code Transformation Saved Us 4,500 Years of Developer Work - Slashdot](https://developers.slashdot.org/story/24/08/25/0049230/amazon-ceo-ai-assisted-code-transformation-saved-us-4500-years-of-developer-work)
48. [A quote from Andy Jassy - Amazon CEO](https://simonwillison.net/2024/Aug/24/andy-jassy-amazon-ceo/)
49. [How Amazon’s generative AI tool for developers is saving 4,500 years of work, \$260 million annually - Digiday](https://digiday.com/media/how-amazons-genai-tool-for-developers-is-saving-4500-years-of-work-260-million-annually/)
50. [Amazon upgraded 30,000 internal apps to Java 17 with Amazon Q Developer](https://agentsinthewild.co/use-cases/amazon-q-java-upgrades)
51. [Google CEO says 75% of the company’s code is AI-generated - Fast Company](https://www.fastcompany.com/91531519/google-ceo-says-75-of-the-companys-code-is-ai-generated)
52. [Google's 75% AI Code: What Pichai Didn't Say at Cloud Next](https://newsanalysis.net/pichai-google-75-percent-ai-code-claim/)
53. [googles code ai sundar pichai](https://fortune.com/2024/10/30/googles-code-ai-sundar-pichai)
54. [sundar pichai says ai making 141602216](https://www.aol.com/sundar-pichai-says-ai-making-141602216.html)
55. [75% Of Code At Google Is Now Generated By AI: CEO Sundar Pichai](https://officechai.com/ai/75-of-code-at-google-is-now-generated-by-ai-ceo-sundar-pichai/)
56. [AirBnB: Large-Scale Test Framework Migration Using LLMs - ZenML LLMOps Database](https://www.zenml.io/llmops-database/large-scale-test-framework-migration-using-llms)
57. [How Airbnb Leveraged Large Language Models for a Groundbreaking Code Migration - Christopher Zerafa, PhD](https://zerafachris.github.io/bio/ai-airbnb-code-migration/)
58. [Atlassian Rovo & Rovo Dev: AI Agents in Jira for Software Teams](https://lupusconsulting.com/blog/atlassian-rovo-and-rovo-dev-the-rise-of-ai-agents-for-software-teams)
59. [Work with Rovo Dev in Bitbucket Pipelines](https://support.atlassian.com/rovo/docs/work-with-rovo-dev-in-bitbucket-pipelines/)
60. [How we made vulnerability fixes review-ready with Agentic Pipelines - Inside Atlassian](https://www.atlassian.com/blog/bitbucket/vulnerability-fixes-with-agentic-pipelines)
61. [Rovo DevOps Integration: Connectors, Rovo Dev, Bitbucket](https://crosstowntech.com/apps/rovo-devops-integration/)
62. [Atlassian says Rovo cut PR review time 45%. Here's the measurement they didn't publish. - DEV Community](https://dev.to/cole_halton_42f71d71b809b/atlassian-says-rovo-cut-pr-review-time-45-heres-the-measurement-they-didnt-publish-53po)
63. [30.8% Faster PRs: How AI-Driven Rovo Dev Code Reviewer Improved the Developer Productivity at Atlassian - Inside Atlassian](https://www.atlassian.com/blog/ai-at-work/developer-productivity-improved-with-rovo-dev)
64. [Meet Code Reviewer, now available with Jira - Inside Atlassian](https://www.atlassian.com/blog/development/code-reviewer)
65. [DORA 2025 Report: How AI Is Reshaping Development - Opsera](https://opsera.ai/blog/dora-2025-report-ai-software-development)
66. [2025 DORA Report: State of AI-assisted Software Development](https://businessdatasolutions.github.io/ai-wiki/sources/2025-09-23-dora-2025-state-of-ai-assisted-software-development)
67. [Technology Radar Vol. 33 (Nov 2025)](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2025/11/tr_technology_radar_vol_33_en.pdf)
68. [Spec-driven development](https://www.thoughtworks.com/radar/techniques/spec-driven-development)
69. [Spec-Driven Development: Spec Kit, Kiro, OpenSpec Compared](https://juliantellez.com/blog/what-spec-driven-development-is)
70. [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://daniliants.com/insights/understanding-spec-driven-development-kiro-spec-kit-and-tessl/)
71. [Techniques](https://www.thoughtworks.com/radar/techniques)
72. [Thoughtworks Radar 35: what to adopt with agents](https://www.onext.es/en/insights/thoughtworks-radar-35-what-to-adopt-agents/)
73. [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity - METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
74. [A randomized trial by METR found that experienced developers completed real coding tasks 19% slower when allowed to use AI tools — yet afterwards, they estimated on average that AI had made them 20% faster. - ScienceBlog.com](https://scienceblog.com/t-a-randomized-trial-by-metr-found-that-experienced-developers-completed-real-coding-tasks-19-slower-when-allowed-to-use-ai-tools-yet-afterwards-they-estimated-on-average-that-ai-had-made-them-20-fast/)
75. [METR 2026: AI Made Developers 19% Slower. Is That Still True?](https://ingenire.com/blog/metr-2026-developer-productivity-study)
76. <https://gitclear-public.s3.us-west-2.amazonaws.com/GitClear-AI-Copilot-Code-Quality-2025.pdf>
77. [Manage mods for your organization - Claude Code Docs](https://code.claude.com/docs/en/plugins/mods/admin)
78. [Doctolib: Doctolib's AI Adoption Playbook: from 30-person pilot to company-wide deployment](https://dust.tt/customers/doctolibs-ai-adoption-playbook-from-30-person-pilot-to-company-wide-deployment)
79. [Agentic AI Transforms Work Practices: Doctolib's Pioneering Approach - Dawn Liphardt](https://www.dawnliphardt.com/agentic-ai-transforms-work-practices-doctolibs-pioneering-approach/)
