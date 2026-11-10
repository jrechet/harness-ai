---
name: harness-init
description: Pose le premier palier de l'instrumentation IA d'un dépôt — un AGENTS.md court comme source unique, avec mode, règles justifiées et datées, Interdits, et les stubs CLAUDE.md / Copilot / Cursor — après trois questions et une reconnaissance du repo. N'écrit que ce que l'agent ne peut pas découvrir seul, retire d'un fichier existant ce qui ne sert plus, puis s'arrête : les paliers suivants sont d'autres pas, menés par harness-step. Utiliser dès que l'utilisateur veut « commencer avec Claude Code / Copilot / Cursor sur ce projet », créer ou refaire un AGENTS.md ou CLAUDE.md, « instrumenter le repo pour l'IA », ou ne sait pas par où commencer — même sans employer le mot init. Ne pas utiliser pour auditer sans modifier (harness-audit) ni pour avancer un dépôt déjà cadré (harness-step).
---

# Harness init — le pas 1

Un AGENTS.md généré par scan du repo (arborescence, commandes de build, conventions de nommage) est du bruit : l'agent découvre tout ça seul en lisant le code. Les règles utiles naissent d'incidents, pas d'un scan. Ce skill pose donc **peu** : un fichier court qui ne dit que le non-découvrable, et un mode explicite.

Il pose le palier 1, « Cadré », et rien d'autre. Un palier est un endroit où l'on peut rester : ce qui est écrit ici doit tenir debout sans le pas suivant. Pas de section Maintenance, pas de marqueur de harvest, pas de Processus de travail, pas de contrat de tâche : ce sont les pas 2 et 4, que harness-step propose quand l'utilisateur veut aller plus loin. Un fichier qui cite un contrat qui n'existe pas encore promet ce qu'il ne tient pas.

Mode par défaut : **délégation** (l'agent reçoit une tâche entière et revient avec une PR). L'assistance (l'humain pilote et relit chaque diff) se choisit explicitement à l'entretien.

## Déroulé

### 1. Entretien — trois questions, en une fois
Pose-les ensemble, avec le défaut proposé. Ne commence rien avant les réponses.

1. **Mode** : délégation (défaut) ou assistance ? Si l'équipe relit chaque diff en direct et qu'aucun agent ne tourne hors session, propose assistance.
2. **Interdits** : qu'est-ce qu'un agent ne doit jamais toucher ou faire (dossiers, secrets, base partagée, migrations prod, force push) ?
3. **Outils et CI** : quels agents (Claude Code seul, ou aussi Copilot, Cursor, Codex) ? Quelle CI, et quels checks **bloquent** la fusion aujourd'hui ?

Si le propriétaire ne sait pas (« je ne l'ai jamais relu »), ne comble pas à sa place : écris moins. L'équipe, la première tâche à déléguer et le processus de travail ne se demandent pas ici.

### 2. Reconnaissance — ne rien écrire avant d'avoir vérifié
- **Où sont les faits.** ADR, post-mortems, notes d'exploitation, CONTRIBUTING, notes de session laissées par un agent : c'est là que vivent les incidents datés. Lis-les avant le code. Un incident chiffré vaut dix conventions.
- **Fichiers d'instructions existants** (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `copilot-instructions.md`) : ne jamais écraser. Classe chaque ligne : à garder, à raccourcir parce qu'un garde-fou la porte, à retirer. Un retrait a un motif, voir « Retirer ».
- **La bonne branche et les fichiers de dossier.** Lis les fichiers d'instructions sur la branche que la PR visera. Cherche les `CLAUDE.md` et `AGENTS.md` de sous-dossiers (`find . -name CLAUDE.md -o -name AGENTS.md`) : ils sont chargés à la demande, c'est là que va ce qui ne concerne qu'eux. Ils se nettoient comme la racine.
- **Secrets.** Cherche clés d'API, mots de passe, tokens (`grep -rnE "apiKey=|api_key|token|password|secret|Bearer |sk_"` sur les fichiers d'instructions, la config et ce qu'ils incluent). Un secret trouvé ne se recopie jamais : dis dans le compte rendu où il est, qu'il reste dans l'historique git et doit être régénéré, et ajoute l'Interdit correspondant.
- **Commandes réelles** : repère build, test, lint, et **exécute-les**. Une commande qui échoue ou n'existe pas ne va pas dans le fichier ; elle va dans « non confirmé » du compte rendu.
- **Garde-fous, et s'ils bloquent.** Pour chaque linter, test d'architecture, script de check : note son chemin, ce qu'il vérifie, et lis la CI pour voir s'il **bloque**. Un job en `continue-on-error`, un filtre de chemins qui ne le déclenche pas, un hook local, un job cité par un document mais absent du workflow : ce garde-fou ne garantit rien. Des tests qui n'affirment rien non plus.

Test pour chaque phrase candidate : *si je l'enlève, l'agent fait-il quelque chose de différent ?* Si non, elle ne va pas dans le fichier.

### 3. Écriture
Depuis `references/agents-template.md`, bloc « Pas 1 » :
- `AGENTS.md` à la racine, **sous 60 lignes**, ligne de mode en tête. Sections vides supprimées plutôt que remplies de générique.
- Chaque règle, et chaque interdit, porte trois choses : **pourquoi** (l'incident, ou « pas d'incident connu » plutôt qu'une raison inventée), **par quoi elle est vérifiée** (`Vérifiée par : <chemin>` seulement pour un garde-fou que tu as vu bloquer, sinon `(non vérifiée)`), et **depuis quand** (`[AAAA-MM]`, la date de l'incident ou de la décision ; à défaut, aujourd'hui). Une règle reprise d'un ancien fichier garde sa date d'origine : elle ne rajeunit pas parce qu'on la recopie.
- Une règle que le dépôt viole déjà le dit, avec le fichier : l'agent ne doit pas prendre le contre-exemple pour modèle.
- Stubs : `CLAUDE.md` contenant uniquement `@AGENTS.md` ; `.github/copilot-instructions.md` et `.cursor/rules/agents.mdc` selon les outils déclarés.
- Un marqueur de harvest déjà présent est gardé tel quel. On n'en pose pas.

### 4. Gate — l'état mesuré
`python3 cli/harness.py status <repo>` (CLI du dépôt harness-ai) écrit `.harness/state.json`. Attendu : palier 1, cinq vérifications sur cinq, aucune « référence sans cible ». Corrige avant de rendre la main. L'audit complet n'est pas le gate du pas 1 : c'est un pas du palier 3.

### 5. Compte rendu, puis on s'arrête
Toujours le même format :
- **Avant et après** : palier, lignes chargées par session, nombre de règles.
- **Fichiers** créés ou modifiés (chemin, lignes).
- **Retiré**, par motif, une ligne chacun avec la raison.
- **Secrets** trouvés et ce qu'il reste à faire.
- **Règles écrites**, avec leur statut (vérifiée par quoi, ou non vérifiée) et leur date.
- **Commandes** confirmées et non confirmées.
- **Questions** au propriétaire, numérotées, avec le défaut proposé : les lignes périmées à confirmer, ce que tu as observé sans pouvoir l'expliquer.
- **Le pas suivant possible**, en une ligne, sans le faire. C'est à l'utilisateur de dire s'il veut aller plus loin (`harness target`), et à harness-step de le mener.

## Retirer

Sur un dépôt qui a déjà des instructions, le plus gros du travail est de retirer. La question pour chaque ligne n'est pas « est-elle vraie » mais « change-t-elle encore ce que fait l'agent ». Trois motifs, à ne pas confondre :

| Motif | C'est | Exemples | Ce qu'on fait |
|---|---|---|---|
| **Inutile** | Découvrable dans le dépôt, ou ce qu'un modèle fait sans qu'on le dise | Arborescence, stack, « écris du code propre », « réfléchis étape par étape », journal de session | On retire, sans demander |
| **Nuisible** | Écrite pour une limite disparue, ou contraire à un garde-fou : elle dégrade le travail d'un agent d'aujourd'hui | « Réécris le fichier entier au-delà de 500 lignes », « demande confirmation avant chaque commande » en délégation, une consigne que la CI refuse | On retire, et on le signale à part |
| **Périmée** | Vraie hier, plus aujourd'hui | Compatibilité avec un navigateur ou une version abandonnés | **On demande** : seul le propriétaire le sait. Une ligne périmée se retire après sa réponse, jamais avant |

Ne retire jamais une ligne née d'un incident parce qu'elle a l'air évidente : c'est précisément celle que le dépôt ne dit pas. Dans un fichier généré de cent lignes, il y en a souvent deux, tout en bas.

## Délégation vs assistance — ce qui change au pas 1

| | Délégation (défaut) | Assistance |
|---|---|---|
| Qui vérifie | La CI et les garde-fous ; personne ne relit en route | L'humain, à chaque diff |
| Règle `(non vérifiée)` | Une dette : elle sera sautée un jour sur dix | Un coût de contexte seulement |
| Suite naturelle | Garde-fous (palier 3), puis processus et contrats (palier 4) | Souvent rien : le palier 1 suffit |

## Ce qu'on n'écrit pas
- Arborescence, liste des modules, stack technique : découvrable.
- Conventions que le modèle applique déjà (nommage standard, gestion de ressources idiomatique).
- Commandes non testées, règles « au cas où », principes génériques.
- « Vérifiée par » pour un garde-fou qu'on n'a pas vu bloquer.
- Le matériel des paliers suivants.

## Pièges fréquents
- Répondre soi-même aux questions de l'entretien pour aller plus vite : le mode et les interdits viennent de l'utilisateur, pas du scan.
- Écraser un CLAUDE.md existant parce qu'il est mauvais : on trie ligne à ligne et on dit ce qu'on a retiré.
- Dépasser 60 lignes « parce que c'est important » : si c'est important et long, c'est un fichier de référence chargé à la demande.
- Oublier la ligne de mode : harness-audit s'en sert pour choisir son barème.
- Croire un document qui dit « vérifié par le lint » sans ouvrir le workflow.
- Enchaîner sur le pas suivant parce qu'on y est : l'utilisateur n'a rien demandé de plus.
