J'ai écrit le premier contrat de tâche déléguée, et la vérification visée (`L4.contracts`) est passée au vert. La forme est en place, mais rien ne prouve encore que les agents travaillent mieux.

- **Le pas** : écrire le contrat de la tâche que le propriétaire a désignée, « ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test », dans `.claude/skills/ajouter-endpoint/SKILL.md`, puis le citer dans une nouvelle section « Tâches déléguées » d'AGENTS.md. Le propriétaire a renvoyé à `docs/` pour le contenu, qui vient donc des ADR 0001, 0002 et 0003, du post-mortem du double débit et du code existant.
- **Avant et après** : on reste au palier 1 atteint, avec le palier 4 visé. Le palier 4 passe de 2/5 à 3/5. Ligne qui a basculé : `[ ] → [x] Au moins un contrat de tâche existe et est référencé`.
- **Ce que ça change pour l'agent** : quand on lui confie un ticket « nouvel endpoint », il suit une procédure :
  - il pose les couches dans l'ordre, du domaine vers le handler ;
  - il recherche la clé d'idempotence dans la transaction en copiant `Transfer` et non `OpenAccount` ;
  - il ajoute la route à `routes()` et ne touche jamais à la liste des exemptions ;
  - il traduit les erreurs en codes HTTP seulement dans `writeDomainError` ;
  - il implémente un nouveau port dans les deux adaptateurs (mémoire et PostgreSQL) ;
  - il s'arrête et demande si le ticket ne fixe pas la forme de l'API ou s'il faut une migration ;
  - il sait quand la tâche est finie.
- **Ce qui n'est pas prouvé** : `status` mesure seulement qu'un fichier existe et qu'il est cité. Aucune PR d'agent n'a encore suivi ce contrat, donc aucune preuve de fond n'existe. Elle viendra d'un harness-harvest sur de vraies PR « ajouter-endpoint » : `L4.clean_prs` reste en attente. Plusieurs points du contrat ne sont tenus que par la revue :
  - la recherche de la clé dans la transaction ;
  - l'en-tête `Idempotency-Replayed` ;
  - l'absence de flottants, puisque le job `lint` ne bloque pas.
- **Fichiers** :
  - `.claude/skills/ajouter-endpoint/SKILL.md` (nouveau) ;
  - `AGENTS.md` (+3 lignes, 44 au total, sous la limite de 60).

  Je n'ai rien commité. Ma première commande, qui combinait `cd`, `ls` et `cat`, a été refusée faute de validation possible dans cette séance ; j'ai fait les mêmes lectures avec les outils de fichiers.
- **Questions** :
  1. Le contrat impose l'en-tête `Idempotency-Replayed: true` à tout nouvel endpoint d'écriture, conformément à la règle d'AGENTS.md. Or cette règle n'est vérifiée par rien, et `POST /transfers` ne l'applique pas encore. On garde cette exigence pour les nouveaux endpoints ? Défaut proposé : oui.
  2. Je commite ces deux fichiers sur une branche et j'ouvre une PR ? Défaut proposé : oui, branche `harness/contrat-ajouter-endpoint`.
- **Le pas suivant possible** : `L4.cut_the_agent`. Il consiste à prendre, dans `.harness/audit.json`, la première étape qui n'existe que dans un prompt et à la faire porter par un script ou un job de CI.