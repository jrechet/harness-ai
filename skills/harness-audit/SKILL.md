---
name: harness-audit
description: Audite l'instrumentation IA d'un dépôt ou d'un processus — agents, skills, AGENTS.md / CLAUDE.md / règles Cursor, scripts adossés, CLI, linters et tests d'architecture, GitHub Actions ou autre exécuteur distant — et vérifie que chaque responsabilité est au bon étage (jugement / procédure / logique locale / exécution distante). Produit un rapport à format fixe (Markdown + JSON) avec un verdict par élément et un plan de remédiation priorisé. Utiliser dès que l'utilisateur veut auditer, revoir, critiquer, fiabiliser, nettoyer ou « remettre à plat » des agents, skills, scripts, workflows ou un AGENTS.md (le sien ou celui d'un repo tiers), se demande si un skill fait trop de choses, si une règle devrait devenir un linter ou une commande CLI, ou si « on peut couper l'agent et que ça marche encore » — même sans employer le mot audit.
---

# Harness audit

Un harness est sain quand **l'agent n'est qu'un accélérateur** : si on le coupe, l'équipe peut encore faire tourner le processus avec le CLI et les workflows. Dès que du processus obligatoire ne vit plus que dans un prompt ou un SKILL.md, il peut être sauté, mal interprété ou halluciné. Le but de cet audit est de trouver ces fuites et de dire précisément où chaque morceau doit aller.

## Le modèle à quatre couches

Classe chaque responsabilité observée dans une couche. Une responsabilité au mauvais étage est un défaut, même si « ça marche aujourd'hui ».

| Couche | Rôle | Porte-parole typique | Ce qui doit y être |
|---|---|---|---|
| **L1 Jugement** | Décider : quel type de release, est-ce prêt, que faire si ça casse, demander une validation | Agent (prompt, sous-agents) | Choix entre options, interprétation de retours *structurés*, dialogue humain, points d'arrêt |
| **L2 Procédure** | Raconter : quand appeler quoi, dans quel ordre, comment lire les résultats | Skill (SKILL.md, références) | Vocabulaire, séquence nominale, cas d'abandon, format attendu des retours |
| **L3 Logique locale** | Garantir : pré-conditions, calculs, transformations, idempotence | CLI testé (sous-commandes), ou script si vraiment isolé | Tout ce qui est obligatoire, vérifiable, reproductible sans IA |
| **L4 Exécution distante** | Agir avec les droits : build, tag, publish, deploy | GitHub Actions / pipeline / API | Ce qui touche des ressources partagées, auditées, avec secrets |

Règles de gravité qui en découlent :
- Une **pré-condition** racontée en L2 au lieu d'être un `exit 1` en L3 → défaut P1 (l'agent peut passer outre).
- Une **action L4** déclenchable sans passer par L3 (l'agent appelle l'API directement) → P1 (pas de garde-fou, pas de dry-run uniforme).
- De la **logique L3 dupliquée** dans plusieurs scripts par skill → P2 (CLI implicite non testé).
- Un **retour non structuré** (l'agent lit des logs) là où L1 doit décider → P2 (succès hallucinés).
- Du **jugement L1 codé en dur** dans un script (« si le ticket contient X alors… ») → P3 sauf si ça bloque un cas réel.

## Déroulé

### 1. Inventaire — ne rien juger avant d'avoir tout vu
Liste exhaustivement : agents (définitions, prompts système, sous-agents), fichiers d'instructions (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `copilot-instructions.md`, et leurs `@includes` ou équivalents chargés automatiquement), skills (SKILL.md + références + `scripts/`), scripts adossés (`.mjs`, `.sh`, `.py`), commandes CLI existantes, garde-fous L3 (linters custom, Checkstyle, ArchUnit, scripts de check, hooks, templates de PR), workflows (`.github/workflows/*.yml`, inputs, secrets, `workflow_dispatch`), et le ou les contrats/documents de process s'il y en a. Pour chaque élément, note : chemin, couche *déclarée* (où il est rangé), couche *réelle* (ce qu'il fait vraiment), qui l'appelle, ce qu'il appelle.

Construis le graphe d'appels avant toute analyse. Si un élément n'a aucun appelant, c'est déjà une information (candidat BLOCK ou MERGE).

Si des fichiers manquent (un script référencé mais absent, un workflow nommé dans un skill mais introuvable), demande-les plutôt que de supposer ; l'absence elle-même est un constat à reporter.

### 2. Le test « coupe l'agent »
Avant le détail, réponds à une question globale : *si on supprime tous les agents et skills, un humain pressé ou un cron peut-il exécuter le processus de bout en bout avec le CLI + les workflows ?* Parcours le processus nominal étape par étape et note chaque étape qui n'existe **que** dans un prompt. Ce parcours alimente directement le score de santé et la section « Fuites de processus » du rapport.

### 3. Analyse élément par élément
Pour chaque élément, pose dans l'ordre :

1. **Vérité du process** : y a-t-il une étape obligatoire ici qui n'est pas encodée en L3/L4 ?
2. **Pré-conditions** : sont-elles vérifiées par du code (sortie non nulle, message typé) ou racontées ?
3. **Retours** : la sortie est-elle structurée (JSON/exit codes/URL du run/artefacts/prochaine action possible) ou un texte libre à interpréter ?
4. **Dry-run** : peut-on obtenir le plan sans exécuter ? Pour toute action L4 irréversible (tag, publish, deploy prod), existe-t-il un point d'arrêt humain entre plan et exécution ?
5. **Duplication** : cette logique existe-t-elle ailleurs (autre script, CLI, workflow) ?
6. **Testabilité** : la logique L3 a-t-elle des tests ? Peut-on l'exécuter hors agent ?
7. **Droits** : les secrets et permissions sont-ils tenus en L4 uniquement ?

### 4. Verdict
Attribue exactement un verdict par élément :

| Verdict | Sens | Exemple |
|---|---|---|
| **KEEP** | Bonne couche, bon périmètre | Skill qui décrit la séquence et pointe vers `release plan` / `release run` |
| **INLINE** | Trop petit pour exister seul, à absorber dans son appelant | Script de 10 lignes qui formate un argument avant d'appeler le CLI |
| **PUSH_DOWN** | Descend d'une couche (L2→L3, L3→L4) | Vérification « develop est vert » écrite dans le SKILL.md → sous-commande CLI avec `exit 1` |
| **PROMOTE** | Monte d'une couche (L3→L2, L2→L1) | Script qui décide seul du type de release → décision rendue à l'agent, le script n'expose que les options |
| **MERGE** | Fusionner avec un autre élément (doublon) | Trois `.mjs` qui appellent `gh workflow run` avec des variations → une seule sous-commande |
| **SPLIT** | Mélange plusieurs couches, à séparer | Skill qui contient de la procédure *et* du code de calcul de version |
| **BLOCK** | Dangereux ou mort : à retirer ou neutraliser avant tout | Agent qui peut déclencher le deploy prod sans dry-run ni validation ; script jamais appelé |

Attribue une priorité : **P1** = risque de release/deploy incorrect ou non maîtrisé, **P2** = fragilité ou duplication qui finira par casser, **P3** = hygiène.

### 5. Plan de remédiation
Ordonne par priorité puis par dépendance (on crée la sous-commande CLI *avant* de supprimer les scripts qui la dupliquent). Chaque item : verdict, élément, action concrète (fichier à créer/modifier/supprimer), critère de vérification (comment on saura que c'est fait), et un point d'approbation humaine explicite pour tout BLOCK ou toute suppression. Ne modifie rien toi-même pendant l'audit : le rapport est l'entrée d'une étape de remédiation séparée, item par item.

## Cas particulier : auditer un AGENTS.md / CLAUDE.md

Un fichier d'instructions de repo est un élément L2 pur. Les mêmes questions s'appliquent, avec quelques spécificités :

- **Règle racontée vs règle vérifiée.** Pour chaque règle obligatoire (« jamais d'injection par champ », « pas de couleur hors tokens », « toute route a un test d'autorisation »), cherche le garde-fou L3 correspondant : règle eslint/stylelint custom, Checkstyle, ArchUnit, script de check en PR gate, hook. Une règle avec garde-fou est saine et peut même être raccourcie dans le fichier ; une règle sans garde-fou est une fuite à reporter dans la section « Règles racontées sans vérification » — verdict PUSH_DOWN avec l'outil cible nommé.
- **Coût de contexte.** Compte les lignes réellement chargées par session (fichier + `@includes`). Sépare instruction (ce qui change le comportement) et référence (commandes, structure des modules, troubleshooting). La référence doit être déportée dans des fichiers chargés à la demande ou des skills ; signale en P3 un fichier dont plus de la moitié est de la référence, en P2 s'il dépasse largement ce qu'un modèle lit avec attention (ordre de grandeur : plusieurs centaines de lignes).
- **Bruit.** Une règle qu'un modèle récent applique déjà sans qu'on le lui dise (conventions de nommage standard, try-with-resources) coûte du contexte pour rien ; recommande INLINE ou suppression, sauf si un incident montre qu'elle a été violée.
- **Justification.** Note si les règles expliquent *pourquoi* (idéalement avec l'incident ou l'issue à l'origine) ou sont de simples MUST. C'est un point fort à mentionner explicitement, car c'est ce qui fait tenir la règle dans les cas non prévus.
- **Maintenance.** Le fichier dit-il comment il évolue (ajout dans la même PR qu'un commentaire de review, suppression des règles obsolètes) ? Sans cette clause, il dérive.
- **Cohérence interne.** Relis les exemples de code et les commandes : une erreur dans un exemple sera copiée fidèlement par l'agent. Vérifie que deux sections ne se contredisent pas.
- **Ce qui manque souvent** : le processus de travail (quand s'arrêter et demander, critère de « fini », quoi faire face à un test flaky, comment découper une tâche) et des procédures par type de tâche (contrats) plutôt qu'un seul monolithe. L'absence n'est pas un défaut si le repo vise l'assistance humaine ; c'en est un si l'objectif est de déléguer des tâches entières.

Dans ce mode, le test « coupe l'agent » devient : *si on supprime le fichier, qu'est-ce que la CI laisse passer qu'elle ne laissait pas passer avant ?* Chaque réponse est une règle à pousser en L3.

## Rapport

Produis **toujours** les deux sorties, dans cet ordre : le Markdown (lecture humaine) puis le JSON (lecture machine, pour suivre l'évolution d'un audit à l'autre). Le format exact est dans `references/report-template.md` — lis-le avant d'écrire le rapport et respecte les sections et les clés telles quelles, même si une section est vide (écris alors « Aucun »). Un format stable permet de diffuser et comparer deux audits ; une section improvisée casse ça.

Dans le rapport, chaque constat cite son chemin et, si possible, la ligne. Un constat sans preuve localisable n'y va pas.

Écris aussi le bloc JSON seul dans `.harness/audit.json` du dépôt audité : c'est ce que lit `harness status` (CLI du dépôt harness-ai) pour la vue par couche et le palier 3. Si l'utilisateur ne veut pas de fichier dans son repo, dis-le et donne le JSON dans la réponse.

## Ce qui n'est pas un défaut

- Un skill long parce qu'il décrit beaucoup de cas d'abandon : c'est de la procédure, c'est sa place.
- Un script `.mjs` isolé qui ne fait *que* traduire un appel CLI pour un environnement sans le CLI installé — tant qu'il n'ajoute pas de logique.
- Un agent qui demande confirmation « trop souvent » : préfère ce défaut à l'inverse ; signale-le en P3 seulement.
- Du jugement laissé à l'agent sur des choix réellement ouverts (ordre de communication, message de release) : c'est L1.

## Pièges fréquents

- Juger la couche par le dossier où le fichier est rangé plutôt que par ce qu'il fait.
- Recommander PUSH_DOWN partout : un CLI qui encode du jugement devient rigide et l'équipe le contournera.
- Oublier les workflows eux-mêmes : un `workflow_dispatch` sans input `dry_run` ou sans `environment` protégé est une fuite L4, pas un problème d'agent.
- Compter un retour « lisible » comme structuré : si l'agent doit chercher « SUCCESS » dans un log, ce n'est pas structuré.
- Classer une convention de style ou de nommage parmi les fuites : une fuite est une règle dont la violation a une conséquence sur le produit, la prod ou la sécurité. Le style sans garde-fou est du bruit (INLINE) ou un pointeur vers le linter, et compte en P3 au plus.
