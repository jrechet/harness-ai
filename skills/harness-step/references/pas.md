# Les pas, vérification par vérification

Pour chaque vérification en échec de `harness status` : le pas, ce qu'il coûte, à quoi on reconnaît qu'il est fait. Un pas par invocation. Les gabarits de texte sont dans `skills/harness-init/references/agents-template.md`.

## Palier 1 — Cadré

Au palier 0, plusieurs vérifications échouent ensemble : le pas est **harness-init**, en entier. Quand une seule manque, le pas est ciblé :

| Vérification | Le pas | Coût | Fait quand |
|---|---|---|---|
| `L1.source` | harness-init | Trois questions, une demi-heure | AGENTS.md existe |
| `L1.mode` | Demander le mode, écrire la ligne en tête | Une question | La ligne « Mode : » est lue par `status` |
| `L1.short` | Déporter la référence dans `docs/agents/` ou retirer le bruit, voir « Retirer » de harness-init | Tri ligne à ligne | 60 lignes au plus |
| `L1.single_source` | Fusionner le contenu utile de CLAUDE.md dans AGENTS.md, réduire CLAUDE.md à `@AGENTS.md` | Tri ligne à ligne | CLAUDE.md est un stub |
| `L1.forbidden` | Demander les interdits, écrire la section | Une question | La section existe |

## Palier 2 — Bouclé

Ce palier se gagne dans le temps : deux vérifications sont des fichiers, deux sont des faits.

| Vérification | Le pas | Coût | Fait quand |
|---|---|---|---|
| `L2.maintenance`, `L2.rule_convention` | Ajouter le bloc « Pas 2 » du gabarit : section Maintenance, convention `rule:`, marqueur `ref=init` si le fichier n'en a pas. Dire à l'équipe, en deux phrases, comment écrire un `rule:` | Dix minutes, et une habitude à prendre | Les deux vérifications passent |
| `L2.marker_fresh` | Lancer harness-harvest, s'il y a eu des revues depuis le marqueur | Une PR de harvest à relire | Le marqueur a moins de 45 jours |
| `L2.signal` | Rien à écrire. Le signal vient d'un `rule:` en review ou d'une PR d'agent corrigée. S'il n'y en a pas, le dire : la boucle est posée, elle n'a pas encore tourné | Du temps | Un harvest trouve un signal réel |

Si le marqueur est frais et qu'il n'y a pas de signal, **ce palier n'a plus de pas** : il attend. Si l'objectif est plus haut, passe au premier pas du palier 3 ; sinon, dis-le et arrête-toi. Inventer une règle pour faire passer la vérification est le contraire du but.

## Palier 3 — Vérifié

Une règle à la fois. Préfère celle qui a un incident, puis celle dont le garde-fou coûte le moins.

| Vérification | Le pas | Coût | Fait quand |
|---|---|---|---|
| `L3.ci` | Proposer une CI minimale qui lance les commandes confirmées d'AGENTS.md | Un workflow | Un workflow existe et a tourné vert |
| `L3.guarded` | Prendre **une** règle `(non vérifiée)` et la faire porter par un outil : une option d'un linter déjà là, un test, un script appelé par la CI. Puis réduire la règle à sa ligne « Vérifiée par » | Du code de garde-fou, d'une ligne de config à un script testé | Le garde-fou a été **vu rouge** sur une violation, puis vert |
| `L3.justified` | Demander le pourquoi des règles qui n'en ont pas. Sans réponse : « pas d'incident connu », ou retrait | Des questions | La moitié des règles disent pourquoi |
| `L3.audit` | Lancer harness-audit, écrire son JSON dans `.harness/audit.json`. S'il reste un P1 : le pas suivant sera de le traiter | Un audit à relire | Un audit existe sans P1 ouvert |

Trois choses apprises sur de vrais dépôts :
- Un garde-fou ne compte que s'il **bloque**. Un job en `continue-on-error`, un filtre de chemins qui ne le déclenche pas ou un hook local qu'on saute avec `--no-verify` ne garantissent rien.
- Un workflow planifié ou à lancement manuel ne tourne que depuis la **branche par défaut**. Un garde-fou fusionné sur une branche de travail seule est inerte.
- Pousser tout en garde-fou rend un dépôt rigide. Une règle de jugement reste une phrase.

## Palier 4 — Délégué

| Vérification | Le pas | Coût | Fait quand |
|---|---|---|---|
| `L4.mode` | Demander si l'équipe veut passer en délégation. En assistance, ce palier n'est pas un objectif | Une question | Mode délégation |
| `L4.process` | Trois questions : quand s'arrêter et demander, quand une tâche est finie, quoi faire d'une CI rouge ou d'un test instable. Écrire le bloc « Pas 4 » | Trois questions | La section existe |
| `L4.contracts` | Demander la première tâche répétitive à confier. Écrire son contrat `.claude/skills/<tâche>/SKILL.md` : étapes, vérifications, critère de fini. Puis seulement la ligne « Tâches déléguées » | Une question, un fichier court | Le contrat existe et il est cité |
| `L4.clean_prs` | Lancer harness-harvest sur une fenêtre qui contient des PR d'agent. Chaque correction après coup est une règle ou un garde-fou manquant : le pas est d'en traiter une | Des PR à observer | Un harvest sans correction après coup |
| `L4.cut_the_agent` | Dans le dernier audit, prendre la première étape qui n'existe que dans un prompt et la pousser dans un script ou un workflow | Du code | Le test de l'audit passe |

## Références sans cible

`status` les liste à part. Elles passent avant tout autre pas :
- **Contrat cité, SKILL.md introuvable** : écrire le contrat, ou retirer la ligne.
- **Garde-fou cité, chemin introuvable** : la règle n'est plus vérifiée. Remettre `(non vérifiée)`, ou retrouver où le garde-fou est parti.
