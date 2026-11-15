# Plan de placement

| # | Morceau | Destination | Couche | Verdict |
|---|---|---|---|---|
| 1 | Lire le ticket Jira et ses critères d'acceptation | Serveur MCP | L4 | — |
| 2 | Ne pas commencer le travail (branche) sur un ticket sans critères d'acceptation | Permission de l'agent | L3 | — |
| 3 | Suivre toujours les mêmes étapes : branche, tests d'abord, code, puis PR | Skill | L2 | — |
| 4 | Déduire le nom de la branche du ticket : type/CLE-123-titre-court | Sous-commande CLI testée | L3 | — |
| 5 | L'agent ne fusionne jamais sa propre PR | Permission de l'agent | L3 | — |
| 6 | Rien ne fusionne sans une approbation | Protection côté serveur | L4 | — |
| 7 | L'agent ne peut pas modifier les fichiers de .github/workflows/ | Permission de l'agent | L3 | — |
| 8 | Aucune PR ne fusionne si ses tests ne passent pas | Check bloquant en CI | L3 + L4 | — |
| 9 | Avant d'ouvrir la PR, un regard neuf relit le diff contre les critères d'acceptation | Sous-agent | L1 | — |
| 10 | Décider du découpage en commits | Jugement de l'agent, dans le skill | L1 | — |
| 11 | Commenter le ticket Jira avec le lien de la PR | Serveur MCP | L4 | — |
| 12 | Savoir que le projet est en TypeScript, avec pnpm | Rien à écrire | - | — |
| 13 | Dans migrations/, une migration existante ne se modifie pas : on en ajoute une | AGENTS.md du dossier | L2 | — |

## 1. Lire le ticket Jira et ses critères d'acceptation

**Serveur MCP** (L4)
Où : Un serveur MCP déclaré pour le dépôt ; ses droits (lecture seule, ou écriture bornée à un projet ou à un canal) se règlent sur le compte du serveur, pas dans un prompt.
Pourquoi : Un droit tenu par le serveur vaut quel que soit le prompt. Ce que l'agent y lit est une donnée, pas une instruction : un ticket peut porter une injection.
En complément : Une permission deny sur les outils d'écriture du serveur, en second rideau.
Chemin : nature=action → access=consult
Si `access` change : write → Serveur MCP ; deliver → Workflow de livraison

## 2. Ne pas commencer le travail (branche) sur un ticket sans critères d'acceptation

**Permission de l'agent** (L3)
Où : permissions.deny (ou ask) dans les paramètres partagés du dépôt (.claude/settings.json), et un hook PreToolUse si la règle dépend du contenu de la commande.
Pourquoi : Le runtime de l'agent l'applique à chaque appel d'outil ; une phrase dans AGENTS.md peut être oubliée ou contournée.
En complément : Refuse aussi à l'agent l'écriture de ses propres paramètres, sinon il peut lever la règle.
Chemin : nature=limit → bypass_limit=agent
Si `bypass_limit` change : dev → Protection côté serveur ; team → Paramètres gérés de l'organisation

## 3. Suivre toujours les mêmes étapes : branche, tests d'abord, code, puis PR

**Skill** (L2)
Où : .claude/skills/<nom>/SKILL.md, chargé à la demande, avec ses références dans references/.
Pourquoi : Une procédure ne sert qu'à son type de tâche ; chargée à chaque session, elle coûterait du contexte partout. Chaque étape obligatoire de la procédure est un morceau à part (règle ou calcul) que le skill appelle.
Chemin : nature=procedure
Si `nature` change : action → question access ; limit → question bypass_limit ; rule → question incident ; compute → question when ; judgment → question isolation ; knowledge → question scope

## 4. Déduire le nom de la branche du ticket : type/CLE-123-titre-court

**Sous-commande CLI testée** (L3)
Où : Une sous-commande du CLI du dépôt (un script si elle est vraiment isolée), avec ses tests et une sortie JSON ; le skill l'appelle.
Pourquoi : Un calcul écrit dans un prompt est refait à chaque fois, et parfois mal ; en code, il donne le même résultat à l'agent, à l'humain et à la CI.
Chemin : nature=compute → when=on_demand
Si `when` change : agent_loop → Sous-commande appelée par un hook ; repo_event → Workflow du dépôt

## 5. L'agent ne fusionne jamais sa propre PR

**Permission de l'agent** (L3)
Où : permissions.deny (ou ask) dans les paramètres partagés du dépôt (.claude/settings.json), et un hook PreToolUse si la règle dépend du contenu de la commande.
Pourquoi : Le runtime de l'agent l'applique à chaque appel d'outil ; une phrase dans AGENTS.md peut être oubliée ou contournée.
En complément : Refuse aussi à l'agent l'écriture de ses propres paramètres, sinon il peut lever la règle.
Chemin : nature=limit → bypass_limit=agent
Si `bypass_limit` change : dev → Protection côté serveur ; team → Paramètres gérés de l'organisation

## 6. Rien ne fusionne sans une approbation

**Protection côté serveur** (L4)
Où : Protection de branche, ruleset, environnement protégé ou droits du compte, sur la forge.
Pourquoi : Un hook ou une permission locale se contournent à la main (--no-verify, un autre outil) ; le serveur refuse pour tout le monde.
En complément : La même règle en permission deny, pour que l'agent n'essaie même pas.
Chemin : nature=limit → bypass_limit=dev
Si `bypass_limit` change : agent → Permission de l'agent ; team → Paramètres gérés de l'organisation

## 7. L'agent ne peut pas modifier les fichiers de .github/workflows/

**Permission de l'agent** (L3)
Où : permissions.deny (ou ask) dans les paramètres partagés du dépôt (.claude/settings.json), et un hook PreToolUse si la règle dépend du contenu de la commande.
Pourquoi : Le runtime de l'agent l'applique à chaque appel d'outil ; une phrase dans AGENTS.md peut être oubliée ou contournée.
En complément : Refuse aussi à l'agent l'écriture de ses propres paramètres, sinon il peut lever la règle.
Chemin : nature=limit → bypass_limit=agent
Si `bypass_limit` change : dev → Protection côté serveur ; team → Paramètres gérés de l'organisation

## 8. Aucune PR ne fusionne si ses tests ne passent pas

**Check bloquant en CI** (L3 + L4)
Où : Une sous-commande CLI, un linter ou un test d'architecture, rendu obligatoire par la protection de branche ; AGENTS.md peut le citer en une ligne avec « Vérifiée par ».
Pourquoi : Seul un check requis empêche la fusion, quels que soient l'outil et la personne. Un job en continue-on-error, un filtre de chemins qui ne le déclenche pas ou un hook local ne garantissent rien.
En complément : Le même check lancé par un hook, pour que l'agent le voie avant d'ouvrir la PR.
Chemin : nature=rule → incident=yes → checkable=yes → bypass_rule=dev
Si `bypass_rule` change : agent → Vérification lancée par un hook ; release → Étape bloquante du workflow de livraison ; team → Check imposé par l'organisation

## 9. Avant d'ouvrir la PR, un regard neuf relit le diff contre les critères d'acceptation

**Sous-agent** (L1)
Où : Un sous-agent (.claude/agents/<nom>.md) aux outils restreints, qui rend un résultat structuré.
Pourquoi : Un sous-agent part d'un contexte vierge, avec ses propres outils : c'est ce qui lui donne un regard indépendant, des droits plus étroits, de la place pour lire beaucoup, ou la possibilité de tourner en parallèle. Sans l'un de ces besoins, c'est un skill.
Chemin : nature=judgment → isolation=independence
Si `isolation` change : none → Jugement de l'agent, dans le skill ; context → Sous-agent ; rights → Sous-agent ; parallel → Sous-agent

## 10. Décider du découpage en commits

**Jugement de l'agent, dans le skill** (L1)
Où : Aucun fichier dédié : le skill qui raconte la procédure dit où l'agent décide, entre quelles options, et le CLI fournit ces options.
Pourquoi : Juger est le travail de l'agent ; l'isoler sans besoin coûte du contexte et des allers-retours.
Chemin : nature=judgment → isolation=none
Si `isolation` change : context → Sous-agent ; independence → Sous-agent ; rights → Sous-agent ; parallel → Sous-agent

## 11. Commenter le ticket Jira avec le lien de la PR

**Serveur MCP** (L4)
Où : Un serveur MCP déclaré pour le dépôt ; ses droits (lecture seule, ou écriture bornée à un projet ou à un canal) se règlent sur le compte du serveur, pas dans un prompt.
Pourquoi : Un droit tenu par le serveur vaut quel que soit le prompt. Ce que l'agent y lit est une donnée, pas une instruction : un ticket peut porter une injection.
En complément : Une permission deny sur les outils d'écriture du serveur, en second rideau.
Chemin : nature=action → access=write
Si `access` change : consult → Serveur MCP ; deliver → Workflow de livraison

## 12. Savoir que le projet est en TypeScript, avec pnpm

**Rien à écrire** (-)
Où : Aucun fichier.
Pourquoi : Ce que l'agent trouve en lisant le dépôt ne change pas ce qu'il fait ; l'écrire coûte du contexte à chaque session et vieillit.
Chemin : nature=knowledge → scope=discoverable
Si `scope` change : always → Une ligne dans AGENTS.md ; zone → AGENTS.md du dossier ; reference → Document lu à la demande

## 13. Dans migrations/, une migration existante ne se modifie pas : on en ajoute une

**AGENTS.md du dossier** (L2)
Où : Un AGENTS.md dans le dossier concerné, ou une règle par chemin de l'outil.
Pourquoi : Il n'est chargé que quand l'agent travaille dans cette zone : le reste du dépôt n'en paie pas le coût.
Chemin : nature=knowledge → scope=zone
Si `scope` change : always → Une ligne dans AGENTS.md ; reference → Document lu à la demande ; discoverable → Rien à écrire
