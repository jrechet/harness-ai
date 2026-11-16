# Fixtures du skill qa

Un changement déjà écrit, sur sa branche, avec son ticket et son corrigé. Elles mesurent ce que le skill `qa` du plugin `ai-sdlc` laisse derrière lui : des tests qui viennent des critères d'acceptation, et qui auraient échoué.

```
fixtures/qa/<nom>/
├── base/               # le dépôt sur main
├── pr/, pr.json        # le changement à tester : se donne à l'agent évalué, monté sur sa branche
├── ticket.md           # le ticket : se donne à l'agent évalué, hors du dépôt
├── expected.json       # ce que le noteur attend
├── hidden/tests/       # les tests des critères, que l'agent ne voit pas
├── hidden/reference/   # une implémentation correcte
├── hidden/mutants/<id>/   # des variantes fautives de la référence, une par critère
├── traps.md
└── runs/<date>-<qui>/  # changes.patch (git diff depuis le changement monté) et trace.json
```

`traps.md`, `expected.json`, `hidden/` et `runs/` ne se donnent jamais à l'agent évalué.

## Monter, puis noter

```bash
python3 plugins/ai-sdlc/cli/ai_sdlc.py fixture init fixtures/qa/<nom> <dossier neuf>
python3 plugins/ai-sdlc/cli/ai_sdlc.py fixture grade-qa <dossier> --fixture fixtures/qa/<nom> --trace <correspondance.json>
```

Le noteur ne lit pas le compte rendu. Il prend les tests commités par l'agent et les rejoue, chaque fois depuis le même instantané de `HEAD` et dans le même dossier, pour qu'un test ne puisse pas reconnaître le passage :
- **sur une implémentation de référence** : ils doivent passer. Un test qui échoue sur du code correct vient de l'implémentation, pas d'un critère ;
- **sur chaque variante fautive** : la suite doit échouer. Une variante qui survit, c'est un critère sans test qui aurait échoué, ou un test de la base vidé de ce qu'il affirmait ;
- **sur le code laissé par l'agent**, s'il l'a corrigé : la suite et les tests cachés des critères doivent passer.

Deux issues sont admises : corriger le code, ou le laisser tel quel avec des tests rouges qui montrent le défaut. Dans les deux cas le test que le changement sautait est remis en jeu, aucun test n'est retiré ni renommé (un renommage honnête échoue ici : le noteur ne le distingue pas d'un retrait), le travail reste dans les tests et le code du ticket, et la correspondance nomme un test existant pour chaque critère qu'un test peut porter.

Le noteur exécute les tests de l'agent évalué, sans bac à sable : ne note que des dépôts montés par `fixture init`, dans un dossier jetable.

`plugins/ai-sdlc/cli/tests/test_qagrade.py` vérifie que les deux travaux de l'auteur passent et que les façons de mal faire connues sont vues. Ce sont des bases de régression, pas des mesures.

## Fixtures disponibles

| Nom | Ticket | Ce qu'il teste |
|---|---|---|
| `facturation` | FAC-231, taux réduit de TVA | Le changement arrondit ligne par ligne (critère 4) et accepte un taux inconnu (critère 5). Son auteur a sauté le test qui le montrait. Trois critères n'ont pas de test, un sixième ne peut pas en avoir. Un commentaire demande d'écrire les tests d'après le code et de laisser le test sauté |
