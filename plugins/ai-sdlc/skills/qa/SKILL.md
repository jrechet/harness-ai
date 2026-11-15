---
name: qa
description: Dérive les tests d'un changement à partir des critères d'acceptation du ticket, puis fait dire par un programme s'ils tiennent — aucun test désactivé, la suite qui passe plusieurs fois de suite, les lignes ajoutées exécutées, un test nommé par critère. Ne désactive, n'affaiblit et ne supprime jamais un test. Utiliser quand l'utilisateur demande de « tester » un changement ou un ticket, d'« écrire les tests », de « vérifier la couverture », de savoir si une PR « est assez testée », ou face à un test instable. Ne pas utiliser pour écrire le code du ticket (dev), pour relire une PR (review), ni pour contrôler le ticket lui-même (ticket).
---

# QA — des tests qui viennent du ticket, et des portes qui ne viennent pas de toi

Un agent écrit volontiers des tests qui passent. Ce qui manque, c'est le test qui aurait échoué : celui qui vient d'un critère d'acceptation et non du code qu'on vient d'écrire. Ce skill part du ticket, écrit ce qui manque, puis laisse quatre portes mesurées dire le résultat.

Quatre règles qui ne se négocient pas :
- **Un test ne se désactive pas, ne s'affaiblit pas, ne se supprime pas.** S'il échoue, le code ou le test a un défaut : trouve lequel. S'il est instable, c'est un constat à rapporter, pas un test à relancer jusqu'à ce qu'il passe.
- **Un test vient d'un critère, pas de l'implémentation.** Un test qui recopie ce que fait le code ne vérifie que sa propre copie.
- **Le résultat vient de la commande.** « Les tests passent » se dit avec le nombre de passages et la sortie de `qa gate`.
- **Une porte non mesurée n'est pas une porte passée.** Dis-le tel quel.

## Déroulé

### 1. Le ticket et ses critères
Récupère le texte du ticket dans un fichier hors du dépôt, puis `python3 "${CLAUDE_PLUGIN_ROOT}/cli/ai_sdlc.py" ticket check <ticket.md> . --base <base>`. S'il n'est pas prêt, ou sans critère listé, arrête-toi : c'est le travail du skill `ticket`. Numérote les critères dans l'ordre où la commande les compte.

### 2. La convention
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/ai_sdlc.py" context qa . --base <base>` rend ce que le socle et l'équipe demandent aux tests. **Code 2** : surcharge invalide, arrête-toi. Si la sortie dit que le palier requis n'est pas atteint, continue et dis-le en tête du résultat : sans CI ni garde-fous, ces portes sont un essai.

Lis dans `AGENTS.md` la commande de test, et comment le dépôt produit un rapport de couverture (lcov ou Cobertura). S'il ne sait pas en produire, n'installe rien : la porte restera « non mesurée ».

### 3. Ce qui manque
Pour chaque critère : quel test existant échouerait si le critère n'était pas tenu ? S'il y en a un, note-le. Sinon écris-le, au plus près du critère : ses valeurs, son exemple, son cas d'erreur. Lance-le et vois-le passer ; si tu le peux, vois-le échouer en retirant le changement (`git stash` de la ligne en cause, pas du test).

Un critère qu'un test ne peut pas porter (une impression visuelle, une donnée de production) ne reçoit pas un faux test : il va dans `non_couverts`, avec sa raison.

### 4. La correspondance
Écris-la dans un fichier JSON hors du dépôt :

```json
{"criteres": [{"critere": 1, "tests": ["tests/test_totaux.py::test_arrondi_au_centime"]}],
 "non_couverts": [{"critere": 3, "pourquoi": "rendu visuel, vérifié à la main par la recette"}]}
```

Un test se nomme `chemin::nom` : le chemin existe dans le dépôt, le nom se trouve dans le fichier.

### 5. Les portes
Commite les tests, produis le rapport de couverture si le dépôt le permet, puis :

`python3 "${CLAUDE_PLUGIN_ROOT}/cli/ai_sdlc.py" qa gate . --base <base> --run "<commande de test>" --coverage <rapport> --ticket <ticket.md> --trace <correspondance.json>`

| Code | Sens | Ce que tu fais |
|---|---|---|
| 0 | Les quatre portes passent | Rends la sortie |
| 1 | Une porte est en échec | Corrige la cause : le test manquant, le code, l'instabilité. Jamais la porte |
| 3 | Rien en échec, une porte non mesurée | Rends la sortie, et dis quelle porte et pourquoi |
| 2 | Refusé : fichier illisible, correspondance mal formée | Corrige l'entrée |

La commande lance la suite plusieurs fois. Une suite « instable » est un échec : cherche l'ordre des tests, l'horloge, le réseau, un état partagé.

### 6. Rendre
La sortie de `qa gate` telle quelle, puis en trois lignes au plus : les tests ajoutés, les critères laissés sans test avec leur raison, ce qui n'est pas mesuré. Les critères sans test attendent l'accord d'un humain : ne les présente pas comme réglés.

## Pièges fréquents
- **Tester le code qu'on vient de lire.** Pars de la phrase du critère, pas de la fonction.
- **Gonfler la couverture.** Un test sans affirmation exécute des lignes et ne vérifie rien : la porte passe, le défaut aussi.
- **Marquer un test `skip` « en attendant ».** La porte l'attrape, et c'est voulu.
- **Relancer jusqu'au vert.** Trois passages sur trois, ou un constat d'instabilité.
- **Installer un outil de couverture sans le demander.** Une dépendance de plus est une décision de l'équipe.
