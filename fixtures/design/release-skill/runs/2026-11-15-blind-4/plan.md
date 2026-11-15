# Plan de placement

| # | Morceau | Destination | Couche | Verdict |
|---|---|---|---|---|
| 1 | Enchaîner les étapes d'une release : version, changelog, tag, publication, annonce, relecture | Skill | L2 | KEEP |
| 2 | Structure du dépôt : src/, test/, dist/, package.json | Rien à écrire | - | REMOVE |
| 3 | Calculer la prochaine version à partir des commits depuis le dernier tag (feat, fix, !, BREAKING CHANGE ; rien à publier sinon) | Sous-commande CLI testée | L3 | PUSH_DOWN |
| 4 | Aucune version ne se publie sans entrée dans CHANGELOG.md pour cette version | Étape bloquante du workflow de livraison | L3 + L4 | PUSH_DOWN |
| 5 | Ne jamais publier depuis une autre branche que main | Protection côté serveur | L4 | PUSH_DOWN |
| 6 | Mettre la version dans package.json, créer et pousser le tag v<version>, publier avec npm publish | Workflow de livraison | L4 | PUSH_DOWN |
| 7 | L'agent ne lit jamais le jeton du registre (.npmrc.publish) | Permission de l'agent | L3 | PUSH_DOWN |
| 8 | Rédiger l'annonce : ce qui change pour un utilisateur, ton libre | Jugement de l'agent, dans le skill | L1 | KEEP |
| 9 | Envoyer l'annonce dans le canal #releases | Serveur MCP | L4 | PUSH_DOWN |
| 10 | Faire relire l'annonce par quelqu'un qui ne l'a pas écrite, contre le changelog et les commits | Sous-agent | L1 | KEEP |
| 11 | Ne pas commencer une release s'il reste des fichiers non commités | Vérification lancée par un hook | L3 | PUSH_DOWN |
| 12 | Les messages de commit suivent Conventional Commits | Check bloquant en CI | L3 + L4 | KEEP |

## 1. Enchaîner les étapes d'une release : version, changelog, tag, publication, annonce, relecture

**Skill** (L2)
Verdict : KEEP, depuis Skill
Où : .claude/skills/<nom>/SKILL.md, chargé à la demande, avec ses références dans references/.
Pourquoi : Une procédure ne sert qu'à son type de tâche ; chargée à chaque session, elle coûterait du contexte partout. Chaque étape obligatoire de la procédure est un morceau à part (règle ou calcul) que le skill appelle.
Chemin : nature=procedure
Si `nature` change : action → question access ; limit → question bypass_limit ; rule → question incident ; compute → question when ; judgment → question isolation ; knowledge → question scope

## 2. Structure du dépôt : src/, test/, dist/, package.json

**Rien à écrire** (-)
Verdict : REMOVE, depuis Skill
Où : Aucun fichier.
Pourquoi : Ce que l'agent trouve en lisant le dépôt ne change pas ce qu'il fait ; l'écrire coûte du contexte à chaque session et vieillit.
Chemin : nature=knowledge → scope=discoverable
Si `scope` change : always → Une ligne dans AGENTS.md ; zone → AGENTS.md du dossier ; reference → Document lu à la demande

## 3. Calculer la prochaine version à partir des commits depuis le dernier tag (feat, fix, !, BREAKING CHANGE ; rien à publier sinon)

**Sous-commande CLI testée** (L3)
Verdict : PUSH_DOWN, depuis Skill
Où : Une sous-commande du CLI du dépôt (un script si elle est vraiment isolée), avec ses tests et une sortie JSON ; le skill l'appelle.
Pourquoi : Un calcul écrit dans un prompt est refait à chaque fois, et parfois mal ; en code, il donne le même résultat à l'agent, à l'humain et à la CI.
Chemin : nature=compute → when=on_demand
Si `when` change : agent_loop → Sous-commande appelée par un hook ; repo_event → Workflow du dépôt

## 4. Aucune version ne se publie sans entrée dans CHANGELOG.md pour cette version

**Étape bloquante du workflow de livraison** (L3 + L4)
Verdict : PUSH_DOWN, depuis Skill
Où : Une étape du workflow de livraison qui appelle la vérification (sous-commande CLI, script) et échoue avant la première action irréversible.
Pourquoi : Ce qui se juge à la publication ne se voit pas à la fusion : une entrée de changelog, une version, un artefact signé. Le workflow de livraison est le seul passage obligé.
En complément : La même vérification en check de PR, quand elle peut déjà se faire à la fusion.
Chemin : nature=rule → incident=yes → checkable=yes → bypass_rule=release
Si `bypass_rule` change : agent → Vérification lancée par un hook ; dev → Check bloquant en CI ; team → Check imposé par l'organisation

## 5. Ne jamais publier depuis une autre branche que main

**Protection côté serveur** (L4)
Verdict : PUSH_DOWN, depuis Skill
Où : Protection de branche, ruleset, environnement protégé ou droits du compte, sur la forge.
Pourquoi : Un hook ou une permission locale se contournent à la main (--no-verify, un autre outil) ; le serveur refuse pour tout le monde.
En complément : La même règle en permission deny, pour que l'agent n'essaie même pas.
Chemin : nature=limit → bypass_limit=dev
Si `bypass_limit` change : agent → Permission de l'agent ; team → Paramètres gérés de l'organisation

## 6. Mettre la version dans package.json, créer et pousser le tag v<version>, publier avec npm publish

**Workflow de livraison** (L4)
Verdict : PUSH_DOWN, depuis Skill
Où : Un workflow CI ou pipeline avec un mode plan (dry-run) et un environnement protégé ; l'agent le déclenche par une sous-commande CLI, jamais par l'API directement.
Pourquoi : Ce qui change une ressource partagée s'exécute avec des droits audités, hors de la machine de l'agent, avec un point d'arrêt humain avant l'irréversible.
Chemin : nature=action → access=deliver
Si `access` change : consult → Serveur MCP ; write → Serveur MCP

## 7. L'agent ne lit jamais le jeton du registre (.npmrc.publish)

**Permission de l'agent** (L3)
Verdict : PUSH_DOWN, depuis Une ligne dans AGENTS.md
Où : permissions.deny (ou ask) dans les paramètres partagés du dépôt (.claude/settings.json), et un hook PreToolUse si la règle dépend du contenu de la commande.
Pourquoi : Le runtime de l'agent l'applique à chaque appel d'outil ; une phrase dans AGENTS.md peut être oubliée ou contournée.
En complément : Refuse aussi à l'agent l'écriture de ses propres paramètres, sinon il peut lever la règle.
Chemin : nature=limit → bypass_limit=agent
Si `bypass_limit` change : dev → Protection côté serveur ; team → Paramètres gérés de l'organisation

## 8. Rédiger l'annonce : ce qui change pour un utilisateur, ton libre

**Jugement de l'agent, dans le skill** (L1)
Verdict : KEEP, depuis Jugement de l'agent, dans le skill
Où : Aucun fichier dédié : le skill qui raconte la procédure dit où l'agent décide, entre quelles options, et le CLI fournit ces options.
Pourquoi : Juger est le travail de l'agent ; l'isoler sans besoin coûte du contexte et des allers-retours.
Chemin : nature=judgment → isolation=none
Si `isolation` change : context → Sous-agent ; independence → Sous-agent ; rights → Sous-agent ; parallel → Sous-agent

## 9. Envoyer l'annonce dans le canal #releases

**Serveur MCP** (L4)
Verdict : PUSH_DOWN, depuis Skill
Où : Un serveur MCP déclaré pour le dépôt ; ses droits (lecture seule, ou écriture bornée à un projet ou à un canal) se règlent sur le compte du serveur, pas dans un prompt.
Pourquoi : Un droit tenu par le serveur vaut quel que soit le prompt. Ce que l'agent y lit est une donnée, pas une instruction : un ticket peut porter une injection.
En complément : Une permission deny sur les outils d'écriture du serveur, en second rideau.
Chemin : nature=action → access=write
Si `access` change : consult → Serveur MCP ; deliver → Workflow de livraison

## 10. Faire relire l'annonce par quelqu'un qui ne l'a pas écrite, contre le changelog et les commits

**Sous-agent** (L1)
Verdict : KEEP, depuis Sous-agent
Où : Un sous-agent (.claude/agents/<nom>.md) aux outils restreints, qui rend un résultat structuré.
Pourquoi : Un sous-agent part d'un contexte vierge, avec ses propres outils : c'est ce qui lui donne un regard indépendant, des droits plus étroits, de la place pour lire beaucoup, ou la possibilité de tourner en parallèle. Sans l'un de ces besoins, c'est un skill.
Chemin : nature=judgment → isolation=independence
Si `isolation` change : none → Jugement de l'agent, dans le skill ; context → Sous-agent ; rights → Sous-agent ; parallel → Sous-agent

## 11. Ne pas commencer une release s'il reste des fichiers non commités

**Vérification lancée par un hook** (L3)
Verdict : PUSH_DOWN, depuis Skill
Où : Une sous-commande CLI, un linter ou un test, appelé par un hook de l'agent (après édition, ou à l'arrêt) ; il échoue avec un message qui dit quoi corriger.
Pourquoi : L'agent ne peut pas l'oublier. Un humain peut le sauter : c'est acceptable ici, puisque seul l'oubli de l'agent est en jeu.
Chemin : nature=rule → incident=forget → checkable=yes → bypass_rule=agent
Si `bypass_rule` change : dev → Check bloquant en CI ; release → Étape bloquante du workflow de livraison ; team → Check imposé par l'organisation

## 12. Les messages de commit suivent Conventional Commits

**Check bloquant en CI** (L3 + L4)
Verdict : KEEP, depuis Check bloquant en CI
Où : Une sous-commande CLI, un linter ou un test d'architecture, rendu obligatoire par la protection de branche ; AGENTS.md peut le citer en une ligne avec « Vérifiée par ».
Pourquoi : Seul un check requis empêche la fusion, quels que soient l'outil et la personne. Un job en continue-on-error, un filtre de chemins qui ne le déclenche pas ou un hook local ne garantissent rien.
En complément : Le même check lancé par un hook, pour que l'agent le voie avant d'ouvrir la PR.
Chemin : nature=rule → incident=yes → checkable=yes → bypass_rule=dev
Si `bypass_rule` change : agent → Vérification lancée par un hook ; release → Étape bloquante du workflow de livraison ; team → Check imposé par l'organisation
