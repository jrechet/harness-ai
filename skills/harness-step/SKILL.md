---
name: harness-step
description: Fait avancer l'instrumentation IA d'un dépôt d'un pas, et d'un seul — lit l'état mesuré par `harness status`, demande une fois jusqu'où l'utilisateur veut aller, propose le plus petit pas vers ce palier avec ce qu'il coûte et ce qu'il change, le fait après accord, montre l'avant et l'après, puis s'arrête. Utiliser quand l'utilisateur demande « où j'en suis », « c'est quoi la suite », « le prochain pas », « continue le harness », « monte d'un palier », dit qu'il veut s'arrêter à un palier, ou revient après un harness-init — même sans nommer le skill. Ne pas utiliser pour un audit complet (harness-audit) ni pour collecter les retours de review (harness-harvest) : ce skill les appelle quand le pas le demande.
---

# Harness step — un pas à la fois

Mettre en place un harness n'est pas un chantier qu'on subit d'un bloc. C'est une suite de petits pas dont chacun se voit, et dont on peut descendre quand on veut. Ce skill en fait **un** par invocation.

Trois règles qui ne se négocient pas :
- **Un palier est un endroit où l'on peut rester.** L'utilisateur dit jusqu'où il va. Au-delà, on ne propose rien, on ne suggère rien, on ne laisse rien d'à moitié posé.
- **Un pas, puis on s'arrête.** Pas de « pendant que j'y suis ». Le pas suivant est une autre invocation, décidée par l'utilisateur.
- **Chaque pas montre son avant et son après**, mesurés par le CLI, pas racontés.

## Déroulé

### 1. Mesurer
`python3 cli/harness.py status <repo>` (CLI du dépôt harness-ai). Garde la sortie : c'est l'« avant ».

### 2. L'objectif, demandé une seule fois
Si `status` dit « aucun palier visé », pose **une** question avec ce tableau, puis écris la réponse avec `python3 cli/harness.py target <n> <repo>` :

| Palier | Ce que ça apporte | Ce que ça demande |
|---|---|---|
| 1 Cadré | L'agent sait où il est et ce qu'il ne touche pas | Une demi-heure, quatre questions |
| 2 Bouclé | Les remarques de review deviennent des règles | Une habitude : écrire `rule:` en review, et quelques semaines |
| 3 Vérifié | Les règles obligatoires sont tenues par des outils, plus par du texte | Une CI, et du code de garde-fou règle par règle |
| 4 Délégué | Des tâches entières partent et reviennent propres | Des contrats de tâche, et des PR d'agent à observer |

Défaut proposé : le palier 1 pour un dépôt qui démarre, le palier courant plus un sinon. S'arrêter au palier 1 est un choix sain, pas un abandon : en assistance, il suffit souvent.

Si un palier est déjà visé, ne repose pas la question.

### 3. Objectif atteint : le dire, et s'arrêter
Si `status` dit « objectif atteint », réponds-le en une phrase. Ne propose pas le palier suivant. La seule chose qu'on rappelle : ce qui est posé s'entretient, voir « Quand il n'y a plus de pas ».

### 4. Choisir le pas
Le pas est la **première vérification en échec** du premier palier non atteint, dans l'ordre de `status`. `references/pas.md` dit, pour chaque vérification, ce qu'est le pas, ce qu'il coûte et à quoi on reconnaît qu'il est fait. Une « référence sans cible » signalée par `status` passe avant tout : c'est une promesse non tenue de ce qui est déjà posé.

Au palier 0, le pas est harness-init : passe-lui la main.

### 5. Annoncer avant de faire
En quatre lignes : ce que tu vas faire, ce que ça change pour l'agent, ce que ça touche (fichiers, CI, habitudes de l'équipe), ce qu'on verra après. Attends l'accord, sauf si la demande disait déjà d'y aller. Un pas qui demande une information que seul le propriétaire détient commence par la question.

### 6. Faire ce pas, et lui seul
Ne pose rien du pas suivant. Si le pas révèle un problème hors périmètre, note-le pour le compte rendu.

### 7. Mesurer encore
Relance `status`. Si la vérification visée n'a pas basculé, le pas n'est pas fait : dis pourquoi, ne maquille pas.

### 8. Compte rendu, puis on s'arrête
Toujours le même format :
- **Le pas** : une phrase.
- **Avant et après** : palier, vérifications passées sur le total du palier, la ligne qui a basculé.
- **Ce que ça change pour l'agent** : une phrase concrète.
- **Ce qui n'est pas prouvé** : voir « Ce que la mesure prouve ».
- **Fichiers** touchés.
- **Questions**, numérotées, avec le défaut proposé, s'il y en a.
- **Le pas suivant possible**, en une ligne, seulement s'il est dans l'objectif. Sinon : « objectif atteint ».

## Ce que la mesure prouve, et ce qu'elle ne prouve pas

`status` mesure la **forme** du harness : des fichiers, des sections, des mentions. Un palier gagné dit que le mécanisme est en place, pas que les agents travaillent mieux. Ne laisse jamais l'utilisateur confondre les deux.

La preuve du fond vient d'ailleurs, et prend du temps :
- **Les PR d'agent du dépôt.** harness-harvest compte les corrections après coup, les checks rouges, les questions répétées. C'est la tendance de ces nombres, d'un harvest à l'autre, qui dit si les agents travaillent mieux. Les paliers 2 et 4 s'appuient dessus : ils ne se gagnent pas en une séance.
- **Le garde-fou qu'on a vu mordre.** Au palier 3, un garde-fou n'est compté que s'il a été vu rouge sur une violation.

Dans le compte rendu, dis laquelle de ces preuves existe pour ce pas, ou qu'il n'y en a pas encore.

## Quand il n'y a plus de pas

Ce qui est posé vieillit : une règle reçoit un garde-fou, un contexte change, un nouveau modèle n'a plus besoin d'une consigne. Propose une **revue de pertinence** (harness-audit, section du même nom) dans deux cas seulement : le modèle utilisé par l'équipe a changé, ou six mois ont passé depuis la dernière. `python3 cli/harness.py rules <repo>` donne l'âge de chaque règle. La revue retire ; elle n'ajoute rien.

## Pièges fréquents
- Enchaîner deux pas parce que le second est petit.
- Proposer le palier suivant à quelqu'un qui a dit où il s'arrêtait.
- Annoncer un palier gagné comme une preuve que les agents travaillent mieux.
- Faire d'un pas du palier 2 ou 4 une affaire de fichiers : ces paliers se gagnent sur des PR réelles, dans le temps. Poser la section ne suffit pas, et il faut le dire.
- Créer la section « Tâches déléguées » avant le contrat qu'elle cite.
