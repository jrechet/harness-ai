---
name: harness-stress
description: Met les skills de harness-ai à l'épreuve sur les projets types de `fixtures/`, à l'aveugle, puis propose leurs corrections dans une PR dédiée — annonce le plan et son coût avant de lancer quoi que ce soit, fait jouer chaque skill ou chaque tâche par un agent neuf qui n'a jamais vu le corrigé, note avec le CLI, range chaque écart dans une seule cause, ne corrige que le texte des skills, puis mesure sur des projets tenus à l'écart. Utiliser quand le propriétaire demande de « stresser », « tester », « mesurer » ou « évaluer » un skill ou tout le harness, de rejouer le banc après un changement de modèle, de vérifier qu'une modification de SKILL.md n'a rien cassé, ou de savoir si une règle ou une couche du harness sert encore. Ne jamais lancer de soi-même : une campagne coûte des centaines de milliers de tokens.
---

# Harness stress

Un skill ne s'améliore pas en le relisant : il s'améliore en le regardant échouer. Ce skill organise cet échec, le note sans complaisance, et en tire des corrections **qui valent ailleurs que sur le banc**.

Le risque de l'exercice est connu : un agent qui peut modifier à la fois la copie et le corrigé fait toujours monter la note. D'où quatre règles qui ne se discutent pas.

- **Tu ne touches jamais au corrigé.** `expected.json`, `traps.md`, `tasks/`, `owner.md` et le code du noteur (`cli/`) sont hors de ta portée d'écriture. Si le corrigé te semble faux, c'est une question pour le propriétaire, dans la PR.
- **Tu ne corriges que le texte des skills** (`skills/**`), une leçon par commit.
- **Une leçon se dit sans nommer le banc.** Si tu ne peux pas l'écrire sans citer un projet type ou un de ses identifiants, ce n'est pas une leçon : c'est du par cœur.
- **Les projets `holdout` ne servent qu'à mesurer.** Tu ne lis pas leurs écarts pour corriger un skill. Tu regardes seulement si leur note a bougé.

## Déroulé

### 1. Le plan, et son prix, avant tout
`python3 cli/harness.py bench plan` liste les exécutions d'agent et leur coût estimé. Restreins avec `--kind audit|init|task`, `--fixture <nom>`, `--role tuning|holdout|all`.

Annonce au propriétaire : ce que la campagne mesure, combien d'exécutions, combien de tokens, et ce qu'elle ne mesure pas. Si sa demande nommait déjà le périmètre (« stresse l'audit sur ts-monorepo »), lance. Si elle était ouverte (« stresse le harness »), propose deux ou trois périmètres avec leur prix et attends son choix. Ne dépasse jamais le budget annoncé sans redemander.

### 2. Préparer chaque exécution, hors du dépôt
L'agent évalué ne doit rien pouvoir lire du corrigé. Tout se passe dans un dossier de travail temporaire, jamais sous `fixtures/`.

- **Le kit** : une copie de `skills/` et de `cli/` dans le dossier temporaire. C'est tout ce que l'agent connaît de harness-ai.
- **Le dépôt** :
  - mesure d'audit : `bench prepare <projet> <dir> --arm asis` ;
  - mesure d'init : `bench prepare <projet> <dir> --arm asis` s'il a déjà des instructions, `--arm bare` sinon ;
  - mesure de tâche : un `bench prepare` par bras, `bare`, `asis`, `harness`.

### 3. Jouer, à l'aveugle
Un **agent neuf par exécution**, sans mémoire de cette session. Son message contient, et rien d'autre :
- pour un skill : le chemin du kit, le chemin du dépôt, le skill à suivre, et pour un init le contenu de `owner.md` présenté comme les réponses du propriétaire. Il rend ses fichiers dans le dépôt de travail et son compte rendu ;
- pour une tâche : le chemin du dépôt et le contenu de `task.md`. Pas de kit, pas de skill : on mesure ce que les instructions du dépôt lui font faire.

Ne lui donne ni indice, ni critère de notation, ni le nom du projet type. Ne lance pas la même exécution deux fois en espérant mieux : la variance se traite à l'étape 5.

### 4. Noter et enregistrer
```bash
python3 cli/harness.py fixture check <projet> --audit <dir>/.harness/audit.json
python3 cli/harness.py fixture check <projet> --init <dir>
python3 cli/harness.py bench check <projet> <tâche> <dir>
python3 cli/harness.py bench record --kind <audit|init|task> --fixture <projet> [--task <tâche> --arm <bras>] \
    --model <le modèle évalué, tel que la session le donne> --score <note> [--ok] --run <chemin des sorties>
```
Range les sorties dans `fixtures/repos/<projet>/runs/<date>-<mesure>-blind[-<bras>]/` : ce que l'agent a écrit, son compte rendu, la sortie du noteur. Enregistre **toutes** les exécutions, les mauvaises comprises.

### 5. Ranger chaque écart dans une cause, et une seule

| Cause | À quoi on la reconnaît | Ce que tu en fais |
|---|---|---|
| **Skill** | Le texte du skill a mené là, ou n'a rien dit pour l'empêcher. Tu peux citer la phrase, ou son absence | Une correction du skill, étape 6 |
| **Noteur** | L'agent a raison et le corrigé a tort, ou trop étroit : un verdict défendable refusé, un mot-clé qui dépend de la langue | Une question au propriétaire. Tu ne touches à rien |
| **Projet** | Le projet type a un défaut : une commande cassée, un piège non planté que l'agent a trouvé | Une question au propriétaire. Un piège trouvé en plus est une bonne nouvelle |
| **Variance** | Rejouée une fois, l'exécution donne l'inverse | Tu le notes. Pas de correction sur un coup de dés |

Un écart sans cause établie reste « non expliqué » dans le rapport. C'est une réponse honnête.

### 6. Corriger les skills, dans une PR dédiée
Branche `stress/<AAAA-MM-JJ>`, jamais `main`. Un commit par leçon : `stress(<skill>): <la leçon en une phrase>`, avec dans le corps l'exécution qui l'a montrée.

Avant chaque commit, vérifie que la leçon est générale :
```bash
git diff --cached -- skills | grep -nE "^\+.*($(ls fixtures/repos | paste -sd'|'))" && echo "leçon par cœur : réécris-la"
```
Vérifie aussi qu'elle ne fait pas grossir le skill sans fin : une leçon remplace ou précise une phrase plus souvent qu'elle n'en ajoute. Un skill qui passe 150 lignes se découpe.

### 7. Mesurer la correction
- Rejoue **seulement** les exécutions en échec, sur les projets `tuning`.
- Puis joue une fois les projets `holdout` (`bench plan --role holdout`). C'est la seule mesure qui compte : si elle n'a pas bougé, la correction n'a rien appris de général ; si elle a baissé, retire la correction.
- Deux tours de correction au plus par campagne. Au-delà, tu règles le skill sur le banc.

### 8. Le rapport, format fixe
Dans la description de la PR, et en réponse au propriétaire :
- **Ce qui a été mesuré** : périmètre, nombre d'exécutions, coût réel face au coût annoncé.
- **Avant et après**, une ligne par exécution : projet, mesure, bras, note avant, note après. `python3 cli/harness.py bench report` donne le registre.
- **Les projets tenus à l'écart** : leur note avant et après, à part.
- **Les écarts, par cause**, avec la preuve de chacun.
- **Les corrections**, une ligne par commit.
- **Questions au propriétaire**, numérotées, avec le défaut proposé : tout ce qui touche au corrigé, au noteur ou à un projet type.
- **Ce qui n'est pas prouvé.**

## La campagne de génération : ce qui ne sert plus

Quand le modèle utilisé change, le propriétaire peut demander de rejouer les **tâches** sur tous leurs bras. C'est la mesure du poids mort :
- là où le bras `bare` rattrape le bras `harness`, les règles que la tâche exerce ne changent plus rien pour ce modèle : ce sont des candidates au retrait ;
- là où le bras `asis` fait moins bien que `bare`, les instructions trouvées dans le dépôt gênent.

Tu ne retires rien toi-même. Tu listes les candidates avec les deux notes, et c'est une question au propriétaire. Les skills de harness-ai sont soumis à la même mesure : une consigne de skill que plus aucune exécution ne rend utile se signale de la même façon.

Une tâche réussie sur un seul bras ne prouve rien dans un sens ni dans l'autre : une exécution est un tirage. Dis-le, et propose de rejouer avant de conclure.

## Pièges fréquents
- Lancer « juste une exécution pour voir » sans l'annoncer.
- Lire `traps.md` pour comprendre un écart sur un projet `holdout`.
- Corriger le skill pour qu'il dise le mot que le noteur cherche.
- Conclure sur une seule exécution.
- Empiler les leçons : dix corrections locales font un skill que plus personne ne lit en entier, modèle compris.
