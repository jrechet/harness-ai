J'ai écrit le contrat de la première tâche à déléguer et je l'ai cité dans AGENTS.md. `status` confirme que la vérification visée est passée. Rien n'est commité.

- **Le pas** : le propriétaire a choisi la tâche « ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test ». Son contrat est maintenant dans `.claude/skills/ajouter-endpoint/SKILL.md` et cité sous une nouvelle section « Tâches déléguées » d'AGENTS.md.
- **Avant et après** : on reste au palier 1 atteint (objectif : palier 4). Le palier 4 passe de 2/5 à 3/5. La ligne qui a basculé : « Au moins un contrat de tâche existe et est référencé ».
- **Ce que ça change pour l'agent** : quand on lui confie une nouvelle route, il a un parcours écrit, des couches jusqu'à la PR. Pour une route qui modifie un solde, le contrat impose trois choses : la clé d'idempotence cherchée dans la transaction, l'en-tête `Idempotency-Replayed: true` sur un rejeu, et des tests du rejeu et du conflit. Il dit aussi ce qui ne sert pas de modèle (`fees.go`, l'exemption de `POST /accounts`).
- **Ce qui n'est pas prouvé** : `status` vérifie seulement qu'un fichier existe et qu'il est cité. Il ne dit pas que les PR d'agent sur cette tâche reviennent propres. Cette preuve viendra d'un harness-harvest sur de vraies PR d'agent (vérification « PR sans correction après coup », en attente). Il n'en existe aucune pour l'instant. Ce pas n'ajoute aucun garde-fou qui bloque.
- **Fichiers** :
  - `.claude/skills/ajouter-endpoint/SKILL.md` (créé)
  - `AGENTS.md` (section « Tâches déléguées » ajoutée, deux lignes)
- **Questions** :
  1. J'ai laissé l'en-tête `Idempotency-Replayed` absent de `POST /transfers` : le contrat demande de le signaler, pas de le corriger au passage. Défaut proposé : le traiter à part, c'est l'action 5 de l'audit.
  2. Le contrat suppose qu'un agent ne peut pas lancer `make test-integration` (le pilote pgx manque dans `go.mod`) et lui demande de l'écrire dans la PR. Défaut proposé : garder cela jusqu'à ce que l'action 6 de l'audit (tests d'intégration PostgreSQL en CI) soit faite.
- **Hors périmètre, noté pour plus tard** : la réponse du propriétaire à ma première question ajoutait trois choses à ne pas faire. Elles étaient déjà dans les Interdits d'AGENTS.md ; le contrat les reprend dans sa section « Jamais ».
- **Le pas suivant possible** : faire passer le test « coupe l'agent » de l'audit, en déplaçant dans un script ou un workflow la première étape qui n'existe que dans un prompt.