---
name: harness-harvest
description: Fait évoluer un AGENTS.md / CLAUDE.md et les contrats de tâches à partir de ce qui s'est réellement passé depuis le dernier harvest — commentaires de review `rule:`, corrections après coup sur des PRs d'agent, reverts, checks CI ignorés, tâches récurrentes — et propose dans une PR dédiée des ajouts, retraits, raccourcissements, push-down en CI ou nouveaux contrats, chacun justifié par ses preuves. Source GitHub en premier, extensible (Jira, GitLab…). Utiliser quand l'utilisateur veut « mettre à jour les règles », « voir ce qu'on a appris ce mois-ci », « faire le ménage dans AGENTS.md », exploiter les reviews ou les PRs récentes pour améliorer l'instrumentation, ou quand un harvest planifié se déclenche — même sans employer le mot harvest. Ne pas utiliser pour créer le fichier initial (harness-init) ni pour un audit sans proposition de changement (harness-audit).
---

# Harness harvest

Un AGENTS.md ne s'améliore pas en le relisant : il s'améliore en confrontant ses règles à ce qui s'est passé. Ce skill cherche des **signaux** dans l'activité récente, les transforme en **candidats** de changement, et les propose dans une PR où chaque candidat est un commit séparé, justifié par des liens. Il n'écrit jamais directement dans la branche principale.

L'important n'est pas la source, c'est ce qu'on y cherche. Le catalogue des signaux, leur force et le schéma d'évidence commun sont dans `references/signals.md` ; les sources ne sont que des adaptateurs qui produisent ce schéma. Lis le catalogue avant de commencer.

## Déroulé

### 1. Cadrer la fenêtre
- Cherche le marqueur `<!-- harvest: last=<date> ref=<sha ou url> -->` dans la section « Maintenance » de AGENTS.md. La fenêtre va de cette date à maintenant.
- Sans marqueur : fenêtre de 30 jours, et dis-le dans la PR ; le marqueur sera posé par cette PR.
- Lis la ligne « Mode » de AGENTS.md. En délégation, une règle racontée sans garde-fou est un défaut à traiter ; en assistance, c'est un coût de contexte.
- Identifie ce qui compte comme **PR d'agent** : auteur bot, trailer `Co-Authored-By` d'un agent, préfixe de branche, label. Demande si rien n'est évident ; ne devine pas.

### 2. Collecter — scripts d'abord, lecture ensuite
Chaque source a un script dans `scripts/` qui produit le JSON d'évidences du catalogue, sans LLM : `scripts/github.py --repo <owner/repo> --agents-md AGENTS.md` pour GitHub (options et marqueurs d'agent dans `references/signals.md`). Lance le script, ne reconstitue pas les évidences à la main depuis l'interface. Si le script manque ou échoue, dis-le et limite la PR à ce qui a pu être collecté ; une évidence non collectée n'est pas inventée.

Lis aussi l'état courant : AGENTS.md, ses règles une par une, les contrats dans `.claude/skills/`, les garde-fous CI existants. Sans ça, impossible de détecter une règle orpheline ou un doublon.

### 3. Regrouper en candidats
Une évidence seule n'est pas un candidat, sauf un `rule:` explicite. Regroupe par règle existante touchée, par fichiers ou zone, par reviewer et motif. Pour chaque groupe, pose dans l'ordre :

1. **Existe-t-il déjà une règle ?** Si oui et qu'elle a été violée : elle est mal placée ou mal dite, pas absente. Si oui et qu'elle n'a aucune évidence : candidate orpheline.
2. **Un garde-fou peut-il la porter ?** Règle de lint, test d'architecture, check de PR, hook. Si oui, la proposition est PUSH_DOWN avec l'outil nommé, et AGENTS.md ne garde qu'une ligne « Vérifiée par ».
3. **Est-ce une règle ou une tâche ?** Trois PRs du même type en un mois, c'est un contrat de tâche à créer, pas une phrase à ajouter.
4. **La règle est-elle formulable au présent, vérifiable, en une phrase ?** Sinon, ce n'est pas encore une règle : propose une question à l'équipe dans la PR plutôt qu'un texte.

### 4. Décider
Un verdict par candidat :

| Verdict | Quand | Ce que contient le commit |
|---|---|---|
| **PUSH_DOWN** | Un outil peut vérifier la règle | Le garde-fou (ou son squelette) + la ligne « Vérifiée par » dans AGENTS.md |
| **ADD** | Règle neuve, justifiée, non vérifiable aujourd'hui | La ligne dans « Règles » avec pourquoi, lien, et `(non vérifiée)` |
| **SHORTEN** | Règle existante désormais couverte par un garde-fou | La règle réduite à une ligne de pointeur |
| **REMOVE** | Règle sans évidence depuis deux harvests ou contredite par la pratique | La suppression, avec la raison dans le message de commit |
| **CONTRACT** | Tâche récurrente sans contrat | Un squelette de `.claude/skills/<tâche>/SKILL.md` |
| **ASK** | Signal réel mais règle non formulable | Une question dans la description de la PR, pas de changement de fichier |

Ce qui ne devient jamais un candidat : une convention devinée depuis le code sans incident, une règle qu'un modèle récent applique déjà, une préférence d'un seul reviewer exprimée une fois sans `rule:`.

### 5. Proposer
Une PR, format fixe dans `references/proposal-template.md` : un commit par candidat, description qui liste les candidats avec verdict, preuves et ce qui a été ignoré et pourquoi, section « non collecté », et mise à jour du marqueur de harvest en dernier commit. Jamais de push direct, jamais de fusion automatique. S'il n'y a aucun candidat, la PR ne contient que le marqueur et la liste des règles confirmées par l'absence d'incident : c'est une information utile.

## Pièges fréquents
- Ajouter une phrase parce qu'un signal existe : le premier réflexe est le garde-fou, le deuxième le contrat, la phrase en dernier.
- Reproposer un candidat refusé au harvest précédent : relis les PRs de harvest fermées dans la fenêtre et marque ces candidats comme déjà refusés.
- Traiter une PR humaine corrigée comme un signal d'agent : seules les PRs d'agent et les `rule:` explicites parlent de l'instrumentation.
- Oublier les retraits : un harvest qui n'a que des ADD fait grossir le fichier jusqu'au monolithe.
- Collecter à la main depuis l'interface : c'est lent, non reproductible et ça finit par inventer.
