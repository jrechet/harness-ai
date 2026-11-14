## Compte rendu — harness-step

**Le pas** : la règle `Idempotency-Key` est maintenant tenue par un test Go. C'est la seule règle dont l'incident est encore ouvert : le postmortem 2026-04 dit « un nouvel endpoint d'écriture peut encore oublier la clé : la revue est le seul contrôle ». Le test parcourt toutes les routes HTTP. Chaque route qui n'est pas en lecture (ni GET ni HEAD) doit répondre `400 idempotency_key_required` quand la clé manque. Il tourne dans le job `test`, qui bloque déjà en CI.

**Avant et après**
- Palier : 1 · Cadré, avant comme après. Objectif : 3.
- Palier 3 : 2/4 avant, 2/4 après. **La vérification visée n'a pas basculé.** Les règles tenues par un outil passent de 1/8 à 2/8, alors qu'il en faut 4/8 pour la valider. Le pas est fait pour cette règle, mais la vérification `L3.guarded` reste en échec. Il faudra encore deux règles gardées, chacune dans son propre pas.
- La ligne qui a changé : dans `harness rules`, `AGENTS.md:17` passe de « non, marquée » à « oui ».
- J'ai vu le garde-fou mordre. J'ai ajouté une fausse route `POST /accounts/{id}/credit` sans clé : le test est passé au rouge avec un message qui renvoie au postmortem. J'ai retiré la fausse route : `go vet`, `go test ./...` et `archcheck` passent.

**Ce que ça change pour l'agent** : s'il ajoute un endpoint d'écriture sans exiger `Idempotency-Key`, le job `test` le bloque en CI. Avant, seule la revue pouvait le voir.

**Ce qui n'est pas prouvé**
- `status` mesure la forme du harness, pas si les agents travaillent mieux. Aucune PR d'agent n'a encore buté sur ce garde-fou ; la preuve viendra des prochains harvests.
- Le test ne vérifie que la présence de la clé. La seconde moitié de la règle, « cherchée dans la transaction, jamais avant », reste confiée à la revue, et la règle l'écrit.
- Le test envoie un corps `{}` à chaque route. Une route qui refuse ce corps avant même de regarder la clé sortira rouge, ce qui pousse à vérifier la clé en premier. La seule route d'écriture actuelle (`POST /transfers`) passe.

**Fichiers**
- `internal/adapters/httpapi/server.go` : les routes sont désormais listées dans une seule table que le test peut parcourir. Le comportement ne change pas.
- `internal/adapters/httpapi/idempotency_guard_test.go` (nouveau) : le garde-fou, avec une liste d'exemptions dont chaque entrée doit donner sa raison. Un second test échoue si une exemption ne correspond plus à aucune route.
- `AGENTS.md` : la règle porte maintenant « Vérifiée par » et le marqueur « (non vérifiée) » est retiré. Le fichier fait toujours moins de 60 lignes.
- Rien n'est commité ni poussé : les changements sont dans la copie de travail, et j'attends ton accord pour ouvrir la PR. Je n'ai pas touché au dossier `.harness/`, qui n'est pas suivi par git.

**Points bloqués en séance** : deux commandes groupées (`ls`/`cat` du kit, `grep` dans le CLI) ont été refusées, car cette session ne peut pas valider de permission. Je les ai remplacées par des lectures directes, sans perte pour le pas.

**Questions**
1. `POST /accounts` est exempté, comme AGENTS.md le disait déjà. Cet endpoint modifie-t-il un solde au sens de la règle ? Défaut proposé : oui, il faudra l'aligner un jour puis retirer l'exemption, mais pas dans ce pas.

**Hors périmètre, noté** : le job `lint` est en `continue-on-error`, donc la règle « aucun flottant » n'a aucun garde-fou qui bloque. `internal/app/fees.go` la viole déjà.

**Le pas suivant possible** : garder une deuxième règle racontée. La moins chère est sans doute « une migration appliquée ne se modifie plus », avec un check de PR qui refuse toute modification d'un fichier existant de `migrations/`. Ce check tiendrait aussi la ligne correspondante des Interdits.