J'ai fait un pas : AGENTS.md a maintenant une section « Processus de travail », écrite avec les réponses du propriétaire. La vérification visée est passée au vert, mais le palier atteint reste 1.

- **Le pas** : j'ai posé au propriétaire les trois questions de `L4.process` et j'ai écrit ses réponses, à la formulation près, avant « Maintenance de ce fichier ». J'ai vérifié avant que `make test` et `make arch` existent bien dans le `Makefile`.

- **Avant et après** :

  | | Palier atteint | Palier 4 — Délégué |
  |---|---|---|
  | Avant | 1 · Cadré | 1/5 |
  | Après | 1 · Cadré | 2/5 |

  La ligne qui a basculé : « Une section « Processus de travail » cadre l'agent ». Le palier 2 attend toujours son premier vrai signal de revue (`L2.signal`), ce qui ne bloque pas la montée vers le palier 4. Le palier 1 tient toujours : AGENTS.md passe de 33 à 39 lignes, la limite est 60.

- **Ce que ça change pour l'agent** : sur un ticket délégué, il sait maintenant :
  - quand demander avant d'agir : migration, contrat d'API, `deploy.yml`, ou ticket ambigu sur un montant ou un arrondi ;
  - quand il a fini : `make test` et `make arch` verts, un test qui couvre le changement, et le pourquoi en deux lignes dans la PR ;
  - quoi faire d'une CI rouge ou d'un test instable.

- **Ce qui n'est pas prouvé** : `status` vérifie seulement que la section existe, pas que les agents la respectent. Il n'y a pas encore de preuve sur le fond. Elle viendra d'un harness-harvest sur de vraies PR d'agent : moins de corrections après coup, et des questions posées aux bons moments. Rien de ce texte n'est tenu par un outil, c'est du jugement écrit.

- **Fichiers** : `AGENTS.md` seulement, non commité.
  - J'ai laissé tel quel `.harness/` (`config.json`, `state.json`), qui était déjà non suivi avant mon passage.
  - Ma première commande shell (lister le kit) a été refusée faute d'approbation possible. J'ai lu les mêmes fichiers autrement, sans effet sur le pas.

- **Questions** :
  1. Le propriétaire a donné le critère de fini avec `make test`, qui ne lance pas `go vet`. Le tableau en tête d'AGENTS.md demande pourtant `go vet ./... && go test ./...`. Faut-il ajouter `go vet` à la cible `test` du `Makefile` ? Défaut proposé : oui, pour que les deux disent la même chose. C'est hors de ce pas, je n'y ai pas touché.
  2. Le critère de fini ne mentionne ni `make test-integration` quand on touche `internal/adapters/postgres` (ces tests ne tournent pas en CI), ni le job `migrations`. Faut-il les ajouter ? Défaut proposé : les ajouter au critère de fini.

- **Le pas suivant possible** : `L4.contracts`. Il faut demander au propriétaire la première tâche répétitive à confier, puis écrire son contrat `.claude/skills/<tâche>/SKILL.md` et le citer dans AGENTS.md.