---
name: harness-init
description: Met en place l'instrumentation IA d'un dépôt à partir de zéro — AGENTS.md comme source unique, stubs CLAUDE.md / Copilot / Cursor, convention de retour `rule:` et premier contrat de tâche — après un court entretien (mode délégation ou assistance, équipe, CI, outils) et une reconnaissance du repo. N'écrit que ce que l'agent ne peut pas découvrir seul, installe le mécanisme d'amélioration plutôt que du contenu, et termine par un harness-audit en mode gate. Utiliser dès que l'utilisateur veut « commencer avec Claude Code / Copilot / Cursor sur ce projet », créer ou refaire un AGENTS.md ou CLAUDE.md, « instrumenter le repo pour l'IA », ne sait pas par où commencer, ou veut déléguer des tâches à un agent — même sans employer le mot init. Ne pas utiliser pour auditer un harness existant sans le modifier (c'est harness-audit).
---

# Harness init

Un AGENTS.md généré par scan du repo (arborescence, commandes de build, conventions de nommage) est du bruit : l'agent découvre tout ça seul en lisant le code. Les règles utiles naissent d'incidents, pas d'un scan. Ce skill installe donc **un mécanisme, pas du contenu** : un fichier court qui ne dit que le non-découvrable, un mode explicite qui fixe la sévérité des audits à venir, et la convention de retour qui fera grandir le fichier à partir de cas réels.

Mode par défaut : **délégation** (l'agent reçoit une tâche entière et revient avec une PR, personne ne relit en cours de route). L'assistance (l'humain pilote et relit chaque diff) se choisit explicitement à l'entretien. La différence est détaillée dans `references/agents-template.md`.

## Déroulé

### 1. Entretien — une seule salve de questions
Pose toutes les questions en une fois, avec le défaut proposé pour chacune. Ne commence rien avant les réponses.

1. **Mode** : délégation (défaut) ou assistance ? Si l'équipe relit chaque diff en direct et qu'aucun agent ne tourne hors session, propose assistance.
2. **Équipe** : combien de personnes touchent le repo ? Un dev seul a moins besoin du fichier (sa mémoire d'agent apprend déjà) ; dis-le et allège.
3. **CI et garde-fous** : quelle CI, quels checks bloquants aujourd'hui ? Ce sont les seules règles qu'on pourra citer comme vérifiées.
4. **Outils** : Claude Code seul, ou aussi Copilot, Cursor, Codex ? Ça décide des stubs.
5. **Première tâche à déléguer** : quelle tâche répétitive l'équipe aimerait confier en premier (bump de dépendance, clé i18n, composant, migration…) ? Elle devient le premier contrat.
6. **Interdits** : qu'est-ce qu'un agent ne doit jamais toucher ou faire (dossiers, secrets, migrations prod, force push…) ?

### 2. Reconnaissance — ne rien écrire avant d'avoir vérifié
- **Fichiers d'instructions existants** (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `copilot-instructions.md`) : ne jamais écraser. Lis-les, classe chaque ligne en instruction / référence / bruit, et propose ce qu'on garde, déplace ou supprime. Si le fichier est long, lance harness-audit dessus avant d'écrire.
- **La bonne branche et les fichiers de dossier.** Lis les fichiers d'instructions sur la branche que la PR visera (souvent `develop`, pas la branche par défaut du clone) : ils diffèrent parfois d'une branche à l'autre. Cherche aussi les `CLAUDE.md` et `AGENTS.md` de sous-dossiers (`find . -name CLAUDE.md -o -name AGENTS.md`) : ils sont déjà chargés à la demande, donc c'est là que va la référence qui les concerne, pas dans un nouveau dossier qui les doublerait.
- **Secrets.** Tu relis ces fichiers ligne à ligne : c'est le moment de chercher clés d'API, mots de passe, tokens, URLs avec identifiants (`grep -nE "apiKey=|api_key|token|password|secret|Bearer "` sur les fichiers d'instructions et ce qu'ils incluent). Un secret trouvé ne se recopie jamais, même « en lecture seule » : remplace-le par une variable d'environnement, dis dans le compte rendu qu'il reste dans l'historique git et doit être régénéré, et ajoute l'Interdit correspondant à AGENTS.md.
- **Commandes réelles** : repère build, test, lint, et **exécute-les** pour confirmer qu'elles marchent. Une commande qui échoue ne va pas dans le fichier ; elle va dans la section « non vérifié » du compte rendu.
- **Garde-fous L3 existants** : linters custom, tests d'architecture, scripts de check, PR gates, hooks. Note chemin et ce qu'ils vérifient.
- **Non-découvrable** : ce qu'on ne peut pas déduire du code — pourquoi tel choix d'archi, quel service est fragile, quel dossier est généré, quelle commande a des effets de bord. Interroge l'utilisateur si tu l'observes sans l'expliquer.

Test pour chaque phrase candidate : *si je l'enlève, l'agent fait-il quelque chose de différent ?* Si non, elle ne va pas dans le fichier.

### 3. Écriture
Depuis `references/agents-template.md`, dans cet ordre :
- `AGENTS.md` à la racine, **sous 60 lignes**, ligne de mode en tête, sections du template dans l'ordre, sections vides supprimées plutôt que remplies de générique.
- Stubs : `CLAUDE.md` contenant uniquement `@AGENTS.md` ; `.github/copilot-instructions.md` et `.cursor/rules/agents.mdc` selon les outils déclarés, texte du template.
- Premier contrat : `.claude/skills/<tâche>/SKILL.md` pour la tâche choisie en 5, avec étapes, vérifications et critère de fini. Court ; il grandira avec les incidents. AGENTS.md le référence par nom sans recopier.

### 4. Installer la boucle de retour
- La section « Maintenance » de AGENTS.md porte la convention : tout commentaire de review qui commence par `rule:` est une règle candidate, ajoutée dans la même PR avec le lien vers le commentaire, ou collectée plus tard par harness-harvest.
- Chaque règle écrite aujourd'hui porte sa justification (pourquoi, ou incident) et, quand il existe, le garde-fou qui la vérifie. Une règle sans l'un ni l'autre est marquée `(non vérifiée)` pour que l'audit la retrouve. Quand aucun incident n'est connu, écris-le (« Pourquoi : décision d'architecture, pas d'incident connu ») plutôt que d'inventer une raison plausible : une justification fabriquée a l'air d'un incident et fausse le prochain harvest.
- Si harness-harvest n'est pas installé, dis-le : la collecte est manuelle jusque-là.
- Un marqueur de harvest déjà présent dans le fichier existant est **gardé tel quel**, même périmé : le remettre à aujourd'hui simulerait un harvest qui n'a pas eu lieu. Le marqueur `ref=init` ne se pose que sur un fichier qui n'en avait pas.

### 5. Gate — état mesuré puis harness-audit
Lance d'abord `python3 cli/harness.py status <repo>` (CLI du dépôt harness-ai) : il écrit `.harness/state.json` et affiche le palier atteint avec les vérifications qui manquent. L'objectif de l'init est le palier 1 « Cadré » complet ; si une vérification échoue, corrige avant d'aller plus loin. Puis lance harness-audit sur ce qui vient d'être écrit. Corrige les constats structurels (longueur, part de référence, clause de maintenance, cohérence des stubs, règle non vérifiée en mode délégation sans garde-fou nommé). Les constats de fond qui demandent de créer un linter ou un check CI ne se corrigent pas ici : ils vont dans le compte rendu comme prochaines étapes.

### 6. Compte rendu
Toujours le même format : palier atteint selon `harness status` et vérifications restantes ; fichiers créés ou modifiés (chemin, lignes) ; secrets trouvés et ce qu'il reste à faire (régénérer, purger) ; mode retenu et pourquoi ; règles écrites avec leur statut (vérifiée par <garde-fou> / non vérifiée) ; commandes confirmées et non confirmées ; résultat du gate ; trois prochaines étapes, la première étant presque toujours « pousser la première règle non vérifiée en CI ».

## Délégation vs assistance — ce qui change concrètement

| | Délégation (défaut) | Assistance |
|---|---|---|
| Qui vérifie | La CI et les garde-fous ; personne ne relit en route | L'humain, à chaque diff |
| Règle racontée sans garde-fou | Défaut P1 pour l'audit : elle sera sautée un jour sur dix | Coût de contexte seulement |
| Section « Processus de travail » | Obligatoire : quand s'arrêter et demander, critère de fini, CI rouge, taille de PR | Absente |
| Contrats par tâche | Un par tâche déléguée, dès la première | Optionnels |
| Signal de retour | PRs d'agent rejetées ou corrigées, commentaires `rule:` | Commentaires `rule:` seulement |

## Ce qu'on n'écrit pas
- Arborescence, liste des modules, stack technique : découvrable.
- Conventions que le modèle applique déjà sans qu'on le lui dise (nommage standard, gestion de ressources idiomatique).
- Commandes non testées, règles « au cas où », principes génériques (« écris du code propre »).
- Du contenu de skill recopié dans AGENTS.md : on pointe, on ne duplique pas.

## Pièges fréquents
- Répondre soi-même aux questions de l'entretien pour aller plus vite : le mode et les interdits viennent de l'utilisateur, pas du scan.
- Écraser un CLAUDE.md existant parce qu'il est mauvais : on fusionne et on dit ce qu'on a retiré.
- Dépasser 60 lignes « parce que c'est important » : si c'est important et long, c'est un skill ou un fichier de référence chargé à la demande.
- Oublier la ligne de mode : harness-audit s'en sert pour choisir son barème.
- Poser un workflow planifié ou à lancement manuel sur une branche de travail : GitHub ne planifie un workflow, et n'accepte un `workflow_dispatch`, que depuis la branche par défaut. Un garde-fou fusionné sur `develop` seul est inerte ; il doit aussi arriver sur `main`, et le compte rendu doit le dire.
