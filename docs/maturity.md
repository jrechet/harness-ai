# Modèle de maturité

Cinq paliers, chacun gagné par des vérifications **mesurées** sur le dépôt, jamais déclarées. `harness status` les calcule et écrit `.harness/state.json` ; une interface n'a qu'à lire ce fichier. Les seuils sont des constantes de `cli/harnesslib/maturity.py`.

Un palier est atteint quand toutes ses vérifications passent et que le palier précédent est atteint. Chaque vérification qui échoue porte l'action suivante : l'état dit toujours quoi faire ensuite.

| Palier | Nom | Ce que ça veut dire | Vérifications |
|---|---|---|---|
| 0 | Rien | L'agent part de zéro à chaque session | aucune |
| 1 | Cadré | L'agent sait où il est | AGENTS.md existe · ligne « Mode » · au plus 60 lignes · CLAUDE.md est un stub `@AGENTS.md` ou absent · section Interdits |
| 2 | Bouclé | Les incidents deviennent des règles | section Maintenance · convention `rule:` documentée · marqueur de harvest de moins de 45 jours · le dernier harvest a trouvé au moins un signal réel (S1 à S4, pas S5) |
| 3 | Vérifié | Les règles obligatoires sont portées par des outils | une CI existe · au moins 50 % des règles « Vérifiée par » · au moins 50 % disent pourquoi · un audit existe sans P1 ouvert |
| 4 | Délégué | Des tâches entières reviennent propres | mode délégation · section Processus de travail · au moins un contrat référencé · PRs d'agent sans correction après coup (S2 = 0) dans le dernier harvest · test « coupe l'agent » de l'audit réussi |

## Pourquoi ces vérifications et pas d'autres

- **Palier 2 exige un signal, pas un fichier.** Un marqueur de harvest posé par harness-init ne suffit pas : il faut qu'un harvest ait trouvé quelque chose. Sinon la boucle est décorative. Les règles orphelines (S5) ne comptent pas : elles disent qu'il n'y a pas de signal, pas qu'il y en a un.
- **Palier 3 compte les règles vérifiées dans le texte**, via la mention « Vérifiée par : ». C'est une convention d'écriture, donc contournable, mais elle oblige à nommer l'outil ; et l'audit, lui, va vérifier que l'outil existe.
- **Palier 4 se mesure sur les PRs**, pas sur le mode déclaré. Une PR d'agent corrigée après coup est une règle ou un garde-fou manquant. Zéro S2 sur une fenêtre avec des PRs d'agent est la seule preuve que la délégation fonctionne.

## La vue par couche

À côté des paliers, `state.json` porte une vue par couche L1 à L4 : nombre d'éléments par étage et nombre d'éléments mal placés, tirés du dernier `.harness/audit.json`. Sans audit, une estimation grossière depuis les fichiers (contrats, outils de lint, workflows) avec l'indication de lancer harness-audit.

## Fichiers

```
<repo>/.harness/
├── audit.json     # bloc « Données machine » du dernier harness-audit
├── harvest.json   # évidences du dernier harness-harvest (sortie de `harness harvest github`)
└── state.json     # écrit par `harness status` ; schéma harness-state/1
```

Le dossier `.harness/` se versionne : l'historique de `state.json` est l'historique de la progression.

## Lancer

```bash
python3 cli/harness.py status <chemin-du-repo>
```

Pour la vue graphique et l'historique des `state.json` commités :

```bash
python3 cli/harness.py serve <chemin-du-repo>
```

Options : `--format json`, `--no-write`, `--audit`, `--harvest`, `--today` pour des sorties reproductibles.
