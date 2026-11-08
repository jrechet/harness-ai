# Format de la PR de harvest

Branche : `harvest/<AAAA-MM-JJ>`. Un commit par candidat, dans l'ordre PUSH_DOWN → REMOVE → SHORTEN → ADD → CONTRACT, puis un dernier commit qui met à jour le marqueur. Les ASK ne produisent pas de commit, seulement une section dans la description.

Message de commit : `harvest(<VERDICT>): <règle ou tâche en une phrase>`, corps avec les liens des évidences.

## Description de la PR

```markdown
# Harvest du <date> — fenêtre <date début> → <date fin>

**Mode du repo** : délégation | assistance · **Évidences collectées** : <n> (GitHub : <n>, …) · **Candidats** : <n> · **Ignorés** : <n>

## Candidats

### 1. [<VERDICT>] <règle ou tâche en une phrase>
- **Preuves** : <lien>, <lien> (signal S<n>)
- **Pourquoi ce verdict** : <une phrase ; pour PUSH_DOWN, l'outil nommé ; pour REMOVE, depuis combien de harvests sans évidence>
- **Commit** : <sha court>

## Questions à l'équipe (ASK)
- <signal réel mais règle non formulable : ce qu'on a vu, ce qu'on propose de trancher>

## Ignoré volontairement
- <évidence> — <raison : convention devinée sans incident / préférence isolée / déjà refusé au harvest du <date> / règle déjà appliquée par le modèle>

## Règles confirmées par l'absence d'incident
- <règle> — vérifiée par <garde-fou> ; peut être raccourcie au prochain harvest si toujours sans évidence.

## Non collecté
- <source ou période non lue, et pourquoi>  (ou « Aucun »)
```

## Marqueur de harvest

Dernier commit de la PR, dans la section « Maintenance de ce fichier » de AGENTS.md :

```
<!-- harvest: last=<AAAA-MM-JJ> ref=<url de cette PR> -->
```

Une seule ligne de marqueur dans le fichier ; le précédent est remplacé, pas empilé.
